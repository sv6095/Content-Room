# Content Room — Detailed Project Overview

> **Content Room** is a full-stack, AI-powered content management platform built specifically for digital creators, social media managers, and marketers — with a strong focus on the **Indian creator ecosystem**. It combines content generation, safety moderation, competitive intelligence, advanced scheduling, and next-generation AI labs all into one unified product.

---

## 🌟 What Is Content Room?

Content Room solves a real problem for creators: **the entire content workflow is fragmented**. You write captions in one tool, check safety in another, plan your calendar elsewhere, and post manually. Content Room brings all of this together under one roof.

The platform lets you go from a raw idea all the way through AI-generated assets, safety verification, cultural adaptation, competitor insights, and finally scheduled publishing — without ever leaving the app. It is designed to support **India's diverse languages, regions, and cultural moments** (festivals, cricket seasons, regional events), making it uniquely suited for Bharat creators.

The application uses a **React + TypeScript** frontend served by Vite, communicating with a **Python FastAPI** backend that orchestrates multiple large language models, AWS cloud AI services, and specialized AI microservices.

---

## 🔐 Authentication & User System

Content Room is designed with a **no-gate philosophy**: most powerful features are completely accessible without creating an account. This reduces friction and lets creators start generating value immediately.

### Flexible Access Model
- **Without login**: Users can freely use the Creator Studio, Moderation, Competitor Intelligence, Content Calendar, Intelligence Hub, and Novel AI Lab.
- **With login**: Users gain access to content history, scheduled post management, saved content library, and personalized preferences.

### Security Infrastructure
- **JWT-based sessions**: Tokens are generated on login and automatically included in all API calls. Default expiry is 30 days, making sessions persistent and convenient.
- **Argon2 password hashing**: Argon2 is the winner of the Password Hashing Competition and is considered more secure than the commonly used bcrypt or SHA-based approaches. All user passwords are hashed with Argon2 before storage.
- **CORS protection**: The backend only accepts requests from configured origins, preventing cross-site attacks.
- **SQL injection prevention**: The SQLAlchemy ORM layer ensures all database queries are parameterized.
- **Input validation**: All incoming API requests are validated against Pydantic schemas, rejecting malformed data before it reaches business logic.

### Authentication Endpoints
- `POST /api/v1/auth/register` — Creates a new user with hashed credentials
- `POST /api/v1/auth/login` — Validates credentials, returns a JWT token
- `GET /api/v1/auth/profile` — Returns the logged-in user's profile data
- `POST /api/v1/auth/logout` — Invalidates the session

---

## ✨ Feature 1: Creator Studio

The Creator Studio is the primary content generation workspace. It is the most used feature and the first thing creators interact with.

### Content Type Selection
You begin by choosing what kind of content you are working with:
- **Text** — Blog posts, captions, news articles, scripts, social media copy
- **Image** — Photos, infographics, design mockups
- **Audio** — Podcasts, voice memos, recordings
- **Video** — Reels, clips, tutorials, ads

Selecting a type intelligently changes the upload interface and the context passed to the AI for better results.

### AI Generation Tools

Once content or a file is uploaded, you can trigger the following generators individually or all at once with a single "Generate All" button:

**Caption Generator**
- Takes your content and generates an attention-grabbing caption tailored for your chosen platform.
- Platform presets are built in so caption length is automatically respected: Twitter/X (280 chars), Instagram (2,200 chars), LinkedIn (3,000 chars), Facebook (63,206 chars), or a custom character length you set manually with a slider.
- The slider lets you fine-tune the exact length between 100 and 3,000 characters.

**Summary Generator**
- Condenses long-form content into a concise summary (around 150 words).
- Useful for creating "above the fold" descriptions, preview snippets, or newsletter summaries.

**Hashtag Generator**
- Analyzes the content topic and generates relevant, trending hashtags.
- You control the quantity with a slider from 3 to 20 hashtags.
- Output hashtags are displayed as clickable chips and can be copied in one click.

### AI Media Analysis Mode
When you upload an image, audio, or video file, you can toggle on **AI Media Analysis Mode**. In this mode, the AI analyzes the media file itself (not just your written description) to automatically extract understood content and then generate captions, summaries, and hashtags from that understanding. This means you can upload a photo and get a caption written for it — no text input needed. For video, sampled frames are analyzed and merged into a generation context.

