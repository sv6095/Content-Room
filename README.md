
**CONTENT ROOM**

*Complete Product & Architecture Overview*

|<p>**80M+**</p><p>Indian Creators</p>|<p>**7**</p><p>Core Features</p>|<p>**9**</p><p>Indian Languages</p>|<p>**13**</p><p>AWS Services</p>|
| :-: | :-: | :-: | :-: |

**India's First AI-Powered Content Workflow Platform for the Creator Economy**

*Hackathon Submission 2025  ·  Confidential*


# **1. What Is Content Room?**
Content Room is a full-stack, AI-powered content management platform built specifically for digital creators, social media managers, and marketers — with a deep focus on the Indian creator ecosystem. It solves the core problem facing every creator today: the entire content workflow is fragmented. You write captions in one tool, check safety in another, plan your calendar elsewhere, and post manually.

Content Room brings all of this together under one roof. The platform lets you go from a raw idea all the way through AI-generated assets, safety verification, cultural adaptation, competitor insights, and scheduled publishing — without ever leaving the app.

|**Core Thesis**|
| :- |
|India's 80M+ content creators operate in one of the world's most linguistically complex, culturally fragmented,|
|and socially sensitive environments. A post that resonates in Tamil Nadu can be deeply offensive in Punjab.|
|A caption that performs on Instagram can trigger a shadowban on YouTube. A creator burning out over months|
|of overposting leaves measurable linguistic signals that no existing platform detects.|
||
|Content Room was built to solve all of this — simultaneously — in one platform.|

## **1.1 The Fragmentation Problem**
Before Content Room, a professional Indian creator had to manage this workflow across 8+ separate tools:

|**Workflow Step**|**Existing Tool**|**Problem**|
| :- | :- | :- |
|Caption writing|ChatGPT / Jasper|No Indian cultural context, no platform optimization|
|Content safety check|Manual review|No automated moderation, no shadowban awareness|
|Regional adaptation|Google Translate|Translation without cultural nuance — often harmful|
|Competitor research|Manual browsing|Hours of manual work with no structured output|
|Content calendar|Notion / Google Sheets|No AI generation, no festival awareness|
|Scheduling|Buffer / Hootsuite|No pre-flight safety, no Indian language support|
|Creator wellness|Nothing|No tool exists for this — world gap|
|Multi-platform repurposing|Manual rewriting|No simultaneous platform-specific adaptation|

## **1.2 The Content Room Solution**
Content Room collapses this 8-tool workflow into a single platform with 7 deeply integrated feature modules, each communicating with the others. Ideas from Competitor Intelligence flow to the Content Calendar. Pre-flight results from the Scheduler link to Intelligence Hub tools. Creator wellness data from the Mental Health Meter informs the Burnout Predictor's schedule adaptation.

## **1.3 Technology Foundation**

|<p>**Frontend**</p><p>React 18 + TypeScript</p><p>Vite build tool</p><p>TailwindCSS + shadcn/ui</p><p>React Query + React Hook Form</p><p>React Router v6</p><p>Lucide React icons</p>|<p>**Backend**</p><p>Python FastAPI (async)</p><p>Uvicorn ASGI server</p><p>SQLAlchemy async ORM</p><p>PostgreSQL (prod) / SQLite (dev)</p><p>python-jose JWT + Argon2</p><p>Pydantic v2 validation</p>|
| :- | :- |

# **2. Authentication & User System**

|**No-Gate Philosophy**|
| :- |
|Most of Content Room's powerful features are completely accessible without creating an account.|
|Creator Studio, Moderation, Competitor Intelligence, Content Calendar, Intelligence Hub, and Novel AI Lab|
|all work without login. This reduces friction and lets creators start generating value immediately.|
|Login unlocks: content history, scheduled post management, saved content library, and preferences.|

## **2.1 Security Architecture**

|**Security Layer**|**Technology**|**Detail**|
| :- | :- | :- |
|Session management|JWT (python-jose)|30-day default expiry — persistent, convenient sessions. Token auto-included in all API calls.|
|Password hashing|Argon2|Winner of the Password Hashing Competition. More secure than bcrypt or SHA-based approaches. All passwords hashed before storage.|
|Cross-origin protection|CORS middleware|Backend only accepts requests from configured origins. Prevents cross-site request forgery.|
|SQL injection prevention|SQLAlchemy ORM|All database queries parameterized through ORM layer — no raw SQL construction.|
|Input validation|Pydantic v2 schemas|All incoming API requests validated against strict schemas. Malformed data rejected before reaching business logic.|

## **2.2 Authentication Endpoints**

|**Method**|**Endpoint**|**Function**|
| :- | :- | :- |
|POST|/api/v1/auth/register|Creates new user with hashed Argon2 credentials|
|POST|/api/v1/auth/login|Validates credentials, returns JWT token|
|GET|/api/v1/auth/profile|Returns logged-in user's profile data (auth required)|
|POST|/api/v1/auth/logout|Invalidates the active session|

|**01**|**✨  Creator Studio**|
| :-: | :- |

The Creator Studio is the primary content generation workspace — the first feature creators interact with and the most frequently used. It transforms raw ideas or uploaded media into polished, platform-ready content across multiple languages.

## **3.1 Content Type Selection**
The workspace begins with choosing the content type being worked on. This selection intelligently changes the upload interface and the context passed to AI for better generation results:

