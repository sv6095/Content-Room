"""
DynamoDB repositories for Content Room.

This module centralizes all table access used by API routers.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from boto3.dynamodb.conditions import Attr, Key

from config import settings

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_epoch_seconds(days: int = 1) -> int:
    return int(time.time()) + (days * 24 * 60 * 60)


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class DynamoRepositoryError(Exception):
    """Raised when a DynamoDB operation fails."""


class DynamoClient:
    def __init__(self) -> None:
        import boto3

        kwargs: Dict[str, Any] = {"region_name": os.environ.get("AWS_REGION", "ap-south-1")}

        self.resource = boto3.resource("dynamodb", **kwargs)
        self.client = self.resource.meta.client

    def table(self, table_name: str):
        return self.resource.Table(table_name)


class UsersRepository:
    def __init__(self, ddb: DynamoClient):
        self.table = ddb.table(settings.users_table_name)

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        res = self.table.get_item(Key={"user_id": user_id})
        return res.get("Item")

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            res = self.table.query(
                IndexName=settings.users_email_index_name,
                KeyConditionExpression=Key("email").eq(email),
                Limit=1,
            )
            items = res.get("Items", [])
            return items[0] if items else None
        except Exception:
            # Fallback for environments without EmailIndex.
            res = self.table.scan(
                FilterExpression=Attr("email").eq(email),
                Limit=1,
            )
            items = res.get("Items", [])
            return items[0] if items else None

    def create_user(self, name: str, email: str, password_hash: str) -> Dict[str, Any]:
        now = utc_now_iso()
        item = {
            "user_id": _gen_id("usr"),
            "name": name,
            "email": email.lower(),
            "password_hash": password_hash,
            "is_active": True,
            "is_verified": False,
            "preferred_language": "en",
            "created_at": now,
            "updated_at": now,
        }
        self.table.put_item(Item=item)
        return item


class ContentRepository:
    def __init__(self, ddb: DynamoClient):
        self.table = ddb.table(settings.content_table_name)
        self.user_index = settings.content_user_index_name

    def create_content(self, item: Dict[str, Any]) -> Dict[str, Any]:
        now = utc_now_iso()
        payload = {
            "content_id": item.get("content_id") or _gen_id("cnt"),
            "user_id": item["user_id"],
            "record_type": item.get("record_type", "content"),
            "status": item.get("status", "draft"),
            "created_at": item.get("created_at", now),
            "updated_at": item.get("updated_at", now),
            **item,
        }
        self.table.put_item(Item=payload)
        return payload

    def update_content(self, content_id: str, updates: Dict[str, Any]) -> None:
        updates = {**updates, "updated_at": utc_now_iso()}
        expr_parts = []
        values: Dict[str, Any] = {}
        names: Dict[str, str] = {}
        idx = 0
        for key, value in updates.items():
            idx += 1
            k = f"#k{idx}"
            v = f":v{idx}"
            names[k] = key
            values[v] = value
            expr_parts.append(f"{k} = {v}")

        self.table.update_item(
            Key={"content_id": content_id},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )

    def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        res = self.table.get_item(Key={"content_id": content_id})
        return res.get("Item")

    def delete_content(self, content_id: str) -> None:
        self.table.delete_item(Key={"content_id": content_id})

    def list_for_user(
        self,
        user_id: str,
        record_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        items = self._query_user_items(user_id)
        if record_type:
            items = [i for i in items if i.get("record_type") == record_type]
        if status:
            items = [i for i in items if i.get("status") == status]
        items.sort(key=lambda i: i.get("updated_at", i.get("created_at", "")), reverse=True)
        return items

    def _query_user_items(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            res = self.table.query(
                IndexName=self.user_index,
                KeyConditionExpression=Key("user_id").eq(user_id),
            )
            return res.get("Items", [])
        except Exception:
            # Fallback if index SK differs from expected config.
            res = self.table.scan(
                FilterExpression=Attr("user_id").eq(user_id),
            )
            return res.get("Items", [])


class AnalysisRepository:
    def __init__(self, ddb: DynamoClient):
        self.table = ddb.table(settings.analysis_table_name)
        self.user_index = settings.analysis_user_index_name

    def create_analysis(self, item: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "analysis_id": item.get("analysis_id") or _gen_id("ana"),
            "created_at": item.get("created_at") or utc_now_iso(),
            **item,
        }
        self.table.put_item(Item=payload)
        return payload

    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        res = self.table.get_item(Key={"analysis_id": analysis_id})
        return res.get("Item")

    def list_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            res = self.table.query(
                IndexName=self.user_index,
                KeyConditionExpression=Key("user_id").eq(user_id),
            )
            return res.get("Items", [])
        except Exception:
            res = self.table.scan(FilterExpression=Attr("user_id").eq(user_id))
            return res.get("Items", [])


class AICacheRepository:
    def __init__(self, ddb: DynamoClient):
        self.table = ddb.table(settings.ai_cache_table_name)
        self.key_name = settings.ai_cache_key_attr

    def _hash(self, prompt: str, model: str) -> str:
        return hashlib.sha256(f"{model}|{prompt}".encode("utf-8")).hexdigest()

    def get(self, prompt: str, model: str) -> Optional[Dict[str, Any]]:
        key = self._hash(prompt, model)
        res = self.table.get_item(Key={self.key_name: key})
        return res.get("Item")

    def put(self, prompt: str, model: str, response: str, ttl_days: int = 7) -> Dict[str, Any]:
        key = self._hash(prompt, model)
        item = {
            self.key_name: key,
            "prompt_hash": key,
            "cache_key": key,
            "model": model,
            "response": response,
            "created_at": utc_now_iso(),
            "ttl": to_epoch_seconds(ttl_days),
        }
        self.table.put_item(Item=item)
        return item


class ModerationCacheRepository:
    def __init__(self, ddb: DynamoClient):
        self.table = ddb.table(settings.moderation_cache_table_name)
        self.key_name = settings.moderation_cache_key_attr

    def hash_content(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def get(self, content_hash: str) -> Optional[Dict[str, Any]]:
        res = self.table.get_item(Key={self.key_name: content_hash})
        return res.get("Item")

    def put(self, content_hash: str, payload: Dict[str, Any], ttl_days: int = 2) -> Dict[str, Any]:
        item = {
            self.key_name: content_hash,
            "image_hash": content_hash,
            "content_hash": content_hash,
            "created_at": utc_now_iso(),
            "ttl": to_epoch_seconds(ttl_days),
            **payload,
        }
        self.table.put_item(Item=item)
        return item


_ddb_client: Optional[DynamoClient] = None
_users_repo: Optional[UsersRepository] = None
_content_repo: Optional[ContentRepository] = None
_analysis_repo: Optional[AnalysisRepository] = None
_ai_cache_repo: Optional[AICacheRepository] = None
_mod_cache_repo: Optional[ModerationCacheRepository] = None


def get_ddb_client() -> DynamoClient:
    global _ddb_client
    if _ddb_client is None:
        _ddb_client = DynamoClient()
    return _ddb_client


def get_users_repo() -> UsersRepository:
    global _users_repo
    if _users_repo is None:
        _users_repo = UsersRepository(get_ddb_client())
    return _users_repo


def get_content_repo() -> ContentRepository:
    global _content_repo
    if _content_repo is None:
        _content_repo = ContentRepository(get_ddb_client())
    return _content_repo


def get_analysis_repo() -> AnalysisRepository:
    global _analysis_repo
    if _analysis_repo is None:
        _analysis_repo = AnalysisRepository(get_ddb_client())
    return _analysis_repo


def get_ai_cache_repo() -> AICacheRepository:
    global _ai_cache_repo
    if _ai_cache_repo is None:
        _ai_cache_repo = AICacheRepository(get_ddb_client())
    return _ai_cache_repo


def get_moderation_cache_repo() -> ModerationCacheRepository:
    global _mod_cache_repo
    if _mod_cache_repo is None:
        _mod_cache_repo = ModerationCacheRepository(get_ddb_client())
    return _mod_cache_repo