### Multi-Language Translation
After generating your caption and summary, you can immediately translate the output into 8 major Indian languages with one click:
- Hindi (हिंदी)
- Telugu (తెలుగు)
- Tamil (தமிழ்)
- Bengali (বাংলা)
- Kannada (ಕನ್ನಡ)
- Malayalam (മലയാളം)
- Gujarati (ગુજરાતી)
- Odia (ଓଡ଼ିଆ)

Both the caption and summary are translated simultaneously. Translated text appears below the originals in a distinct green-tinted box and can be copied independently.

### Save to My Content
Any generated content can be saved to your personal content library (accessible when logged in). The original text, generated caption, summary, and hashtags are all stored together. From the studio, you can jump directly to viewing that saved item.

---

## 🛡️ Feature 2: Content Moderation

The Content Moderation module is a comprehensive safety analysis system that checks whether your content violates community guidelines, platform policies, or ethical standards — before you publish it.

### Supported Input Types
- **Text** — Paste any caption, script, post, or body of text for safety analysis.
- **Image** — Upload a photo or graphic file to be visually analyzed.
- **Audio** — Upload a recording; it is first transcribed to text, then moderated.
- **Video** — Upload a video clip; sampled frames are extracted and analyzed visually.
- **Multimodal (combined)** — You can provide two or more of the above simultaneously for a combined analysis that cross-references all inputs.

### AI Provider Stack
- **Primary**: AWS Rekognition for image moderation and sampled video frame moderation.
- **AWS Transcribe**: Converts audio to text for transcription-based moderation.
- **AWS Comprehend**: Performs sentiment analysis on text.
- **LLM Fallback**: OpenAI, Groq, or OpenRouter models are used as fallbacks if AWS services are unavailable or quota is exceeded.

### Decision Output
Every moderation check returns a clear verdict:
- ✅ **ALLOW** — Content is safe for publishing
- ⚠️ **FLAG** — Content may violate policies; human review recommended
- 🚫 **BLOCK** — Content definitively violates standards

The moderation panel also shows:
- **AI Analysis narrative**: A plain-English explanation of why the content was flagged
- **Flagged items list**: Specific phrases, elements, or labels that triggered concern
- **Audio transcript**: If audio was uploaded, the full transcription is shown
- **Processing time**: Displayed in milliseconds for transparency
- **Provider used**: Shows which AI service performed the analysis

---

## 🔍 Feature 3: Competitor Intelligence

This is a deep competitor analysis module that helps creators understand what their rivals are doing and identify strategic opportunities.

### How It Works
1. Paste any **public URL** (Instagram profile, Twitter/X handle, YouTube channel, LinkedIn page, blog, etc.)
2. Enter your **niche** for context (e.g., "Sustainable Fashion", "Personal Finance", "Tech Reviews")
3. Hit **Identify Gaps & Opportunities**

The backend scrapes available public data from the URL, runs it through the AI, and returns a rich structured analysis.

### Strategic Edge Report
The output is organized into three sections accessible by tab:

**🎯 Gaps Tab**
- Lists specific content opportunities where your competitor is weak or missing entirely.
- Each gap is labeled with an **IMPACT** rating (HIGH / MEDIUM / LOW) — how much your audience would value this content.
- Each gap is labeled with an **EFFORT** rating — how hard it would be to execute.
- Clicking a gap card reveals **"Your Move"** — a specific, actionable recommendation for how to exploit the gap.

**🗺️ Strategy Tab**
- Provides a written narrative of the competitor's overall content strategy.
- Shows a **Scorecard** with four metrics rated out of 100: Content Quality, Engagement, Consistency, and Innovation.
- Highlights the competitor's **strongest** and **weakest** metric for quick strategic orientation.

**🚀 Ideas Tab**
- Presents a list of **Winning Content Ideas** that you should create, inspired by the competitor's audience behavior but positioned specifically for your brand.
- Each idea shows its format type (Reel, Story, Blog, Thread, etc.), a description of why it wins, and a category tag (Quick Win, Credibility Boost, Engagement Driver, Long Game).
- Ideas can be **copied to clipboard** instantly or sent directly to the Content Calendar with one click.

---

## 📅 Feature 4: Content Calendar

The Content Calendar generates a complete, month-long publishing plan tailored to your specific niche.