|**Type**|**Use Cases**|**AI Behaviour**|
| :- | :- | :- |
|Text|Blog posts, captions, news articles, scripts, social media copy|Analyzes written content directly for generation|
|Image|Photos, infographics, design mockups|Visual analysis mode available — AI reads the image itself|
|Audio|Podcasts, voice memos, recordings|Transcribed first, then analyzed for generation context|
|Video|Reels, clips, tutorials, ads|Frame extraction + transcription for full context analysis|

## **3.2 AI Generation Tools**
Once content or a file is uploaded, generators can be triggered individually or all at once with a single "Generate All" button:

### **Caption Generator**
- Generates attention-grabbing captions tailored to the chosen platform.
- Built-in platform presets automatically respect character limits:
- Twitter/X: 280 characters
- Instagram: 2,200 characters
- LinkedIn: 3,000 characters
- Facebook: 63,206 characters
- Custom: set manually via a 100–3,000 character slider

### **Summary Generator**
- Condenses long-form content into ~150-word concise summaries.
- Designed for 'above the fold' descriptions, preview snippets, and newsletter summaries.

### **Hashtag Generator**
- Analyzes content topic and generates relevant, trending hashtags.
- Quantity controlled by a slider from 3 to 20 hashtags.
- Output displayed as clickable chips with one-click copy.

## **3.3 AI Media Analysis Mode**

|**How Media Analysis Works**|
| :- |
|When an image, audio, or video file is uploaded, toggling AI Media Analysis Mode causes the AI|
|to analyze the media file itself — not just a text description — and automatically extract understood|
|content to generate captions, summaries, and hashtags from that understanding.|
||
|This means: upload a photo → get a caption written for it. No text input required.|
|Audio is transcribed first. Video frames are extracted and analyzed visually.|

## **3.4 Multi-Language Translation**
After generating caption and summary, one-click translation into 8 major Indian languages is available simultaneously:

|**Language**|**Script**|**Region**|
| :- | :- | :- |
|Hindi|Devanagari (हिंदी)|Pan-India — largest reach|
|Telugu|Telugu (తెలుగు)|Andhra Pradesh, Telangana|
|Tamil|Tamil (தமிழ்)|Tamil Nadu, Sri Lanka|
|Bengali|Bengali (বাংলা)|West Bengal, Bangladesh|
|Kannada|Kannada (ಕನ್ನಡ)|Karnataka|
|Malayalam|Malayalam (മലയാളം)|Kerala|
|Gujarati|Gujarati (ગુજરાતી)|Gujarat|
|Odia|Odia (ଓଡ଼ିଆ)|Odisha|

Both the caption and summary are translated simultaneously. Translated text appears in a distinct green-tinted box and can be copied independently.

## **3.5 Content Library**
Any generated content can be saved to the personal content library (when logged in). The original text, generated caption, summary, and hashtags are stored together as a single content record. Direct navigation to the saved item is available from within the Studio.

|**02**|**🛡️  Content Moderation**|
| :-: | :- |

The Content Moderation module is a comprehensive safety analysis system that checks whether content violates community guidelines, platform policies, or ethical standards — before publication. It supports all four content modalities and provides clear, actionable verdicts.

## **4.1 Supported Input Types**

|**Modality**|**How It's Processed**|**AI Services Used**|
| :- | :- | :- |
|Text|Direct analysis of pasted text content|AWS Comprehend + LLM fallback|
|Image|Visual analysis of uploaded photo or graphic|AWS Rekognition (primary)|
|Audio|Transcribed to text first, then moderated|AWS Transcribe → AWS Comprehend|
|Video|Frames extracted and analyzed visually|AWS Rekognition (frame-by-frame)|
|Multimodal|Two or more inputs analyzed simultaneously — results cross-referenced|All of the above in parallel|

## **4.2 AI Provider Stack**
- Primary image/video: AWS Rekognition — production-grade NSFW, violence, and unsafe content detection.
- Audio transcription: AWS Transcribe — converts audio to text for text-based moderation pipeline.
- Text sentiment: AWS Comprehend — structured sentiment and toxicity scoring.
- Fallback chain: OpenAI → Groq → OpenRouter — automatic failover if AWS services are unavailable or quota exceeded.

## **4.3 Decision Output**

|<p>**Three-Level Verdict**</p><p>✅ ALLOW — Content is safe for publishing</p><p>⚠️ FLAG — May violate policies; human review recommended</p><p>🚫 BLOCK — Definitively violates standards</p>|<p>**Supporting Detail Panel**</p><p>AI narrative explanation in plain English</p><p>Flagged items list (specific triggers)</p><p>Full audio transcript (if audio uploaded)</p><p>Processing time in milliseconds</p><p>Provider used (for transparency)</p>|
| :- | :- |

|**03**|**🔍  Competitor Intelligence**|
| :-: | :- |

The Competitor Intelligence module is a deep strategic analysis system. Paste any public URL — Instagram profile, Twitter/X handle, YouTube channel, LinkedIn page, or blog — enter your niche for context, and receive a structured multi-tab analysis of gaps, strategy, and actionable content ideas.

## **5.1 The Three Strategic Tabs**
### **Gaps Tab — Where Competitors Are Weak**
- Lists specific content opportunities where the competitor is weak or missing entirely.
- Each gap is labeled with an IMPACT rating (HIGH / MEDIUM / LOW) — how much your audience would value this content.
- Each gap is labeled with an EFFORT rating — how hard it would be to execute.
- Clicking a gap card reveals "Your Move" — a specific, actionable recommendation for how to exploit the gap.

