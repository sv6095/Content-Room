# Content Room — AWS Deployment Plan

> **Goal**: Deploy Content Room 100% on AWS using a serverless, event-driven architecture.  
> Frontend → S3 + CloudFront · Backend → Lambda + API Gateway (FastAPI + Mangum) · Data → DynamoDB · AI → Bedrock, Rekognition, Comprehend, Transcribe, Translate · Pipeline → Step Functions · Scheduling → EventBridge · Monitoring → CloudWatch

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [AWS Account Setup & IAM](#2-aws-account-setup--iam)
3. [DynamoDB — Database Layer](#3-dynamodb--database-layer)
4. [S3 Buckets — Media & Frontend Hosting](#4-s3-buckets--media--frontend-hosting)
5. [Secrets Manager — Credentials & API Keys](#5-secrets-manager--credentials--api-keys)
6. [Backend — Lambda + API Gateway](#6-backend--lambda--api-gateway)
7. [Step Functions — Pre-Flight Pipeline](#7-step-functions--pre-flight-pipeline)
8. [EventBridge — Content Scheduling](#8-eventbridge--content-scheduling)
9. [Frontend — Build & CloudFront Deployment](#9-frontend--build--cloudfront-deployment)
10. [CloudWatch — Monitoring & Alerts](#10-cloudwatch--monitoring--alerts)
11. [Environment Variables Reference](#11-environment-variables-reference)
12. [Post-Deployment Checklist](#12-post-deployment-checklist)
13. [Cost Estimate](#13-cost-estimate)

---

## 1. Prerequisites

Before deploying, ensure you have the following ready on your local machine:

| Tool | Version | Install |
|---|---|---|
| AWS CLI | v2+ | `winget install Amazon.AWSCLI` |
| AWS SAM CLI | Latest | `winget install Amazon.SAM-CLI` |
| Python | 3.10+ | `winget install Python.Python.3.10` |
| Node.js | 18+ | `winget install OpenJS.NodeJS.LTS` |
| Bun (Frontend) | Latest | `irm bun.sh/install.ps1 \| iex` |
| Git LFS | Latest | `winget install GitHub.GitLFS` |

### Configure AWS CLI
```powershell
aws configure
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region name: ap-south-1   # Mumbai — closest to Bharat
# Default output format: json
```

> **Region**: Use `ap-south-1` (Mumbai) as your primary region for lowest latency to Indian users.  
> Bedrock Nova Lite/Pro also available in `ap-south-1` as of 2024.

---

## 2. AWS Account Setup & IAM

### 2.1 Enable AWS Bedrock Model Access

1. Go to **AWS Console → Amazon Bedrock → Model Access** in `ap-south-1`
2. Request access to:
   - **Amazon Nova Lite** (`amazon.nova-lite-v1:0`)
   - **Amazon Nova Pro** (`amazon.nova-pro-v1:0`)
3. Wait for access to be granted (usually instant for Nova models)

### 2.2 Create IAM Role for Lambda

Create a role named `content-room-lambda-role` with these managed policies:

```powershell
# Create the Lambda execution role
aws iam create-role `
  --role-name content-room-lambda-role `
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach AWS managed policies
$policies = @(
  "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
  "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
  "arn:aws:iam::aws:policy/AmazonS3FullAccess",
  "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
  "arn:aws:iam::aws:policy/ComprehendFullAccess",
  "arn:aws:iam::aws:policy/AmazonRekognitionFullAccess",
  "arn:aws:iam::aws:policy/AmazonTranscribeFullAccess",
  "arn:aws:iam::aws:policy/TranslateFullAccess",
  "arn:aws:iam::aws:policy/AmazonEventBridgeFullAccess",
  "arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess",
  "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
  "arn:aws:iam::aws:policy/CloudWatchFullAccess"
)

foreach ($policy in $policies) {
  aws iam attach-role-policy --role-name content-room-lambda-role --policy-arn $policy
}
```

> **Security Note**: For production, scope these policies down to specific resource ARNs using the principle of least privilege.

### 2.3 Create IAM Role for Step Functions

```powershell
aws iam create-role `
  --role-name content-room-stepfunctions-role `
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "states.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy `
  --role-name content-room-stepfunctions-role `
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaRole"
```

---

## 3. DynamoDB — Database Layer

Content Room uses **5 purpose-built DynamoDB tables** replacing the local SQLite/PostgreSQL database.

### 3.1 Create All Tables

```powershell
$region = "ap-south-1"

# 1. Users table
aws dynamodb create-table `
  --table-name ContentRoom-Users `
  --attribute-definitions AttributeName=user_id,AttributeType=S `
  --key-schema AttributeName=user_id,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region $region

# 2. Content table (with GSI on scheduled_at)
aws dynamodb create-table `
  --table-name ContentRoom-Content `
  --attribute-definitions `
    AttributeName=content_id,AttributeType=S `
    AttributeName=user_id,AttributeType=S `
    AttributeName=scheduled_at,AttributeType=S `
  --key-schema AttributeName=content_id,KeyType=HASH `
  --global-secondary-indexes '[
    {
      "IndexName": "UserIdIndex",
      "KeySchema": [
        {"AttributeName": "user_id", "KeyType": "HASH"},
        {"AttributeName": "scheduled_at", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]' `
  --billing-mode PAY_PER_REQUEST `
  --region $region

# 3. Analysis table — stores pre-flight pipeline results
aws dynamodb create-table `
  --table-name ContentRoom-Analysis `
  --attribute-definitions `
    AttributeName=analysis_id,AttributeType=S `
    AttributeName=user_id,AttributeType=S `
  --key-schema AttributeName=analysis_id,KeyType=HASH `
  --global-secondary-indexes '[
    {
      "IndexName": "UserIdIndex",
      "KeySchema": [{"AttributeName": "user_id", "KeyType": "HASH"}],
      "Projection": {"ProjectionType": "ALL"}
    }
  ]' `
  --billing-mode PAY_PER_REQUEST `
  --region $region

# 4. AICache table — Bedrock prompt caching with TTL
aws dynamodb create-table `
  --table-name ContentRoom-AICache `
  --attribute-definitions AttributeName=prompt_hash,AttributeType=S `
  --key-schema AttributeName=prompt_hash,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region $region

aws dynamodb update-time-to-live `
  --table-name ContentRoom-AICache `
  --time-to-live-specification "Enabled=true,AttributeName=ttl" `
  --region $region

# 5. ModerationCache table — image SHA-256 caching
aws dynamodb create-table `
  --table-name ContentRoom-ModerationCache `
  --attribute-definitions AttributeName=image_hash,AttributeType=S `
  --key-schema AttributeName=image_hash,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region $region

aws dynamodb update-time-to-live `
  --table-name ContentRoom-ModerationCache `
  --time-to-live-specification "Enabled=true,AttributeName=ttl" `
  --region $region
```

---

## 4. S3 Buckets — Media & Frontend Hosting

### 4.1 Create S3 Buckets

```powershell
$accountId = (aws sts get-caller-identity --query Account --output text)
$region = "ap-south-1"

# Media uploads bucket (private — accessed via presigned URLs only)
aws s3api create-bucket `
  --bucket "content-room-media-$accountId" `
  --region $region `
  --create-bucket-configuration LocationConstraint=$region

# Block all public access on media bucket
aws s3api put-public-access-block `
  --bucket "content-room-media-$accountId" `
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Frontend static hosting bucket (public read)
aws s3api create-bucket `
  --bucket "content-room-frontend-$accountId" `
  --region $region `
  --create-bucket-configuration LocationConstraint=$region

# Enable static website hosting on frontend bucket
aws s3api put-bucket-website `
  --bucket "content-room-frontend-$accountId" `
  --website-configuration '{
    "IndexDocument": {"Suffix": "index.html"},
    "ErrorDocument": {"Key": "index.html"}
  }'
```

### 4.2 Configure CORS on Media Bucket

```powershell
aws s3api put-bucket-cors `
  --bucket "content-room-media-$accountId" `
  --cors-configuration '{
    "CORSRules": [{
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedOrigins": ["https://your-cloudfront-domain.cloudfront.net"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }]
  }'
```

> **Replace** `your-cloudfront-domain` with your actual CloudFront domain after Step 9.

### 4.3 Configure CORS on Media Bucket (for ML Model Files)

Large ML model files (`nsfw.caffemodel`, `resnet_moderation.pth`) should be tracked via **Git LFS** and stored in the media bucket rather than bundled in Lambda:

```powershell
# Upload ML models to S3
aws s3 cp "Backend/ml_models/" "s3://content-room-media-$accountId/ml_models/" --recursive
```

Lambda will download these on cold start or you can use Lambda Layers for smaller models.

---

## 5. Secrets Manager — Credentials & API Keys

Store all sensitive keys in AWS Secrets Manager. Lambda reads them at runtime — **no hardcoded credentials**.

### 5.1 Store All Secrets

```powershell
$region = "ap-south-1"

# JWT Secret Key
aws secretsmanager create-secret `
  --name "content-room/jwt-secret" `
  --secret-string '{"SECRET_KEY": "your-32-char-minimum-random-string"}' `
  --region $region

# AI Provider API Keys (fallback chain)
aws secretsmanager create-secret `
  --name "content-room/ai-keys" `
  --secret-string '{
    "GROQ_API_KEY": "gsk_your_groq_key",
    "OPENAI_API_KEY": "sk-your_openai_key",
    "OPENROUTER_API_KEY": "sk-or-v1-your_key",
    "GEMINI_API_KEY": "your_gemini_key"
  }' `
  --region $region

# Social OAuth Keys
aws secretsmanager create-secret `
  --name "content-room/social-oauth" `
  --secret-string '{
    "TWITTER_API_KEY": "",
    "TWITTER_API_SECRET": "",
    "TWITTER_ACCESS_TOKEN": "",
    "TWITTER_ACCESS_TOKEN_SECRET": "",
    "INSTAGRAM_APP_ID": "",
    "INSTAGRAM_APP_SECRET": "",
    "LINKEDIN_CLIENT_ID": "",
    "LINKEDIN_CLIENT_SECRET": ""
  }' `
  --region $region
```

> **Generate a secure JWT secret**:  
> `python -c "import secrets; print(secrets.token_urlsafe(32))"`

---

## 6. Backend — Lambda + API Gateway

### 6.1 Prepare Lambda Deployment Package

The FastAPI application is deployed to Lambda using **Mangum** as the ASGI adapter.

#### Step 1: Install Mangum

Add `mangum` to `Backend/requirements.txt` if not already present:

```
mangum==0.17.0
```

#### Step 2: Create Lambda Handler

Create `Backend/lambda_handler.py`:

```python
"""
AWS Lambda entry point for Content Room FastAPI backend.
Mangum adapts ASGI (FastAPI) to the Lambda event format.
"""
from mangum import Mangum
from main import app

# Handler for API Gateway proxy integration
handler = Mangum(app, lifespan="off")
```

> **Note**: Set `lifespan="off"` because Lambda does not support long-running lifespan events. Database initialization is handled per-request instead.

#### Step 3: Update `database.py` for DynamoDB

The existing `database.py` uses SQLAlchemy + SQLite/PostgreSQL. For production AWS deployment, the backend services should use **boto3 DynamoDB** directly. The current code still works if you point `DATABASE_URL` to an external PostgreSQL (e.g., Amazon RDS or Supabase), but the architecture recommends DynamoDB.

**Recommended approach for the hackathon**: Use **Amazon RDS PostgreSQL** (Serverless v2) to keep the existing SQLAlchemy ORM code working with zero changes, and migrate to DynamoDB later.

```powershell
# Create RDS Aurora Serverless v2 PostgreSQL (optional — works with existing code)
aws rds create-db-cluster `
  --db-cluster-identifier content-room-db `
  --engine aurora-postgresql `
  --engine-version 15.4 `
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=4 `
  --database-name contentroom `
  --master-username contentroom `
  --master-user-password "YourSecurePassword123!" `
  --region ap-south-1
```

#### Step 4: Build Lambda Package

```powershell
# Navigate to Backend
cd "c:\projects\Content Room\Content Room\Backend"

# Create deployment directory
New-Item -ItemType Directory -Force -Path ".\lambda_package"

# Install dependencies into package directory
pip install -r requirements.txt -t .\lambda_package --platform manylinux2014_x86_64 --python-version 3.10 --only-binary=:all:

# Copy application code
Copy-Item -Recurse -Force `
  config, routers, services, models, middleware, utils, database.py, main.py, lambda_handler.py `
  .\lambda_package\

# Zip the package
Compress-Archive -Path .\lambda_package\* -DestinationPath .\content-room-backend.zip -Force
```

> **ML Models Note**: The `caffemodel` and `.pth` files are large. Do **not** include them in the Lambda zip. Store them in S3 and load them at runtime, or create a Lambda Layer for smaller models.

#### Step 5: Create Lambda Function

```powershell
$accountId = (aws sts get-caller-identity --query Account --output text)
$region = "ap-south-1"

aws lambda create-function `
  --function-name content-room-backend `
  --runtime python3.10 `
  --handler lambda_handler.handler `
  --zip-file fileb://content-room-backend.zip `
  --role "arn:aws:iam::${accountId}:role/content-room-lambda-role" `
  --timeout 30 `
  --memory-size 1024 `
  --environment Variables="{
    AWS_DEFAULT_REGION=$region,
    ENVIRONMENT=production,
    DEBUG_MODE=false,
    LLM_PROVIDER=groq,
    USE_DYNAMODB=true,
    S3_MEDIA_BUCKET=content-room-media-$accountId,
    SECRETS_PREFIX=content-room,
    LOG_LEVEL=INFO,
    RATE_LIMIT_PER_MINUTE=60
  }" `
  --region $region

# Update size (if code > 50MB, upload via S3)
aws s3 cp content-room-backend.zip "s3://content-room-media-$accountId/deployments/backend.zip"
aws lambda update-function-code `
  --function-name content-room-backend `
  --s3-bucket "content-room-media-$accountId" `
  --s3-key "deployments/backend.zip" `
  --region $region
```

#### Step 6: Create API Gateway

```powershell
# Create HTTP API (API Gateway v2 — lower cost, lower latency than REST API)
$apiId = (aws apigatewayv2 create-api `
  --name content-room-api `
  --protocol-type HTTP `
  --cors-configuration `
    AllowOrigins="https://your-cloudfront-domain.cloudfront.net",`
    AllowMethods="GET,POST,PUT,DELETE,OPTIONS",`
    AllowHeaders="Authorization,Content-Type,Accept",`
    MaxAge=300 `
  --region $region `
  --query ApiId --output text)

# Create Lambda integration
$integrationId = (aws apigatewayv2 create-integration `
  --api-id $apiId `
  --integration-type AWS_PROXY `
  --integration-uri "arn:aws:lambda:${region}:${accountId}:function:content-room-backend" `
  --payload-format-version 2.0 `
  --region $region `
  --query IntegrationId --output text)

# Create catch-all route
aws apigatewayv2 create-route `
  --api-id $apiId `
  --route-key "ANY /{proxy+}" `
  --target "integrations/$integrationId" `
  --region $region

# Deploy to production stage
aws apigatewayv2 create-stage `
  --api-id $apiId `
  --stage-name production `
  --auto-deploy `
  --region $region

# Allow API Gateway to invoke Lambda
aws lambda add-permission `
  --function-name content-room-backend `
  --statement-id apigw-invoke `
  --action lambda:InvokeFunction `
  --principal apigateway.amazonaws.com `
  --source-arn "arn:aws:execute-api:${region}:${accountId}:${apiId}/*" `
  --region $region

# Get the API endpoint
Write-Host "API Endpoint: https://$apiId.execute-api.$region.amazonaws.com/production"
```

---

## 7. Step Functions — Pre-Flight Pipeline

The 6-check Pre-Flight Analysis pipeline runs in parallel using AWS Step Functions Standard Workflows.

### 7.1 Create Individual Check Lambda Functions

Create 6 separate Lambda functions — one per pre-flight check. Each reads the content payload and returns its specific analysis result.

```powershell
$checks = @("anti-cancel", "shadowban", "culture-adapt", "content-safety", "mental-health", "asset-spinoffs")

foreach ($check in $checks) {
  aws lambda create-function `
    --function-name "content-room-preflight-$check" `
    --runtime python3.10 `
    --handler "lambda_handler.handler" `
    --zip-file fileb://content-room-backend.zip `
    --role "arn:aws:iam::${accountId}:role/content-room-lambda-role" `
    --timeout 30 `
    --memory-size 512 `
    --environment Variables="{CHECK_TYPE=$check,AWS_DEFAULT_REGION=$region}" `
    --region $region
}
```

### 7.2 Define the State Machine

Create `step-functions-preflight.json`:

```json
{
  "Comment": "Content Room Pre-Flight 6-Check Parallel Pipeline",
  "StartAt": "RunAllChecks",
  "States": {
    "RunAllChecks": {
      "Type": "Parallel",
      "Branches": [
        {
          "StartAt": "AntiCancelShield",
          "States": {
            "AntiCancelShield": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:ap-south-1:ACCOUNT_ID:function:content-room-preflight-anti-cancel",
              "Retry": [{"ErrorEquals": ["States.ALL"], "IntervalSeconds": 1, "MaxAttempts": 2}],
              "End": true
            }
          }
        },
        {
          "StartAt": "ShadowbanPredictor",
          "States": {
            "ShadowbanPredictor": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:ap-south-1:ACCOUNT_ID:function:content-room-preflight-shadowban",
              "Retry": [{"ErrorEquals": ["States.ALL"], "IntervalSeconds": 1, "MaxAttempts": 2}],
              "End": true
            }
          }
        },
        {
          "StartAt": "CultureAdaptation",
          "States": {
            "CultureAdaptation": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:ap-south-1:ACCOUNT_ID:function:content-room-preflight-culture-adapt",
              "Retry": [{"ErrorEquals": ["States.ALL"], "IntervalSeconds": 1, "MaxAttempts": 2}],
              "End": true
            }
          }
        },
        {
          "StartAt": "ContentSafety",
          "States": {
            "ContentSafety": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:ap-south-1:ACCOUNT_ID:function:content-room-preflight-content-safety",
              "Retry": [{"ErrorEquals": ["States.ALL"], "IntervalSeconds": 1, "MaxAttempts": 2}],
              "End": true
            }
          }
        },
        {
          "StartAt": "MentalHealthTone",
          "States": {
            "MentalHealthTone": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:ap-south-1:ACCOUNT_ID:function:content-room-preflight-mental-health",
              "Retry": [{"ErrorEquals": ["States.ALL"], "IntervalSeconds": 1, "MaxAttempts": 2}],
              "End": true
            }
          }
        },
        {
          "StartAt": "AssetSpinoffs",
          "States": {
            "AssetSpinoffs": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:ap-south-1:ACCOUNT_ID:function:content-room-preflight-asset-spinoffs",
              "Retry": [{"ErrorEquals": ["States.ALL"], "IntervalSeconds": 1, "MaxAttempts": 2}],
              "End": true
            }
          }
        }
      ],
      "Next": "AggregateResults"
    },
    "AggregateResults": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:ap-south-1:ACCOUNT_ID:function:content-room-backend",
      "Parameters": {
        "action": "aggregate_preflight",
        "results.$": "$"
      },
      "End": true
    }
  }
}
```

```powershell
# Replace ACCOUNT_ID placeholder
(Get-Content step-functions-preflight.json) -replace 'ACCOUNT_ID', $accountId | Set-Content step-functions-preflight.json

# Create the state machine
aws stepfunctions create-state-machine `
  --name content-room-preflight-pipeline `
  --definition file://step-functions-preflight.json `
  --role-arn "arn:aws:iam::${accountId}:role/content-room-stepfunctions-role" `
  --region $region
```

---

## 8. EventBridge — Content Scheduling

EventBridge Scheduler creates one-time triggers for every approved scheduled post.

### 8.1 Create Scheduler IAM Role

```powershell
aws iam create-role `
  --role-name content-room-scheduler-role `
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "scheduler.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam attach-role-policy `
  --role-name content-room-scheduler-role `
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaRole"
```

### 8.2 How Scheduling Works

When a creator approves a post and sets a publish date, the backend calls:

```python
import boto3

scheduler = boto3.client('scheduler', region_name='ap-south-1')

scheduler.create_schedule(
    Name=f"post-{content_id}",
    ScheduleExpression=f"at({publish_datetime.strftime('%Y-%m-%dT%H:%M:%S')})",
    Target={
        'Arn': f'arn:aws:lambda:ap-south-1:{account_id}:function:content-room-backend',
        'RoleArn': f'arn:aws:iam::{account_id}:role/content-room-scheduler-role',
        'Input': json.dumps({'action': 'publish_post', 'content_id': content_id})
    },
    FlexibleTimeWindow={'Mode': 'OFF'},
    ActionAfterCompletion='DELETE'  # Auto-clean after firing
)
```

---

## 9. Frontend — Build & CloudFront Deployment

### 9.1 Build the Frontend

```powershell
cd "c:\projects\Content Room\Content Room\Frontend"

# Set production API URL (replace with your actual API Gateway URL)
$env:VITE_API_BASE_URL = "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/production"

# Build
npm run build
# or if using bun:
bun run build

# Output is in ./dist/
```

### 9.2 Upload to S3

```powershell
$accountId = (aws sts get-caller-identity --query Account --output text)
$frontendBucket = "content-room-frontend-$accountId"

# Sync built files to S3
aws s3 sync .\dist\ "s3://$frontendBucket/" `
  --delete `
  --cache-control "max-age=31536000,immutable" `
  --exclude "index.html"

# Upload index.html with no-cache (so CloudFront always fetches the latest)
aws s3 cp .\dist\index.html "s3://$frontendBucket/index.html" `
  --cache-control "no-cache, no-store, must-revalidate"
```

### 9.3 Create CloudFront Distribution

```powershell
$frontendBucket = "content-room-frontend-$accountId"

# Create Origin Access Control (OAC)
$oacId = (aws cloudfront create-origin-access-control `
  --origin-access-control-config '{
    "Name": "content-room-oac",
    "Description": "OAC for Content Room frontend",
    "SigningProtocol": "sigv4",
    "SigningBehavior": "always",
    "OriginAccessControlOriginType": "s3"
  }' `
  --query OriginAccessControl.Id --output text)

# Create distribution
aws cloudfront create-distribution --distribution-config '{
  "CallerReference": "content-room-frontend-2024",
  "Comment": "Content Room Frontend CDN",
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "S3-content-room-frontend",
      "DomainName": "FRONTEND_BUCKET.s3.ap-south-1.amazonaws.com",
      "S3OriginConfig": {"OriginAccessIdentity": ""},
      "OriginAccessControlId": "OAC_ID"
    }]
  },
  "DefaultCacheBehavior": {
    "ViewerProtocolPolicy": "redirect-to-https",
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "TargetOriginId": "S3-content-room-frontend",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}
    }
  },
  "CustomErrorResponses": {
    "Quantity": 1,
    "Items": [{
      "ErrorCode": 403,
      "ResponseCode": "200",
      "ResponsePagePath": "/index.html",
      "ErrorCachingMinTTL": 0
    }]
  },
  "PriceClass": "PriceClass_200",
  "Enabled": true
}'
```

> **PriceClass_200** covers North America, Europe, Asia, Middle East, and Africa edge locations — including Mumbai, Chennai, and Kolkata POPs for Bharat.

### 9.4 Update S3 Bucket Policy for CloudFront OAC

After getting the CloudFront distribution ARN, update the S3 bucket policy:

```powershell
$distributionArn = "arn:aws:cloudfront::${accountId}:distribution/YOUR_DISTRIBUTION_ID"