### Generation Inputs
- **Month and Year**: Specify which month to plan for
- **Your Niche**: Enter your content category (Fashion, Finance, Gaming, etc.)
- **Goals**: Describe what you want to achieve this month (e.g., "grow followers by 20%", "launch a new product")

### What You Get
The AI generates a structured 30-day calendar with:
- **Daily post ideas** with specific topic recommendations
- **Indian festival integration**: Major festivals, regional events, and cultural occasions are automatically woven into the plan. For example, if it's October, Diwali content slots are included.
- **Content mix variety**: The calendar balances different formats (reels, stories, carousels, long-form) to keep audiences engaged throughout the month.
- **Export-ready format**: The output is rendered as clean Markdown that can be copied and pasted into any calendar or project management tool.

### Idea to Calendar Flow
Ideas discovered in Competitor Intelligence can be sent directly to the Content Calendar with one click, pre-filling the calendar generation form with the discovered idea as a seed.

---

## 📡 Feature 5: Content Scheduler

The Scheduler is where content planning is translated into a time-stamped publishing blueprint. Its unique feature is a mandatory **Pre-Flight Analysis** that runs before any item can be scheduled.

### The Pre-Flight System
Before scheduling anything, the system runs **6 AI checks in parallel** on your content:

1. **Anti-Cancel Shield** — Scans for flagged keywords, entities, and phrases that could trigger public backlash in the Indian context.
2. **Shadowban Prediction** — Estimates the probability (0–100%) that the content will be algorithmically suppressed on your chosen platform.
3. **Culture Adaptation** — Evaluates how well the content resonates for your target region and gives an alignment score.
4. **Content Safety (Moderation)** — Runs a standard safety check.
5. **Mental Health Tone Analysis** — Analyzes the emotional health of your language patterns and provides a creator wellbeing tip.
6. **Asset Spin-offs** — Instantly generates 3–4 quick content variations from your main post (for Twitter, LinkedIn, WhatsApp, etc.).

The Pre-Flight Report shows:
- **Overall Pass / Fail banner**
- **Cancel Risk**: LOW / MEDIUM / HIGH with color coding
- **Shadowban Probability**: Percentage with color-coded risk indicator
- **Safety Score**: 0–100 quality score
- **Alignment Score**: How culturally matched your content is to your region (0–100)
- **Sentiment**: POSITIVE / NEUTRAL / NEGATIVE
- **Quick Assets Generated count**

Each section is expandable to reveal full details. After reviewing the report, you either **Approve** (proceed to scheduling) or **Discard** (go back and edit).

### Scheduling Controls
The pre-flight supports the following configuration:
- **Platform**: Instagram, Facebook, Twitter/X, YouTube, LinkedIn
- **Language**: Full list of Indian and major world languages
- **Target Region**: City-level granularity (Mumbai, Delhi, Chennai, Kolkata, Bangalore, etc.)
- **Niche**: Optional content category for context
- **Festival**: Optional cultural event for context
- **Risk Level Dial**: A slider from 0 to 100 that you use to set how conservative (brand-safe) or aggressive (viral-chasing) the content should be

After approval, you set the **title**, **date**, **time**, and optionally attach a **media file**. Scheduled posts are displayed in a **grouped calendar view** organized by day.

---

## ⚡ Feature 6: Intelligence Hub

The Intelligence Hub is a suite of 6 specialized strategic AI tools for creators who want to make data-driven content decisions.

### Tab 1: Culture Engine
Rewrites any piece of content so that it emotionally resonates with a specific regional audience in India.

You provide:
- The original content
- Target region (e.g., "Chennai", "Gen-Z Delhi", "Rural Rajasthan")
- Optional festival or occasion context
- Optional content niche
- Output language (any Indian or global language)

The AI rewrites the content using regional tone, cultural idioms, festival references, and language-appropriate expression. Output includes:
- The culturally adapted version of the content
- An **Alignment Score** (0–100) showing how well it matches the target audience
- Tags showing which regional "hooks" were used
- Warnings if any regional taboos were triggered

### Tab 2: Risk vs. Reach
Gives you a **Risk Dial** (0–100 slider) to control how safe or how provocative your output is:
- 0–25: Brand-safe, professional, polished
- 26–50: Conversational, slightly opinionated
- 51–75: Bold, hook-driven, hot takes
- 76–100: Maximum impact, shock value