### **Strategy Tab — Competitor's Overall Approach**
- Written narrative of the competitor's overall content strategy.
- Scorecard with four metrics rated out of 100: Content Quality, Engagement, Consistency, and Innovation.
- Highlights the competitor's strongest and weakest metric for quick strategic orientation.

### **Ideas Tab — What You Should Create**
- List of Winning Content Ideas inspired by the competitor's audience behavior but positioned for your brand.
- Each idea shows: format type (Reel, Story, Blog, Thread, etc.), description of why it wins, and a category tag.

|**Category Tag**|**Meaning**|
| :- | :- |
|Quick Win|High impact, low effort — execute this week|
|Credibility Boost|Positions you as an authority in the niche|
|Engagement Driver|Optimized for comments, shares, saves|
|Long Game|Slower burn but builds lasting audience loyalty|

- Ideas can be copied to clipboard instantly or sent directly to the Content Calendar with one click.

|**04**|**📅  Content Calendar**|
| :-: | :- |

The Content Calendar generates a complete, month-long publishing plan tailored to the creator's specific niche, goals, and the cultural calendar of India.

## **6.1 Generation Inputs**

|**Input**|**Purpose**|
| :- | :- |
|Month and Year|Specifies which month to plan — calendar is generated with date-accurate entries|
|Your Niche|Content category (Fashion, Finance, Gaming, etc.) — informs topic selection and tone|
|Goals|What you want to achieve (e.g., 'grow followers by 20%', 'launch a product') — shapes content mix|

## **6.2 What You Get**
- Daily post ideas with specific topic recommendations for each day of the month.
- Indian festival integration: Major festivals, regional events, and cultural occasions automatically woven into the plan. October → Diwali content slots included. March → Holi content slots included.
- Content mix variety: Calendar balances formats (reels, stories, carousels, long-form) to maintain audience engagement throughout the month.
- Export-ready format: Output rendered as clean Markdown that can be copied directly into any calendar or project management tool.

|**Idea-to-Calendar Flow**|
| :- |
|Ideas discovered in Competitor Intelligence can be sent directly to the Content Calendar with one click.|
|This pre-fills the calendar generation form with the discovered idea as a seed topic,|
|creating a seamless pipeline from competitor research to your own content plan.|

|**05**|**📡  Content Scheduler**|
| :-: | :- |

The Scheduler translates content planning into time-stamped publishing blueprints. Its defining feature is a mandatory Pre-Flight Analysis that runs before any item can be scheduled — ensuring nothing goes live that hasn't passed a 6-point AI safety review.

## **7.1 The Pre-Flight System — 6 Parallel AI Checks**
Before scheduling anything, the system runs 6 AI checks in parallel on your content:

|**#**|**Check**|**What It Detects**|**Output**|
| :- | :- | :- | :- |
|1|Anti-Cancel Shield|Flagged keywords, entities, and phrases likely to trigger public backlash in the Indian context|Risk level: LOW / MEDIUM / HIGH|
|2|Shadowban Prediction|Algorithmic suppression likelihood on the chosen platform based on content signals|Probability percentage (0–100%)|
|3|Culture Adaptation|Regional resonance for the target city/audience — cultural alignment scoring|Alignment Score (0–100)|
|4|Content Safety|Standard safety and moderation check across text and media|Safety Score (0–100)|
|5|Mental Health Tone|Emotional health of language patterns — creator wellbeing signals in the writing|Sentiment + wellbeing tip|
|6|Asset Spin-offs|Automatically generates 3–4 quick content variations from the main post|Ready-to-use variations for Twitter, LinkedIn, WhatsApp|

## **7.2 Pre-Flight Configuration**
The pre-flight system is configured per submission — giving creators precise control over the analysis context:

|**Setting**|**Options**|
| :- | :- |
|Platform|Instagram, Facebook, Twitter/X, YouTube, LinkedIn|
|Language|Full list of Indian and major world languages|
|Target Region|City-level: Mumbai, Delhi, Chennai, Kolkata, Bangalore + more|
|Niche|Optional content category for context-aware analysis|
|Festival|Optional cultural event to calibrate sensitivity thresholds|
|Risk Level Dial|Slider 0–100: 0 = ultra-conservative brand-safe, 100 = maximum viral aggression|

## **7.3 Pre-Flight Report & Decision Flow**

|**The Pre-Flight Report Shows**|
| :- |
|Overall Pass / Fail banner — immediate go / no-go verdict|
|Cancel Risk: LOW / MEDIUM / HIGH with color coding|
|Shadowban Probability: Percentage with color-coded risk indicator|
|Safety Score: 0–100 content quality and compliance score|
|Alignment Score: Cultural match to target region (0–100)|
|Sentiment: POSITIVE / NEUTRAL / NEGATIVE|
|Quick Assets Generated: Count of spin-off variations ready to use|
||
|Each section is expandable for full detail. After reviewing, the creator either:|
|`  `✅ APPROVE — Content proceeds to scheduling (set title, date, time, optional media)|
|`  `❌ DISCARD — Returns to editing with specific feedback on what to fix|

Approved scheduled posts are displayed in a grouped calendar view organized by day.

|**06**|**⚡  Intelligence Hub**|
| :-: | :- |

The Intelligence Hub is a suite of 6 specialized strategic AI tools for creators who want to make data-driven content decisions. Each tab is an independent powerful capability; together they form a comprehensive creator intelligence layer.

