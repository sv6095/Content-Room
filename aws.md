# AWS Hackathon - Google Form Answers

Here are the suggested answers to fill out in the form, tailored to the Content Room project:

### 1. What's the specific GenAI model you're using?
**Question:** Which models do you plan to invoke via Bedrock?

**Answer:**
> We plan to invoke **Anthropic Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`) via Amazon Bedrock as our primary orchestrator for complex reasoning, multi-step agent workflows, cultural emotional rewriting, and high-fidelity text generation. In addition to Bedrock models, we will use **Amazon Rekognition** as our primary managed AI service for real-time image moderation, label detection, and visual analysis.

---

### 2. What's your data strategy?
**Question:** What are your data sources, and how will you store and process the data on AWS?

**Answer:**
> **Data Sources:** 
> User-uploaded media (images, documents, text), automated market trend feeds, user persona profiles, and generated schedule metadata.
> 
> **Storage & Processing on AWS:**
> - **Amazon S3:** Used as our primary object store for all raw media uploads, generated assets, and intermediate processed files.
> - **Amazon RDS (PostgreSQL):** We will migrate our current SQLite database to Amazon RDS to securely store structured data including user schemas, scheduling history, analytics, and content metadata.
> - **AWS Lambda / EventBridge:** To handle asynchronous data processing and content scheduler triggers. 
> - **Data Flow:** Media assets uploaded to S3 will trigger workflows that invoke Amazon Rekognition (for safety/context labeling) and Amazon Bedrock (for metadata synthesis/captioning), saving the final structured output back into RDS.

---

### 3. What is your "24-hour Goal"?
**Question:** What is the very first technical milestone you will achieve once credits are credited to your account?

**Answer:**
> **Goal: "End-to-End Migration to Native AWS Services"**
> 
> Within the first 24 hours of receiving AWS credits, our very first technical milestone is to migrate our existing local AI fallbacks entirely onto AWS infrastructure. Specifically, we will:
> 1. Switch our primary LLM routing entirely over to **Amazon Bedrock** (Claude 3 Sonnet).
> 2. Fully transition our two-pass image moderation pipeline from local OpenCV heuristics to **Amazon Rekognition**.
> 3. Migrate our local database to **Amazon RDS**.
> 4. Successfully process an end-to-end "Content Creation + Emotion Rewriting + Image Moderation" request purely through managed AWS services without resting on local fallbacks.
