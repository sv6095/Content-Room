import { useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Loader2, Globe, Sliders, ShieldCheck, Layers, HeartPulse, Eye, Copy, Check,
} from "lucide-react";
import {
  intelligenceAPI,
  type RiskReachResponse,
  type CultureRewriteResponse,
  type AntiCancelResponse,
  type AssetExplosionResponse,
  type AssetItem,
  type MentalHealthResponse,
  type ShadowbanResponse,
} from "@/services/api";

// ─── Tab definitions ──────────────────────────────────────
const TABS = [
  { id: "culture", label: "Culture Engine",     icon: Globe },
  { id: "risk",    label: "Risk vs Reach",       icon: Sliders },
  { id: "cancel",  label: "Anti-Cancel Shield",  icon: ShieldCheck },
  { id: "assets",  label: "Asset Explosion",     icon: Layers },
  { id: "mental",  label: "Mental Health",       icon: HeartPulse },
  { id: "shadow",  label: "Shadowban Predictor", icon: Eye },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ─── Shared helpers ───────────────────────────────────────
function Spinner() {
  return <Loader2 className="h-4 w-4 animate-spin" />;
}

function ResultBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 rounded-xl border border-border bg-muted/30 p-4 space-y-3 animate-fade-in">
      {children}
    </div>
  );
}