## **8.1 Tab 1: Culture Engine**
Rewrites any piece of content so that it emotionally resonates with a specific regional audience in India.

|**Input**|**Detail**|
| :- | :- |
|Original content|Paste any draft caption, post, or script|
|Target region|e.g., 'Chennai', 'Gen-Z Delhi', 'Rural Rajasthan'|
|Festival / occasion context|Optional — calibrates tone for cultural moments|
|Content niche|Optional — informs vocabulary and references|
|Output language|Any Indian or global language|

Output includes the culturally adapted content, an Alignment Score (0–100), tags showing which regional 'hooks' were used, and warnings if any regional taboos were triggered.

## **8.2 Tab 2: Risk vs. Reach**
Gives creators a Risk Dial (0–100 slider) to control how safe or provocative the output is:

|**Risk Range**|**Tone Profile**|**Best For**|
| :- | :- | :- |
|0–25|Brand-safe, professional, polished|Corporate brands, family-friendly creators|
|26–50|Conversational, slightly opinionated|Lifestyle creators, personal brands|
|51–75|Bold, hook-driven, hot takes|Tech/finance commentators, debate creators|
|76–100|Maximum impact, shock value|Viral-first creators, controversy-native channels|

Results show: Safety Score (passes moderation?), Estimated Engagement Probability (% chance of high engagement), and Moderation Risk (% chance of triggering platform flags).

## **8.3 Tab 3: Anti-Cancel Shield**
A reputational pre-screening tool specifically for Indian digital creators. Scans draft content for:

- Flagged keywords categorized as CRITICAL (immediate action) or WARNING (review needed) severity, with category labels: hate speech, religious sensitivity, political danger, etc.
- Detected entities: public figures, organizations, or communities mentioned in the content.
- Safe alternative suggestions: rewritten versions or specific phrases to replace risky language.
- Overall risk verdict: LOW, MEDIUM, or HIGH risk.
- Critical threat alert: triggers if content contains violence, murder language, or hate speech that will almost certainly be actioned by platform Trust & Safety teams.

## **8.4 Tab 4: Asset Explosion**
Takes one idea and instantly generates 12 platform-native content assets in parallel:

|**#**|**Asset Type**|**#**|**Asset Type**|
| :- | :- | :- | :- |
|1|Tweet (Twitter/X)|7|Facebook Post|
|2|Instagram Caption|8|Reddit Headline|
|3|LinkedIn Post|9|Email Subject Line|
|4|YouTube Title|10|Blog Intro|
|5|YouTube Description|11|Push Notification|
|6|WhatsApp Status|12|Motion Graphics Script|

Each asset is optimized for its platform's format, character limit, tone, and audience expectations. Assets display in a 2-column grid with quality scores (0–100) and one-click copy buttons.

## **8.5 Tab 5: Mental Health Meter**
Analyzes a creator's recent post history to detect early signs of burnout using linguistic entropy analysis. Paste 3 or more recent posts (separated by ---). Output includes:

- Burnout Score (0–100): Higher score = more burnout signals detected.
- Burnout Risk level: LOW (healthy), MEDIUM (watch out), HIGH (burnout risk).
- Linguistic Entropy: Measures how repetitive, monotone, or chaotic language patterns are.
- Sentiment Trend: Shows whether the creator's emotional tone is declining over time.
- Personalized recommendations: Specific advice calibrated to the creator's current mental state.

## **8.6 Tab 6: Shadowban Predictor**
Analyzes content before posting to estimate the likelihood of algorithmic suppression on Instagram, Facebook, Twitter/X, or YouTube. Returns:

- Shadowban Probability: Exact percentage.
- Risk Level: LOW / MEDIUM / HIGH.
- Risk Factors: Specific elements in the content causing concern.
- Risky Hashtags: Individual hashtags flagged as potentially shadowban-triggering.
- AI Deep Analysis: Full narrative explanation of why the risk exists.
- Recommendation: Specific actions to reduce shadowban risk before posting.

|**07**|**🚀  Novel AI Lab**|
| :-: | :- |

The Novel AI Lab houses the most experimental and cutting-edge multi-agent AI features on the platform. These tools go beyond single-model generation and use multi-agent pipelines, RAG systems, and parallel production workflows.

## **9.1 Tab 1: Signal Intelligence — 3-Agent Swarm**
Deploys a 3-agent AI swarm to analyze one or more competitor social media handles or URLs. Agents run sequentially, with each building on the previous output:

|**Agent**|**Name**|**What It Does**|
| :- | :- | :- |
|Agent 1|🕵️ Scraper Agent|Collects publicly available content data from the handles/URLs|
|Agent 2|📊 Analyst Agent|Identifies patterns, trends, content formats, and posting frequency across the scraped data|
|Agent 3|🎯 Strategist Agent|Creates a specific, personalized content brief for the user based on what is working for competitors|

Multiple competitor handles can be analyzed simultaneously. Niche and target Indian region can be specified. Each agent's output is displayed in its own card with copy functionality.

## **9.2 Tab 2: Trend Injection RAG**
Uses a Retrieval-Augmented Generation (RAG) system to inject hyper-local, real-time trend data into existing content:

- Paste existing content → choose a region → specify niche.
- System retrieves current regional trends, local festivals, and cultural context.
- Rewrites the content to include trend-relevant references naturally.
- Output shows: regional context tags (languages and festivals), trending topics list, and the trend-enhanced content version.
- Supported regions: Mumbai, Delhi, Chennai, Kolkata, Bangalore, Hyderabad, Punjab, and Pan-India.