Enter your idea and set your desired risk level. The AI generates the content at exactly that risk appetite. Results show:
- **Safety Score** (how likely it passes moderation)
- **Estimated Engagement Probability** (% chance of high engagement)
- **Moderation Risk** (% chance of triggering platform flags)

### Tab 3: Anti-Cancel Shield
A reputational pre-screening tool for Indian digital creators.

Paste any draft content and the shield scans it for:
- **Flagged keywords** categorized as CRITICAL or WARNING severity, with category labels (hate speech, religious sensitivity, political danger, etc.)
- **Detected entities** — public figures, organizations, or communities mentioned in the content
- **Safe alternative suggestions** — rewritten versions or phrases to replace risky language
- **Overall risk verdict**: LOW, MEDIUM, or HIGH risk
- **Critical threat alert**: Triggers if the content contains violence, murder language, or hate speech that will almost certainly be actioned by platform Trust & Safety teams

### Tab 4: Asset Explosion
Takes one idea and instantly generates **12 platform-native content assets in parallel**.

The 12 asset types generated:
1. Tweet
2. Instagram Caption
3. LinkedIn Post
4. YouTube Title
5. YouTube Description
6. WhatsApp Status
7. Facebook Post
8. Reddit Headline
9. Email Subject Line
10. Blog Intro
11. Push Notification
12. Motion Graphics Script

Each asset is optimized for its specific platform's format, character limit, tone, and audience expectations. Assets are displayed in a 2-column grid with quality scores (0–100) and one-click copy buttons.

### Tab 5: Mental Health Meter
Analyzes a creator's recent post history to detect signs of creator burnout.

You paste 3 or more recent posts (separated by `---`). The AI analyzes:
- **Burnout Score** (0–100): A linguistic entropy-based score where higher means more burnout signals
- **Burnout Risk level**: LOW (healthy), MEDIUM (watch out), HIGH (burnout risk)
- **Linguistic Entropy**: Measures how repetitive, monotone, or chaotic the language patterns are
- **Sentiment Trend**: Shows whether the creator's emotional tone is declining over time
- **Personalized recommendations**: Specific advice for the creator's current state

### Tab 6: Shadowban Predictor
Analyzes content before it is posted to estimate the likelihood of it being algorithmically suppressed (shadowbanned) on your chosen platform.

Supports: Instagram, Facebook, Twitter/X, YouTube

Analysis returns:
- **Shadowban Probability**: Exact percentage
- **Risk Level**: LOW / MEDIUM / HIGH
- **Risk Factors**: Specific elements in the content causing concern
- **Risky Hashtags**: Individual hashtags flagged as potentially shadowban-triggering
- **AI Deep Analysis**: Full narrative explanation from the model
- **Recommendation**: Specific actions to reduce shadowban risk

---

## 🚀 Feature 7: Novel AI Lab

The Novel AI Lab houses the most experimental and cutting-edge multi-agent AI features on the platform. These tools go beyond single-model generation and use multi-agent pipelines.

### Tab 1: Signal Intelligence
Deploys a **3-agent swarm** to analyze one or more competitor social media handles or URLs.

The three agents run sequentially:
1. **🕵️ Scraper Agent** — Collects publicly available content data from the handles
2. **📊 Analyst Agent** — Identifies patterns, trends, content formats, and posting frequency
3. **🎯 Strategist Agent** — Creates a specific content brief for the user based on what is working for competitors

You can input multiple competitor handles at once, specify your niche, and target a specific Indian region. Each agent's output is displayed in its own card with copy functionality.

### Tab 2: Trend Injection RAG
Uses a **Retrieval-Augmented Generation (RAG)** system to inject hyper-local trend data into any piece of content.

How it works:
- Paste your existing content
- Choose a region (Mumbai, Delhi, Chennai, Kolkata, Bangalore, Hyderabad, Punjab, or Pan-India)
- Specify your creator niche
- The system retrieves current regional trends, local festivals, and cultural context, then re-writes your content to include them

Output shows:
- **Regional context tags** showing languages and festivals relevant to the region
- **Trending topics** in that region
- **Trend-enhanced version** of your original content

### Tab 3: Multimodal Production
Converts a single idea into multiple **production-ready content formats**.

