import { useState } from "react";
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
import ReactMarkdown from "react-markdown";
import { Spinner, ResultBox, Chip, CopyBtn } from "@/components/shared/IntelPrimitives";

// ─── Tab definitions ──────────────────────────────────────
const TABS = [
  { id: "signal",    label: "Signal Intelligence",    icon: Radar },
  { id: "trends",    label: "Trend Injection RAG",    icon: Globe2 },
  { id: "multimodal",label: "Multimodal Production",  icon: Clapperboard },
  { id: "adapt",     label: "Platform Adapter",       icon: Layers },
  { id: "burnout",   label: "Burnout Predictor",      icon: Brain },
] as const;

type TabId = (typeof TABS)[number]["id"];

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
      <div className="text-sm text-muted-foreground prose prose-sm dark:prose-invert max-w-none leading-relaxed">
        <ReactMarkdown>{output}</ReactMarkdown>
      </div>
    </div>
  );
}

// ─── 1. Signal Intelligence ──────────────────────────────
function SignalTab() {
  const [handles, setHandles] = useState<string[]>([""]);
  const [niche, setNiche]     = useState("");
  const [region, setRegion]   = useState("pan-india");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<SignalIntelResponse | null>(null);
  const [error, setError]     = useState("");

  const addHandle = () => setHandles([...handles, ""]);
  const removeHandle = (i: number) => setHandles(handles.filter((_, idx) => idx !== i));
  const updateHandle = (i: number, v: string) => { const h = [...handles]; h[i] = v; setHandles(h); };

  const run = async () => {
    const validHandles = handles.filter(h => h.trim());
    if (!validHandles.length || !niche.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await novelAPI.signalIntelligence(validHandles, niche, region));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

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
          <AgentCard emoji="🕵️" name={result.agents.scraper.name}    output={result.agents.scraper.output} />
          <AgentCard emoji="📊" name={result.agents.analyst.name}     output={result.agents.analyst.output} />
          <AgentCard emoji="🎯" name={result.agents.strategist.name}  output={result.agents.strategist.output} />
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
          {/* Region Context */}
          <div className="flex gap-2 flex-wrap">
            {result.region_context.languages.map((l, i) => <Chip key={i} text={l} color="blue" />)}
            {result.region_context.festivals.slice(0, 3).map((f, i) => <Chip key={i} text={`🎉 ${f}`} color="orange" />)}
          </div>

          {/* Trending Topics */}
          <ResultBox>
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">📈 Trending in {result.region}</span>
              <CopyBtn text={result.trending_topics} />
            </div>
            <div className="text-sm text-muted-foreground prose prose-sm dark:prose-invert max-w-none leading-relaxed">
              <ReactMarkdown>{result.trending_topics}</ReactMarkdown>
            </div>
          </ResultBox>

          {/* Enhanced Content */}
          <ResultBox>
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">✨ Trend-Enhanced Content</span>
              <CopyBtn text={result.enhanced_content} />
            </div>
            <div className="text-sm text-muted-foreground prose prose-sm dark:prose-invert max-w-none leading-relaxed">
              <ReactMarkdown>{result.enhanced_content}</ReactMarkdown>
            </div>
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
            {["Hindi","Tamil","Telugu","Bengali","Marathi","Kannada","English"].map(l => (
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
          <p className="text-sm text-muted-foreground">{result.successful} of {result.total_formats} formats generated</p>
          {result.productions.map((prod: MultimodalProduction, idx: number) => (
            <ResultBox key={idx}>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">{prod.format_name}</span>
                <CopyBtn text={prod.content} />
              </div>
              <div className="text-sm text-muted-foreground prose prose-sm dark:prose-invert max-w-none leading-relaxed">
                <ReactMarkdown>{prod.content}</ReactMarkdown>
              </div>
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
    instagram: "📸", youtube: "▶️", twitter: "🐦", linkedin: "💼",
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
              <div className="text-sm text-muted-foreground prose prose-sm dark:prose-invert max-w-none leading-relaxed">
                <ReactMarkdown>{preview.optimized_content}</ReactMarkdown>
              </div>
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
            <div className="text-sm text-muted-foreground prose prose-sm dark:prose-invert max-w-none leading-relaxed">
              <ReactMarkdown>{result.adapted_schedule}</ReactMarkdown>
            </div>
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