## **9.3 Tab 3: Multimodal Production**
Converts a single idea into multiple production-ready content formats simultaneously. Choose any combination of 6 format types:

|**Format**|**Output Description**|
| :- | :- |
|Podcast Script|Full dialogue-ready script for audio recording — includes host prompts, talking points, and timing cues|
|Video Storyboard|Shot-by-shot visual breakdown for video production — scene descriptions, camera directions, duration per shot|
|Audio Narration|Voice-over narration script optimized for natural spoken delivery|
|Multilingual Adaptation|Content rewritten in 5 different languages simultaneously|
|Thumbnail Brief|Complete creative direction for a YouTube or social media thumbnail — composition, text, color, mood|
|Motion Graphics Script|Text and timing cues for animated content — transitions, text-on-screen moments, animation beats|

Select primary language and niche, then generate all selected formats in parallel. Each output is displayed with full markdown rendering and copy buttons.

## **9.4 Tab 4: Platform Adapter**
Takes one piece of content and produces platform-optimized versions for multiple social networks simultaneously. Select any combination of: Instagram, Facebook, YouTube, Twitter/X, LinkedIn. For each platform, the adapter:

- Rewrites content to match that platform's tone, style, and format conventions.
- Respects character limits and formatting norms (hashtag placement, emoji usage, link handling).
- Suggests a recommended posting time for peak engagement on that platform.
- Labels each output as 'ready to publish' or 'failed' with a reason.

## **9.5 Tab 5: Burnout Predictor (Advanced)**
A more advanced version of the Mental Health Meter that goes beyond diagnosis to generate a self-adapting schedule. Paste multiple recent posts, specify niche and current weekly posting target. System outputs:

|**Output**|**Detail**|
| :- | :- |
|Burnout Score (0–100)|Linguistic entropy-based analysis across pasted posts|
|Linguistic Entropy|Measures repetitiveness, monotone patterns, and chaotic language signals|
|Sentiment Drift|Tracks whether emotional tone is declining across posts over time|
|Content Repetition Index|Measures how similar posts are becoming to each other|
|Workload Mode|RECOVERY (significant burnout — reduce sharply), REDUCED (mild fatigue — scale back), NORMAL (healthy — maintain)|
|Adapted Posting Target|AI automatically adjusts your weekly target down or up based on wellbeing analysis|
|Self-Evolving Weekly Schedule|Complete AI-generated schedule matching your current capacity — specific days, times, and content types|

# **10. Data Storage & Content Library**
All generated and processed content is stored in the database when users are logged in, using SQLAlchemy's async engine for high concurrency without blocking. The database switches automatically between PostgreSQL (production) and SQLite (development) based on environment configuration.

## **10.1 Content Record Schema**

|**Field**|**Type**|**Purpose**|
| :- | :- | :- |
|content\_type|enum|text / image / audio / video — determines how it was generated|
|source\_text|text|Original input text provided by the creator|
|generated\_caption|text|AI-generated caption output|
|generated\_summary|text|AI-generated ~150 word summary|
|hashtags|array|Array of AI-generated hashtag strings|
|moderation\_status|enum|ALLOW / FLAG / BLOCK — result from moderation check|
|workflow\_status|enum|draft / scheduled / published / cancelled|
|created\_at / updated\_at|timestamp|Audit trail for content history|

## **10.2 Scheduled Post Schema**

|**Field**|**Type**|**Purpose**|
| :- | :- | :- |
|title|string|Creator-defined post title for identification|
|description|text|Notes or context about the scheduled post|
|scheduled\_at|datetime|Precise publication date and time|
|platform|enum|Target platform: Instagram / Facebook / Twitter / YouTube / LinkedIn|
|status|enum|pending / published / cancelled|
|moderation\_passed|boolean|Whether pre-flight analysis was passed|
|media\_url|string|Optional attached media file URL in S3|

# **11. Social Platform Integration & Settings**
## **11.1 Social Platform Connections**
OAuth and API connection infrastructure is provided for three major platforms. Connection status for all linked platforms is viewable from the Settings page via the /api/v1/social/status endpoint:

|**Platform**|**Connection Type**|**Capability**|
| :- | :- | :- |
|Twitter/X|OAuth + API credentials|Connect and publish directly from the Scheduler|
|Instagram|OAuth URL generation|Account connection for scheduled publishing|
|LinkedIn|OAuth URL generation|Account connection for scheduled publishing|

## **11.2 Settings Page**
- Profile: Update display name and email address.
- Theme: Toggle between Dark Mode and Light Mode — class-based theming with smooth transitions and full coverage.
- Language: Choose the interface language preference.
- Platform Connections: Link and manage connected social media accounts.

# **12. AI Provider Fallback System**
The backend never relies on a single AI provider. A smart fallback chain is in place — if any provider fails (quota exceeded, timeout, error), the system automatically retries the next provider in the chain, ensuring near-zero downtime for users and graceful degradation:

|**Fallback Chain (in order)**|
| :- |
|1\. AWS Bedrock — primary for most text generation tasks|
|2\. AWS Rekognition — primary for image and video moderation|
|3\. OpenAI GPT models — primary for text generation and competitor analysis fallback|
|4\. Groq — fast inference fallback when OpenAI is unavailable|
|5\. OpenRouter — model routing fallback as final catch-all|
||
|Automatic retry logic triggers on: quota exceeded, timeout, 5xx errors, model unavailability.|
|Fallback selection is invisible to the user — the experience remains consistent regardless of which provider serves the request.|