You choose which of 6 format types to generate:
- **Podcast Script** — Full dialogue-ready script for audio recording
- **Video Storyboard** — Shot-by-shot visual breakdown for video production
- **Audio Narration** — Voice-over narration script
- **Multilingual Adaptation** — Content in 5 different languages simultaneously
- **Thumbnail Brief** — Creative direction for a YouTube or social media thumbnail
- **Motion Graphics Script** — Text and timing cues for animated content

You select your primary language and niche, then click to generate all selected formats in parallel. Each output is displayed with full markdown rendering and copy buttons.

### Tab 4: Platform Adapter
Takes one piece of content and produces platform-optimized versions for multiple social media networks simultaneously.

Select any combination of: Instagram, Facebook, YouTube, Twitter/X, LinkedIn

For each platform, the adapter:
- Rewrites the content to match that platform's tone, style, and format conventions
- Respects character limits and formatting norms
- Suggests a **recommended posting time** for peak engagement
- Labels each output as "ready to publish" or "failed"

### Tab 5: Burnout Predictor
A more advanced version of the Mental Health Meter with **schedule adaptation**.

You paste multiple recent posts (min 2), specify your niche and current weekly posting target. The system:
- Calculates a **Burnout Score** (0–100)
- Analyzes **linguistic entropy**, **sentiment drift**, and **content repetition index**
- Assigns a **Workload Mode**: RECOVERY (significant burnout detected), REDUCED (mild fatigue), or NORMAL (healthy)
- **Automatically adjusts your weekly posting target** down or up based on your wellbeing
- Generates a complete **Self-Evolving Weekly Schedule** — an AI-adapted plan that matches your current capacity

---

## 🗄️ Data Storage and Content Library

When users are logged in, all generated and processed content is stored in the database.

### Content Record Fields
Each saved content item stores:
- Content type (text / image / audio / video)
- Original source text
- AI-generated caption
- AI-generated summary
- Array of AI-generated hashtags
- Moderation status
- Workflow status
- Timestamps

### Scheduled Post Record Fields
Each scheduled post stores:
- Title
- Description / notes
- Scheduled date and time
- Platform target
- Status (pending / published / cancelled)
- Moderation pass/fail flag
- Optional media file attachment URL

The database switches automatically between **PostgreSQL** (production) and **SQLite** (development) based on environment configuration. All database operations use **async/await** patterns through SQLAlchemy's async engine, allowing high concurrency without blocking.

---

## 🌐 Social Platform Integration

The application provides OAuth and API connection infrastructure for major social platforms.

**Supported platforms:**
- **Twitter/X**: Connect and publish directly
- **Instagram**: OAuth URL generation for account connection
- **LinkedIn**: OAuth URL generation for account connection

Connection status for all linked platforms can be viewed from the Settings page. The `/api/v1/social/status` endpoint returns a live status dashboard of all platform connections.

---

## ⚙️ Settings & User Preferences

The Settings page gives logged-in users control over:
- **Profile**: Update display name and email address
- **Theme**: Toggle between Dark Mode and Light Mode
- **Language**: Choose the interface language preference
- **Platform Connections**: Link and manage social media accounts

---

## 🔁 AI Provider Fallback System

The backend never relies on a single AI provider. A smart fallback chain is in place:

1. **AWS Bedrock** (primary for many tasks)
2. **AWS Rekognition** (primary for image and video-frame moderation)
3. **OpenAI GPT models** (primary for text generation and competitor analysis)
4. **Groq** (fast inference fallback)
5. **OpenRouter** (model routing fallback)

If any provider fails (quota exceeded, timeout, error), the system automatically retries the next provider in the chain. This ensures near-zero downtime for users and graceful degradation.

---

## ⚡ Performance Architecture

The backend is built for high concurrency and low latency:

- **Async/Await throughout**: Every database call, external API call, and file operation uses Python's `asyncio`. This means thousands of simultaneous users can be served without thread blocking.
- **Parallel AI calls**: Any task that needs multiple AI results (e.g., generating caption + summary + hashtags simultaneously, or running all 6 pre-flight checks at once) fires off all API calls in parallel.
- **Connection pooling**: The database connection pool is managed by SQLAlchemy's async engine, reusing connections efficiently.
- **Rate limiting**: Built-in protection prevents any single user or IP from overwhelming the API.

