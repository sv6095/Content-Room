import { useMemo, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Radar, Globe2, Clapperboard, Layers, Brain, Plus, X,
} from "lucide-react";
import {
  novelAPI,
  type SignalIntelResponse,
  type TrendInjectionResponse,
  type MultimodalResponse,
  type MultimodalProduction,
  type PlatformAdaptResponse,
  type PlatformPreview,
  type BurnoutResponse,
} from "@/services/api";
import { Spinner, ResultBox, Chip, CopyBtn, LLMOutput } from "@/components/shared/IntelPrimitives";
import { ALLOWED_LANGUAGE_OPTIONS } from "@/constants/languages";

// ─── Tab definitions ──────────────────────────────────────
const TABS = [
  { id: "signal",    label: "Signal Intelligence",    icon: Radar },
  { id: "trends",    label: "Trend Injection RAG",    icon: Globe2 },
  { id: "multimodal",label: "Multimodal Production",  icon: Clapperboard },
  { id: "adapt",     label: "Platform Adapter",       icon: Layers },
  { id: "burnout",   label: "Burnout Predictor",      icon: Brain },
] as const;

type TabId = (typeof TABS)[number]["id"];
type SignalStep = "scraper" | "analyst" | "strategist";
type SignalMode = "digest" | "operator" | "raw";

/** Agent output card — unique to the Signal Intelligence multi-agent pipeline. */
function AgentCard({ emoji, name, output }: { emoji: string; name: string; output: string }) {
  return (
    <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold flex items-center gap-1.5">
          <span>{emoji}</span> {name}
        </span>
        <CopyBtn text={output} />
      </div>
      <LLMOutput text={output} />
    </div>
  );
}

type SignalSection = { title: string; content: string };
type SignalBrief = { title: string; format: string; hook: string; angle: string; urgency: string };
type NovelViewMode = "digest" | "operator" | "raw";
const SCRAPER_SCHEMA = [
  "TOP POST PATTERNS",
  "HOOK PATTERNS",
  "POSTING CADENCE",
  "HASHTAG STRATEGY",
  "FORMAT DISTRIBUTION",
] as const;
const ANALYST_SCHEMA = [
  "VIRALITY PATTERNS",
  "CONTENT GAPS",
  "TIMING INSIGHTS",
  "AUDIENCE SENTIMENT",
  "WEAKNESS MAP",
] as const;

function normalizeSectionTitle(title: string): string {
  return (title || "").replace(/\s+/g, " ").trim().toUpperCase();
}

function orderSectionsBySchema(sections: SignalSection[], schema: readonly string[]): SignalSection[] {
  const byTitle = new Map(sections.map((s) => [normalizeSectionTitle(s.title), s]));
  const ordered = schema
    .map((name) => byTitle.get(name))
    .filter(Boolean) as SignalSection[];
  const extras = sections.filter((s) => !schema.includes(normalizeSectionTitle(s.title) as (typeof schema)[number]));
  return [...ordered, ...extras];
}

function parseAllCapsSections(text: string): SignalSection[] {
  const body = (text || "").trim();
  if (!body) return [];
  const re = /(?:^|\n)\s*([A-Z][A-Z0-9_&/\-\s]{3,})\s*\n/g;
  const matches = [...body.matchAll(re)];
  if (matches.length === 0) return [{ title: "Output", content: body }];

  const sections: SignalSection[] = [];
  for (let i = 0; i < matches.length; i++) {
    const m = matches[i];
    const start = (m.index ?? 0) + m[0].length;
    const end = i + 1 < matches.length ? (matches[i + 1].index ?? body.length) : body.length;
    const title = m[1].replace(/_/g, " ").trim();
    const content = body.slice(start, end).trim();
    if (content) sections.push({ title, content });
  }
  return sections;
}

