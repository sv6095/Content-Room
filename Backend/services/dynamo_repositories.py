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
from decimal import Decimal
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


def _to_dynamodb_safe(value: Any) -> Any:
    """
    Convert Python values to DynamoDB-safe structures.
    DynamoDB does not accept float; use Decimal recursively.
    """
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_dynamodb_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_safe(v) for v in value]
    return value


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
        normalized_email = email.strip().lower()
        try:
            res = self.table.query(
                IndexName=settings.users_email_index_name,
                KeyConditionExpression=Key("email").eq(normalized_email),
                Limit=1,
            )
            items = res.get("Items", [])
            return items[0] if items else None
        except Exception:
            # Fallback for environments without EmailIndex.
            # IMPORTANT: Do not use Limit=1 with filtered scan; Dynamo applies
            # limit before filter, which can miss valid matches.
            scan_kwargs: Dict[str, Any] = {
                "FilterExpression": Attr("email").eq(normalized_email),
            }
            while True:
                res = self.table.scan(**scan_kwargs)
                items = res.get("Items", [])
                if items:
                    return items[0]
                last_key = res.get("LastEvaluatedKey")
                if not last_key:
                    break
                scan_kwargs["ExclusiveStartKey"] = last_key
            return None

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

    def get_llm_usage(self, user_id: str) -> Dict[str, Any]:
        item = self.get_by_id(user_id) or {}
        return {
            "llm_total_cost_usd": float(item.get("llm_total_cost_usd", 0.0)),
            "llm_call_count": int(item.get("llm_call_count", 0)),
            "llm_input_tokens_est": int(item.get("llm_input_tokens_est", 0)),
            "llm_output_tokens_est": int(item.get("llm_output_tokens_est", 0)),
        }

    def increment_llm_usage(
        self,
        user_id: str,
        cost_usd: float,
        input_tokens_est: int,
        output_tokens_est: int,
    ) -> None:
        self.table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=(
                "SET llm_total_cost_usd = if_not_exists(llm_total_cost_usd, :zero) + :cost, "
                "llm_call_count = if_not_exists(llm_call_count, :zero_int) + :one, "
                "llm_input_tokens_est = if_not_exists(llm_input_tokens_est, :zero_int) + :in_tokens, "
                "llm_output_tokens_est = if_not_exists(llm_output_tokens_est, :zero_int) + :out_tokens, "
                "updated_at = :now"
            ),
            ExpressionAttributeValues={
                ":zero": Decimal(str(cost_usd)),
                ":cost": Decimal(str(cost_usd)),
                ":zero_int": 0,
                ":one": 1,
                ":in_tokens": int(input_tokens_est),
                ":out_tokens": int(output_tokens_est),
                ":now": utc_now_iso(),
            },
        )

    def consume_high_cost_nova_usage_once(self, user_id: str) -> bool:
        """
        Atomically consume one-time high-cost Nova usage for a user.

        Returns:
            True if usage consumed successfully.
            False if the user has already consumed their one-time quota.
        """
        try:
            self.table.update_item(
                Key={"user_id": user_id},
                UpdateExpression=(
                    "SET high_cost_nova_usage_count = if_not_exists(high_cost_nova_usage_count, :zero) + :inc, "
                    "updated_at = :now, high_cost_nova_used_at = :now"
                ),
                ConditionExpression=(
                    "attribute_not_exists(high_cost_nova_usage_count) OR high_cost_nova_usage_count < :limit"
                ),
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":inc": 1,
                    ":limit": 1,
                    ":now": utc_now_iso(),
                },
            )
            return True
        except Exception as e:
            # ConditionalCheckFailedException -> quota already consumed.
            if e.__class__.__name__ == "ConditionalCheckFailedException":
                return False
            error_code = None
            response = getattr(e, "response", None)
            if isinstance(response, dict):
                error_code = response.get("Error", {}).get("Code")
            if error_code == "ConditionalCheckFailedException":
                return False
            raise

    def consume_feature_usage(self, user_id: str, feature: str, limit: int = 3) -> bool:
        """
        Atomically consume a feature usage with configurable per-user limit.

        Example feature values:
        - image_generation
        - video_generation
        - voice_generation

        Returns:
            True if usage consumed successfully.
            False if user already reached the limit.
        """
        safe_feature = "".join(ch for ch in feature if ch.isalnum() or ch == "_").strip("_")
        if not safe_feature:
            raise ValueError("Invalid feature key")

        count_attr = f"{safe_feature}_usage_count"
        used_at_attr = f"{safe_feature}_used_at"
        try:
            self.table.update_item(
                Key={"user_id": user_id},
                UpdateExpression=(
                    "SET #count = if_not_exists(#count, :zero) + :inc, "
                    "#used_at = :now, updated_at = :now"
                ),
                ConditionExpression=(
                    "attribute_not_exists(#count) OR #count < :limit"
                ),
                ExpressionAttributeNames={
                    "#count": count_attr,
                    "#used_at": used_at_attr,
                },
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":inc": 1,
                    ":limit": limit,
                    ":now": utc_now_iso(),
                },
            )
            return True
        except Exception as e:
            if e.__class__.__name__ == "ConditionalCheckFailedException":
                return False
            response = getattr(e, "response", None)
            if isinstance(response, dict):
                code = response.get("Error", {}).get("Code")
                if code == "ConditionalCheckFailedException":
                    return False
            raise


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
        safe_payload = _to_dynamodb_safe(payload)
        self.table.put_item(Item=safe_payload)
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

    def get_global_llm_usage(self) -> Dict[str, Any]:
        analysis_id = "global_llm_usage"
        item = self.get_analysis(analysis_id) or {}
        return {
            "llm_total_cost_usd": float(item.get("llm_total_cost_usd", 0.0)),
            "llm_call_count": int(item.get("llm_call_count", 0)),
            "llm_input_tokens_est": int(item.get("llm_input_tokens_est", 0)),
            "llm_output_tokens_est": int(item.get("llm_output_tokens_est", 0)),
            "analysis_id": analysis_id,
        }

    def increment_global_llm_usage(
        self,
        cost_usd: float,
        input_tokens_est: int,
        output_tokens_est: int,
    ) -> None:
        self.table.update_item(
            Key={"analysis_id": "global_llm_usage"},
            UpdateExpression=(
                "SET llm_total_cost_usd = if_not_exists(llm_total_cost_usd, :zero) + :cost, "
                "llm_call_count = if_not_exists(llm_call_count, :zero_int) + :one, "
                "llm_input_tokens_est = if_not_exists(llm_input_tokens_est, :zero_int) + :in_tokens, "
                "llm_output_tokens_est = if_not_exists(llm_output_tokens_est, :zero_int) + :out_tokens, "
                "created_at = if_not_exists(created_at, :now), "
                "updated_at = :now, "
                "record_type = if_not_exists(record_type, :record_type)"
            ),
            ExpressionAttributeValues={
                ":zero": Decimal(str(cost_usd)),
                ":cost": Decimal(str(cost_usd)),
                ":zero_int": 0,
                ":one": 1,
                ":in_tokens": int(input_tokens_est),
                ":out_tokens": int(output_tokens_est),
                ":now": utc_now_iso(),
                ":record_type": "llm_usage",
            },
        )


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