function Chip({ text, color }: { text: string; color: "purple" | "blue" | "orange" | "green" | "red" }) {
  const map = {
    purple: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    blue:   "bg-blue-500/10 text-blue-400 border-blue-500/20",
    orange: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    green:  "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    red:    "bg-red-500/10 text-red-400 border-red-500/20",
  };
  return <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${map[color]}`}>{text}</span>;
}

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      title="Copy"
      className="opacity-60 hover:opacity-100 transition-opacity"
    >
      {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
    </button>
  );
}

function ErrMsg({ msg }: { msg: string }) {
  return <p className="text-sm text-destructive mt-2">{msg}</p>;
}

// ─── Culture Engine ───────────────────────────────────────
function CultureTab() {
  const [content, setContent]   = useState("");
  const [region, setRegion]     = useState("");
  const [festival, setFestival] = useState("");
  const [niche, setNiche]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<CultureRewriteResponse | null>(null);
  const [error, setError]       = useState("");

  const run = async () => {
    if (!content.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await intelligenceAPI.cultureRewrite(
        content,
        region.trim() || "general",
        festival.trim() || undefined,
        niche.trim() || undefined,
      ));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="c-region">Target Region / Audience</Label>
            <Input id="c-region" value={region} onChange={e => setRegion(e.target.value)}
              placeholder="e.g. Chennai, Gen-Z Delhi, Rajasthan…" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="c-festival">Festival / Occasion</Label>
            <Input id="c-festival" value={festival} onChange={e => setFestival(e.target.value)}
              placeholder="e.g. Diwali, Onam, IPL season…" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="c-niche">Niche</Label>
            <Input id="c-niche" value={niche} onChange={e => setNiche(e.target.value)}
              placeholder="e.g. Fashion, Finance, Food…" />
          </div>
        </div>
        <div className="md:col-span-2 space-y-1.5">
          <Label htmlFor="c-content">Original Content</Label>
          <Textarea id="c-content" rows={7} value={content} onChange={e => setContent(e.target.value)}
            placeholder="Paste your content here…" className="resize-none" />
        </div>
      </div>

      <Button onClick={run} disabled={loading || !content.trim()} variant="hero" className="w-full">
        {loading ? <><Spinner /><span className="ml-2">Adapting…</span></> : "🌍 Emotionally Adapt for Region"}
      </Button>
      {error && <ErrMsg msg={error} />}

      {result && (
        <ResultBox>
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">Adapted Version</span>
            <CopyBtn text={result.rewritten} />
          </div>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{result.rewritten}</p>
          <div className="flex gap-2 flex-wrap pt-1">
            <Chip text={`Region: ${result.region}`} color="purple" />
            <Chip text={`Tone: ${result.persona_applied}`} color="blue" />
            {result.festival && <Chip text={`Festival: ${result.festival}`} color="orange" />}
          </div>
        </ResultBox>
      )}
    </div>
  );
}

// ─── Risk vs Reach ────────────────────────────────────────
function RiskTab() {
  const [content, setContent]     = useState("");
  const [riskLevel, setRiskLevel] = useState(50);
  const [platform, setPlatform]   = useState("instagram");
  const [niche, setNiche]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState<RiskReachResponse | null>(null);
  const [error, setError]         = useState("");

  const riskColor = riskLevel <= 25 ? "text-emerald-400" : riskLevel <= 50 ? "text-yellow-400" : riskLevel <= 75 ? "text-orange-400" : "text-red-400";

  const run = async () => {
    if (!content.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await intelligenceAPI.riskReachGenerate(content, riskLevel, platform, niche || undefined));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <Label>Risk Dial</Label>
          <span className={`text-lg font-bold ${riskColor}`}>{riskLevel}/100</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-emerald-400 font-semibold w-10">SAFE</span>
          <input id="risk-dial" type="range" min={0} max={100} value={riskLevel}
            onChange={e => setRiskLevel(Number(e.target.value))}
            aria-label="Risk level dial" className="flex-1 h-2 accent-orange-500 cursor-pointer" />
          <span className="text-xs text-red-400 font-semibold w-10 text-right">VIRAL</span>
        </div>
        <p className="text-xs text-muted-foreground text-center">
          {riskLevel <= 25 ? "🟢 Brand-safe, polished tone"
           : riskLevel <= 50 ? "🟡 Conversational, slightly opinionated"
           : riskLevel <= 75 ? "🟠 Bold, hook-driven, hot-takes"
           : "🔴 Maximum impact — shock value"}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="r-platform">Platform</Label>
          <select id="r-platform" aria-label="Platform" value={platform} onChange={e => setPlatform(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-ring focus:outline-none">
            <option value="instagram">Instagram</option>
            <option value="twitter">Twitter / X</option>
            <option value="youtube">YouTube</option>
            <option value="linkedin">LinkedIn</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="r-niche">Niche</Label>
          <Input id="r-niche" value={niche} onChange={e => setNiche(e.target.value)} placeholder="e.g. Finance, Fashion…" />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="r-content">Content / Idea</Label>
        <Textarea id="r-content" rows={4} value={content} onChange={e => setContent(e.target.value)}
          placeholder="Enter content or idea to rewrite…" className="resize-none" />
      </div>

      <Button onClick={run} disabled={loading || !content.trim()} variant="hero" className="w-full">
        {loading ? <><Spinner /><span className="ml-2">Generating…</span></> : "🎯 Generate at This Risk Level"}
      </Button>
      {error && <ErrMsg msg={error} />}

      {result && (
        <ResultBox>
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">{result.tone_label} Mode</span>
            <CopyBtn text={result.generated} />
          </div>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{result.generated}</p>
          <div className="grid grid-cols-3 gap-3 text-center mt-2">
            {[
              { label: "Safety Score", value: result.safety_score, color: "text-emerald-400" },
              { label: "Engagement Est.", value: `${result.estimated_engagement_probability}%`, color: "text-blue-400" },
              { label: "Moderation Risk", value: `${result.moderation_risk_percent}%`, color: "text-orange-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-lg bg-muted p-3">
                <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
                <p className={`text-lg font-bold ${color}`}>{value}</p>
              </div>
            ))}
          </div>
        </ResultBox>
      )}
    </div>
  );
}

// ─── Anti-Cancel Shield ───────────────────────────────────
function CancelTab() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<AntiCancelResponse | null>(null);
  const [error, setError]     = useState("");

  const run = async () => {
    if (!content.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await intelligenceAPI.antiCancelAnalyze(content));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  const riskColor = result?.risk_level === "HIGH" ? "text-red-400" : result?.risk_level === "MEDIUM" ? "text-yellow-400" : "text-emerald-400";

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="ac-content">Content to Audit</Label>
        <Textarea id="ac-content" rows={6} value={content} onChange={e => setContent(e.target.value)}
          placeholder="Paste your draft post, caption, or script here…" className="resize-none" />
      </div>
      <Button onClick={run} disabled={loading || !content.trim()} variant="hero" className="w-full">
        {loading ? <><Spinner /><span className="ml-2">Scanning…</span></> : "🛡️ Run Anti-Cancel Scan"}
      </Button>
      {error && <ErrMsg msg={error} />}

      {result && (
        <ResultBox>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="text-sm font-semibold">Scan Results</span>
            <span className={`text-sm font-bold ${riskColor}`}>
              {result.risk_level === "HIGH" ? "🚨 HIGH RISK" : result.risk_level === "MEDIUM" ? "⚠️ MEDIUM RISK" : "✅ LOW RISK"}
            </span>
          </div>

          {result.local_flags.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Flagged Keywords</p>
              <div className="flex flex-wrap gap-2">
                {result.local_flags.map((f, i) => (
                  <Chip key={i} text={`${f.keyword} (${f.category})`} color="red" />
                ))}
              </div>
            </div>
          )}

          {result.detected_entities.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Detected Entities</p>
              <div className="flex flex-wrap gap-2">
                {result.detected_entities.map((e, i) => (
                  <Chip key={i} text={`${e.text} (${e.type})`} color="orange" />
                ))}
              </div>
            </div>
          )}

          {result.safe_alternatives.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Recommendations</p>
              <ul className="space-y-1">
                {result.safe_alternatives.map((s, i) => (
                  <li key={i} className="text-sm text-muted-foreground flex gap-2">
                    <span className="text-emerald-400 shrink-0">→</span> {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.recommendation && (
            <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
              <p className="text-sm text-muted-foreground">{result.recommendation}</p>
            </div>
          )}
        </ResultBox>
      )}
    </div>
  );
}

// ─── Asset Explosion ──────────────────────────────────────
function AssetsTab() {
  const [idea, setIdea]       = useState("");
  const [niche, setNiche]     = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<AssetExplosionResponse | null>(null);
  const [error, setError]     = useState("");
  const [copied, setCopied]   = useState<string | null>(null);

  const run = async () => {
    if (!idea.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await intelligenceAPI.explodeAssets(idea, niche || undefined));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  const handleCopy = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const platformEmojis: Record<string, string> = {
    tweet: "🐦", instagram_caption: "📸", linkedin_post: "💼",
    youtube_title: "▶️", youtube_description: "📄", tiktok_hook: "🎵",
    whatsapp_status: "💬", facebook_post: "👍", reddit_headline: "🔖",
    email_subject: "📧", blog_intro: "✍️", push_notification: "🔔",
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="md:col-span-2 space-y-1.5">
          <Label htmlFor="ae-idea">Core Idea</Label>
          <Textarea id="ae-idea" rows={4} value={idea} onChange={e => setIdea(e.target.value)}
            placeholder="e.g. 'Just launched my skincare brand targeting college students in Tier-2 cities'"
            className="resize-none" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ae-niche">Niche</Label>
          <Input id="ae-niche" value={niche} onChange={e => setNiche(e.target.value)} placeholder="e.g. Beauty, Fitness…" />
        </div>
      </div>

      <Button onClick={run} disabled={loading || !idea.trim()} variant="hero" className="w-full">
        {loading ? <><Spinner /><span className="ml-2">Generating 12 assets…</span></> : "💥 1 Idea → 12 Assets"}
      </Button>
      {error && <ErrMsg msg={error} />}

      {result && (
        <div className="mt-2 space-y-3 animate-fade-in">
          <p className="text-sm text-muted-foreground">
            {result.successful_assets} of {result.total_assets} assets generated
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {result.assets.map((item: AssetItem, idx: number) => (
              <div key={idx} className="rounded-xl border border-border bg-muted/20 p-3 group">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    {platformEmojis[item.asset_type] || "📝"} {item.platform}
                  </span>
                  <button onClick={() => handleCopy(String(idx), item.content)}
                    title="Copy" className="opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity">
                    {copied === String(idx) ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  </button>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{item.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Mental Health Meter ──────────────────────────────────
function MentalTab() {
  const [posts, setPosts]     = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<MentalHealthResponse | null>(null);
  const [error, setError]     = useState("");

  const run = async () => {
    if (!posts.trim()) return;
    const postList = posts.split("\n---\n").map(p => p.trim()).filter(Boolean);
    if (!postList.length) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await intelligenceAPI.mentalHealthAnalyze(postList));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  const burnoutColor = result
    ? result.burnout_score > 60 ? "text-red-400" : result.burnout_score > 35 ? "text-yellow-400" : "text-emerald-400"
    : "";

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="mh-posts">Recent Posts (separate with ---)</Label>
        <Textarea id="mh-posts" rows={8} value={posts} onChange={e => setPosts(e.target.value)}
          placeholder={"Post 1: Had a great shoot today!\n---\nPost 2: New reel is up!\n---\nPost 3: Another day…"}
          className="resize-none font-mono text-sm" />
      </div>
      <Button onClick={run} disabled={loading || !posts.trim()} variant="hero" className="w-full">
        {loading ? <><Spinner /><span className="ml-2">Analyzing…</span></> : "🧠 Analyze Creator Wellbeing"}
      </Button>
      {error && <ErrMsg msg={error} />}

      {result && (
        <ResultBox>
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">Wellbeing Report</span>
            <Chip
              text={result.burnout_risk === "HIGH" ? "High Burnout Risk" : result.burnout_risk === "MEDIUM" ? "Watch Out" : "Healthy"}
              color={result.burnout_risk === "HIGH" ? "red" : result.burnout_risk === "MEDIUM" ? "orange" : "green"}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-muted-foreground">Burnout Score</span>
              <span className={`text-sm font-bold ${burnoutColor}`}>{result.burnout_score}/100</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
              <div
                className={`h-2 rounded-full transition-all ${result.burnout_score > 60 ? "bg-red-500" : result.burnout_score > 35 ? "bg-yellow-500" : "bg-emerald-500"}`}
                ref={el => { if (el) el.style.width = `${result.burnout_score}%`; }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-center">
            <div className="rounded-lg bg-muted p-3">
              <p className="text-xs text-muted-foreground mb-0.5">Linguistic Entropy</p>
              <p className="text-lg font-bold">{result.linguistic_entropy?.toFixed(2) ?? "—"}</p>
            </div>
            <div className="rounded-lg bg-muted p-3">
              <p className="text-xs text-muted-foreground mb-0.5">Sentiment Trend</p>
              <p className="text-lg font-bold">{result.sentiment_trend ?? "—"}</p>
            </div>
          </div>

          {result.recommendations && (
            <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
              <p className="text-sm text-muted-foreground">{result.recommendations}</p>
            </div>
          )}
        </ResultBox>
      )}
    </div>
  );
}

// ─── Shadowban Predictor ──────────────────────────────────
function ShadowTab() {
  const [content, setContent]   = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<ShadowbanResponse | null>(null);
  const [error, setError]       = useState("");

  const run = async () => {
    if (!content.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      setResult(await intelligenceAPI.predictShadowban(content, undefined, platform));
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Request failed."); }
    finally { setLoading(false); }
  };

  const riskColor = result?.risk_level === "HIGH" ? "text-red-400" : result?.risk_level === "MEDIUM" ? "text-yellow-400" : "text-emerald-400";

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="sb-platform">Platform</Label>
          <select id="sb-platform" aria-label="Platform" value={platform} onChange={e => setPlatform(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-ring focus:outline-none">
            <option value="instagram">Instagram</option>
            <option value="twitter">Twitter / X</option>
            <option value="youtube">YouTube</option>
            <option value="tiktok">TikTok</option>
          </select>
        </div>
        <div className="md:col-span-2 space-y-1.5">
          <Label htmlFor="sb-content">Content / Caption</Label>
          <Textarea id="sb-content" rows={4} value={content} onChange={e => setContent(e.target.value)}
            placeholder="Paste your post content or caption here…" className="resize-none" />
        </div>
      </div>

      <Button onClick={run} disabled={loading || !content.trim()} variant="hero" className="w-full">
        {loading ? <><Spinner /><span className="ml-2">Predicting…</span></> : "🔍 Predict Shadowban Risk"}
      </Button>
      {error && <ErrMsg msg={error} />}

      {result && (
        <ResultBox>
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">Risk Assessment</span>
            <span className={`text-sm font-bold ${riskColor}`}>
              {result.risk_level === "HIGH" ? "🚨 HIGH RISK" : result.risk_level === "MEDIUM" ? "⚠️ MEDIUM RISK" : "✅ LOW RISK"}
            </span>
          </div>

          <div className="rounded-lg bg-muted p-3 text-center">
            <p className="text-xs text-muted-foreground mb-0.5">Shadowban Probability</p>
            <p className={`text-2xl font-bold ${riskColor}`}>{result.shadowban_probability}%</p>
          </div>

          {result.risk_factors.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Risk Factors</p>
              <ul className="space-y-1">
                {result.risk_factors.map((f, i) => (
                  <li key={i} className="text-sm text-muted-foreground flex gap-2">
                    <span className="text-red-400 shrink-0">⚡</span> {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.risky_hashtags.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Risky Hashtags</p>
              <div className="flex flex-wrap gap-2">
                {result.risky_hashtags.map((h, i) => <Chip key={i} text={h} color="red" />)}
              </div>
            </div>
          )}

          {result.recommendation && (
            <div className="rounded-lg border border-primary/20 bg-primary/5 p-3">
              <p className="text-sm text-muted-foreground">{result.recommendation}</p>
            </div>
          )}
        </ResultBox>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────
export default function IntelligenceHub() {
  const [activeTab, setActiveTab] = useState<TabId>("culture");

  const tabComponents: Record<TabId, React.ReactNode> = {
    culture: <CultureTab />,
    risk:    <RiskTab />,
    cancel:  <CancelTab />,
    assets:  <AssetsTab />,
    mental:  <MentalTab />,
    shadow:  <ShadowTab />,
  };

  const active = TABS.find(t => t.id === activeTab)!;

  return (
    <DashboardLayout>
      <div className="space-y-6 animate-fade-in">
        <div>
          <h2 className="text-2xl font-bold mb-1">⚡ Intelligence Hub</h2>
          <p className="text-muted-foreground">Strategic AI intelligence for Bharat creators.</p>
        </div>

        {/* Tab Bar */}
        <div className="flex flex-wrap gap-2">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`intel-tab-${id}`}
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
              {activeTab === "culture" && "Emotional re-adaptation for any region, culture, or occasion"}
              {activeTab === "risk"    && "Control content risk appetite from brand-safe to maximally viral"}
              {activeTab === "cancel"  && "Pre-publication reputation defense for the Indian digital landscape"}
              {activeTab === "assets"  && "One idea → 12 platform-native content assets in parallel"}
              {activeTab === "mental"  && "Linguistic entropy analysis for creator burnout detection"}
              {activeTab === "shadow"  && "Algorithmic suppression risk prediction before you post"}
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