function parseStrategistBriefs(text: string): { briefs: SignalBrief[]; weeklySummary: string; calendar: string } {
  const body = (text || "").trim();
  const blockRe =
    /TITLE:\s*["“”]?(.+?)["“”]?\s*FORMAT:\s*(.+?)\s*HOOK:\s*([\s\S]*?)\s*ANGLE:\s*([\s\S]*?)\s*URGENCY:\s*(HIGH|MEDIUM|LOW)/gi;
  const briefs = [...body.matchAll(blockRe)].map((m) => ({
    title: m[1].trim(),
    format: m[2].trim(),
    hook: m[3].trim(),
    angle: m[4].trim(),
    urgency: m[5].trim(),
  }));
  const weeklySummary = (body.match(/WEEKLY_STRATEGY_SUMMARY[\s:]*([\s\S]*?)(?=CONTENT_CALENDAR_SUGGESTION|$)/i)?.[1] || "").trim();
  const calendar = (body.match(/CONTENT_CALENDAR_SUGGESTION[\s\S]*?(?:\([\s\S]*?\))?\s*:?\s*([\s\S]*)$/i)?.[1] || "").trim();
  return { briefs, weeklySummary, calendar };
}

function parseLabeledSections(text: string, labels: readonly string[]): Record<string, string> {
  const body = (text || "").trim();
  const out: Record<string, string> = {};
  if (!body) return out;
  labels.forEach((l) => {
    const escaped = l.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const labelRe = new RegExp(`${escaped}\\s*:`, "i");
    const start = body.search(labelRe);
    if (start < 0) return;
    const from = body.slice(start);
    const nextLabel = labels
      .filter((x) => x !== l)
      .map((x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .map((x) => new RegExp(`\\n\\s*${x}\\s*:`, "i"))
      .map((re) => from.search(re))
      .filter((idx) => idx > 0)
      .sort((a, b) => a - b)[0];
    const raw = nextLabel ? from.slice(0, nextLabel) : from;
    out[l] = raw.replace(labelRe, "").trim();
  });
  return out;
}

function parseBurnoutScheduleRows(schedule: string): Array<{ task: string; effort: string; format: string; topic: string; tip: string }> {
  const rows: Array<{ task: string; effort: string; format: string; topic: string; tip: string }> = [];
  const lineRows = (schedule || "")
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.includes("|") && /task|effort|format|topic|wellness/i.test(l));
  for (const line of lineRows) {
    const parts = line.split("|").map((p) => p.trim()).filter(Boolean);
    if (parts.length < 5) continue;
    rows.push({
      task: parts[0].replace(/^TASK\s*:?/i, "").trim(),
      effort: parts[1].replace(/^EFFORT\s*:?/i, "").trim(),
      format: parts[2].replace(/^FORMAT\s*:?/i, "").trim(),
      topic: parts[3].replace(/^TOPIC\s*:?/i, "").trim(),
      tip: parts[4].replace(/^WELLNESS_TIP\s*:?/i, "").trim(),
    });
  }
  return rows;
}

// ─── 1. Signal Intelligence ──────────────────────────────
function SignalTab() {
  const [handles, setHandles] = useState<string[]>([""]);
  const [niche, setNiche]     = useState("");
  const [region, setRegion]   = useState("pan-india");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<SignalIntelResponse | null>(null);
  const [error, setError]     = useState("");
  const [activeStep, setActiveStep] = useState<SignalStep>("scraper");
  const [mode, setMode] = useState<SignalMode>("digest");

  const addHandle = () => setHandles([...handles, ""]);
  const removeHandle = (i: number) => setHandles(handles.filter((_, idx) => idx !== i));
  const updateHandle = (i: number, v: string) => { const h = [...handles]; h[i] = v; setHandles(h); };

  const run = async () => {
    const validHandles = handles.filter(h => h.trim());
    if (!validHandles.length || !niche.trim()) return;
    setLoading(true); setError(""); setResult(null); setActiveStep("scraper");
    try {
      setResult(await novelAPI.signalIntelligence(validHandles, niche, region));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  const scraperSections = useMemo(() => {
    if (!result) return [];
    return orderSectionsBySchema(parseAllCapsSections(result.agents.scraper.output), SCRAPER_SCHEMA);
  }, [result]);
  const analystSections = useMemo(() => {
    if (!result) return [];
    return orderSectionsBySchema(parseAllCapsSections(result.agents.analyst.output), ANALYST_SCHEMA);
  }, [result]);
  const strategistParsed = useMemo(
    () => (result ? parseStrategistBriefs(result.agents.strategist.output) : { briefs: [], weeklySummary: "", calendar: "" }),
    [result]
  );
  const urgencyHigh = strategistParsed.briefs.filter((b) => b.urgency.toUpperCase() === "HIGH").length;
  const summaryChips = useMemo(() => {
    if (!result) return [];
    const formatDist = result.agents.scraper.output.match(/Instagram:\s*([^\n]+)/i)?.[1]?.trim();
    const cadence = result.agents.scraper.output.match(/(\d{1,2}\s*AM\s*-\s*\d{1,2}\s*PM.*?)\./i)?.[1]?.trim();
    const sentiment = result.agents.analyst.output.match(/(\d+%[^.]*frustration[^.]*)/i)?.[1]?.trim();
    const primaryGap = analystSections.find((s) => normalizeSectionTitle(s.title) === "CONTENT GAPS")?.content.split("\n")[0]?.trim();
    return [
      formatDist ? `Top format mix: ${formatDist}` : null,
      cadence ? `Best posting window: ${cadence}` : null,
      `High-urgency briefs: ${urgencyHigh}`,
      sentiment ? `Sentiment risk: ${sentiment}` : null,
      primaryGap ? `Primary gap: ${primaryGap.replace(/^[-*\d.\s]+/, "")}` : null,
    ].filter(Boolean) as string[];
  }, [result, analystSections, urgencyHigh]);

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Competitor Handles / URLs</Label>
        {handles.map((h, i) => (
          <div key={i} className="flex gap-2">
            <Input
              placeholder="@competitor or URL"
              value={h}
              onChange={e => updateHandle(i, e.target.value)}
              disabled={loading}
            />
            {handles.length > 1 && (
              <Button variant="ghost" size="icon" onClick={() => removeHandle(i)} disabled={loading}>
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        ))}
        <Button variant="outline" size="sm" onClick={addHandle} disabled={loading} className="gap-1">
          <Plus className="h-3 w-3" /> Add Handle
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="si-niche">Your Niche</Label>
          <Input id="si-niche" placeholder="e.g. Fitness" value={niche} onChange={e => setNiche(e.target.value)} disabled={loading} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="si-region">Region</Label>
          <select id="si-region" title="Region" value={region} onChange={e => setRegion(e.target.value)} disabled={loading}
            className="w-full h-9 rounded-lg border border-border bg-background px-3 text-sm">
            {["pan-india","mumbai","delhi","chennai","kolkata","bangalore","hyderabad","punjab"].map(r => (
              <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <Button onClick={run} disabled={loading || !niche.trim()} className="w-full">
        {loading ? <><Spinner /> Deploying 3 Agents...</> : "🤖 Deploy Signal Intelligence Agents"}
      </Button>

      {result && (
        <div className="space-y-3 animate-fade-in">
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-3">
            <p className="text-xs uppercase tracking-wide text-primary mb-2">Executive Summary</p>
            <div className="flex flex-wrap gap-2">
              {summaryChips.map((chip, i) => <Chip key={i} text={chip} color="blue" />)}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              {([
                ["scraper", "01 Scraper"],
                ["analyst", "02 Analyst"],
                ["strategist", "03 Strategist"],
              ] as Array<[SignalStep, string]>).map(([step, label]) => (
                <button
                  key={step}
                  onClick={() => setActiveStep(step)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${
                    activeStep === step ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="flex gap-1 rounded-lg border border-border p-1">
              {(["digest", "operator", "raw"] as SignalMode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`px-2.5 py-1 text-xs rounded-md ${mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
                >
                  {m[0].toUpperCase() + m.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {mode === "raw" && (
            <AgentCard
              emoji={activeStep === "scraper" ? "🕵️" : activeStep === "analyst" ? "📊" : "🎯"}
              name={result.agents[activeStep].name}
              output={result.agents[activeStep].output}
            />
          )}

          {mode !== "raw" && activeStep === "scraper" && (
            <div className="grid gap-3 md:grid-cols-2">
              {scraperSections.length === 0 && (
                <ResultBox>
                  <LLMOutput text={result.agents.scraper.output} />
                </ResultBox>
              )}
              {scraperSections.map((s, i) => (
                <details key={i} open={mode === "digest" ? i < 2 : true} className="rounded-xl border border-border bg-muted/20 p-3">
                  <summary className="cursor-pointer text-sm font-semibold">{s.title}</summary>
                  <div className="pt-2 text-sm text-muted-foreground">
                    <LLMOutput text={s.content} />
                  </div>
                </details>
              ))}
            </div>
          )}

          {mode !== "raw" && activeStep === "analyst" && (
            <div className="grid gap-3 md:grid-cols-2">
              {analystSections.length === 0 && (
                <ResultBox>
                  <LLMOutput text={result.agents.analyst.output} />
                </ResultBox>
              )}
              {analystSections.map((s, i) => (
                <div key={i} className="rounded-xl border border-border bg-muted/20 p-3 space-y-2">
                  <p className="text-sm font-semibold">{s.title}</p>
                  <LLMOutput text={mode === "digest" ? s.content.split("\n").slice(0, 3).join("\n") : s.content} />
                </div>
              ))}
            </div>
          )}

          {mode !== "raw" && activeStep === "strategist" && (
            <div className="space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                {strategistParsed.briefs.length === 0 && (
                  <ResultBox>
                    <LLMOutput text={result.agents.strategist.output} />
                  </ResultBox>
                )}
                {strategistParsed.briefs.map((b, i) => (
                  <div key={i} className="rounded-xl border border-border bg-muted/20 p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold">{b.title}</p>
                      <Chip text={b.urgency} color={b.urgency.toUpperCase() === "HIGH" ? "red" : b.urgency.toUpperCase() === "MEDIUM" ? "yellow" : "green"} />
                    </div>
                    <p className="text-xs text-primary">{b.format}</p>
                    <p className="text-sm text-muted-foreground"><strong>Hook:</strong> {b.hook}</p>
                    {mode === "operator" && <p className="text-sm text-muted-foreground"><strong>Angle:</strong> {b.angle}</p>}
                  </div>
                ))}
              </div>
              {strategistParsed.weeklySummary && (
                <ResultBox>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">Weekly Strategy Summary</span>
                    <CopyBtn text={strategistParsed.weeklySummary} />
                  </div>
                  <LLMOutput text={strategistParsed.weeklySummary} />
                </ResultBox>
              )}
              {mode === "operator" && strategistParsed.calendar && (
                <ResultBox>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">This Week Calendar Suggestion</span>
                    <CopyBtn text={strategistParsed.calendar} />
                  </div>
                  <LLMOutput text={strategistParsed.calendar} />
                </ResultBox>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── 2. Trend Injection RAG ──────────────────────────────
function TrendsTab() {
  const [content, setContent] = useState("");
  const [region, setRegion]   = useState("mumbai");
  const [niche, setNiche]     = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<TrendInjectionResponse | null>(null);
  const [error, setError]     = useState("");
  const [mode, setMode]       = useState<NovelViewMode>("digest");

  const run = async () => {
    if (!content.trim() || !niche.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await novelAPI.trendInjection(content, region, niche));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Content to Enhance</Label>
        <Textarea placeholder="Paste or type your content here..." value={content} onChange={e => setContent(e.target.value)}
          disabled={loading} rows={4} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="tr-region">Target Region</Label>
          <select id="tr-region" title="Target Region" value={region} onChange={e => setRegion(e.target.value)} disabled={loading}
            className="w-full h-9 rounded-lg border border-border bg-background px-3 text-sm">
            {["mumbai","delhi","chennai","kolkata","bangalore","hyderabad","punjab","pan-india"].map(r => (
              <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="tr-niche">Creator Niche</Label>
          <Input id="tr-niche" placeholder="e.g. Tech Reviews" value={niche} onChange={e => setNiche(e.target.value)} disabled={loading} />
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <Button onClick={run} disabled={loading || !content.trim() || !niche.trim()} className="w-full">
        {loading ? <><Spinner /> Injecting Local Trends...</> : "🌐 Inject Hyper-Local Trends"}
      </Button>

      {result && (
        <div className="space-y-3 animate-fade-in">
          <div className="flex justify-end">
            <div className="flex gap-1 rounded-lg border border-border p-1">
              {(["digest", "operator", "raw"] as NovelViewMode[]).map((m) => (
                <button key={m} onClick={() => setMode(m)} className={`px-2.5 py-1 text-xs rounded-md ${mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>
                  {m[0].toUpperCase() + m.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Region Context */}
          <div className="flex gap-2 flex-wrap">
            {result.region_context.languages.map((l, i) => <Chip key={i} text={l} color="blue" />)}
            {result.region_context.festivals.slice(0, 3).map((f, i) => <Chip key={i} text={`🎉 ${f}`} color="orange" />)}
          </div>

          {mode === "raw" ? (
            <ResultBox>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">📈 Raw Trend Discovery</span>
                <CopyBtn text={result.trending_topics} />
              </div>
              <LLMOutput text={result.trending_topics} />
            </ResultBox>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {(result.trending_topics.split(/\n(?=\s*(?:[-•]|\d+\.|TREND))/i).filter(Boolean).slice(0, mode === "digest" ? 3 : 8)).map((item, idx) => (
                <div key={idx} className="rounded-xl border border-border bg-muted/20 p-3">
                  <p className="text-sm text-muted-foreground">{item.trim()}</p>
                </div>
              ))}
            </div>
          )}

          {/* Enhanced Content */}
          <ResultBox>
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">✨ Trend-Enhanced Content</span>
              <CopyBtn text={result.enhanced_content} />
            </div>
            <LLMOutput text={result.enhanced_content} />
          </ResultBox>
        </div>
      )}
    </div>
  );
}

// ─── 3. Multimodal Production ────────────────────────────
const FORMAT_OPTIONS = [
  { key: "podcast_script",        label: "🎙️ Podcast Script" },
  { key: "video_storyboard",      label: "🎬 Video Storyboard" },
  { key: "audio_narration",       label: "🔊 Audio Narration" },
  { key: "multilingual_adapt",    label: "🌐 Multilingual (5 langs)" },
  { key: "thumbnail_brief",       label: "🖼️ Thumbnail Brief" },
  { key: "motion_graphics_script",label: "✨ Motion Graphics" },
];

function MultimodalTab() {
  const [seed, setSeed]             = useState("");
  const [niche, setNiche]           = useState("");
  const [language, setLanguage]     = useState("Hindi");
  const [selectedFmts, setSelected] = useState<string[]>(["podcast_script", "video_storyboard"]);
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState<MultimodalResponse | null>(null);
  const [error, setError]           = useState("");
  const [mode, setMode]             = useState<NovelViewMode>("digest");

  const toggleFmt = (key: string) => {
    setSelected(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);
  };

  const run = async () => {
    if (!seed.trim() || !niche.trim() || !selectedFmts.length) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await novelAPI.multimodalProduction(seed, selectedFmts, niche, language));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Seed Content / Idea</Label>
        <Textarea placeholder="Your core idea or content..." value={seed} onChange={e => setSeed(e.target.value)}
          disabled={loading} rows={3} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="mm-niche">Niche</Label>
          <Input id="mm-niche" placeholder="e.g. Travel" value={niche} onChange={e => setNiche(e.target.value)} disabled={loading} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="mm-lang">Primary Language</Label>
          <select id="mm-lang" title="Primary Language" value={language} onChange={e => setLanguage(e.target.value)} disabled={loading}
            className="w-full h-9 rounded-lg border border-border bg-background px-3 text-sm">
            {ALLOWED_LANGUAGE_OPTIONS.map(l => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label>Output Formats</Label>
        <div className="flex flex-wrap gap-2">
          {FORMAT_OPTIONS.map(f => (
            <button key={f.key} onClick={() => toggleFmt(f.key)} disabled={loading}
              className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-all ${
                selectedFmts.includes(f.key)
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground hover:border-primary/40"
              }`}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <Button onClick={run} disabled={loading || !seed.trim() || !selectedFmts.length} className="w-full">
        {loading ? <><Spinner /> Producing {selectedFmts.length} Formats...</> : `🎬 Produce ${selectedFmts.length} Formats`}
      </Button>

      {result && (
        <div className="space-y-3 animate-fade-in">
          <div className="flex justify-end">
            <div className="flex gap-1 rounded-lg border border-border p-1">
              {(["digest", "operator", "raw"] as NovelViewMode[]).map((m) => (
                <button key={m} onClick={() => setMode(m)} className={`px-2.5 py-1 text-xs rounded-md ${mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>
                  {m[0].toUpperCase() + m.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <p className="text-sm text-muted-foreground">{result.successful} of {result.total_formats} formats generated</p>
          {result.productions.map((prod: MultimodalProduction, idx: number) => (
            <ResultBox key={idx}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">{prod.format_name}</span>
                  <Chip text={prod.success ? "Ready" : "Failed"} color={prod.success ? "green" : "red"} />
                </div>
                <CopyBtn text={prod.content} />
              </div>
              {mode === "digest" ? <LLMOutput text={prod.content.split("\n").slice(0, 8).join("\n")} /> : <LLMOutput text={prod.content} />}
            </ResultBox>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── 4. Auto-Publish Agent ───────────────────────────────
const PLATFORM_OPTIONS = [
  { key: "instagram", label: "📸 Instagram" },
  { key: "facebook",  label: "📘 Facebook" },
  { key: "youtube",   label: "▶️ YouTube" },
  { key: "twitter",   label: "🐦 Twitter/X" },
  { key: "linkedin",  label: "💼 LinkedIn" },
];

function AdaptTab() {
  const [content, setContent]       = useState("");
  const [niche, setNiche]           = useState("");
  const [platforms, setPlatforms]   = useState<string[]>(["instagram", "twitter"]);
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState<PlatformAdaptResponse | null>(null);
  const [error, setError]           = useState("");
  const [mode, setMode]             = useState<NovelViewMode>("digest");

  const togglePlatform = (key: string) => {
    setPlatforms(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);
  };

  const run = async () => {
    if (!content.trim() || !niche.trim() || !platforms.length) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await novelAPI.platformAdapt(content, platforms, niche));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  const platformIcons: Record<string, string> = {
    instagram: "📸", facebook: "📘", youtube: "▶️", twitter: "🐦", linkedin: "💼",
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Content to Adapt</Label>
        <Textarea placeholder="Paste your content to see how it adapts across platforms..." value={content}
          onChange={e => setContent(e.target.value)} disabled={loading} rows={4} />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="ap-niche">Your Niche</Label>
        <Input id="ap-niche" placeholder="e.g. Personal Finance" value={niche} onChange={e => setNiche(e.target.value)} disabled={loading} />
      </div>

      <div className="space-y-1.5">
        <Label>Target Platforms</Label>
        <div className="flex flex-wrap gap-2">
          {PLATFORM_OPTIONS.map(p => (
            <button key={p.key} onClick={() => togglePlatform(p.key)} disabled={loading}
              className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-all ${
                platforms.includes(p.key)
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground hover:border-primary/40"
              }`}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <Button onClick={run} disabled={loading || !content.trim() || !platforms.length} className="w-full">
        {loading ? <><Spinner /> Adapting for {platforms.length} Platforms...</> : `🔄 Adapt for ${platforms.length} Platforms`}
      </Button>

      {result && (
        <div className="space-y-3 animate-fade-in">
          <div className="flex justify-end">
            <div className="flex gap-1 rounded-lg border border-border p-1">
              {(["digest", "operator", "raw"] as NovelViewMode[]).map((m) => (
                <button key={m} onClick={() => setMode(m)} className={`px-2.5 py-1 text-xs rounded-md ${mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>
                  {m[0].toUpperCase() + m.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <p className="text-sm text-muted-foreground">{result.successful} of {result.total_platforms} platform adaptations ready</p>
          {result.previews.map((preview: PlatformPreview, idx: number) => (
            <ResultBox key={idx}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">
                  {platformIcons[preview.platform] || "📱"} {preview.platform.charAt(0).toUpperCase() + preview.platform.slice(1)}
                </span>
                <div className="flex items-center gap-2">
                  {preview.recommended_time && <Chip text={`⏰ ${preview.recommended_time}`} color="yellow" />}
                  <Chip text={preview.status === "ready_to_publish" ? "✅ Adapted" : "❌ Failed"} color={preview.success ? "green" : "red"} />
                  <CopyBtn text={preview.optimized_content} />
                </div>
              </div>
              {mode === "raw" ? (
                <LLMOutput text={preview.optimized_content} />
              ) : (
                <div className="space-y-2">
                  {(() => {
                    const parsed = parseLabeledSections(preview.optimized_content, [
                      "OPTIMIZED_CONTENT",
                      "HASHTAGS_OR_TAGS",
                      "BEST_TIME_TO_POST",
                      "FORMAT_RECOMMENDATION",
                      "ENGAGEMENT_HOOKS",
                      "SEO_METADATA",
                      "COMPLIANCE_CHECK",
                    ]);
                    const keys = Object.keys(parsed);
                    if (keys.length === 0) return <LLMOutput text={preview.optimized_content} />;
                    const visible = mode === "digest" ? keys.slice(0, 3) : keys;
                    return visible.map((k) => (
                      <div key={k} className="rounded-lg border border-border/60 p-2">
                        <p className="text-xs uppercase tracking-wide text-primary mb-1">{k.replace(/_/g, " ")}</p>
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{parsed[k]}</p>
                      </div>
                    ));
                  })()}
                </div>
              )}
            </ResultBox>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── 5. Burnout Predictor ────────────────────────────────
function BurnoutTab() {
  const [posts, setPosts]         = useState<string[]>(["", "", ""]);
  const [niche, setNiche]         = useState("");
  const [target, setTarget]       = useState(7);
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState<BurnoutResponse | null>(null);
  const [error, setError]         = useState("");
  const [mode, setMode]           = useState<NovelViewMode>("digest");

  const addPost = () => setPosts([...posts, ""]);
  const updatePost = (i: number, v: string) => { const p = [...posts]; p[i] = v; setPosts(p); };
  const removePost = (i: number) => setPosts(posts.filter((_, idx) => idx !== i));

  const run = async () => {
    const validPosts = posts.filter(p => p.trim());
    if (validPosts.length < 2 || !niche.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await novelAPI.burnoutPredict(validPosts, niche, target));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  const modeColors: Record<string, string> = {
    RECOVERY: "text-red-400",
    REDUCED:  "text-yellow-400",
    NORMAL:   "text-emerald-400",
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Paste recent posts (min 2)</Label>
        {posts.map((p, i) => (
          <div key={i} className="flex gap-2">
            <Textarea
              placeholder={`Post ${i + 1}...`}
              value={p}
              onChange={e => updatePost(i, e.target.value)}
              disabled={loading}
              rows={2}
              className="text-sm"
            />
            {posts.length > 2 && (
              <Button variant="ghost" size="icon" onClick={() => removePost(i)} disabled={loading} className="shrink-0">
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        ))}
        <Button variant="outline" size="sm" onClick={addPost} disabled={loading} className="gap-1">
          <Plus className="h-3 w-3" /> Add Post
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="bo-niche">Niche</Label>
          <Input id="bo-niche" placeholder="e.g. Gaming" value={niche} onChange={e => setNiche(e.target.value)} disabled={loading} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="bo-target">Weekly Post Target</Label>
          <Input id="bo-target" type="number" min={1} max={21} value={target}
            onChange={e => setTarget(Number(e.target.value))} disabled={loading} />
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <Button onClick={run} disabled={loading || posts.filter(p => p.trim()).length < 2 || !niche.trim()} className="w-full">
        {loading ? <><Spinner /> Analyzing Burnout Signals...</> : "🧠 Predict Burnout & Adapt Schedule"}
      </Button>

      {result && (
        <div className="space-y-3 animate-fade-in">
          <div className="flex justify-end">
            <div className="flex gap-1 rounded-lg border border-border p-1">
              {(["digest", "operator", "raw"] as NovelViewMode[]).map((m) => (
                <button key={m} onClick={() => setMode(m)} className={`px-2.5 py-1 text-xs rounded-md ${mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>
                  {m[0].toUpperCase() + m.slice(1)}
                </button>
              ))}
            </div>
          </div>
          {/* Burnout Score Header */}
          <div className="grid grid-cols-4 gap-2 text-center">
            {[
              { label: "Burnout Score", value: `${result.burnout_analysis.burnout_score}/100`,
                color: result.burnout_analysis.burnout_score >= 70 ? "text-red-400" : result.burnout_analysis.burnout_score >= 40 ? "text-yellow-400" : "text-emerald-400" },
              { label: "Entropy", value: `${result.burnout_analysis.entropy}`, color: "text-blue-400" },
              { label: "Sentiment", value: `${result.burnout_analysis.sentiment_drift}`, color: "text-violet-400" },
              { label: "Repetition", value: `${(result.burnout_analysis.repetition_index * 100).toFixed(0)}%`, color: "text-orange-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-lg bg-muted p-2">
                <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
                <p className={`text-sm font-bold ${color}`}>{value}</p>
              </div>
            ))}
          </div>

          {/* Mode Banner */}
          <div className={`rounded-lg border p-3 ${
            result.workload_mode === "RECOVERY" ? "border-red-500/30 bg-red-500/5"
            : result.workload_mode === "REDUCED" ? "border-yellow-500/30 bg-yellow-500/5"
            : "border-emerald-500/30 bg-emerald-500/5"
          }`}>
            <p className={`text-sm font-bold ${modeColors[result.workload_mode] || "text-muted-foreground"}`}>
              {result.mode_description}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Weekly target adjusted: {result.original_target} → {result.adjusted_target} posts/week
            </p>
          </div>

          {/* Burnout Signals */}
          {result.burnout_analysis.signals.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.burnout_analysis.signals.map((s, i) => (
                <Chip key={i} text={s} color={result.burnout_analysis.burnout_score >= 70 ? "red" : result.burnout_analysis.burnout_score >= 40 ? "yellow" : "green"} />
              ))}
            </div>
          )}

          {/* Adapted Schedule */}
          <ResultBox>
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">📅 Self-Evolving Weekly Plan</span>
              <CopyBtn text={result.adapted_schedule} />
            </div>
            {mode === "raw" ? (
              <LLMOutput text={result.adapted_schedule} />
            ) : (
              <div className="space-y-2">
                {(() => {
                  const rows = parseBurnoutScheduleRows(result.adapted_schedule);
                  if (rows.length === 0) return <LLMOutput text={result.adapted_schedule} />;
                  const visible = mode === "digest" ? rows.slice(0, 4) : rows;
                  return visible.map((r, idx) => (
                    <div key={idx} className="rounded-lg border border-border/60 p-2 grid gap-1">
                      <p className="text-sm font-semibold">{r.task || "Task"}</p>
                      <div className="flex gap-2 flex-wrap">
                        {r.effort && <Chip text={`Effort: ${r.effort}`} color="yellow" />}
                        {r.format && <Chip text={`Format: ${r.format}`} color="blue" />}
                      </div>
                      {r.topic && <p className="text-sm text-muted-foreground">Topic: {r.topic}</p>}
                      {r.tip && <p className="text-sm text-muted-foreground">Tip: {r.tip}</p>}
                    </div>
                  ));
                })()}
              </div>
            )}
          </ResultBox>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────
export default function NovelHub() {
  const [activeTab, setActiveTab] = useState<TabId>("signal");

  const tabComponents: Record<TabId, React.ReactNode> = {
    signal:    <SignalTab />,
    trends:    <TrendsTab />,
    multimodal:<MultimodalTab />,
    adapt:     <AdaptTab />,
    burnout:   <BurnoutTab />,
  };

  const active = TABS.find(t => t.id === activeTab)!;

  return (
    <DashboardLayout>
      <div className="space-y-6 animate-fade-in">
        <div>
          <h2 className="text-2xl font-bold mb-1">🚀 Novel AI Lab</h2>
          <p className="text-muted-foreground">Next-generation multi-agent AI features for Bharat creators.</p>
        </div>

        {/* Tab Bar */}
        <div className="flex flex-wrap gap-2">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`novel-tab-${id}`}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all border ${
                activeTab === id
                  ? "bg-primary text-primary-foreground border-primary shadow-soft"
                  : "border-border text-muted-foreground hover:text-foreground hover:border-primary/40 hover:bg-primary/5"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Active Tab Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <active.icon className="h-5 w-5 text-primary" />
              {active.label}
            </CardTitle>
            <CardDescription>
              {activeTab === "signal"    && "Multi-agent swarm intelligence that scrapes, analyzes, and generates content briefs from competitor data"}
              {activeTab === "trends"    && "RAG-powered hyper-local trend injection — enhance any content with real-time regional context"}
              {activeTab === "multimodal"&& "One seed idea → production-ready scripts for podcast, video, multilingual, thumbnails, and more"}
              {activeTab === "adapt"     && "See how your content adapts and differs for every platform — optimized length, hashtags, format, and tone"}
              {activeTab === "burnout"   && "Predictive linguistic burnout detection with AI-adapted weekly schedules that evolve in real-time"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {tabComponents[activeTab]}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
