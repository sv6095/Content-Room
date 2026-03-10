import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Search, TrendingUp, Lightbulb, Target, Rocket, Info, Copy, Check, CalendarPlus } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import api, { APIError } from '@/services/api';
import type { CompetitorAnalysisStructured } from '@/services/api';
import { toast } from 'sonner';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

type InsightSection = {
    title: string;
    content: string;
};

type WinningIdea = {
    title: string;
    format: string;
    whyItWins: string;
    tag?: string;
};

type CalendarIdeaPayload = {
    title: string;
    format: string;
    whyItWins: string;
    tag?: string;
    niche?: string;
};

type ParsedInsight = {
    sourceNote: string | null;
    strategy: string;
    scorecard: {
        contentQuality: number | null;
        engagement: number | null;
        consistency: number | null;
        innovation: number | null;
    };
    gaps: Array<{
        title: string;
        impact: 'HIGH' | 'MEDIUM' | 'LOW';
        effort: 'HIGH' | 'MEDIUM' | 'LOW';
        description: string;
        yourMove: string;
    }>;
    ideas: WinningIdea[];
    sections: InsightSection[];
};

function parsedFromStructured(
    sourceNote: string | null,
    structured: CompetitorAnalysisStructured
): ParsedInsight {
    return {
        sourceNote,
        strategy: cleanMarkdownMarkers(structured.competitorStrategy || ''),
        scorecard: {
            contentQuality: structured.scorecard?.contentQuality ?? null,
            engagement: structured.scorecard?.engagement ?? null,
            consistency: structured.scorecard?.consistency ?? null,
            innovation: structured.scorecard?.innovation ?? null,
        },
        gaps: (structured.gaps || []).map((gap) => ({
            title: cleanMarkdownMarkers(gap.title || ''),
            impact: gap.impact || 'MEDIUM',
            effort: gap.effort || 'MEDIUM',
            description: cleanMarkdownMarkers(gap.description || ''),
            yourMove: cleanMarkdownMarkers(gap.yourMove || ''),
        })),
        ideas: (structured.winningIdeas || []).map((idea) => ({
            title: cleanMarkdownMarkers(idea.title || ''),
            format: cleanMarkdownMarkers(idea.format || ''),
            whyItWins: cleanMarkdownMarkers(idea.whyItWins || ''),
            tag: idea.tag,
        })),
        sections: [],
    };
}

function cleanMarkdownMarkers(text: string): string {
    return text.replace(/\*\*/g, '').replace(/__/g, '').trim();
}

