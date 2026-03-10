import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { EmptyState } from '@/components/shared/EmptyState';
import {
  Calendar, Clock, Plus, Trash2, Loader2, AlertCircle,
  Rocket, CheckCircle2, XCircle, ChevronDown, ChevronUp, Paperclip
} from 'lucide-react';
import {
  schedulerAPI,
  pipelineAPI,
  type ScheduledPost,
  type PreFlightResponse,
  APIError,
} from '@/services/api';
import { ALLOWED_LANGUAGE_OPTIONS } from '@/constants/languages';

// ─── Supported language list ───────────────────────────────
const LANGUAGES = [...ALLOWED_LANGUAGE_OPTIONS];
const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');

const PLATFORMS = ["instagram", "facebook", "twitter", "youtube", "linkedin"];

// ─── Pre-Flight Report UI ─────────────────────────────────
function ScorePill({
  label, value, color,
}: { label: string; value: string | number; color: string }) {
  return (
    <div className="rounded-lg bg-muted/60 p-2.5 text-center">
      <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
      <p className={`text-sm font-bold ${color}`}>{value}</p>
    </div>
  );
}

function PreFlightReport({
  report, onApprove, onDiscard,
}: {
  report: PreFlightResponse;
  onApprove: () => void;
  onDiscard: () => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const s = report.summary;

  const cancelColor =
    s.cancel_risk === 'HIGH' ? 'text-red-400' :
    s.cancel_risk === 'MEDIUM' ? 'text-yellow-400' : 'text-emerald-400';

  const shadowColor =
    (s.shadowban_probability ?? 0) >= 60 ? 'text-red-400' :
    (s.shadowban_probability ?? 0) >= 30 ? 'text-yellow-400' : 'text-emerald-400';

  const passColor = s.overall_pass ? 'text-emerald-400' : 'text-red-400';
  const passLabel = s.overall_pass ? '✅ Content Looks Good' : '🚨 Issues Found — Review Before Scheduling';

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Banner */}
      <div className={`rounded-xl border p-4 ${
        s.overall_pass
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : 'border-red-500/30 bg-red-500/5'
      }`}>
        <p className={`text-base font-bold ${passColor}`}>{passLabel}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          Pre-flight ran {6 - s.errors_count} of 6 checks in parallel.{' '}
          {s.errors_count > 0 && `${s.errors_count} check(s) had errors.`}
        </p>
      </div>

      {/* Score Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <ScorePill
          label="Cancel Risk"
          value={s.cancel_risk}
          color={cancelColor}
        />
        <ScorePill
          label="Shadowban %"
          value={s.shadowban_probability !== undefined ? `${s.shadowban_probability}%` : '—'}
          color={shadowColor}
        />
        <ScorePill
          label="Safety Score"
          value={s.safety_score !== undefined ? `${s.safety_score}/100` : '—'}
          color="text-blue-400"
        />
        <ScorePill
          label="Alignment"
          value={s.alignment_score !== undefined ? `${s.alignment_score}/100` : '—'}
          color="text-violet-400"
        />
        <ScorePill
          label="Sentiment"
          value={s.content_sentiment}
          color={s.content_sentiment === 'POSITIVE' ? 'text-emerald-400' : s.content_sentiment === 'NEGATIVE' ? 'text-red-400' : 'text-yellow-400'}
        />
        <ScorePill
          label="Quick Assets"
          value={`${s.assets_generated} generated`}
          color="text-orange-400"
        />
      </div>

      {/* Mental Health Quick Tip */}
      {report.mental_health && (
        <div className="rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
          <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-1">💡 Creator Tip</p>
          <p className="text-sm text-muted-foreground">{report.mental_health.tone_advice}</p>
        </div>
      )}

      {/* Expandable Detail Sections */}
      {report.culture && (
        <details className="rounded-xl border border-border overflow-hidden">
          <summary className="px-4 py-3 cursor-pointer text-sm font-medium flex items-center justify-between hover:bg-muted/30 transition-colors list-none">
            <span>🌍 Culture Adaptation</span>
            <span className="text-xs text-muted-foreground">Score: {report.culture.alignment_score ?? '—'}/100</span>
          </summary>
          <div className="px-4 pb-3 space-y-2">
            <p className="text-xs text-muted-foreground">Adapted version:</p>
            <p className="text-sm bg-muted/30 rounded-lg p-2 whitespace-pre-wrap">{report.culture.rewritten}</p>
          </div>
        </details>
      )}

      {report.anti_cancel && (
        <details className="rounded-xl border border-border overflow-hidden">
          <summary className="px-4 py-3 cursor-pointer text-sm font-medium flex items-center justify-between hover:bg-muted/30 transition-colors list-none">
            <span>🛡️ Anti-Cancel Result</span>
            <span className={`text-xs font-bold ${cancelColor}`}>{s.cancel_risk}</span>
          </summary>
          <div className="px-4 pb-3 space-y-2">
            {report.anti_cancel.recommendation && (
              <p className="text-sm text-muted-foreground">{report.anti_cancel.recommendation}</p>
            )}
            {report.anti_cancel.local_flags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {report.anti_cancel.local_flags.slice(0, 5).map((f, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-orange-500/15 text-orange-400 border border-orange-500/20">
                    ⚠ {f.keyword}
                  </span>
                ))}
              </div>
            )}
          </div>
        </details>
      )}

      {report.shadowban && (
        <details className="rounded-xl border border-border overflow-hidden">
          <summary className="px-4 py-3 cursor-pointer text-sm font-medium flex items-center justify-between hover:bg-muted/30 transition-colors list-none">
            <span>🔍 Shadowban Prediction</span>
            <span className={`text-xs font-bold ${shadowColor}`}>{report.shadowban.shadowban_probability}%</span>
          </summary>
          <div className="px-4 pb-3">
            <p className="text-sm text-muted-foreground">{report.shadowban.recommendation}</p>
          </div>
        </details>
      )}

      {report.assets && report.assets.assets.length > 0 && (
        <details className="rounded-xl border border-border overflow-hidden">
          <summary className="px-4 py-3 cursor-pointer text-sm font-medium flex items-center justify-between hover:bg-muted/30 transition-colors list-none">
            <span>💥 Quick Content Spin-offs</span>
            <span className="text-xs text-muted-foreground">{report.assets.total_generated} generated</span>
          </summary>
          <div className="px-4 pb-3 space-y-2">
            {report.assets.assets.map((a, i) => (
              <div key={i} className="rounded-lg bg-muted/30 p-2">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">{a.platform}</p>
                <p className="text-sm text-muted-foreground line-clamp-2">{a.content}</p>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-1">
        <Button
          variant="hero"
          className="flex-1"
          onClick={onApprove}
        >
          <CheckCircle2 className="h-4 w-4 mr-2" />
          Approve &amp; Set Schedule
        </Button>
        <Button variant="outline" onClick={onDiscard}>
          <XCircle className="h-4 w-4 mr-2" />
          Discard
        </Button>
      </div>
    </div>
  );
}

// ─── Main Scheduler Page ──────────────────────────────────
export default function Scheduler() {
  const [searchParams] = useSearchParams();
  const contentIdParam = searchParams.get('contentId');
  const contentId = useMemo(() => {
    if (!contentIdParam) return undefined;
    const n = parseInt(contentIdParam, 10);
    return Number.isNaN(n) ? undefined : n;
  }, [contentIdParam]);

  const [posts, setPosts]                   = useState<ScheduledPost[]>([]);
  const [isLoading, setIsLoading]           = useState(true);
  const [isCreating, setIsCreating]         = useState(false);
  const [isSubmitting, setIsSubmitting]     = useState(false);
  const [isAnalyzing, setIsAnalyzing]       = useState(false);
  const [error, setError]                   = useState<string | null>(null);
  const [deletingId, setDeletingId]         = useState<number | null>(null);
  const [preflightReport, setPreflightReport] = useState<PreFlightResponse | null>(null);
  const [showApprovalForm, setShowApprovalForm] = useState(false);

  // Pipeline inputs
  const [content, setContent]     = useState('');
  const [region, setRegion]       = useState('');
  const [language, setLanguage]   = useState('English');
  const [platform, setPlatform]   = useState('instagram');
  const [niche, setNiche]         = useState('');
  const [riskLevel, setRiskLevel] = useState(50);
  const [festival, setFestival]   = useState('');

  // Schedule form (shown after pre-flight approval)
  const [form, setForm] = useState({ title: '', notes: '', date: '', time: '' });
  const [mediaFile, setMediaFile] = useState<File | null>(null);

  useEffect(() => { fetchPosts(); }, []);

  const fetchPosts = async () => {
    setIsLoading(true); setError(null);
    try {
      setPosts(await schedulerAPI.listPosts());
    } catch (err) {
      setError(err instanceof APIError ? err.message : 'Failed to load scheduled items.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!content.trim()) return;
    setIsAnalyzing(true); setError(null); setPreflightReport(null);
    try {
      const report = await pipelineAPI.analyze({
        content,
        region: region || 'general',
        target_language: language,
        platform,
        niche: niche || undefined,
        risk_level: riskLevel,
        festival: festival || undefined,
      });
      setPreflightReport(report);
    } catch (err) {
      setError(err instanceof APIError ? err.message : 'Pre-flight analysis failed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApprove = () => {
    // Pre-fill the schedule title from content snippet
    setForm(f => ({ ...f, title: content.slice(0, 60).trim() + (content.length > 60 ? '…' : '') }));
    setShowApprovalForm(true);
  };

  const handleDiscard = () => {
    setPreflightReport(null);
    setShowApprovalForm(false);
  };

  const handleAdd = async () => {
    if (!form.title.trim() || !form.date || !form.time) return;
    setIsSubmitting(true); setError(null);
    try {
      const scheduledAt = new Date(`${form.date}T${form.time}`).toISOString();
      let created: ScheduledPost;

      if (mediaFile) {
        const result = await schedulerAPI.createPostWithMedia(
          form.title.trim(),
          scheduledAt,
          mediaFile,
          form.notes.trim() || undefined,
          platform
        );
        created = result.post;
      } else {
        created = await schedulerAPI.createPost({
          title: form.title.trim(),
          description: form.notes.trim() || undefined,
          scheduled_at: scheduledAt,
          content_id: contentId,
          platform,
        });
      }
      setPosts(prev => [...prev, created].sort(
        (a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime()
      ));
      // Reset everything
      setForm({ title: '', notes: '', date: '', time: '' });
      setMediaFile(null);
      setContent(''); setRegion(''); setNiche(''); setFestival('');
      setPreflightReport(null); setShowApprovalForm(false); setIsCreating(false);
    } catch (err) {
      setError(err instanceof APIError ? err.message : 'Failed to add item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await schedulerAPI.cancelPost(id);
      setPosts(prev => prev.filter(p => p.id !== id));
    } catch (err) {
      setError(err instanceof APIError ? err.message : 'Failed to remove item.');
    } finally {
      setDeletingId(null);
    }
  };

  const fmt = (iso: string) =>
    new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });

  // Group posts by date
  const grouped = posts
    .filter(p => p.status !== 'cancelled')
    .reduce<Record<string, ScheduledPost[]>>((acc, post) => {
      const day = new Date(post.scheduled_at).toLocaleDateString(undefined, {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
      });
      (acc[day] = acc[day] ?? []).push(post);
      return acc;
    }, {});

  return (
    <DashboardLayout>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold mb-1">📅 Content Schedule</h2>
            <p className="text-muted-foreground">
              Upload content → run AI pre-flight → schedule with confidence.
            </p>
          </div>
          {!isCreating && (
            <Button variant="hero" onClick={() => { setIsCreating(true); setError(null); }}>
              <Plus className="h-4 w-4 mr-2" />
              Analyze &amp; Schedule
            </Button>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive">
            <p className="text-sm font-medium flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {error}
            </p>
          </div>
        )}

        {/* ── Pre-Flight Analyzer ─────────────────────────────── */}
        {isCreating && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Rocket className="h-5 w-5 text-primary" />
                Pre-Flight Content Analyzer
              </CardTitle>
              <CardDescription>
                Paste your content. The AI will run all 6 intelligence checks in parallel before you schedule.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Content input */}
              <div className="space-y-1.5">
                <Label htmlFor="pf-content">Content / Caption</Label>
                <Textarea
                  id="pf-content"
                  rows={4}
                  placeholder="Paste your post, caption, or script here…"
                  value={content}
                  onChange={e => setContent(e.target.value)}
                  className="resize-none"
                />
              </div>

              {/* Media input */}
              <div className="space-y-1.5">
                <Label htmlFor="pf-media">Upload Media (Image, Video, Document)</Label>
                <Input
                  id="pf-media"
                  type="file"
                  accept="image/*,video/*,.pdf,.doc,.docx"
                  onChange={e => setMediaFile(e.target.files?.[0] || null)}
                  className="cursor-pointer"
                />
              </div>

              {/* Config row */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="pf-platform">Platform</Label>
                  <select
                    id="pf-platform"
                    aria-label="Target platform"
                    value={platform}
                    onChange={e => setPlatform(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-ring focus:outline-none"
                  >
                    {PLATFORMS.map(p => (
                      <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pf-lang">🌐 Language</Label>
                  <select
                    id="pf-lang"
                    aria-label="Output language"
                    value={language}
                    onChange={e => setLanguage(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-ring focus:outline-none"
                  >
                    {LANGUAGES.map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pf-region">Target Region</Label>
                  <Input
                    id="pf-region"
                    placeholder="e.g. mumbai, chennai…"
                    value={region}
                    onChange={e => setRegion(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pf-niche">Niche (optional)</Label>
                  <Input
                    id="pf-niche"
                    placeholder="e.g. Fashion, Tech…"
                    value={niche}
                    onChange={e => setNiche(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pf-festival">Festival (optional)</Label>
                  <Input
                    id="pf-festival"
                    placeholder="e.g. Diwali, Holi…"
                    value={festival}
                    onChange={e => setFestival(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="pf-risk">Risk Level: {riskLevel}/100</Label>
                  <input
                    id="pf-risk"
                    type="range"
                    min={0}
                    max={100}
                    value={riskLevel}
                    aria-label={`Risk level: ${riskLevel} out of 100`}
                    onChange={e => setRiskLevel(Number(e.target.value))}
                    className="w-full h-2 accent-orange-500 cursor-pointer mt-2"
                  />
                </div>
              </div>

              {/* Analyze button */}
              {!preflightReport && !showApprovalForm && (
                <div className="flex flex-col sm:flex-row gap-3">
                  <Button
                    variant="hero"
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || !content.trim()}
                    className="flex-1"
                    id="pf-analyze-btn"
                    title={!content.trim() ? "Add text content to run pre-flight checks" : ""}
                  >
                    {isAnalyzing
                      ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Running 6 AI checks in parallel…</>
                      : <><Rocket className="h-4 w-4 mr-2" />Run Pre-Flight Analysis</>
                    }
                  </Button>
                  <Button 
                    variant="secondary"
                    onClick={() => {
                      setForm(f => ({ ...f, title: content.slice(0, 60).trim() + (content.length > 60 ? '…' : '') || mediaFile?.name || 'Scheduled Post' }));
                      setShowApprovalForm(true);
                      setPreflightReport(null);
                    }}
                    disabled={!content.trim() && !mediaFile}
                    className="flex-1"
                  >
                    <CheckCircle2 className="h-4 w-4 mr-2" />Skip to Schedule
                  </Button>
                  <Button variant="outline" onClick={() => { setIsCreating(false); setPreflightReport(null); setShowApprovalForm(false); }}>
                    Cancel
                  </Button>
                </div>
              )}

              {/* ── Pre-Flight Report ── */}
              {preflightReport && !showApprovalForm && (
                <div className="border-t border-border pt-4">
                  <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                    <Rocket className="h-4 w-4 text-primary" />
                    Pre-Flight Report
                  </h3>
                  <PreFlightReport
                    report={preflightReport}
                    onApprove={handleApprove}
                    onDiscard={handleDiscard}
                  />
                </div>
              )}

              {/* ── Schedule Form (post-approval) ── */}
              {showApprovalForm && (
                <div className="border-t border-border pt-4 space-y-4">
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    Set Your Schedule
                  </h3>
                  <div className="space-y-1.5">
                    <Label htmlFor="sch-title">Title *</Label>
                    <Input
                      id="sch-title"
                      placeholder="e.g. Diwali Campaign Reel"
                      value={form.title}
                      onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="sch-notes">Notes (optional)</Label>
                    <Textarea
                      id="sch-notes"
                      placeholder="Any reminders, ideas, or context for this task…"
                      value={form.notes}
                      onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                      rows={3}
                      className="resize-none"
                    />
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <Label htmlFor="sch-date">Date *</Label>
                      <Input
                        id="sch-date"
                        type="date"
                        value={form.date}
                        onChange={e => setForm(f => ({ ...f, date: e.target.value }))}
                        min={new Date().toISOString().split('T')[0]}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="sch-time">Time *</Label>
                      <Input
                        id="sch-time"
                        type="time"
                        value={form.time}
                        onChange={e => setForm(f => ({ ...f, time: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <Button
                      variant="hero"
                      onClick={handleAdd}
                      disabled={!form.title.trim() || !form.date || !form.time || isSubmitting}
                    >
                      {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                      Add to Schedule
                    </Button>
                    <Button variant="outline" onClick={handleDiscard} disabled={isSubmitting}>
                      Back to Report
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* ── Calendar View ─────────────────────────────────────── */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : Object.keys(grouped).length > 0 ? (
          <div className="space-y-6">
            {Object.entries(grouped).map(([day, dayPosts]) => (
              <div key={day}>
                <div className="flex items-center gap-3 mb-3">
                  <Calendar className="h-4 w-4 text-primary" />
                  <span className="text-sm font-semibold text-primary">{day}</span>
                  <div className="flex-1 h-px bg-border" />
                </div>

                <div className="space-y-2">
                  {dayPosts.map(post => (
                    <div
                      key={post.id}
                      className="flex items-start justify-between gap-4 p-4 rounded-xl border border-border bg-card hover:bg-accent/30 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{post.title}</p>
                        {post.description && (
                          <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">{post.description}</p>
                        )}
                        <div className="flex items-center gap-1 mt-1.5 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {fmt(post.scheduled_at)}
                          {post.media_url && (
                            <div className="flex items-center gap-1 ml-3 text-primary">
                              <Paperclip className="h-3 w-3" />
                              <a href={`${API_BASE}${post.media_url}`} target="_blank" rel="noreferrer" className="hover:underline">
                                Attachment
                              </a>
                            </div>
                          )}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(post.id)}
                        disabled={deletingId === post.id}
                        className="text-muted-foreground hover:text-destructive shrink-0"
                        title="Remove from schedule"
                      >
                        {deletingId === post.id
                          ? <Loader2 className="h-4 w-4 animate-spin" />
                          : <Trash2 className="h-4 w-4" />
                        }
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="py-12">
              <EmptyState
                icon={<Calendar className="h-8 w-8" />}
                title="Nothing scheduled yet"
                description="Click 'Analyze & Schedule' to run a pre-flight check on your content before adding it to the calendar."
              />
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