aws s3api put-bucket-policy `
  --bucket $frontendBucket `
  --policy "{
    'Version': '2012-10-17',
    'Statement': [{
      'Sid': 'AllowCloudFrontOAC',
      'Effect': 'Allow',
      'Principal': {'Service': 'cloudfront.amazonaws.com'},
      'Action': 's3:GetObject',
      'Resource': 'arn:aws:s3:::${frontendBucket}/*',
      'Condition': {
        'StringEquals': {
          'AWS:SourceArn': '${distributionArn}'
        }
      }
    }]
  }"
```

---

## 10. CloudWatch — Monitoring & Alerts

### 10.1 Create Log Groups

```powershell
$logGroups = @(
  "/aws/lambda/content-room-backend",
  "/aws/lambda/content-room-preflight-anti-cancel",
  "/aws/lambda/content-room-preflight-shadowban",
  "/aws/lambda/content-room-preflight-culture-adapt",
  "/aws/lambda/content-room-preflight-content-safety",
  "/aws/lambda/content-room-preflight-mental-health",
  "/aws/lambda/content-room-preflight-asset-spinoffs",
  "/aws/states/content-room-preflight-pipeline"
)

foreach ($group in $logGroups) {
  aws logs create-log-group --log-group-name $group --region $region
  aws logs put-retention-policy --log-group-name $group --retention-in-days 30 --region $region
}
```

### 10.2 Create Alarms

```powershell
# Lambda error rate alarm
aws cloudwatch put-metric-alarm `
  --alarm-name "content-room-lambda-errors" `
  --alarm-description "Lambda error rate > 5% for 5 minutes" `
  --metric-name Errors `
  --namespace AWS/Lambda `
  --dimensions Name=FunctionName,Value=content-room-backend `
  --statistic Sum `
  --period 300 `
  --evaluation-periods 1 `
  --threshold 10 `
  --comparison-operator GreaterThanThreshold `
  --treat-missing-data notBreaching `
  --region $region

