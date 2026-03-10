# AWS Architecture — Layer by Layer Reference

> **Stack**: React + Vite · FastAPI + Mangum · AWS Lambda + API Gateway · DynamoDB · Bedrock (Nova Lite / Nova Pro) · Step Functions · EventBridge · CloudWatch  
> **Region**: `ap-south-1` (Mumbai) — Built on AWS · Powered by Bedrock · Made for Bharat

---

## Table of Contents

1. [Frontend Layer](#1️⃣-frontend-layer)
2. [Media Upload Layer](#2️⃣-media-upload-layer)
3. [API Layer](#3️⃣-api-layer)
4. [Backend Compute Layer](#4️⃣-backend-compute-layer)
5. [AI Pipeline Orchestration](#5️⃣-ai-pipeline-orchestration)
6. [Database Layer](#6️⃣-database-layer)
7. [AI Generation Layer](#7️⃣-ai-generation-layer)
8. [Text Intelligence Layer](#8️⃣-text-intelligence-layer)
9. [Image Moderation Layer](#9️⃣-image-moderation-layer)
10. [Audio / Video Moderation](#🔟-audio--video-moderation)
11. [Language Adaptation](#1️⃣1️⃣-language-adaptation)
12. [Scheduling System](#1️⃣2️⃣-scheduling-system)
13. [AI Cost Optimization](#1️⃣3️⃣-ai-cost-optimization)
14. [Monitoring & Observability](#1️⃣4️⃣-monitoring--observability)
15. [Complete System Flow](#complete-system-flow)
16. [AWS Services Used](#aws-services-used)

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
- Global CDN distribution
- Low latency page loads
- Scalable static hosting

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
- Avoids API size limits
- Reduces backend load
- Scalable media ingestion

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
- Authentication
- API routing
- Presigned URL generation
- Invoking AI pipeline
- Reading/writing DynamoDB
- Caching AI responses

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
- Visual workflow orchestration
- Built-in retries
- Scalable pipeline execution

---

### 6️⃣ Database Layer

**Service**

Amazon DynamoDB

**Tables**

| Table | Purpose |
|---|---|
| Users | User profiles |
| Content | Scheduled posts |
| Analysis | AI analysis reports |
| AICache | Bedrock response cache |
| ModerationCache | Image moderation results |

**Example record**

```
analysis_id:           a102
risk_score:            0.42
toxicity:              0.15
shadowban_probability: 0.19
culture_rewrite:       localized caption
```

**Benefits**
- Millisecond reads
- Serverless scaling
- No infrastructure management

---

### 7️⃣ AI Generation Layer

**Service**

Amazon Bedrock

**Primary model**

Amazon Nova Lite

**Optional complex reasoning**

Nova Pro

**Used for**
- Caption generation
- Cultural rewriting
- Campaign planning
- Competitor analysis

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
- Sentiment detection
- Toxicity detection
- Entity recognition

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
- Violence detection
- Unsafe content detection

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
- Multilingual caption rewriting
- Regional language adaptation

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
- Reduces Bedrock usage
- Faster responses
- Improved cost efficiency

---

### 1️⃣4️⃣ Monitoring & Observability

**Service**

Amazon CloudWatch

**Used for**
- Lambda logs
- API latency metrics
- AI usage monitoring
- Pipeline debugging

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