# **13. Performance Architecture**
## **13.1 Backend Performance**
- Async/Await throughout: Every database call, external API call, and file operation uses Python's asyncio. Thousands of simultaneous users can be served without thread blocking.
- Parallel AI calls: Tasks requiring multiple AI results (caption + summary + hashtags simultaneously, all 6 pre-flight checks at once) fire all API calls in parallel — not sequentially.
- Connection pooling: Database connection pool managed by SQLAlchemy's async engine, reusing connections efficiently across concurrent requests.
- Rate limiting: Built-in protection prevents any single user or IP from overwhelming the API — prevents abuse and ensures fair access.

## **13.2 Frontend Performance**
- Code splitting: React routes automatically split so users only download JavaScript for the current page — not the entire application.
- React Query: Server state is cached and invalidated intelligently, preventing unnecessary re-fetches on navigation.
- Optimistic updates: UI reflects changes instantly while the server processes in the background — perceived zero-latency interactions.

## **13.3 UI Design System**
- Design system: TailwindCSS with a custom design token layer defines all colors, spacing, and typography. shadcn/ui components are pre-configured to follow this system.
- Dark / Light modes: Both fully supported and togglable from Settings. Class-based dark mode ensures smooth transitions and full theme coverage.
- Responsive layout: Mobile-first design. All grid layouts collapse to single columns on small screens. Sidebar collapses to a hidden drawer navigation on mobile.
- Feedback patterns: Every async operation shows a loading spinner. Success and error states use toast notifications (Sonner). Copy buttons confirm with a temporary checkmark icon.

### **Application Routes**

|**Route**|**Module**|
| :- | :- |
|/|Landing page|
|/studio|Creator Studio|
|/moderation|Content Moderation|
|/competitor|Competitor Intelligence|
|/calendar|Content Calendar|
|/scheduler|Content Scheduler|
|/intelligence|Intelligence Hub|
|/novel|Novel AI Lab|
|/settings|Settings|

# **14. Complete Technology Stack**

|**Layer**|**Technology**|**Purpose**|
| :- | :- | :- |
|Frontend framework|React 18 + TypeScript|Component-based UI with full type safety|
|Build tool|Vite|Fast development server and optimized production bundler|
|Routing|React Router v6|Client-side navigation with code splitting|
|Styling|TailwindCSS + shadcn/ui|Utility-first design system with pre-built accessible components|
|Icons|Lucide React|Consistent, scalable icon set|
|State management|React Query + React Context|Server state caching + global auth and language state|
|Forms|React Hook Form + Zod|Performant forms with runtime schema validation|
|Markdown rendering|react-markdown|Rendering AI-generated markdown output in all tabs|
|Backend framework|FastAPI (Python 3.10+)|High-performance async REST API with auto OpenAPI docs|
|Server|Uvicorn (ASGI)|Production-grade async HTTP server|
|Database ORM|SQLAlchemy (async)|Type-safe async database operations|
|Database (prod)|PostgreSQL via asyncpg|Relational data at scale with async driver|
|Database (dev)|SQLite via aiosqlite|Zero-setup local development environment|
|Authentication|python-jose (JWT) + Argon2|Secure 30-day stateless sessions with modern password hashing|
|AI — primary generation|AWS Bedrock (Nova Lite/Pro)|Text generation, cultural rewriting, competitor analysis|
|AI — image/video safety|AWS Rekognition|Frame-level NSFW and violence detection|
|AI — audio|AWS Transcribe + Comprehend|Speech-to-text + sentiment and toxicity analysis|
|AI — translation|AWS Translate|Multilingual caption adaptation across 8+ Indian languages|
|AI — orchestration|AWS Step Functions|Parallel pre-flight pipeline with retries and timeouts|
|AI — fallbacks|OpenAI, Groq, OpenRouter|Redundant text generation providers — automatic failover|
|Scheduling|AWS EventBridge|Persistent serverless content publication scheduling|
|Storage|AWS S3|Media file storage with presigned URL direct upload|
|Database (cloud)|AWS DynamoDB|AI response caching and analysis result storage|
|HTTP client|aiohttp|Async external HTTP requests for competitor scraping|
|Data validation|Pydantic v2|Request/response schema enforcement throughout API|
|Monitoring|AWS CloudWatch|Lambda logs, API latency, pipeline debugging|

# **15. API Surface Summary**
The backend exposes versioned RESTful endpoints under /api/v1/:

|**Module**|**Base Path**|**Key Operations**|
| :- | :- | :- |
|Auth|/auth|Register, Login, Profile, Logout|
|Content Creation|/create|Caption, Summary, Hashtags, Rewrite, Media Extract+Generate|
|Moderation|/moderate|Text, Image, Audio, Video, Multimodal combined|
|Competitor|/competitor|Analyze any public URL with niche context|
|Calendar|/calendar|Generate monthly content plan with festival integration|
|Scheduler|/schedule|List, Create, Delete scheduled posts; Pre-flight pipeline|
|Social|/social|Platform status, Twitter / Instagram / LinkedIn OAuth connect|
|Intelligence|/intelligence|Culture Engine, Risk vs Reach, Anti-Cancel, Asset Explosion, Mental Health, Shadowban|
|Novel AI Lab|/novel|Signal Intelligence, Trend Injection, Multimodal Production, Platform Adapter, Burnout Predictor|
|Translation|/translation|Text translation to any supported language|
|History|/history|User content history (authentication required)|
|Pipeline|/pipeline|Run full pre-flight analysis as a single endpoint|
|Analytics|/analytics|Usage analytics and performance data|

