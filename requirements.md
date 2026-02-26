# Project Requirements and Architecture Setup

This document outlines the required free APIs, datasets, and AWS fallback mechanisms needed for Content Room's Multimodal AI Platform.

## 1. Free APIs & Datasets Required

To run the application entirely on a free-tier stack without AWS costs, you will need the following API keys and model datasets.

### Free APIs
*   **Groq API**: Primary provider for high-speed LLM inference (Free Tier). 
    *   🔗 [Get Groq API Key](https://console.groq.com/keys)
*   **Google Gemini API**: Essential for Gemini 2.0 Flash text generation and AI-powered Image semantic moderation.
    *   🔗 [Get Gemini API Key](https://aistudio.google.com/app/apikey)
*   **Grok xAI API** *(Optional)*: Secondary LLM fallback if Groq rate limits are hit.
    *   🔗 [Get Grok API Key](https://console.x.ai/)

### Open-Source Datasets / Model Weights
For true offline processing algorithms, the system automatically pulls the following neural network datasets based on deep learning pre-training:
*   **Yahoo Open NSFW Model (Caffe/OpenCV)**: Used as a local backbone for image moderation.
    *   🔗 architecture: [open_nsfw/deploy.prototxt](https://raw.githubusercontent.com/yahoo/open_nsfw/master/nsfw_model/deploy.prototxt)
    *   🔗 weights: [resnet_50_1by2_nsfw.caffemodel](https://github.com/yahoo/open_nsfw/raw/master/nsfw_model/resnet_50_1by2_nsfw.caffemodel)
*   **OpenAI Whisper Base Model**: Used for offline audio speech-to-text processing (downloaded automatically at runtime via the `whisper` pip package).

---

## 2. AWS Features Required (Primary Hosted Tier)

If you plan to scale securely using enterprise cloud services, the "AWS mode" utilizes the following components:
*   **AWS Rekognition**: Used for highly accurate image and video moderation, returning detailed content labels and explicit content warnings.
*   **AWS Comprehend**: Used to compute textual safety scores, entity abstraction, and toxicity rating without stressing standard LLM limits.
*   **AWS Transcribe**: Used for heavy batch transcription of long audio or video uploads natively in the cloud.

---

## 3. "Hard Fallback" Architecture Details (Zero AWS Scenario)

The application possesses a highly fault-tolerant architecture. If AWS is absent (i.e., `AWS_ACCESS_KEY_ID` isn't provided or fails), the application executes **Hard Fallbacks** seamlessly through its internally designed 3-Tier Multi-Modal pipeline:

### A. Vision & Image Moderation Fallback
1.  **Semantic Context (Gemini Vision)**: Replaces AWS Rekognition by dynamically prompting *gemini-2.0-flash* with the image bytes. It processes the visual context (distinguishing between real gore vs. a Renaissance painting, analyzing weapons/NSFW) and streams a safety decision.
2.  **OpenCV Heuristics (`cv2`)**: A lightning-fast Edge prefilter checks raw array values. It calculates "skin-ratios", "red-to-dark ratios for blood vs. flowers", and uses the downloaded **Yahoo NSFW ResNet-50 dataset** to reject or flag explicit images instantaneously.

### B. Text & Text Toxicity Fallback
1.  **LocalMod Engine**: Instead of AWS Comprehend, it defaults to a local offline heuristic pipeline for extreme edge phrases and basic hate speech filtering without network latency.
2.  **LLM Multi-Agent System**: Prompts Groq or Gemini passing the flagged text to return a JSON evaluation of `Flags:[], Decision: ALLOW | ESCALATE` for deeper context modeling.

### C. Audio & Transcription Fallback
1.  **OpenAI Whisper (Local Execution)**: Replaces AWS Transcribe by loading `whisper ("base")` in Python memory natively. It captures audio chunks locally creating timestamps mapped against spoken transcripts.
2.  **Google Speech Recognition Free Tier**: The ultimate final fallback; an open web API utilized through `speech_recognition` if local memory exhaustion occurs during Whisper loading.

---

## 4. Social Media Integrations & Additional Configurations

Beyond the AI models and APIs, deploying the full feature set (such as cross-platform posting and storage) requires the following configurations:

### Social Media OAuth Apps
To enable posting and social interactions, you need to configure developer apps for the respective platforms:
*   **LinkedIn Developer App**: Required to acquire `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET`.
    *   🔗 [Create App at LinkedIn Developers](https://www.linkedin.com/developers/)
*   **Facebook/Instagram App**: Required to acquire `FACEBOOK_APP_ID` and `FACEBOOK_APP_SECRET`.
    *   🔗 [Create App at Meta Developers](https://developers.facebook.com/)
*   **Twitter/X Integration**: The system natively uses `twikit` to bypass API limits. No API Key is needed; it simply requires your `TWITTER_USERNAME`, `TWITTER_EMAIL`, and `TWITTER_PASSWORD` to generate a secure local cookie session.

### Storage Options
The application gracefully falls back to local disk storage (`./uploads`), but supports cloud storage:
*   **AWS S3**: Bucket name required if utilizing the primary AWS stack.
*   **Firebase Storage** *(Optional)*: Bucket name and `serviceAccountKey.json` local path required if you choose to use Firebase over AWS for media storage.

### Database
*   **Zero-Setup**: The platform is built to run entirely offline out-of-the-box using an async **SQLite** database (`aiosqlite`).
*   **Production Scaling**: Can be securely connected to a persistent **PostgreSQL** or **MySQL** server by updating the `DATABASE_URL` environment variable.

### Web & Operations (Optional)
*   **Sentry DSN**: For bug tracking in production.
*   **SMTP Mail Server**: Details (like Gmail App Passwords) for sending notification emails.
*   **Redis**: For caching rate-limits and LLM generations (If `CACHE_ENABLED=true`).
