# AWS Service Alignment (Backend)

This file documents where AWS services are initialized and how they are exercised by API flows.

It aligns backend code behavior with the deployment plan while separating:
- services initialized in backend code, and
- services managed primarily as infrastructure.

## 1) Code-initialized AWS services

- Bedrock Runtime
  - Init: `services/llm_service.py` (`AWSBedrockProvider`)
  - Used by: `POST /api/v1/create/*`, pipeline/intelligence generation paths

- Rekognition
  - Init: `services/vision_service.py` and `workflows/preflight_worker.py`
  - Used by: `POST /api/v1/moderate/image`, preflight worker image tasks

- Comprehend
  - Init: `services/moderation_service.py`, `services/pipeline_service.py`, `workflows/preflight_worker.py`
  - Used by: `POST /api/v1/moderate/text`, preflight worker text tasks

- Translate
  - Init: `services/translation_service.py`, `workflows/preflight_worker.py`
  - Used by: `POST /api/v1/translate/*`, preflight worker translation tasks

- Transcribe
  - Init: `services/speech_service.py`, `workflows/preflight_worker.py`
  - Used by: preflight worker transcribe tasks and speech service APIs
  - Note: interactive route transcription currently prefers local/free fallback path in `SpeechService.transcribe()`

- DynamoDB
  - Init: `services/dynamo_repositories.py`
  - Used by: auth/content/scheduler/analytics/history/pipeline persistence

- S3
  - Init: `services/storage_service.py`
  - Used by: `POST /api/v1/media/upload`, `POST /api/v1/media/presigned-upload`, media management

- Step Functions
  - Init: `services/pipeline_orchestration_service.py`
  - Used by: `POST /api/v1/pipeline/analyze` when Step Functions is enabled/configured

## 2) Infra-managed services (not required as backend SDK clients)

- API Gateway
  - Managed in SAM (`template.yaml`) + Lambda/Mangum entrypoint (`lambda_handler.py`)

- Lambda
  - Managed in SAM (`template.yaml`) with app entrypoint in `lambda_handler.py`

- EventBridge
  - Managed in SAM (`template.yaml`) via `AWS::Events::Rule`

- CloudWatch
  - Managed by Lambda runtime logs/metrics and deployment alarms/policies

- X-Ray
  - Managed in SAM (`Tracing: Active`) and IAM policy

- CloudFront
  - Frontend/infrastructure concern, not a backend SDK client

## 3) Scheduler decision

Decision: keep EventBridge scheduling infra-managed for this backend.

Rationale:
- Current scheduler router is a personal content calendar backed by DynamoDB (`routers/scheduler.py`).
- There is no runtime requirement to create dynamic one-time EventBridge Scheduler jobs from API code.
- SAM already provisions periodic EventBridge invocation for publish checks.

If product requirements change to runtime schedule creation/cancellation per item, introduce a dedicated service using `boto3.client("scheduler")` and wire it into scheduler endpoints.

