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
from urllib.parse import urlparse

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
        self.s3_client = None

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
                self.s3_client = boto3.client("s3", region_name=settings.aws_region)
                logger.info("Bedrock runtime client initialized for Nova Reel")
            except Exception as e:
                logger.warning(f"Nova Reel init failed: {e}")

    @staticmethod
    def _split_s3_uri(s3_uri: str) -> tuple[Optional[str], Optional[str]]:
        if not s3_uri or not s3_uri.startswith("s3://"):
            return None, None
        no_scheme = s3_uri[5:]
        slash_idx = no_scheme.find("/")
        if slash_idx == -1:
            return no_scheme, ""
        bucket = no_scheme[:slash_idx]
        key = no_scheme[slash_idx + 1 :]
        return bucket, key

    @staticmethod
    def _canonicalize_s3_uri(value: Optional[str]) -> Optional[str]:
        if not value or not isinstance(value, str):
            return value
        raw = value.strip()
        if not raw:
            return raw
        if raw.startswith("s3://"):
            return raw
        if not raw.startswith("http"):
            return raw

        try:
            parsed = urlparse(raw)
            host = (parsed.netloc or "").strip().lower()
            path = (parsed.path or "").lstrip("/")
            if not host or not path:
                return raw

            # Virtual-hosted-style:
            # https://bucket.s3.<region>.amazonaws.com/key
            if ".s3." in host:
                bucket = host.split(".s3.", 1)[0]
                return f"s3://{bucket}/{path}" if bucket else raw

            # Path-style:
            # https://s3.<region>.amazonaws.com/bucket/key
            if host.startswith("s3.") or host.startswith("s3-"):
                segments = path.split("/", 1)
                if len(segments) == 2 and segments[0] and segments[1]:
                    return f"s3://{segments[0]}/{segments[1]}"
        except Exception:
            return raw

        return raw

    def _resolve_generated_video_from_prefix(self, s3_uri: str) -> Optional[str]:
        if not self.s3_client:
            return None
        bucket, key = self._split_s3_uri(s3_uri)
        if not bucket:
            return None
        prefix = key or ""
        try:
            res = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=50,
            )
            contents = res.get("Contents", []) or []
            mp4_keys = [
                obj.get("Key")
                for obj in contents
                if isinstance(obj.get("Key"), str) and obj.get("Key", "").lower().endswith(".mp4")
            ]
            if not mp4_keys:
                return None
            mp4_keys.sort(reverse=True)
            return f"s3://{bucket}/{mp4_keys[0]}"
        except Exception as e:
            logger.warning("Failed to resolve S3 output object from prefix '%s': %s", s3_uri, e)
            return None

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
            output_s3_uri: Optional[str] = None
            for group in job.get("OutputGroupDetails", []) or []:
                for detail in group.get("OutputDetails", []) or []:
                    for path in detail.get("OutputFilePaths", []) or []:
                        if isinstance(path, str) and path:
                            output_s3_uri = path
                            if path.lower().endswith(".mp4"):
                                break
                    if output_s3_uri and output_s3_uri.lower().endswith(".mp4"):
                        break
                if output_s3_uri and output_s3_uri.lower().endswith(".mp4"):
                    break
            return {
                "job_id": job.get("Id"),
                "status": job.get("Status"),
                "error_message": job.get("ErrorMessage"),
                "output_group_details": job.get("OutputGroupDetails", []),
                "output_s3_uri": self._canonicalize_s3_uri(output_s3_uri),
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
            output_data_config = response.get("outputDataConfig")
            output_s3_uri = None
            if isinstance(output_data_config, dict):
                s3_cfg = output_data_config.get("s3OutputDataConfig") or {}
                candidate = s3_cfg.get("s3Uri")
                if isinstance(candidate, str) and candidate:
                    output_s3_uri = self._resolve_generated_video_from_prefix(candidate) or candidate
            return {
                "invocation_arn": response.get("invocationArn"),
                "status": response.get("status"),
                "failure_message": response.get("failureMessage"),
                "output_data_config": output_data_config,
                "output_s3_uri": self._canonicalize_s3_uri(output_s3_uri),
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