# Step Functions failure alarm
aws cloudwatch put-metric-alarm `
  --alarm-name "content-room-pipeline-failures" `
  --alarm-description "Pre-flight pipeline failures > 5 in 5 minutes" `
  --metric-name ExecutionsFailed `
  --namespace AWS/States `
  --dimensions Name=StateMachineArn,Value="arn:aws:states:${region}:${accountId}:stateMachine:content-room-preflight-pipeline" `
  --statistic Sum `
  --period 300 `
  --evaluation-periods 1 `
  --threshold 5 `
  --comparison-operator GreaterThanThreshold `
  --region $region
```

---

## 11. Environment Variables Reference

### Backend Lambda Environment Variables

Set these in the Lambda function configuration (AWS Console → Lambda → Configuration → Environment variables):

| Variable | Value | Notes |
|---|---|---|
| `AWS_DEFAULT_REGION` | `ap-south-1` | Primary region |
| `ENVIRONMENT` | `production` | Enables production settings |
| `DEBUG_MODE` | `false` | Disables debug output |
| `LLM_PROVIDER` | `groq` or `bedrock` | Primary AI provider |
| `USE_DYNAMODB` | `true` | Switches from SQLite to DynamoDB |
| `S3_MEDIA_BUCKET` | `content-room-media-<accountId>` | Media upload bucket name |
| `SECRETS_PREFIX` | `content-room` | Secrets Manager prefix |
| `LOG_LEVEL` | `INFO` | CloudWatch log verbosity |
| `RATE_LIMIT_PER_MINUTE` | `60` | Per-IP rate limit |
| `STEP_FUNCTIONS_ARN` | `arn:aws:states:...` | Pre-flight pipeline ARN |
| `FRONTEND_URL` | `https://xxxx.cloudfront.net` | CloudFront domain for CORS |
| `ALLOWED_ORIGINS` | `https://xxxx.cloudfront.net` | CORS allowed origins |
| `HF_HUB_DISABLE_TELEMETRY` | `1` | Disables HuggingFace telemetry |
| `HF_HUB_OFFLINE` | `0` | Allow model downloads on cold start |