On the frontend:
- **Code splitting**: React routes are automatically split so users only download the JavaScript they need for the current page.
- **React Query**: Server state is cached and invalidated intelligently, preventing unnecessary re-fetches.
- **Optimistic updates**: UI reflects changes instantly while the server processes in the background.

---

## 🎨 User Interface Design

The frontend is built as a modern, responsive single-page application with a strong visual identity.

**Design system**: TailwindCSS with a custom design token layer defines all colors, spacing, and typography. All components from shadcn/ui are pre-configured to follow this system.

**Dark / Light modes**: Both are fully supported and togglable from settings. The class-based dark mode ensures smooth transitions and full theme coverage.

**Navigation**: A persistent left sidebar lists all major sections. The sidebar collapses on mobile into a hidden drawer navigation. Each section is accessible at a distinct route:
- `/` — Landing page
- `/studio` — Creator Studio
- `/moderation` — Content Moderation
- `/competitor` — Competitor Intelligence
- `/calendar` — Content Calendar
- `/scheduler` — Content Scheduler
- `/intelligence` — Intelligence Hub
- `/novel` — Novel AI Lab
- `/settings` — Settings

**Responsive layout**: The interface is mobile-first. All grid layouts collapse to single columns on small screens, touch targets are large enough for mobile use, and the sidebar adapts to a bottom sheet on mobile.

**Feedback patterns**: Every async operation shows a loading spinner. Success and error states use toast notifications (via Sonner). Copy buttons confirm copies with a temporary checkmark icon. Empty states provide contextual guidance when no data is present.

---

## 🔧 Technology Stack Summary

| Layer | Technology | Purpose |
|---|---|---|
| Frontend framework | React 18 + TypeScript | Component-based UI with type safety |
| Build tool | Vite | Fast development server and production bundler |
| Routing | React Router v6 | Client-side navigation |
| Styling | TailwindCSS + shadcn/ui | Design system and pre-built components |
| Icons | Lucide React | Consistent icon set |
| State management | React Query + React Context | Server state caching + global auth/language state |
| Forms | React Hook Form + Zod | Performant forms with runtime validation |
| Markdown rendering | react-markdown | Rendering AI-generated markdown output |
| Backend framework | FastAPI (Python 3.10+) | High-performance async REST API |
| Server | Uvicorn (ASGI) | Production-grade async HTTP server |
| Database ORM | SQLAlchemy (async) | Type-safe database operations |
| Database (prod) | PostgreSQL via asyncpg | Relational data at scale |
| Database (dev) | SQLite via aiosqlite | Zero-setup local development |
| Authentication | python-jose (JWT) + Argon2 | Secure stateless sessions |
| AI (primary) | AWS Bedrock + Rekognition | Text generation plus image/video-frame moderation |
| AI (speech) | AWS Transcribe + Comprehend | Audio transcription and sentiment analysis |
| AI (fallbacks) | OpenAI, Groq, OpenRouter | Redundant text generation providers |
| HTTP client | aiohttp | Async external HTTP requests |
| Data validation | Pydantic v2 | Request/response schema enforcement |

---

## 📦 API Surface Summary

The backend exposes versioned RESTful endpoints under `/api/v1/`:

| Module | Base Path | Key Operations |
|---|---|---|
| Auth | `/auth` | Register, Login, Profile, Logout |
| Content Creation | `/create` | Caption, Summary, Hashtags, Rewrite, Extract+Generate (image/audio/video supported) |
| Moderation | `/moderate` | Text, Image, Audio, Video, Multimodal |
| Competitor | `/competitor` | Analyze URL |
| Calendar | `/calendar` | Generate monthly plan |
| Scheduler | `/schedule` | List, Create, Delete scheduled posts |
| Social | `/social` | Platform status, Twitter/Instagram/LinkedIn connect |
| Intelligence | `/intelligence` | Culture, Risk, Anti-Cancel, Assets, Mental Health, Shadowban |
| Novel | `/novel` | Signal Intel, Trend Injection, Multimodal, Platform Adapt, Burnout |
| Translation | `/translation` | Text translation to any language |
| History | `/history` | User content history (auth required) |
| Pipeline | `/pipeline` | Run full pre-flight analysis |
| Analytics | `/analytics` | Usage analytics data |

---

*Content Room is built for the next generation of Indian digital creators — combining the power of modern AI with deep cultural intelligence.*