function parseSectionBlocks(body: string): InsightSection[] {
    const headingRegex = /(?:^|\n)\s*(?:##\s*)?(Competitor Strategy|Scorecard|Gaps\s*&\s*Opportunities|Winning Content Ideas)\s*\n/gi;
    const matches = [...body.matchAll(headingRegex)];

    if (matches.length === 0) {
        const parts = body.split(/\n##\s+|^##\s+/m).filter(Boolean);
        return parts
            .map((part) => {
                const [firstLine, ...rest] = part.split('\n');
                return {
                    title: firstLine.trim(),
                    content: rest.join('\n').trim(),
                };
            })
            .filter((section) => section.title && section.content);
    }

    const sections: InsightSection[] = [];
    for (let i = 0; i < matches.length; i++) {
        const current = matches[i];
        const start = (current.index ?? 0) + current[0].length;
        const end = i + 1 < matches.length ? (matches[i + 1].index ?? body.length) : body.length;
        sections.push({
            title: current[1].trim(),
            content: body.slice(start, end).trim(),
        });
    }
    return sections;
}

function extractWinningIdeas(content: string): WinningIdea[] {
    const ideas: WinningIdea[] = [];
    const ideaRegex = /Title:\s*"?(.*?)"?\s*Format:\s*(.*?)\s*Why It Wins:\s*([\s\S]*?)\s*Tag:\s*(.*?)(?=(?:\s*Title:)|$)/gi;
    const matches = [...content.matchAll(ideaRegex)];

    for (const match of matches) {
        const title = cleanMarkdownMarkers((match[1] || '').trim());
        const format = cleanMarkdownMarkers((match[2] || '').trim());
        const whyItWins = cleanMarkdownMarkers((match[3] || '').trim());
        const tag = cleanMarkdownMarkers((match[4] || '').trim());
        if (title && format && whyItWins) {
            ideas.push({ title, format, whyItWins, tag });
        }
    }

    if (ideas.length > 0) return ideas;

    // Fallback: split by "Title:" and try to infer fields.
    const blocks = content.split(/\n?\s*Title:\s*/i).map((x) => x.trim()).filter(Boolean);
    for (const block of blocks) {
        const formatMatch = block.match(/Format:\s*(.*?)(?:\n|Why It Wins:|$)/i);
        const whyMatch = block.match(/Why It Wins:\s*([\s\S]*?)(?:\nTag:|$)/i);
        const tagMatch = block.match(/Tag:\s*([^\n]+)/i);
        const title = cleanMarkdownMarkers(block.split(/\n|Format:|Why It Wins:/i)[0].replace(/^"|"$/g, '').trim());
        const format = cleanMarkdownMarkers((formatMatch?.[1] || '').trim());
        const whyItWins = cleanMarkdownMarkers((whyMatch?.[1] || '').trim());
        const tag = cleanMarkdownMarkers((tagMatch?.[1] || '').trim());
        if (title && format && whyItWins) {
            ideas.push({ title, format, whyItWins, tag });
        }
    }
    return ideas;
}

function parseScorecard(content: string): ParsedInsight['scorecard'] {
    const normalized = cleanMarkdownMarkers(content);
    const pick = (re: RegExp): number | null => {
        const m = normalized.match(re);
        if (!m) return null;
        const v = parseInt(m[1], 10);
        return Number.isNaN(v) ? null : v;
    };
    return {
        contentQuality: pick(/content\s*quality[^0-9]*(\d{1,3})/i),
        engagement: pick(/engagement[^0-9]*(\d{1,3})/i),
        consistency: pick(/consistency[^0-9]*(\d{1,3})/i),
        innovation: pick(/innovation[^0-9]*(\d{1,3})/i),
    };
}

function parseGaps(content: string): ParsedInsight['gaps'] {
    const blocks = content
        .split(/\n(?=\d+\.\s)/)
        .map((x) => x.trim())
        .filter(Boolean);

    const gaps: ParsedInsight['gaps'] = [];
    for (const block of blocks) {
        const lines = block.split('\n').map((line) => cleanMarkdownMarkers(line.trim())).filter(Boolean);
        if (lines.length === 0) continue;

        const title = lines[0].replace(/^\d+\.\s*/, '').trim();
        let impact: 'HIGH' | 'MEDIUM' | 'LOW' = 'MEDIUM';
        let effort: 'HIGH' | 'MEDIUM' | 'LOW' = 'MEDIUM';
        let description = '';
        let yourMove = '';

        for (const line of lines.slice(1)) {
            const impactMatch = line.match(/^[-*]?\s*Impact:\s*(HIGH|MEDIUM|LOW)/i);
            const effortMatch = line.match(/^[-*]?\s*Effort:\s*(HIGH|MEDIUM|LOW)/i);
            const descMatch = line.match(/^[-*]?\s*Description:\s*(.*)$/i);
            const moveMatch = line.match(/^[-*]?\s*Your Move:\s*(.*)$/i);

            if (impactMatch) impact = impactMatch[1].toUpperCase() as 'HIGH' | 'MEDIUM' | 'LOW';
            else if (effortMatch) effort = effortMatch[1].toUpperCase() as 'HIGH' | 'MEDIUM' | 'LOW';
            else if (descMatch) description = descMatch[1].trim();
            else if (moveMatch) yourMove = moveMatch[1].trim();
            else if (!description) description = line.replace(/^[-*]\s*/, '').trim();
        }

        if (title) {
            gaps.push({
                title,
                impact,
                effort,
                description,
                yourMove,
            });
        }
    }
    return gaps;
}

function parseInsightSections(markdown: string): ParsedInsight {
    const trimmed = markdown.trim();
    if (!trimmed) {
        return {
            sourceNote: null,
            strategy: '',
            scorecard: { contentQuality: null, engagement: null, consistency: null, innovation: null },
            gaps: [],
            ideas: [],
            sections: [],
        };
    }

    let body = trimmed;
    let sourceNote: string | null = null;

    // Backend prepends source note as italic markdown: *...*
    const sourceMatch = body.match(/^\*([^*]+)\*\s*/);
    if (sourceMatch) {
        sourceNote = sourceMatch[1].trim();
        body = body.slice(sourceMatch[0].length).trim();
    }

    const sections = parseSectionBlocks(body);
    const strategySection = sections.find((s) => s.title.toLowerCase().includes('strategy'));
    const scorecardSection = sections.find((s) => s.title.toLowerCase().includes('scorecard'));
    const gapsSection = sections.find((s) => s.title.toLowerCase().includes('gap'));
    const ideasSection = sections.find((s) => s.title.toLowerCase().includes('winning') || s.title.toLowerCase().includes('idea'));

    const strategy = strategySection ? cleanMarkdownMarkers(strategySection.content) : '';
    const scorecard = scorecardSection
        ? parseScorecard(scorecardSection.content)
        : { contentQuality: null, engagement: null, consistency: null, innovation: null };
    const gaps = gapsSection ? parseGaps(gapsSection.content) : [];
    const ideas = ideasSection ? extractWinningIdeas(ideasSection.content) : [];

    return { sourceNote, strategy, scorecard, gaps, ideas, sections };
}

const impactColors: Record<'HIGH' | 'MEDIUM' | 'LOW', string> = {
    HIGH: '#FF6B6B',
    MEDIUM: '#FFD700',
    LOW: '#4ADE80',
};

const effortColors: Record<'HIGH' | 'MEDIUM' | 'LOW', string> = {
    HIGH: '#FF6B6B',
    MEDIUM: '#F59E0B',
    LOW: '#4ADE80',
};

const impactBg: Record<'HIGH' | 'MEDIUM' | 'LOW', string> = {
    HIGH: 'rgba(255,107,107,0.12)',
    MEDIUM: 'rgba(255,215,0,0.12)',
    LOW: 'rgba(74,222,128,0.12)',
};

const ideaTagColors: Record<string, string> = {
    'Quick Win': '#FFD700',
    'Credibility Boost': '#00E5FF',
    'Engagement Driver': '#FF6B6B',
    'Long Game': '#A78BFA',
};

function scoreColor(score: number | null) {
    if (score == null) return 'text-muted-foreground';
    if (score >= 60) return 'text-emerald-400';
    if (score >= 40) return 'text-yellow-400';
    return 'text-red-400';
}

function platformFromUrl(url: string): string {
    const u = url.toLowerCase();
    if (u.includes('instagram')) return 'Instagram';
    if (u.includes('x.com') || u.includes('twitter')) return 'Twitter/X';
    if (u.includes('youtube') || u.includes('youtu.be')) return 'YouTube';
    if (u.includes('linkedin')) return 'LinkedIn';
    if (u.includes('facebook')) return 'Facebook';
    return 'Web';
}

function handleFromUrl(url: string): string {
    const clean = url.trim().replace(/\/+$/, '');
    if (!clean) return '@competitor';
    const parts = clean.split('/').filter(Boolean);
    const last = parts[parts.length - 1] || 'competitor';
    return last.startsWith('@') ? last : `@${last}`;
}

function gapEmoji(title: string): string {
    const t = title.toLowerCase();
    if (t.includes('tutorial') || t.includes('education')) return '📚';
    if (t.includes('stories') || t.includes('igtv') || t.includes('video')) return '🎬';
    if (t.includes('collab') || t.includes('expert')) return '🤝';
    if (t.includes('community') || t.includes('ugc') || t.includes('engagement')) return '🔥';
    if (t.includes('consisten')) return '📅';
    return '💡';
}

function parseFormatsFromIdeaText(formatText: string): string[] {
    const t = formatText.toLowerCase();
    const mapped = new Set<string>();
    if (t.includes('reel')) mapped.add('reel');
    if (t.includes('story')) mapped.add('story');
    if (t.includes('live')) mapped.add('live');
    if (t.includes('video') || t.includes('igtv') || t.includes('youtube')) mapped.add('video');
    if (t.includes('blog') || t.includes('article') || t.includes('thread')) mapped.add('blog');
    return Array.from(mapped);
}

const CompetitorAnalysis: React.FC = () => {
    const navigate = useNavigate();
    const [url, setUrl] = useState('');
    const [niche, setNiche] = useState('');
    const [loading, setLoading] = useState(false);
    const [analysis, setAnalysis] = useState<string | null>(null);
    const [sourceNote, setSourceNote] = useState<string | null>(null);
    const [structured, setStructured] = useState<CompetitorAnalysisStructured | null>(null);
    const [copiedIdea, setCopiedIdea] = useState<number | null>(null);
    const [activeGap, setActiveGap] = useState<number | null>(null);
    const [activeTab, setActiveTab] = useState<'gaps' | 'strategy' | 'ideas'>('gaps');
    const parsed: ParsedInsight = structured
        ? parsedFromStructured(sourceNote, structured)
        : analysis
            ? parseInsightSections(analysis)
            : {
            sourceNote: null,
            strategy: '',
            scorecard: { contentQuality: null, engagement: null, consistency: null, innovation: null },
            gaps: [],
            ideas: [],
            sections: [],
        };

    const scoreEntries = useMemo(() => ([
        { key: 'Content', value: parsed.scorecard.contentQuality },
        { key: 'Engagement', value: parsed.scorecard.engagement },
        { key: 'Consistency', value: parsed.scorecard.consistency },
        { key: 'Innovation', value: parsed.scorecard.innovation },
    ]), [parsed.scorecard]);

    const strongest = useMemo(() => {
        const valid = scoreEntries.filter((x) => x.value != null) as Array<{ key: string; value: number }>;
        if (valid.length === 0) return null;
        return [...valid].sort((a, b) => b.value - a.value)[0];
    }, [scoreEntries]);

    const weakest = useMemo(() => {
        const valid = scoreEntries.filter((x) => x.value != null) as Array<{ key: string; value: number }>;
        if (valid.length === 0) return null;
        return [...valid].sort((a, b) => a.value - b.value)[0];
    }, [scoreEntries]);

    const competitorHandle = useMemo(() => handleFromUrl(url), [url]);
    const competitorPlatform = useMemo(() => platformFromUrl(url), [url]);

    const copyIdea = async (idea: WinningIdea, index: number) => {
        const text = `Title: ${idea.title}\nFormat: ${idea.format}\nWhy It Wins: ${idea.whyItWins}`;
        await navigator.clipboard.writeText(text);
        setCopiedIdea(index);
        toast.success("Idea copied to clipboard");
        window.setTimeout(() => setCopiedIdea(null), 1400);
    };

    const addIdeaToCalendar = (idea: WinningIdea) => {
        const payload: CalendarIdeaPayload = {
            title: idea.title,
            format: idea.format,
            whyItWins: idea.whyItWins,
            tag: idea.tag ?? 'Quick Win',
            niche: niche || undefined,
        };
        localStorage.setItem('calendar-idea-prefill', JSON.stringify(payload));
        navigate('/calendar', {
            state: {
                calendarIdea: payload,
                calendarSuggestedFormats: parseFormatsFromIdeaText(idea.format),
            },
        });
    };

    const handleAnalyze = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!url || !niche) {
            toast.error("Please provide both a URL and your niche.");
            return;
        }

        setLoading(true);
        setAnalysis(null);
        setSourceNote(null);
        setStructured(null);
        setActiveGap(null);

        try {
            const response = await api.competitor.analyze(url, niche);
            setAnalysis(response.analysis);
            setSourceNote(response.source_note ?? null);
            setStructured(response.analysis_structured ?? null);
            toast.success("Analysis complete!");
        } catch (error) {
            console.error(error);
            
            // Handle specific API errors
            if (error instanceof APIError) {
                if (error.status === 401) {
                    toast.error("Please log in to analyze competitors.");
                } else if (error.status === 403) {
                    toast.error("You don't have permission to access this feature.");
                } else {
                    toast.error(error.message || "Failed to analyze competitor. Please try again.");
                }
            } else {
                toast.error("Failed to analyze competitor. Please try again.");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <DashboardLayout>
            <div className="space-y-8 animate-fade-in">
            <div className="flex flex-col space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">Competitor Intelligence</h1>
                <p className="text-muted-foreground">
                    Analyze competitor profiles to find content gaps and opportunities for your niche.
                </p>
            </div>

            <Card className="max-w-3xl">
                <CardHeader>
                    <CardTitle>Analyze a Competitor</CardTitle>
                    <CardDescription>
                        Enter a public social media profile URL or blog link to uncover their strategy.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleAnalyze} className="space-y-4">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="url">Competitor URL</Label>
                                <div className="relative">
                                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                    <Input 
                                        id="url" 
                                        placeholder="https://twitter.com/competitor" 
                                        className="pl-9"
                                        value={url}
                                        onChange={(e) => setUrl(e.target.value)}
                                        disabled={loading}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="niche">My Niche</Label>
                                <Input 
                                    id="niche" 
                                    placeholder="e.g. Sustainable Fashion" 
                                    value={niche}
                                    onChange={(e) => setNiche(e.target.value)}
                                    disabled={loading}
                                />
                            </div>
                        </div>
                        <Button type="submit" className="w-full" disabled={loading}>
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Analyzing Strategy...
                                </>
                            ) : (
                                <>
                                    <TrendingUp className="mr-2 h-4 w-4" />
                                    Identify Gaps & Opportunities
                                </>
                            )}
                        </Button>
                    </form>
                </CardContent>
            </Card>

            {(analysis || structured) && (
                <div className="space-y-5">
                    <style>{`
                        @keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
                        @keyframes pulseDot { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
                        .intel-fade { animation: fadeUp .45s ease both; }
                        .intel-score-fill { transition: width .8s ease; }
                    `}</style>

                    <Card className="border-primary/20 bg-[#0D0D0D] text-[#F0F0F0] intel-fade">
                        <CardHeader className="pb-4 border-b border-white/10">
                            <div className="flex items-center gap-2 text-[11px] tracking-[0.18em] uppercase text-[#777]">
                                <span>Competitor Intel</span>
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" style={{ animation: 'pulseDot 2s infinite' }} />
                                <span className="text-emerald-400 tracking-[0.08em]">Live Analysis</span>
                            </div>
                            <div className="flex items-end justify-between gap-4">
                                <div>
                                    <CardTitle className="text-2xl font-bold text-[#F5F5F5]">Strategic Edge Report</CardTitle>
                                    <CardDescription className="text-[#8B8B8B] mt-1">
                                        Scraped from <span className="text-primary">{competitorHandle}</span> · {competitorPlatform} · Updated just now
                                    </CardDescription>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {[
                                        { key: 'gaps', label: '🎯 Gaps' },
                                        { key: 'strategy', label: '🗺 Strategy' },
                                        { key: 'ideas', label: '🚀 Ideas' },
                                    ].map((tab) => (
                                        <button
                                            key={tab.key}
                                            onClick={() => setActiveTab(tab.key as 'gaps' | 'strategy' | 'ideas')}
                                            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                                                activeTab === tab.key
                                                    ? 'bg-primary text-black'
                                                    : 'bg-white/5 text-[#9A9A9A] hover:text-primary'
                                            }`}
                                        >
                                            {tab.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </CardHeader>

                        <CardContent className="pt-5 space-y-5">
                            {parsed.sourceNote && (
                                <div className="rounded-xl border border-primary/25 bg-primary/10 p-4">
                                    <p className="text-xs font-semibold uppercase tracking-wide text-primary mb-1 flex items-center gap-1">
                                        <Info className="h-3.5 w-3.5" />
                                        Source Note
                                    </p>
                                    <p className="text-sm text-[#CFCFCF]">{parsed.sourceNote}</p>
                                </div>
                            )}

                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 intel-fade">
                                {scoreEntries.map((item) => (
                                    <div key={item.key} className="rounded-xl border border-white/10 p-3 bg-white/[0.03]">
                                        <div className="flex items-center justify-between mb-2">
                                            <p className="text-xs uppercase tracking-wide text-[#8A8A8A]">{item.key}</p>
                                            <p className={`text-lg font-semibold ${scoreColor(item.value)}`}>
                                                {item.value ?? '—'}
                                            </p>
                                        </div>
                                        <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                                            <div
                                                className="h-full rounded-full bg-primary intel-score-fill"
                                                style={{ width: `${Math.max(0, Math.min(item.value ?? 0, 100))}%` }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {activeTab === 'gaps' && parsed.gaps.length > 0 && (
                                <div className="grid gap-3 md:grid-cols-2 intel-fade">
                                    {parsed.gaps.map((gap, idx) => (
                                        <div
                                            key={`${gap.title}-${idx}`}
                                            onClick={() => setActiveGap(activeGap === idx ? null : idx)}
                                            className={`rounded-xl border p-4 cursor-pointer transition-all ${
                                                activeGap === idx
                                                    ? 'border-primary bg-primary/10'
                                                    : 'border-white/10 bg-white/[0.03] hover:border-primary/40'
                                            }`}
                                        >
                                            <div className="flex items-start justify-between gap-3 mb-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xl">{gapEmoji(gap.title)}</span>
                                                    <h4 className="font-semibold text-sm">{gap.title}</h4>
                                                </div>
                                                <div className="flex gap-1.5">
                                                    <span
                                                        className="text-[10px] px-2 py-0.5 rounded-full border"
                                                        style={{ color: impactColors[gap.impact], borderColor: `${impactColors[gap.impact]}66`, background: impactBg[gap.impact] }}
                                                    >
                                                        {gap.impact} IMPACT
                                                    </span>
                                                    <span
                                                        className="text-[10px] px-2 py-0.5 rounded-full border"
                                                        style={{ color: effortColors[gap.effort], borderColor: `${effortColors[gap.effort]}66` }}
                                                    >
                                                        {gap.effort} EFFORT
                                                    </span>
                                                </div>
                                            </div>
                                            {gap.description && (
                                                <p className="text-sm text-[#B5B5B5] leading-relaxed">{gap.description}</p>
                                            )}
                                            {activeGap === idx && gap.yourMove && (
                                                <div className="mt-3 rounded-lg border border-primary/30 bg-primary/5 p-3">
                                                    <p className="text-[11px] uppercase tracking-wide text-primary mb-1">Your Move</p>
                                                    <p className="text-sm text-[#E5D36C] leading-relaxed">{gap.yourMove}</p>
                                                </div>
                                            )}
                                            {activeGap !== idx && (
                                                <p className="text-xs text-[#666] mt-2">Click to see your move →</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                            {activeTab === 'gaps' && parsed.gaps.length === 0 && (
                                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-[#B5B5B5]">
                                    No high-confidence gap cards were generated. Review the full analysis below for additional context.
                                </div>
                            )}

                            {activeTab === 'strategy' && (
                                <div className="grid gap-3 md:grid-cols-2 intel-fade">
                                    <div className="rounded-xl border border-white/10 p-4 bg-white/[0.03] md:col-span-2">
                                        <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                                            <TrendingUp className="h-4 w-4 text-primary" />
                                            Competitor Strategy
                                        </h4>
                                        <p className="text-sm text-[#B5B5B5] leading-relaxed">
                                            {parsed.strategy || 'Strategy details unavailable.'}
                                        </p>
                                    </div>
                                    <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
                                        <p className="text-xs uppercase tracking-wide text-red-400 mb-1">Weakest Metric</p>
                                        <p className="text-sm text-[#D4D4D4]">
                                            {weakest ? `${weakest.key} (${weakest.value}/100)` : 'Not available'}
                                        </p>
                                    </div>
                                    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
                                        <p className="text-xs uppercase tracking-wide text-emerald-400 mb-1">Strongest Metric</p>
                                        <p className="text-sm text-[#D4D4D4]">
                                            {strongest ? `${strongest.key} (${strongest.value}/100)` : 'Not available'}
                                        </p>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'ideas' && parsed.ideas.length > 0 && (
                                <div className="grid gap-3 md:grid-cols-3 intel-fade">
                                    {parsed.ideas.map((idea, idx) => (
                                        <div
                                            key={`${idea.title}-${idx}`}
                                            className="rounded-xl border p-4 bg-white/[0.03] transition hover:-translate-y-1"
                                            style={{ borderColor: `${ideaTagColors[idea.tag || 'Quick Win'] || '#FFD700'}55` }}
                                        >
                                            <div className="flex items-start justify-between gap-2 mb-2">
                                                <div>
                                                    {idea.tag && (
                                                        <p
                                                            className="text-[11px] uppercase tracking-wide mb-1"
                                                            style={{ color: ideaTagColors[idea.tag] || '#FFD700' }}
                                                        >
                                                            {idea.tag}
                                                        </p>
                                                    )}
                                                    <h4 className="font-semibold text-sm">{idea.title}</h4>
                                                </div>
                                                <Button variant="outline" size="sm" onClick={() => copyIdea(idea, idx)}>
                                                    {copiedIdea === idx ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                                                </Button>
                                            </div>
                                            <p className="text-xs text-primary mb-2">{idea.format}</p>
                                            <p className="text-sm text-[#B5B5B5] leading-relaxed">{idea.whyItWins}</p>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="mt-3 border-primary/40 text-primary hover:bg-primary/10"
                                                onClick={() => addIdeaToCalendar(idea)}
                                            >
                                                <CalendarPlus className="h-3.5 w-3.5 mr-1.5" />
                                                Add to Calendar
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            )}
                            {activeTab === 'ideas' && parsed.ideas.length === 0 && (
                                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-[#B5B5B5]">
                                    No ready-to-use ideas were parsed from this run. Check the fallback analysis text below.
                                </div>
                            )}

                            {(activeTab === 'gaps' && parsed.gaps.length === 0) ||
                            (activeTab === 'ideas' && parsed.ideas.length === 0) ? (
                                <article className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-primary prose-a:text-blue-500">
                                    <ReactMarkdown>{analysis || ''}</ReactMarkdown>
                                </article>
                            ) : null}
                        </CardContent>
                    </Card>
                </div>
            )}
            </div>
        </DashboardLayout>
    );
};

export default CompetitorAnalysis;