> **Sensitive keys** (JWT secret, API keys) are stored in **AWS Secrets Manager** and fetched at runtime — not stored in environment variables directly.

### Frontend Environment Variables (set before `npm run build`)

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/production` |

---

## 12. Post-Deployment Checklist

After completing all steps above, verify each item:

### Infrastructure Verification
- [ ] All 5 DynamoDB tables created and accessible
- [ ] Both S3 buckets created (media private, frontend public via CloudFront OAC)
- [ ] All secrets stored in Secrets Manager
- [ ] `content-room-lambda-role` has all required policies
- [ ] Lambda function deployed and responding to test events

### Connectivity Tests
```powershell
# Test health endpoint
Invoke-RestMethod "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/production/health"
# Expected: {"status": "healthy", "aws_configured": true, ...}

# Test auth register endpoint  
Invoke-RestMethod -Method POST `
  -Uri "https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/production/api/v1/auth/register" `
  -Body '{"email":"test@test.com","password":"Test123!","name":"Test User"}' `
  -ContentType "application/json"
```

### Feature Verification
- [ ] Frontend loads at CloudFront URL
- [ ] Creator Studio generates captions via Bedrock
- [ ] Content Moderation runs via Rekognition + Comprehend
- [ ] Multi-language translation works via AWS Translate
- [ ] Pre-Flight pipeline executes via Step Functions (check AWS Console → Step Functions)
- [ ] Scheduled posts create EventBridge rules
- [ ] CloudWatch logs are flowing for Lambda executions
- [ ] AI response caching working (second identical request should be faster)

