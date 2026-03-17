"""
Step Functions orchestration service for pre-flight pipeline.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from config import settings
from services.dynamo_repositories import get_analysis_repo
from services.pipeline_service import run_preflight_pipeline

logger = logging.getLogger(__name__)


class PipelineOrchestrationService:
    def __init__(self) -> None:
        self.analysis_repo = get_analysis_repo()
        self.sfn = None
        if settings.enable_stepfunctions_pipeline and settings.stepfunctions_preflight_arn:
            try:
                import boto3

                kwargs: Dict[str, Any] = {"region_name": settings.aws_region}
                self.sfn = boto3.client("stepfunctions", **kwargs)
            except Exception as exc:
                logger.warning("Step Functions client init failed: %s", exc)

    async def start_preflight(self, payload: Dict[str, Any], user_id: str = "anonymous") -> Dict[str, Any]:
        submitted = self.analysis_repo.create_analysis(
            {
                "user_id": user_id,
                "status": "SUBMITTED",
                "request": payload,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        analysis_id = submitted["analysis_id"]

        if self.sfn and settings.stepfunctions_preflight_arn:
            execution_name = analysis_id.replace("_", "-")[:80]
            execution_input = {**payload, "analysis_id": analysis_id, "user_id": user_id}
            result = self.sfn.start_execution(
                stateMachineArn=settings.stepfunctions_preflight_arn,
                name=execution_name,
                input=json.dumps(execution_input),
            )
            self.analysis_repo.create_analysis(
                {
                    "analysis_id": analysis_id,
                    "user_id": user_id,
                    "status": "RUNNING",
                    "execution_arn": result["executionArn"],
                    "request": payload,
                    "created_at": submitted["created_at"],
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            return {
                "analysis_id": analysis_id,
                "execution_arn": result["executionArn"],
                "status": "RUNNING",
                "orchestrator": "stepfunctions",
            }

        # Local fallback to preserve functionality in non-deployed environments.
        report = await run_preflight_pipeline(**payload, user_id=user_id)
        final = self.analysis_repo.create_analysis(
            {
                "analysis_id": analysis_id,
                "user_id": user_id,
                "status": "SUCCEEDED",
                "request": payload,
                "result": report,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )
        return {
            "analysis_id": final["analysis_id"],
            "execution_arn": None,
            "status": final["status"],
            "orchestrator": "local",
        }

    def get_status(self, analysis_id: str) -> Dict[str, Any]:
        row = self.analysis_repo.get_analysis(analysis_id)
        if not row:
            return {"analysis_id": analysis_id, "status": "NOT_FOUND"}
        execution_arn = row.get("execution_arn")
        status = row.get("status", "UNKNOWN")
        if self.sfn and execution_arn:
            desc = self.sfn.describe_execution(executionArn=execution_arn)
            status = desc["status"]
            if status in {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}:
                row["status"] = status
                row["updated_at"] = datetime.utcnow().isoformat()
                if status == "SUCCEEDED" and desc.get("output"):
                    try:
                        row["result"] = json.loads(desc["output"])
                    except Exception:
                        row["result"] = {"raw_output": desc["output"]}
                if status != "SUCCEEDED":
                    row["error"] = desc.get("cause") or desc.get("error")
                self.analysis_repo.create_analysis(row)
        return {"analysis_id": analysis_id, "status": status, "execution_arn": execution_arn}

    def get_result(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        return self.analysis_repo.get_analysis(analysis_id)


_svc: Optional[PipelineOrchestrationService] = None


def get_pipeline_orchestration_service() -> PipelineOrchestrationService:
    global _svc
    if _svc is None:
        _svc = PipelineOrchestrationService()
    return _svc
