# One Day Sprint - Content Room Analysis

## 1. Feature Duplication & Code Issues

### Reused Features / Code Duplication
After reviewing the `Frontend` and `Backend` codebase, here are the instances where similar logic is duplicated:
- **LLM Prompt Patterns**: In `IntelligenceHub.tsx`, each of the 6 tabs (Culture, Risk, Anti-Cancel, Assets, Mental Health, Shadowban) repeats very similar UI logic: State management (`content`, `loading`, `result`, `error`), submit handlers, and rendering a `<ResultBox>`. These could be abstracted into a generic `IntelToolForm` component to reduce code duplication and make the file much smaller than 700 lines.
- **Backend API Calls**: Each Intelligence Hub tab calls a separate endpoint which fundamentally wraps a highly similar prompt to the LLM (via `llm_service.py`). These could be consolidated into a dynamic prompt builder.

### Code Issues
- **Missing Error Recovery**: If an API request fails, it just logs the string. There are no automatic retries on the frontend.
- **Hardcoded Prompts**: Prompts in `culture_engine.py` are heavily hardcoded. If the prompt needs a change, it requires a backend redeployment.
- **Synchronous Rendering Blocks**: React components in IntelligenceHub don't use useMemo for heavy UI, which can cause micro-stutters.

---

## 2. Language Selection Issue in Intelligence Hub (Culture Engine)
**Issue Identified**: 
Currently, the "Culture Engine" (Emotional Re-adaptation) tab hardcodes dialects based on region, and often leans toward Hindi/Hinglish (e.g., `tier2_towns` defaults to Hindi, `delhi` defaults to Hinglish). 
**Solution**: 
Because different users in the same region might want different regional languages (e.g., a creator in Mumbai might want Marathi, Gujarati, or Hindi), we must add a **"Target Language" Dropdown** in `IntelligenceHub.tsx` explicitly asking the user which language they prefer *alongside* the region. This language parameter should be passed down to `culture_engine.py`.

---

## 3. Free Hugging Face Alternatives for NLP (Replacing LLMs)
Currently, `llm_service.py` heavily relies on LLMs (Bedrock, Groq, OpenRouter) for all NLP tasks. We can significantly reduce costs and response times by using **Hugging Face Free Inference API** or **Transformers.js** (for browser-level execution):
- **Anti-Cancel Shield / Moderation**: Instead of using an LLM, we can use a free pre-trained Hugging Face toxicity model (e.g., `unitary/toxic-bert`) to detect hate speech, violence, and brand safety issues instantly.
- **Mental Health Meter**: We can use a zero-shot sentiment/emotion classifier (e.g., `SamLowe/roberta-base-go_emotions`) to determine linguistic entropy and burnout/sentiment trends without wasting LLM tokens.
- **Shadowban Predictor**: We can predict shadowban probabilities using standard NLP spam/clickbait classification models available for free on Hugging Face.

---

## 4. Multi-Model Pipeline in Schedule Plan (Most Important)
**Feature Proposal: The "One-Click Content Analyzer" Pipeline**

Yes, we can definitely build this! Instead of forcing the user to manually visit 6 different tabs in the Intelligence Hub to check their content, we can embed a **Multi-Model Pipeline** inside the `Scheduler.tsx` (Schedule Plan).

**How it works:**
1. **Upload / Paste Context**: The user opens the Schedule Plan, pastes their content/caption, and uploads their media (or just text).
2. **Parallel Processing**: Upon clicking "Analyze & Schedule", the backend triggers an `asyncio.gather()` pipeline that runs all 6 checks concurrently:
   - *Culture Engine*: Translates/Adapts to target language.
   - *Risk vs. Reach*: Checks the vitality score.
   - *Anti-Cancel Shield*: Scans for toxic keywords using Hugging Face NLP.
   - *Asset Explosion*: Suggests spin-off assets.
   - *Mental Health*: Analyzes sentiment.
   - *Shadowban*: Checks for algorithmic suppression risk.
3. **Unified Report**: The user gets a single, unified "Pre-Flight Report" right in the Scheduler. 
4. **Approval**: If the content passes the checks (or the user approves the warnings), it is officially added to the Content Calendar.

**Implementation Steps:**
- **Backend**: Create a new endpoint `/api/pipeline/analyze` that receives the content, calls all 6 internal service functions asynchronously, and returns one merged JSON object.
- **Frontend**: Update `Scheduler.tsx` to include an "Analyze Content" button that displays the unified report before allowing the user to pick a date and hit "Add to Schedule".