### CORS Verification
- [ ] Update `ALLOWED_ORIGINS` Lambda env var with final CloudFront domain
- [ ] Update `FRONTEND_URL` Lambda env var with final CloudFront domain
- [ ] Update S3 media bucket CORS to allow requests from CloudFront domain

### Security Checks
- [ ] No hardcoded API keys in source code or Lambda env vars
- [ ] Media S3 bucket blocks all public access except via presigned URLs
- [ ] Lambda IAM role follows least-privilege (scope down resource ARNs in production)
- [ ] API Gateway has throttling configured (default: 10,000 req/sec, 5,000 burst)
- [ ] CloudFront has HTTPS-only enforced (redirect HTTP → HTTPS)

---

## 13. Cost Estimate

Based on 1,000 active creators, ~30 analyses/month each (30,000 analyses/month):

| Service | Usage | Monthly Cost (USD) |
|---|---|---|
| AWS Lambda | 30K invocations × 2s × 1024MB | ~$1.80 |
| API Gateway (HTTP API) | 30K requests | ~$0.10 |
| Amazon Bedrock Nova Lite | 30K analyses × 500 tokens | ~$9.00 |
| Amazon Comprehend | 30K text analyses | ~$0.75 |
| Amazon Rekognition | 10K image analyses | ~$1.00 |
| Amazon Transcribe | 100 audio hours | ~$2.40 |
| Amazon Translate | 10M characters translated | ~$1.50 |
| DynamoDB (on-demand) | 30K reads + writes | ~$0.50 |
| S3 (storage + requests) | 10GB storage + 100K requests | ~$0.30 |
| CloudFront | 50GB data transfer | ~$4.25 |
| Step Functions | 30K pipeline runs × 6 states | ~$0.75 |
| EventBridge Scheduler | 15K scheduled events | ~$0.08 |
| CloudWatch | Logs + metrics | ~$1.50 |
| **Total** | | **~$24/month** |

