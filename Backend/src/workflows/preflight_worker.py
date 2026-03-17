"""
Lambda worker for Step Functions pre-flight tasks.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import boto3

from config import settings
from services.dynamo_repositories import get_analysis_repo
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

rekognition = boto3.client("rekognition", region_name=settings.aws_region)
comprehend = boto3.client("comprehend", region_name=settings.aws_region)
translate = boto3.client("translate", region_name=settings.aws_region)
transcribe = boto3.client("transcribe", region_name=settings.aws_region)


def _bedrock_task(event: Dict[str, Any]) -> Dict[str, Any]:
    llm = get_llm_service()
    content = event.get("content", "")
    user_id = event.get("user_id")
    prompt = (
        "Run AntiCancelShield, ShadowbanPredictor, and AssetSpinoffs analysis.\n"
        "Return strict JSON with keys anti_cancel, shadowban, assets.\n"
        f"Content:\n{content}"
    )
    result = _run_async(
        llm.generate(
            prompt,
            task="stepfunctions_preflight",
            max_tokens=800,
            user_id=user_id,
        )
    )
    parsed = {"raw": result.get("text", "")}
    try:
        parsed = json.loads(result.get("text", "{}"))
    except Exception:
        pass
    return {"bedrock": parsed, "provider": result.get("provider")}


def _rekognition_task(event: Dict[str, Any]) -> Dict[str, Any]:
    image_bytes_b64 = event.get("image_bytes_b64")
    if not image_bytes_b64:
        return {"rekognition": {"skipped": True}}
    import base64

    image_bytes = base64.b64decode(image_bytes_b64)
    moderation_labels = rekognition.detect_moderation_labels(
        Image={"Bytes": image_bytes},
        MinConfidence=50.0,
    ).get("ModerationLabels", [])
    return {"rekognition": {"moderation_labels": moderation_labels}}


def _comprehend_task(event: Dict[str, Any]) -> Dict[str, Any]:
    text = event.get("content", "")
    if not text.strip():
        return {"comprehend": {"skipped": True}}
    sentiment = comprehend.detect_sentiment(Text=text, LanguageCode="en")
    entities = comprehend.detect_entities(Text=text, LanguageCode="en")
    key_phrases = comprehend.detect_key_phrases(Text=text, LanguageCode="en")
    return {
        "comprehend": {
            "sentiment": sentiment,
            "entities": entities.get("Entities", []),
            "key_phrases": key_phrases.get("KeyPhrases", []),
        }
    }


def _translate_task(event: Dict[str, Any]) -> Dict[str, Any]:
    text = event.get("content", "")
    target_language = event.get("target_language", "en")
    result = translate.translate_text(
        Text=text,
        SourceLanguageCode="auto",
        TargetLanguageCode=target_language,
    )
    return {
        "translate": {
            "translated_text": result.get("TranslatedText"),
            "target_language": target_language,
        }
    }


def _transcribe_start_task(event: Dict[str, Any]) -> Dict[str, Any]:
    media_uri = event.get("media_uri")
    if not media_uri:
        return {"transcribe": {"skipped": True}}
    import uuid

    job_name = f"content-room-{uuid.uuid4().hex[:20]}"
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": media_uri},
        MediaFormat=event.get("media_format", "mp4"),
        LanguageCode=event.get("language_code", "en-US"),
    )
    return {"transcribe": {"job_name": job_name, "status": "IN_PROGRESS"}}


def _transcribe_get_task(event: Dict[str, Any]) -> Dict[str, Any]:
    transcribe_ctx = event.get("transcribe", {})
    job_name = transcribe_ctx.get("job_name")
    if not job_name:
        return {"transcribe": {"skipped": True}}
    resp = transcribe.get_transcription_job(TranscriptionJobName=job_name)
    job = resp.get("TranscriptionJob", {})
    return {"transcribe": {"job_name": job_name, "status": job.get("TranscriptionJobStatus"), "job": job}}


def _aggregate_task(event: Dict[str, Any]) -> Dict[str, Any]:
    # Event is expected to contain outputs from parallel branches.
    analysis_id = event["analysis_id"]
    user_id = event.get("user_id", "anonymous")
    aggregate = {
        "analysis_id": analysis_id,
        "user_id": user_id,
        "status": "SUCCEEDED",
        "result": {
            "bedrock": event.get("bedrock"),
            "rekognition": event.get("rekognition"),
            "comprehend": event.get("comprehend"),
            "translate": event.get("translate"),
            "transcribe": event.get("transcribe"),
        },
        "updated_at": datetime.utcnow().isoformat(),
    }
    get_analysis_repo().create_analysis(aggregate)
    return aggregate


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    task = event.get("task")
    if task == "bedrock":
        return _bedrock_task(event)
    if task == "rekognition":
        return _rekognition_task(event)
    if task == "comprehend":
        return _comprehend_task(event)
    if task == "translate":
        return _translate_task(event)
    if task == "transcribe_start":
        return _transcribe_start_task(event)
    if task == "transcribe_get":
        return _transcribe_get_task(event)
    if task == "aggregate":
        return _aggregate_task(event)
    raise ValueError(f"Unsupported task: {task}")


def _run_async(coro):
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