# **16. AWS Architecture — Every Decision Explained**

|**Architecture Philosophy**|
| :- |
|Content Room follows three architectural principles:|
|`  `1. Serverless-first: Zero infrastructure management — scales from 0 to 10M users without provisioning a server.|
|`  `2. Event-driven: Every component responds to events — no polling, no idle costs, no wasted compute.|
|`  `3. AI-native: Every layer is designed to carry AI workloads — from CDN edge to database cache layer.|

## **16.1 Frontend: React + Vite on S3 + CloudFront**
- Static Hosting Eliminates Server Cost: React app deployed as static files to S3. No web servers to manage, patch, or scale. Costs fractions of a cent per GB.
- CloudFront for Bharat Latency: 400+ global edge locations ensure creators in Tier 2 cities (Indore, Patna, Nagpur) get sub-100ms page loads — identical to Mumbai creators. Without CDN, rural creators see 3-4x higher latency.
- Separation of Concerns: Frontend never touches a database or AI service directly. All intelligence flows through the API layer — secure by design.

## **16.2 Media Upload: Presigned S3 URLs**
- Bypassing API Size Limits: API Gateway has a hard 10MB payload limit. Presigned URLs allow direct client-to-S3 uploads — completely bypassing this ceiling for large media files.
- Event-Driven Processing: S3's native event trigger system fires a Lambda function the moment a file lands in the bucket — immediate upload confirmation while moderation runs in the background.
- Security Model: Presigned URLs expire (15 minutes), are scoped to a specific file path, and can only be used once — more secure than long-lived API credentials.

## **16.3 API Layer: Amazon API Gateway**
- Managed routing, SSL termination, CORS, and throttling — no server management at any scale.
- Native Lambda integration eliminates the need for an intermediate load balancer or reverse proxy.

## **16.4 Backend Compute: Lambda + FastAPI + Mangum**
- Serverless Economics: Lambda charges per millisecond. A 2-second analysis costs ~$0.000033. At 1M analyses/month: ~$33 vs $200-500/month for equivalent EC2.
- Mangum as ASGI Bridge: Translates FastAPI's ASGI protocol to Lambda's event format — the full FastAPI app runs inside Lambda without modification.
- asyncio.to\_thread() for boto3: boto3 is synchronous — it blocks the event loop. Wrapping all boto3 calls in asyncio.to\_thread() keeps FastAPI non-blocking, improving throughput 3-5x under concurrent load.

## **16.5 AI Pipeline: AWS Step Functions**
- The Pre-Flight pipeline requires 6 parallel AI analyses. Chaining these sequentially in Lambda would take 6 × 3-5 seconds = 18-30 seconds. Step Functions collapses this to the slowest single step (3-5 seconds).
- Built-in retry logic with configurable backoff — no custom retry code in Lambda.
- Visual execution graph for every pipeline run — identifies exactly which step failed and why.
- Global 30-second timeout prevents runaway executions from accumulating cost.

## **16.6 Database: Amazon DynamoDB**
- Serverless scaling from 0 to millions of requests per second without configuration changes.
- Single-digit millisecond read latency — cached AI responses served nearly as fast as native computation.
- Schema-free design handles variable analysis structures (text-only vs image+text vs video+text).

## **16.7 Generative AI: Amazon Bedrock (Nova Lite / Nova Pro)**
- Nova Lite: Optimized for high-throughput, low-latency inference. Used for caption generation, hashtag suggestions, and cultural rewrites in the real-time pipeline.
- Nova Pro: Deeper reasoning for competitor analysis synthesis, campaign planning, and multi-step cultural adaptation.
- No Data Off-AWS: Unlike OpenAI or external Anthropic API, Bedrock keeps all inference within the AWS VPC — protecting creators' intellectual property.

## **16.8 Remaining AWS Services**

|**Service**|**Role**|**Why This Choice**|
| :- | :- | :- |
|Amazon Comprehend|Text NLP: sentiment + toxicity scoring|Deterministic JSON scores vs Bedrock's variable output. Native Indian language support.|
|Amazon Rekognition|Image/video NSFW detection|Production-grade model. Native S3 event integration. Results cached in DynamoDB by SHA-256 hash.|
|Amazon Transcribe|Audio-to-text for multimodal moderation|Indian language ASR. Runs async — creators not blocked waiting for transcription.|
|Amazon Translate|Multilingual caption adaptation|$15/million chars vs Bedrock cost for every translation. Script conversion for Hinglish.|
|Amazon EventBridge|Content publication scheduling|99\.99% delivery reliability. Handles 5M+ active schedules without Redis or queue workers.|
|Amazon CloudWatch|End-to-end observability|Captures Lambda logs, API latency, Step Functions history, DynamoDB metrics — zero additional tooling.|

## **16.9 AI Cost Optimization: DynamoDB Prompt Caching**

