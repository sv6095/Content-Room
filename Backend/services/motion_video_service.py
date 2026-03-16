"""
Motion & Video production service for Creator Studio.

Provides executable integrations for:
- AWS Elemental MediaConvert (transcoding jobs)
- Amazon Nova Reel (text-to-video async generation)
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from config import settings

logger = logging.getLogger(__name__)


class MotionVideoError(Exception):
    """Base exception for motion/video processing errors."""
    pass


class MotionVideoService:
    """AWS MediaConvert and Nova Reel orchestration service."""

    def __init__(self):
        self.mediaconvert_client = None
        self.bedrock_runtime_client = None

        if settings.aws_configured and settings.use_aws_mediaconvert:
            try:
                import boto3
                endpoint_url = settings.mediaconvert_endpoint or None
                if not endpoint_url:
                    base_mc = boto3.client("mediaconvert", region_name=settings.aws_region)
                    endpoints = base_mc.describe_endpoints(MaxResults=1).get("Endpoints", [])
                    endpoint_url = endpoints[0]["Url"] if endpoints else None
                if endpoint_url:
                    self.mediaconvert_client = boto3.client(
                        "mediaconvert",
                        region_name=settings.aws_region,
                        endpoint_url=endpoint_url,
                    )
                    logger.info("MediaConvert client initialized")
            except Exception as e:
                logger.warning(f"MediaConvert init failed: {e}")

        if settings.aws_configured and settings.use_aws_nova_reel:
            try:
                import boto3
                self.bedrock_runtime_client = boto3.client(
                    "bedrock-runtime",
                    region_name="us-east-1",
                )
                logger.info("Bedrock runtime client initialized for Nova Reel")
            except Exception as e:
                logger.warning(f"Nova Reel init failed: {e}")

    def _resolve_output_bucket(self) -> str:
        bucket = settings.mediaconvert_output_bucket or settings.s3_bucket_name
        if not bucket:
            raise MotionVideoError("Output S3 bucket is not configured")
        return bucket

    async def start_mediaconvert_job(
        self,
        input_s3_uri: str,
        output_prefix: str = "processed/video",
    ) -> Dict[str, Any]:
        if not self.mediaconvert_client:
            raise MotionVideoError("MediaConvert is not configured")
        if not settings.mediaconvert_role_arn:
            raise MotionVideoError("MEDIACONVERT_ROLE_ARN is required")

        output_bucket = self._resolve_output_bucket()
        out_uri = f"s3://{output_bucket}/{output_prefix}/{uuid.uuid4().hex}/"

        try:
            response = self.mediaconvert_client.create_job(
                Role=settings.mediaconvert_role_arn,
                Settings={
                    "Inputs": [
                        {
                            "FileInput": input_s3_uri,
                        }
                    ],
                    "OutputGroups": [
                        {
                            "Name": "File Group",
                            "OutputGroupSettings": {
                                "Type": "FILE_GROUP_SETTINGS",
                                "FileGroupSettings": {
                                    "Destination": out_uri,
                                },
                            },
                            "Outputs": [
                                {
                                    "ContainerSettings": {"Container": "MP4"},
                                    "VideoDescription": {
                                        "CodecSettings": {
                                            "Codec": "H_264",
                                            "H264Settings": {
                                                "RateControlMode": "QVBR",
                                                "QvbrSettings": {"QvbrQualityLevel": 7},
                                            },
                                        }
                                    },
                                    "AudioDescriptions": [
                                        {
                                            "CodecSettings": {
                                                "Codec": "AAC",
                                                "AacSettings": {
                                                    "Bitrate": 96000,
                                                    "CodingMode": "CODING_MODE_2_0",
                                                    "SampleRate": 48000,
                                                },
                                            }
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
                UserMetadata={
                    "source": "creator_studio",
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            job = response.get("Job", {})
            return {
                "job_id": job.get("Id"),
                "status": job.get("Status", "SUBMITTED"),
                "input_s3_uri": input_s3_uri,
                "output_s3_uri": out_uri,
                "service": "mediaconvert",
            }
        except Exception as e:
            logger.error(f"MediaConvert create_job failed: {e}")
            raise MotionVideoError(str(e))

    def get_mediaconvert_job(self, job_id: str) -> Dict[str, Any]:
        if not self.mediaconvert_client:
            raise MotionVideoError("MediaConvert is not configured")
        try:
            response = self.mediaconvert_client.get_job(Id=job_id)
            job = response.get("Job", {})
            return {
                "job_id": job.get("Id"),
                "status": job.get("Status"),
                "error_message": job.get("ErrorMessage"),
                "output_group_details": job.get("OutputGroupDetails", []),
                "service": "mediaconvert",
            }
        except Exception as e:
            logger.error(f"MediaConvert get_job failed: {e}")
            raise MotionVideoError(str(e))

    async def start_nova_reel_job(
        self,
        prompt: str,
        duration_seconds: int = 6,
        aspect_ratio: str = "16:9",
    ) -> Dict[str, Any]:
        if not self.bedrock_runtime_client:
            raise MotionVideoError("Nova Reel is not configured")

        output_s3_uri = settings.nova_reel_output_s3_uri
        if not output_s3_uri:
            bucket = self._resolve_output_bucket()
            output_s3_uri = f"s3://{bucket}/generated/nova-reel/{uuid.uuid4().hex}/"

        duration_seconds = max(3, min(duration_seconds, 30))
        model_id = settings.nova_reel_model_id

        payload = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {
                "text": prompt,
            },
            "videoGenerationConfig": {
                "durationSeconds": duration_seconds,
                "aspectRatio": aspect_ratio,
            },
        }

        try:
            response = self.bedrock_runtime_client.start_async_invoke(
                modelId=model_id,
                modelInput=payload,
                outputDataConfig={"s3OutputDataConfig": {"s3Uri": output_s3_uri}},
                clientRequestToken=uuid.uuid4().hex,
            )
            return {
                "invocation_arn": response.get("invocationArn"),
                "status": response.get("status", "IN_PROGRESS"),
                "output_s3_uri": output_s3_uri,
                "model_id": model_id,
                "service": "nova_reel",
            }
        except Exception as e:
            logger.error(f"Nova Reel start_async_invoke failed: {e}")
            raise MotionVideoError(str(e))

    def get_nova_reel_status(self, invocation_arn: str) -> Dict[str, Any]:
        if not self.bedrock_runtime_client:
            raise MotionVideoError("Nova Reel is not configured")
        try:
            response = self.bedrock_runtime_client.get_async_invoke(
                invocationArn=invocation_arn
            )
            return {
                "invocation_arn": response.get("invocationArn"),
                "status": response.get("status"),
                "failure_message": response.get("failureMessage"),
                "output_data_config": response.get("outputDataConfig"),
                "service": "nova_reel",
            }
        except Exception as e:
            logger.error(f"Nova Reel get_async_invoke failed: {e}")
            raise MotionVideoError(str(e))


_motion_video_service: Optional[MotionVideoService] = None


def get_motion_video_service() -> MotionVideoService:
    """Get or create singleton motion/video service."""
    global _motion_video_service
    if _motion_video_service is None:
        _motion_video_service = MotionVideoService()
    return _motion_video_service