> At 60-80% DynamoDB AI cache hit rate, Bedrock costs drop to ~**$3–5/month**, bringing total to under **$15/month** at this scale.

---

## Architecture Summary

```
[Indian Creator]
      ↓
[CloudFront CDN]  ←→  [S3 Frontend Bucket] (React + Vite static files)
      ↓
[API Gateway HTTP API]
      ↓
[Lambda: content-room-backend]  (FastAPI + Mangum, 1024MB, 30s timeout)
      ↓
  ┌───├───────────────────────────────────┐
  │   │                                   │
  ↓   ↓                                   ↓
[DynamoDB]    [S3 Pre-signed URL]    [Step Functions]
[AICache]     [Direct Media Upload]  [6-Check Parallel]
[Users]             ↓                     ↓
[Content]     [S3 Event Trigger]    ┌─────┼─────────┐
[Analysis]          ↓               ↓     ↓         ↓
[ModCache]    [Lambda Trigger]   [Bedrock][Compreh.][Rekognition]
                    ↓               ↓     ↓
              [Rekognition]    [Translate][Transcribe]
              [Transcribe]
              [Comprehend]
                                    ↓
                             [CloudWatch Logs]
                             [Metrics & Alarms]
```

---

*Built on AWS · Powered by Bedrock · Made for Bharat*