|**How the Caching Layer Works**|
| :- |
|Every prompt is hashed (MD5/SHA-256) before invoking Bedrock. The hash is the DynamoDB partition key.|
|Lambda checks DynamoDB before every Bedrock call. Cache hits return in <10ms at zero AI inference cost.|
|TTL-enabled cache entries auto-expire — preventing stale cultural recommendations from persisting.|
|Image results cached by SHA-256 hash — the same thumbnail template analyzed once, not repeatedly.|
||
|Estimated savings: 60-80% cache hit rate for common prompt patterns (festival captions, regional rewrites)|
|reduces Bedrock costs by the same factor — the single most economically impactful architectural decision.|

# **17. Competitive Landscape**

|**Platform**|**Core Strength**|**India**|**Moderation**|**Cultural AI**|**Wellness**|
| :- | :- | :- | :- | :- | :- |
|Buffer / Hootsuite|Social scheduling|❌ None|❌ None|❌ None|❌ None|
|Canva AI / Copy.ai|Generic copy generation|⚠️ Minimal|❌ None|❌ None|❌ None|
|Jasper AI|Enterprise AI copy|⚠️ English only|❌ None|❌ None|❌ None|
|Lately.ai|AI social content|❌ None|❌ None|❌ None|❌ None|
|Brandwatch|Social listening|⚠️ Partial|❌ None|❌ None|❌ None|
|Content Room|Full creator workflow|✅ 9 lang, 6 regions|✅ Text+Image+Audio|✅ 6 personas, 7 festivals|✅ Burnout AI|

# **18. Impact & Business Viability**
## **18.1 Market Sizing**

|**Segment**|**Size**|**Content Room Relevance**|
| :- | :- | :- |
|India's active content creators|80M+|Full TAM|
|Monetized creators (10K+ followers)|~8M|Primary paying segment|
|Professional creators (100K+ followers)|~800K|Ideal high-value segment|
|India creator economy GMV (2025)|$3.5B+|Value pool Content Room captures a portion of|

## **18.2 Revenue Tiers**

|**Tier**|**Price**|**What's Included**|**Target Segment**|
| :- | :- | :- | :- |
|Freemium|₹0/month|10 pre-flight analyses/month, basic text moderation|New creators, trial users|
|Creator Pro|₹499/month|Unlimited pre-flight, full Bharat Layer, Burnout Predictor, Competitor Intelligence|Monetized 10K-500K creators|
|Creator Studio|₹1,999/month|Everything in Pro + API access, team collaboration, campaign planner, custom personas|Professional creators, agencies|
|Brand/Agency|₹9,999+/month|White-label dashboard, multi-creator management, custom moderation rules, dedicated support|Talent agencies, brand teams|

## **18.3 Unit Economics**

|**Metric**|**Estimate**|**Basis**|
| :- | :- | :- |
|AWS cost per analysis (with cache)|₹0.8 – ₹2.5|60% cache hit rate — Bedrock + Comprehend + DynamoDB|
|AWS cost per analysis (no cache)|₹4 – ₹12|Full Bedrock + all moderation services|
|Creator Pro AWS cost per user/month|~₹40 – ₹80|30 analyses/month at 60% cache hit rate|
|Creator Pro gross margin|~84 – 92%|₹499 revenue vs ₹40-80 AWS cost|
|Payback period|<1 month|Subscription revenue exceeds AWS cost from Month 1|

## **18.4 Defensibility Moats**
- Data Moat: Every analysis generates training data. After 1M analyses, Content Room's cultural models are trained on more Indian creator content than any competitor could acquire.
- Language Infrastructure Lead: Supporting 9 Indian languages with cultural post-processing is a 12-18 month engineering project for any competitor starting from zero.
- First-Mover Creator Trust: Moderation and wellness prediction require creators to trust the platform with sensitive content. Trust is earned slowly and lost instantly.
- Network Effects: The Competitor Intelligence feature improves as more creators use it — more creators = better benchmarks = more valuable intelligence for each user.
- AWS Partnership Potential: As a flagship India-focused AI application on AWS, Content Room is a candidate for AWS Activate credits and AWS Marketplace listing.

# **19. Official Submission Statement**

|**For Hackathon Submission / README**|
| :- |
|Content Room is a full-stack AI-powered content workflow platform built for India's 80M+ creator economy.|
|The platform features 7 integrated modules: Creator Studio, Content Moderation, Competitor Intelligence,|
|Content Calendar, Content Scheduler with Pre-Flight Analysis, Intelligence Hub (6 specialized tools),|
|and Novel AI Lab (5 multi-agent and RAG-powered tools).|
||
|Built on a fully serverless AWS architecture using Amazon S3, CloudFront, API Gateway, Lambda,|
|Step Functions, DynamoDB, Bedrock (Nova Lite/Pro), Rekognition, Comprehend, Translate, Transcribe,|
|EventBridge, and CloudWatch — 13 AWS services, zero servers.|
||
|The Pre-Flight Pipeline runs 6 AI checks in parallel (Anti-Cancel Shield, Shadowban Prediction,|
|Culture Adaptation, Content Safety, Mental Health Tone Analysis, and Asset Spin-offs) before any|
|content is scheduled. The world-first Creator Burnout Predictor uses linguistic entropy analysis to|
|detect burnout weeks before creators recognize it themselves.|
||
|The Bharat Intelligence Layer covers 6 Indian city personas, 9 languages with transliteration,|
|and 7 festival content adapters — making Content Room the only platform designed natively for the|
|cultural complexity of Indian content creation.|

**CONTENT ROOM**

**Built on AWS · Made for Bharat · Built for Creators**