---

## AWS Architecture — Layer by Layer Reference

---

### 1️⃣ Frontend Layer

**Frontend stack**

React + Vite

**Deployment**

```
Users
↓
CloudFront CDN
↓
S3 Static Hosting
↓
React Application
```

**Benefits**
- global CDN distribution
- low latency page loads
- scalable static hosting

**Services used**
- Amazon S3
- Amazon CloudFront

---

### 2️⃣ Media Upload Layer

Use presigned S3 uploads instead of sending files through the API.

**Flow**

```
User Upload
↓
Frontend requests upload URL
↓
Lambda generates presigned URL
↓
Direct upload to S3
```

**Processing**

```
S3 Upload
↓
S3 Event Trigger
↓
Lambda
↓
Moderation + AI pipeline
```

**Benefits**
- avoids API size limits
- reduces backend load
- scalable media ingestion

---

### 3️⃣ API Layer

**Service**

Amazon API Gateway

**Example routes**

```
POST /generate
POST /analyze
POST /schedule
GET  /content
POST /competitor-analysis
```

**Flow**

```
Frontend
↓
API Gateway
↓
Lambda
```

---

### 4️⃣ Backend Compute Layer

**Service**

AWS Lambda

**Framework**

FastAPI + Mangum

**Responsibilities**
- authentication
- API routing
- presigned URL generation
- invoking AI pipeline
- reading/writing DynamoDB
- caching AI responses

**Recommended configuration**

```
Memory:  1024 MB
Timeout: 30 seconds
```

**Engineering improvement**

All AWS SDK calls run using:

```python
asyncio.to_thread()
```

This prevents boto3 calls from blocking the FastAPI event loop.

---

### 5️⃣ AI Pipeline Orchestration

**Service**

AWS Step Functions

**Purpose**

Manage the pre-flight content analysis pipeline.

**Pipeline flow**

```
User Content
↓
Step Functions
↓
Parallel AI tasks
```

**Steps executed**

| # | Step |
|---|---|
| 1 | Content Analysis |
| 2 | Cultural Adaptation |
| 3 | Safety & Moderation |
| 4 | Creator Wellness |
| 5 | Asset Suggestions |

**Execution protection**

> Global timeout: 30 seconds

**Benefits**
- visual workflow orchestration
- built-in retries
- scalable pipeline execution

---

### 6️⃣ Database Layer

**Service**

Amazon DynamoDB

**Tables**

| Table | Purpose |
|---|---|
| Users | user profiles |
| Content | scheduled posts |
| Analysis | AI analysis reports |
| AICache | Bedrock response cache |
| ModerationCache | image moderation results |

**Example record**

```
analysis_id:           a102
risk_score:            0.42
toxicity:              0.15
shadowban_probability: 0.19
culture_rewrite:       localized caption
```

**Benefits**
- millisecond reads
- serverless scaling
- no infrastructure management

---

### 7️⃣ AI Generation Layer

**Service**

Amazon Bedrock

**Primary model**

Amazon Nova Lite

**Optional complex reasoning**

Nova Pro

**Used for**
- caption generation
- cultural rewriting
- campaign planning
- competitor analysis

**Execution flow**

```
Lambda
↓
Bedrock Nova Lite
↓
AI response
```

---

### 8️⃣ Text Intelligence Layer

**Service**

Amazon Comprehend

**Used for**
- sentiment detection
- toxicity detection
- entity recognition

**Flow**

```
User text
↓
Lambda
↓
Comprehend
↓
Safety scores
```

---

### 9️⃣ Image Moderation Layer

**Service**

Amazon Rekognition

**Workflow**

```
Image Upload
↓
S3
↓
Lambda Trigger
↓
Rekognition
↓
Moderation Results
```

**Capabilities**
- NSFW detection
- violence detection
- unsafe content detection

---

### 🔟 Audio / Video Moderation

**Service**

Amazon Transcribe

**Pipeline**

```
Audio / Video Upload
↓
S3
↓
Lambda
↓
Transcribe
↓
Text moderation via Comprehend
```

This enables multimodal content safety analysis.

---

### 1️⃣1️⃣ Language Adaptation

**Service**

Amazon Translate

**Used for**
- multilingual caption rewriting
- regional language adaptation

Supports India-focused creator workflows.

---

### 1️⃣2️⃣ Scheduling System

**Service**

Amazon EventBridge

**Workflow**

```
User schedules post
↓
EventBridge schedule created
↓
Scheduled Lambda trigger
↓
Content publishing workflow
```

This enables event-driven automation.

---

### 1️⃣3️⃣ AI Cost Optimization

DynamoDB caching layer

**Workflow**

```
User prompt
↓
hash(prompt)
↓
Check DynamoDB cache
↓
Cache hit  → return instantly
Cache miss → call Bedrock
↓
Store result in cache
```

**Benefits**
- reduces Bedrock usage
- faster responses
- improved cost efficiency

---

### 1️⃣4️⃣ Monitoring & Observability

**Service**

Amazon CloudWatch

**Used for**
- Lambda logs
- API latency metrics
- AI usage monitoring
- pipeline debugging

---

## Complete System Flow

```
User
↓
CloudFront
↓
S3 (Frontend)
↓
API Gateway
↓
Lambda (FastAPI)
↓
Step Functions (AI pipeline)
↓
Bedrock (Nova Lite / Nova Pro)
↓
Comprehend
↓
Rekognition
↓
Translate
↓
Transcribe
↓
DynamoDB (data + cache)
↓
S3 (media storage)
↓
EventBridge scheduler
↓
CloudWatch monitoring
```

---

## AWS Services Used

| Layer | Service |
|---|---|
| Frontend Hosting | Amazon S3 |
| CDN | Amazon CloudFront |
| API Layer | Amazon API Gateway |
| Compute | AWS Lambda |
| Workflow | AWS Step Functions |
| Database | Amazon DynamoDB |
| Media Storage | Amazon S3 |
| Generative AI | Amazon Bedrock |
| Text NLP | Amazon Comprehend |
| Vision AI | Amazon Rekognition |
| Translation | Amazon Translate |
| Speech | Amazon Transcribe |
| Scheduling | Amazon EventBridge |
| Monitoring | Amazon CloudWatch |

**Total AWS services used: 13**

---

*Built on AWS · Powered by Bedrock · Made for Bharat*