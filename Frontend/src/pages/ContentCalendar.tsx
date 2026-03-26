import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Calendar as CalendarIcon, Download, ChevronRight, Zap, ArrowRight } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as XLSX from 'xlsx';
import api, { APIError } from '@/services/api';
import type { CachedCalendarItem } from '@/services/api';
import { toast } from 'sonner';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useAuth } from '@/contexts/AuthContext';

const CONTENT_FORMAT_OPTIONS = ['reel', 'video', 'live', 'blog', 'story'] as const;
type ContentFormatOption = typeof CONTENT_FORMAT_OPTIONS[number];
const MONTH_OPTIONS = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'] as const;
const LAST_CALENDAR_STORAGE_KEY_BASE = 'content-calendar:last-view';

// Content format color scheme - professional UX design
const FORMAT_COLORS: Record<string, { bg: string; border: string; text: string; accent: string }> = {
  reel: { bg: 'bg-rose-50 dark:bg-rose-950', border: 'border-rose-200 dark:border-rose-800', text: 'text-rose-700 dark:text-rose-300', accent: 'bg-rose-500' },
  video: { bg: 'bg-blue-50 dark:bg-blue-950', border: 'border-blue-200 dark:border-blue-800', text: 'text-blue-700 dark:text-blue-300', accent: 'bg-blue-500' },
  live: { bg: 'bg-amber-50 dark:bg-amber-950', border: 'border-amber-200 dark:border-amber-800', text: 'text-amber-700 dark:text-amber-300', accent: 'bg-amber-500' },
  blog: { bg: 'bg-emerald-50 dark:bg-emerald-950', border: 'border-emerald-200 dark:border-emerald-800', text: 'text-emerald-700 dark:text-emerald-300', accent: 'bg-emerald-500' },
  story: { bg: 'bg-purple-50 dark:bg-purple-950', border: 'border-purple-200 dark:border-purple-800', text: 'text-purple-700 dark:text-purple-300', accent: 'bg-purple-500' },
  default: { bg: 'bg-slate-50 dark:bg-slate-900', border: 'border-slate-200 dark:border-slate-700', text: 'text-slate-700 dark:text-slate-300', accent: 'bg-slate-500' }
};

const getFormatColor = (format: string) => FORMAT_COLORS[format.toLowerCase()] || FORMAT_COLORS.default;

type CalendarIdeaPayload = {
    title: string;
    format: string;
    whyItWins: string;
    tag?: string;
    niche?: string;
};

type CalendarPost = {
    postNumber: string;
    dateText: string;
    day: number | null;
    autoMapped?: boolean;
    contentPillar: string;
    topic: string;
    format: string;
    captionHook: string;
};

function parseMarkdownTableToAoA(markdown: string): string[][] {
    const lines = markdown
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.startsWith('|') && line.endsWith('|'));

    if (lines.length < 3) return [];

    const headerIdx = lines.findIndex((line) => /Post\s*#|Date|Format/i.test(line));
    if (headerIdx === -1 || headerIdx + 2 >= lines.length) return [];

    const tableLines = lines.slice(headerIdx);
    const rows: string[][] = [];

    for (let i = 0; i < tableLines.length; i++) {
        if (i === 1) {
            continue;
        }
        const cells = tableLines[i]
            .split('|')
            .slice(1, -1)
            .map((cell) => cell.trim());

        if (cells.some((cell) => cell.length > 0)) {
            rows.push(cells);
        }
    }

    return rows;
}

function parseDayFromDateText(dateText: string, month: string, year: number): number | null {
    const normalized = (dateText || '').trim();
    if (!normalized) return null;

    const monthDate = new Date(`${month} 1, ${year}`);
    const monthIdx = Number.isNaN(monthDate.getTime()) ? 0 : monthDate.getMonth();
    const monthNum = monthIdx + 1;
    const maxDay = new Date(year, monthIdx + 1, 0).getDate();

    // yyyy-mm-dd / yyyy/mm/dd
    const isoMatch = normalized.match(/\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b/);
    if (isoMatch) {
        const y = parseInt(isoMatch[1], 10);
        const m = parseInt(isoMatch[2], 10);
        const d = parseInt(isoMatch[3], 10);
        if (y === year && m === monthNum && d >= 1 && d <= maxDay) return d;
    }

    // dd/mm or mm/dd (disambiguate using selected month)
    const slashMatch = normalized.match(/\b([0-3]?\d)[/-]([0-3]?\d)\b/);
    if (slashMatch) {
        const a = parseInt(slashMatch[1], 10);
        const b = parseInt(slashMatch[2], 10);
        if (b === monthNum && a >= 1 && a <= maxDay) return a; // dd/mm
        if (a === monthNum && b >= 1 && b <= maxDay) return b; // mm/dd
        if (a > 12 && a >= 1 && a <= maxDay) return a;
        if (b > 12 && b >= 1 && b <= maxDay) return b;
    }

    // "5 March", "March 5", "5th"
    const dayMatch = normalized.match(/\b([0-3]?\d)(?:st|nd|rd|th)?\b/i);
    if (dayMatch) {
        const day = parseInt(dayMatch[1], 10);
        if (day >= 1 && day <= maxDay) return day;
    }

    const parsed = new Date(`${normalized} ${year}`);
    if (!Number.isNaN(parsed.getTime()) && parsed.getMonth() === monthIdx) {
        return parsed.getDate();
    }

    return null;
}

function parseMarkdownCalendarPosts(markdown: string, month: string, year: number): CalendarPost[] {
    const rows = parseMarkdownTableToAoA(markdown);
    if (rows.length < 2) return [];

    const dataRows = rows.slice(1);
    return dataRows.map((row, idx) => {
        const dateText = row[1] || '';
        return {
            postNumber: row[0] || String(idx + 1),
            dateText,
            day: parseDayFromDateText(dateText, month, year),
            autoMapped: false,
            contentPillar: row[2] || '',
            topic: row[3] || '',
            format: row[4] || '',
            captionHook: row[5] || '',
        };
    });
}

/**
 * Map undated posts to days in the month.
 * @param posts - Array of posts with some potentially missing dates
 * @param daysInMonth - Total days in the month
 * @param startFromDay - Optional: start mapping from this day (useful for current month to start from today)
 * @returns Posts with all dates assigned
 */
function mapPostsToMonth(posts: CalendarPost[], daysInMonth: number, startFromDay: number = 1): CalendarPost[] {
    if (!posts.length || daysInMonth < 1) return posts;
    
    // Validate startFromDay
    const validStartDay = Math.max(1, Math.min(daysInMonth, startFromDay));
    const availableDays = daysInMonth - validStartDay + 1; // Days remaining from start to end of month
    
    const normalized = posts.map((post) => {
        if (post.day && post.day >= 1 && post.day <= daysInMonth) return post;
        return { ...post, day: null };
    });
    const unknown = normalized.filter((p) => !p.day);
    if (unknown.length === 0) return normalized;

    // Distribute remaining posts across available days
    let unknownIdx = 0;
    return normalized.map((post) => {
        if (post.day) return post;
        unknownIdx += 1;
        const distributedDay = Math.max(
            validStartDay,
            Math.min(daysInMonth, Math.ceil(validStartDay + (unknownIdx * availableDays) / (unknown.length + 1) - 1))
        );
        return { ...post, day: distributedDay, autoMapped: true };
    });
}

const ContentCalendar: React.FC = () => {
    const location = useLocation();
    const prefillAppliedRef = useRef(false);
    const { user } = useAuth();
    const today = new Date();
    const userStorageSuffix = user?.id || user?.email || 'anonymous';
    const lastCalendarStorageKey = `${LAST_CALENDAR_STORAGE_KEY_BASE}:${userStorageSuffix}`;
    const calendarIdeaPrefillKey = `calendar-idea-prefill:${userStorageSuffix}`;
    const [month, setMonth] = useState(MONTH_OPTIONS[today.getMonth()]);
    const [year, setYear] = useState(String(today.getFullYear()));
    const [niche, setNiche] = useState('');
    const [goals, setGoals] = useState('Engage with audience and promote services');
    const [contentFormats, setContentFormats] = useState<string[]>([...CONTENT_FORMAT_OPTIONS]);
    const [postsPerMonth, setPostsPerMonth] = useState('12');
    const [loading, setLoading] = useState(false);
    const [calendar, setCalendar] = useState<string | null>(null);
    const [calendarDisplayMonth, setCalendarDisplayMonth] = useState<string | null>(null);
    const [calendarDisplayYear, setCalendarDisplayYear] = useState<number | null>(null);
    const [cachedCalendars, setCachedCalendars] = useState<CachedCalendarItem[]>([]);
    const [loadingCached, setLoadingCached] = useState(false);
    const [selectedCachedId, setSelectedCachedId] = useState<string>("");
    const [resultView, setResultView] = useState<'calendar' | 'table'>('calendar');
    const [expandedDay, setExpandedDay] = useState<number | null>(null);
    const [selectedPost, setSelectedPost] = useState<CalendarPost | null>(null);

    useEffect(() => {
        try {
            const raw = localStorage.getItem(lastCalendarStorageKey);
            if (!raw) return;
            const parsed = JSON.parse(raw) as {
                calendar?: string;
                month?: string;
                year?: number;
            };
            if (parsed?.calendar && typeof parsed.calendar === 'string') {
                setCalendar(parsed.calendar);
                if (parsed.month && MONTH_OPTIONS.includes(parsed.month as typeof MONTH_OPTIONS[number])) {
                    setCalendarDisplayMonth(parsed.month);
                }
                if (typeof parsed.year === 'number' && parsed.year >= 2000 && parsed.year <= 2100) {
                    setCalendarDisplayYear(parsed.year);
                }
            }
        } catch {
            // Ignore malformed local cache.
        }
    }, [lastCalendarStorageKey]);

    useEffect(() => {
        if (!calendar) return;
        const monthToPersist = calendarDisplayMonth || month;
        const parsedYear = parseInt(year, 10);
        const yearToPersist = calendarDisplayYear ?? (Number.isNaN(parsedYear) ? new Date().getFullYear() : parsedYear);
        localStorage.setItem(
            lastCalendarStorageKey,
            JSON.stringify({
                calendar,
                month: monthToPersist,
                year: yearToPersist,
            })
        );
    }, [calendar, calendarDisplayMonth, calendarDisplayYear, month, year, lastCalendarStorageKey]);

    useEffect(() => {
        if (prefillAppliedRef.current) return;
        prefillAppliedRef.current = true;

        const routeState = location.state as
            | { calendarIdea?: CalendarIdeaPayload; calendarSuggestedFormats?: string[] }
            | null;

        let idea: CalendarIdeaPayload | null = routeState?.calendarIdea ?? null;
        const suggestedFormats = routeState?.calendarSuggestedFormats ?? [];

        if (!idea) {
            const raw = localStorage.getItem(calendarIdeaPrefillKey);
            if (raw) {
                try {
                    const parsed = JSON.parse(raw) as CalendarIdeaPayload;
                    if (parsed && parsed.title && parsed.format && parsed.whyItWins) {
                        idea = parsed;
                    }
                } catch {
                    idea = null;
                }
            }
        }

        if (!idea) return;

        if (!niche.trim() && idea.niche?.trim()) {
            setNiche(idea.niche.trim());
        }

        const compiledGoal = [
            'Prioritize this competitor insight in this month plan:',
            `Idea: ${idea.title}`,
            `Format: ${idea.format}`,
            `Why it wins: ${idea.whyItWins}`,
            idea.tag ? `Tag: ${idea.tag}` : '',
        ]
            .filter(Boolean)
            .join('\n');
        setGoals(compiledGoal);

        if (suggestedFormats.length === 0) {
            const t = idea.format.toLowerCase();
            if (t.includes('reel')) suggestedFormats.push('reel');
            if (t.includes('story')) suggestedFormats.push('story');
            if (t.includes('live')) suggestedFormats.push('live');
            if (t.includes('video') || t.includes('igtv') || t.includes('youtube')) suggestedFormats.push('video');
            if (t.includes('blog') || t.includes('article') || t.includes('thread')) suggestedFormats.push('blog');
        }

        const valid = Array.from(new Set(suggestedFormats)).filter((f): f is ContentFormatOption =>
            (CONTENT_FORMAT_OPTIONS as readonly string[]).includes(f)
        );
        if (valid.length > 0) {
            setContentFormats(valid);
        }

        setCalendar(null);
        localStorage.removeItem(calendarIdeaPrefillKey);
        toast.success(`Idea "${idea.title}" added. Review and generate your calendar.`);
    }, [location.state, niche, calendarIdeaPrefillKey]);

    const handleGenerate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!niche) {
            toast.error("Please specify your niche.");
            return;
        }
        if (contentFormats.length === 0) {
            toast.error("Please choose at least one content format.");
            return;
        }
        const parsedPostsPerMonth = parseInt(postsPerMonth, 10);
        if (Number.isNaN(parsedPostsPerMonth) || parsedPostsPerMonth < 1 || parsedPostsPerMonth > 120) {
            toast.error("Posts per month must be between 1 and 120.");
            return;
        }

        setLoading(true);

        try {
            const parsedYear = parseInt(year, 10);
            if (Number.isNaN(parsedYear) || parsedYear < 2000 || parsedYear > 2100) {
                toast.error("Please enter a valid year between 2000 and 2100.");
                return;
            }
            const response = await api.calendar.generate({
                month,
                year: parsedYear,
                niche,
                goals,
                content_formats: contentFormats,
                posts_per_month: parsedPostsPerMonth,
            });
            setCalendar(response.calendar_markdown);
            setCalendarDisplayMonth(month);
            setCalendarDisplayYear(parsedYear);
            setExpandedDay(null);
            setSelectedPost(null);
            toast.success("Calendar generated successfully!");
        } catch (error) {
            console.error(error);
            const message = error instanceof APIError ? error.message : "Failed to generate calendar. Please try again.";
            toast.error(message);
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = () => {
        if (!calendar) return;
        const rows = parseMarkdownTableToAoA(calendar);
        if (rows.length === 0) {
            toast.error("Could not parse the calendar table. Please regenerate and try again.");
            return;
        }

        const worksheet = XLSX.utils.aoa_to_sheet(rows);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, `${month}-${year}`);
        XLSX.writeFile(workbook, `Content-Calendar-${month}-${year}.xlsx`);
    };

    const toggleFormat = (format: string) => {
        setContentFormats((prev) =>
            prev.includes(format)
                ? prev.filter((item) => item !== format)
                : [...prev, format]
        );
    };

    const handleLoadCachedCalendars = async () => {
        const parsedYear = parseInt(year, 10);
        setLoadingCached(true);
        try {
            const response = await api.calendar.getCached({
                month,
                year: Number.isNaN(parsedYear) ? undefined : parsedYear,
                niche: niche.trim() || undefined,
                limit: 20,
            });
            if (response.items.length === 0) {
                toast.info("No saved calendars found for current filters.");
                return;
            }
            setCachedCalendars(response.items);
            const first = response.items[0];
            setSelectedCachedId(first.content_id);
            setCalendar(first.calendar_markdown);
            setCalendarDisplayMonth(first.month || month);
            setCalendarDisplayYear(first.year ?? (Number.isNaN(parsedYear) ? new Date().getFullYear() : parsedYear));
            setResultView('calendar');
            setExpandedDay(null);
            setSelectedPost(null);
            toast.success("Loaded your latest calendar.");
        } catch (error) {
            const message = error instanceof APIError ? error.message : "Failed to load cached calendars.";
            toast.error(message);
        } finally {
            setLoadingCached(false);
        }
    };

    const handleSelectCached = (contentId: string) => {
        setSelectedCachedId(contentId);
        const selected = cachedCalendars.find((item) => item.content_id === contentId);
        if (selected) {
            setCalendar(selected.calendar_markdown);
            setCalendarDisplayMonth(selected.month || month);
            const parsedYear = parseInt(year, 10);
            setCalendarDisplayYear(selected.year ?? (Number.isNaN(parsedYear) ? new Date().getFullYear() : parsedYear));
            setResultView('calendar');
            setExpandedDay(null);
            setSelectedPost(null);
            toast.success("Calendar loaded.");
        }
    };

    const effectiveDisplayMonth = calendarDisplayMonth || month;
    const parsedYearForDisplay = calendarDisplayYear ?? (() => {
        const parsed = parseInt(year, 10);
        return Number.isNaN(parsed) ? new Date().getFullYear() : parsed;
    })();
    const parsedMonthDate = new Date(`${effectiveDisplayMonth} 1, ${parsedYearForDisplay}`);
    const monthIndexForDisplay = Number.isNaN(parsedMonthDate.getTime()) ? 0 : parsedMonthDate.getMonth();
    const daysInMonth = new Date(parsedYearForDisplay, monthIndexForDisplay + 1, 0).getDate();
    const firstWeekday = new Date(parsedYearForDisplay, monthIndexForDisplay, 1).getDay();
    const weekdayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const daySlots: Array<number | null> = [
        ...Array.from({ length: firstWeekday }, () => null),
        ...Array.from({ length: daysInMonth }, (_, idx) => idx + 1),
    ];
    while (daySlots.length % 7 !== 0) daySlots.push(null);

    const rawPosts = calendar ? parseMarkdownCalendarPosts(calendar, effectiveDisplayMonth, parsedYearForDisplay) : [];
    
    const isCurrentMonthView =
        parsedYearForDisplay === today.getFullYear() &&
        monthIndexForDisplay === today.getMonth();
    const todayDay = today.getDate();
    
    // When viewing current month, map posts starting from today; otherwise start from day 1
    const mappingStartDay = isCurrentMonthView ? todayDay : 1;
    const posts = mapPostsToMonth(rawPosts, daysInMonth, mappingStartDay);
    const postsByDay = posts.reduce<Record<number, CalendarPost[]>>((acc, post) => {
        if (!post.day) return acc;
        if (!acc[post.day]) acc[post.day] = [];
        acc[post.day].push(post);
        return acc;
    }, {});
    const autoMappedCount = posts.filter((p) => p.autoMapped).length;
    const mappedDayCount = Object.keys(postsByDay).length;

    return (
        <DashboardLayout>
            <div className="space-y-8 animate-fade-in">
            <div className="flex flex-col space-y-2 md:flex-row md:items-end md:justify-between">
                <div className="space-y-2">
                    <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-primary via-primary to-primary/70 bg-clip-text text-transparent">
                        AI Content Calendar
                    </h1>
                    <p className="text-lg text-muted-foreground max-w-2xl">
                        Generate a month-long content strategy tailored to your niche and audiences. Start from today, every day.
                    </p>
                </div>
                {isCurrentMonthView && (
                    <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary/5 border-2 border-primary/20 w-fit">
                        <Zap className="w-4 h-4 text-primary animate-pulse" />
                        <span className="font-semibold text-sm text-primary">Today: {today.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</span>
                    </div>
                )}
            </div>

            <div className="grid gap-6 md:grid-cols-[1fr_2fr]">
                <Card className="h-fit sticky top-6">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CalendarIcon className="w-5 h-5" />
                            Plan Your Month
                        </CardTitle>
                        <CardDescription>Craft your monthly content strategy.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleGenerate} className="space-y-5">
                            <div className="space-y-3 p-4 rounded-lg bg-muted/30 border border-muted/50">
                                <div className="space-y-2">
                                    <Label htmlFor="month" className="text-xs font-bold uppercase tracking-wide">Month</Label>
                                    <Select value={month} onValueChange={(value) => setMonth(value as typeof MONTH_OPTIONS[number])}>
                                        <SelectTrigger className="h-10">
                                            <SelectValue placeholder="Select Month" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {MONTH_OPTIONS.map(m => (
                                                <SelectItem key={m} value={m}>{m}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                
                                <div className="space-y-2">
                                    <Label htmlFor="year" className="text-xs font-bold uppercase tracking-wide">Year</Label>
                                    <Input 
                                        id="year" 
                                        type="number" 
                                        value={year} 
                                        onChange={(e) => setYear(e.target.value)}
                                        className="h-10"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="niche" className="text-xs font-bold uppercase tracking-wide">My Niche</Label>
                                <Input 
                                    id="niche" 
                                    placeholder="e.g. Finance for Millennials" 
                                    value={niche}
                                    onChange={(e) => setNiche(e.target.value)}
                                    className="h-10"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="goals" className="text-xs font-bold uppercase tracking-wide">Content Goals</Label>
                                <Input 
                                    id="goals" 
                                    placeholder="e.g. Increase engagement" 
                                    value={goals}
                                    onChange={(e) => setGoals(e.target.value)}
                                    className="h-10"
                                />
                            </div>

                            <div className="space-y-3">
                                <Label className="text-xs font-bold uppercase tracking-wide">Content Formats</Label>
                                <div className="grid grid-cols-2 gap-2">
                                    {CONTENT_FORMAT_OPTIONS.map((format) => {
                                        const selected = contentFormats.includes(format);
                                        const colors = getFormatColor(format);
                                        return (
                                            <Button
                                                key={format}
                                                type="button"
                                                variant={selected ? "default" : "outline"}
                                                onClick={() => toggleFormat(format)}
                                                className={`capitalize transition-all duration-300 h-10 font-semibold ${
                                                    selected 
                                                        ? `${colors.bg} ${colors.text} border-2 ${colors.border.replace('border-', 'border-')} shadow-md`
                                                        : 'hover:border-primary/50'
                                                }`}
                                            >
                                                {format}
                                            </Button>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="posts-per-month" className="text-xs font-bold uppercase tracking-wide">Posts Per Month: <span className="text-primary font-bold">{postsPerMonth}</span></Label>
                                <Input
                                    id="posts-per-month"
                                    type="number"
                                    min={1}
                                    max={120}
                                    value={postsPerMonth}
                                    onChange={(e) => setPostsPerMonth(e.target.value)}
                                    className="h-10"
                                />
                                <p className="text-xs text-muted-foreground">Distributes {postsPerMonth} posts across the month.</p>
                            </div>

                            <Button 
                                type="submit" 
                                className="w-full h-11 font-bold text-base gap-2 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-lg hover:shadow-xl transition-all duration-300" 
                                disabled={loading}
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <Zap className="w-5 h-5" />
                                        Generate Plan
                                    </>
                                )}
                            </Button>

                            <Button
                                type="button"
                                variant="outline"
                                className="w-full h-10 font-semibold gap-2 hover:bg-muted/70 transition-colors duration-300"
                                onClick={handleLoadCachedCalendars}
                                disabled={loadingCached}
                            >
                                {loadingCached ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Loading...
                                    </>
                                ) : (
                                    <>
                                        <ChevronRight className="w-4 h-4" />
                                        Load Your Calendars
                                    </>
                                )}
                            </Button>

                            {cachedCalendars.length > 0 && (
                                <div className="space-y-2 pt-2 border-t border-border">
                                    <Label htmlFor="cached-calendar" className="text-xs font-bold uppercase tracking-wide">Previous Calendars</Label>
                                    <Select value={selectedCachedId} onValueChange={handleSelectCached}>
                                        <SelectTrigger id="cached-calendar" className="h-10">
                                            <SelectValue placeholder="Select calendar" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {cachedCalendars.map((item) => {
                                                const stamp = new Date(item.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                                                const label = `${item.month} ${item.year} • ${item.niche} (${stamp})`;
                                                return (
                                                    <SelectItem key={item.content_id} value={item.content_id}>
                                                        {label}
                                                    </SelectItem>
                                                );
                                            })}
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}
                        </form>
                    </CardContent>
                </Card>

                {calendar ? (
                    <Card className="h-full">
                        <CardHeader className="pb-4 border-b border-border/50">
                            <div className="space-y-3 sm:flex sm:items-center sm:justify-between sm:space-y-0">
                                <div className="space-y-1">
                                    <CardTitle className="text-2xl">Your {effectiveDisplayMonth} {parsedYearForDisplay} Calendar</CardTitle>
                                    <CardDescription>Visual planner with {posts.length} content pieces</CardDescription>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                    <div className="flex gap-1 bg-muted/50 p-1 rounded-lg border border-border">
                                        <Button
                                            variant={resultView === 'calendar' ? "default" : "ghost"}
                                            size="sm"
                                            onClick={() => setResultView('calendar')}
                                            className="font-semibold transition-all duration-300"
                                        >
                                            <CalendarIcon className="w-4 h-4 mr-1.5" />
                                            Calendar
                                        </Button>
                                        <Button
                                            variant={resultView === 'table' ? "default" : "ghost"}
                                            size="sm"
                                            onClick={() => setResultView('table')}
                                            className="font-semibold transition-all duration-300"
                                        >
                                            Table
                                        </Button>
                                    </div>
                                    <Button 
                                        variant="outline" 
                                        size="sm" 
                                        onClick={handleDownload}
                                        className="font-semibold gap-1.5 hover:bg-emerald-500/10 hover:border-emerald-500/50 transition-all duration-300"
                                    >
                                        <Download className="w-4 h-4" />
                                        <span className="hidden sm:inline">Export</span>
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="max-h-[800px] overflow-y-auto pt-6">
                            {resultView === 'calendar' ? (
                                <div className="space-y-6">
                                    {/* Enhanced Calendar Stats */}
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                        <div className="p-3 rounded-lg bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 group hover:border-primary/40 transition-all duration-300">
                                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Total Posts</p>
                                            <p className="text-2xl font-bold text-primary mt-1">{posts.length}</p>
                                        </div>
                                        <div className="p-3 rounded-lg bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border border-emerald-200/50 dark:border-emerald-800/50">
                                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Scheduled Days</p>
                                            <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{mappedDayCount}</p>
                                        </div>
                                        <div className="p-3 rounded-lg bg-gradient-to-br from-amber-500/10 to-amber-500/5 border border-amber-200/50 dark:border-amber-800/50">
                                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Auto-Mapped</p>
                                            <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{autoMappedCount}</p>
                                        </div>
                                        <div className="p-3 rounded-lg bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-200/50 dark:border-blue-800/50">
                                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Today</p>
                                            <p className="text-sm font-semibold text-blue-600 dark:text-blue-400 mt-1">{today.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</p>
                                        </div>
                                    </div>

                                    {/* Enhanced Calendar Grid */}
                                    <div className="space-y-4">
                                        <div className="grid grid-cols-7 gap-1 sm:gap-2 bg-gradient-to-b from-muted/40 to-transparent p-3 rounded-lg">
                                            {weekdayLabels.map((label, idx) => {
                                                const isWeekend = idx === 0 || idx === 6;
                                                return (
                                                    <div 
                                                        key={label} 
                                                        className={`text-xs font-bold uppercase tracking-widest text-center py-2 rounded-md transition-colors duration-300 ${
                                                            isWeekend ? 'text-muted-foreground/60' : 'text-primary/80'
                                                        }`}
                                                    >
                                                        {label}
                                                    </div>
                                                );
                                            })}
                                        </div>

                                        <div className="grid grid-cols-7 gap-1 sm:gap-2 auto-rows-max">
                                            {daySlots.map((day, idx) => {
                                                const isToday = isCurrentMonthView && day === todayDay;
                                                const dayPosts = day ? (postsByDay[day] || []) : [];
                                                const isExpanded = expandedDay === day;
                                                const isWeekend = (firstWeekday + (day || 0)) % 7 === 0 || (firstWeekday + (day || 0)) % 7 === 6;
                                                const displayedPosts = isExpanded ? dayPosts : dayPosts.slice(0, 2);
                                                const hasMorePosts = dayPosts.length > 2 && !isExpanded;

                                                return (
                                                    <div
                                                        key={`${day ?? 'empty'}-${idx}`}
                                                        className={`
                                                            transition-all duration-300 rounded-xl border-2 p-3 sm:p-4 min-h-[140px] sm:min-h-[160px]
                                                            ${day 
                                                                ? (isToday 
                                                                    ? 'bg-gradient-to-br from-primary/15 via-primary/5 to-transparent border-primary shadow-lg shadow-primary/20 ring-2 ring-primary/30'
                                                                    : isWeekend
                                                                    ? 'bg-muted/30 border-muted/50 hover:border-primary/50 hover:bg-muted/50'
                                                                    : 'bg-background border-border hover:border-primary/50 hover:bg-muted/30'
                                                                )
                                                                : 'bg-muted/10 border-dashed border-muted/30'
                                                            }
                                                            group cursor-pointer
                                                        `}
                                                    >
                                                        {day ? (
                                                            <div className="space-y-3 h-full flex flex-col">
                                                                <div className="flex items-center justify-between">
                                                                    <div className="flex items-center gap-2">
                                                                        <button
                                                                            type="button"
                                                                            className={`
                                                                                text-lg sm:text-xl font-bold transition-all duration-300
                                                                                ${isToday 
                                                                                    ? 'text-primary bg-primary/10 w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center shadow-md'
                                                                                    : 'text-foreground hover:text-primary'
                                                                                }
                                                                            `}
                                                                            aria-label={`Day ${day}${isToday ? ' - Today' : ''}`}
                                                                        >
                                                                            {day}
                                                                        </button>
                                                                        {isToday && (
                                                                            <div className="flex items-center gap-1">
                                                                                <Zap className="w-3.5 h-3.5 text-primary animate-pulse" />
                                                                                <span className="text-xs font-semibold text-primary">Today</span>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                    {dayPosts.length > 0 && (
                                                                        <div className="text-xs font-bold text-muted-foreground bg-muted/60 px-2 py-1 rounded-full">
                                                                            {dayPosts.length}
                                                                        </div>
                                                                    )}
                                                                </div>

                                                                {dayPosts.length > 0 ? (
                                                                    <div className="space-y-2 flex-1 overflow-hidden">
                                                                        {displayedPosts.map((post, i) => {
                                                                            const format = post.format.toLowerCase();
                                                                            const colors = getFormatColor(format);
                                                                            return (
                                                                                <button
                                                                                    type="button"
                                                                                    key={`${post.postNumber}-${i}`}
                                                                                    className={`
                                                                                        w-full text-left rounded-lg p-2.5 transition-all duration-300
                                                                                        border-l-4 group/post
                                                                                        ${colors.bg} ${colors.border} ${colors.text}
                                                                                        hover:shadow-md hover:scale-105 hover:z-10
                                                                                        transform
                                                                                    `}
                                                                                    style={{ borderLeftColor: colors.accent }}
                                                                                    onClick={() => setSelectedPost(post)}
                                                                                >
                                                                                    <div className="flex items-start justify-between gap-2">
                                                                                        <div className="min-w-0 flex-1">
                                                                                            <p className="text-xs sm:text-sm font-semibold line-clamp-2 leading-tight">{post.topic || post.captionHook}</p>
                                                                                        </div>
                                                                                        <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover/post:opacity-100 transition-opacity flex-shrink-0 mt-0.5" />
                                                                                    </div>
                                                                                    <div className="flex items-center gap-1.5 mt-1.5">
                                                                                        <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-tighter bg-black/10 dark:bg-white/10">
                                                                                            {post.format}
                                                                                        </span>
                                                                                        {post.autoMapped && (
                                                                                            <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-tighter bg-amber-500/20 text-amber-700 dark:text-amber-300">
                                                                                                Auto
                                                                                            </span>
                                                                                        )}
                                                                                    </div>
                                                                                </button>
                                                                            );
                                                                        })}
                                                                        {hasMorePosts && (
                                                                            <button
                                                                                type="button"
                                                                                className="text-xs font-bold text-primary hover:text-primary/80 transition-colors px-2.5 py-1.5 rounded-lg hover:bg-primary/5"
                                                                                onClick={() => setExpandedDay(isExpanded ? null : day)}
                                                                            >
                                                                                <ArrowRight className="w-3 h-3 inline mr-1" />
                                                                                See {dayPosts.length - 2} more
                                                                            </button>
                                                                        )}
                                                                        {isExpanded && dayPosts.length > 2 && (
                                                                            <button
                                                                                type="button"
                                                                                className="text-xs font-bold text-muted-foreground hover:text-foreground transition-colors px-2.5 py-1.5"
                                                                                onClick={() => setExpandedDay(null)}
                                                                            >
                                                                                Show less
                                                                            </button>
                                                                        )}
                                                                    </div>
                                                                ) : (
                                                                    <div className="flex-1 flex items-center justify-center text-center">
                                                                        <p className="text-xs text-muted-foreground/60">No posts</p>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ) : null}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* Enhanced Detail Panel */}
                                    {selectedPost && (
                                        <div className="relative rounded-xl border-2 border-primary/30 bg-gradient-to-br from-primary/5 via-background to-background p-5 sm:p-6 space-y-4 shadow-lg animate-in fade-in slide-in-from-bottom-4 duration-300">
                                            <div className="absolute top-4 left-4 right-4 flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <div className={`w-3 h-3 rounded-full ${getFormatColor(selectedPost.format).accent}`}></div>
                                                    <h3 className="text-sm font-bold">Post {selectedPost.postNumber}</h3>
                                                </div>
                                                <Button 
                                                    variant="ghost" 
                                                    size="sm" 
                                                    onClick={() => setSelectedPost(null)}
                                                    className="hover:bg-muted"
                                                >
                                                    ✕
                                                </Button>
                                            </div>
                                            
                                            <div className="pt-6 space-y-3">
                                                <div className="space-y-1">
                                                    <p className="text-xs font-bold uppercase text-muted-foreground tracking-wide">Date</p>
                                                    <p className="text-sm text-foreground">{selectedPost.dateText || 'Auto-assigned'}</p>
                                                </div>

                                                <div className="grid grid-cols-2 gap-3">
                                                    <div className="space-y-1">
                                                        <p className="text-xs font-bold uppercase text-muted-foreground tracking-wide">Format</p>
                                                        <div className={`inline-block px-3 py-1.5 rounded-lg font-bold text-xs uppercase tracking-tighter ${getFormatColor(selectedPost.format).bg} ${getFormatColor(selectedPost.format).text} border ${getFormatColor(selectedPost.format).border}`}>
                                                            {selectedPost.format}
                                                        </div>
                                                    </div>
                                                    {selectedPost.autoMapped && (
                                                        <div className="space-y-1">
                                                            <p className="text-xs font-bold uppercase text-muted-foreground tracking-wide">Status</p>
                                                            <div className="inline-block px-3 py-1.5 rounded-lg font-bold text-xs uppercase tracking-tighter bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                                                                Auto-Mapped
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>

                                                <div className="space-y-1">
                                                    <p className="text-xs font-bold uppercase text-muted-foreground tracking-wide">Pillar</p>
                                                    <p className="text-sm font-medium text-foreground">{selectedPost.contentPillar || 'N/A'}</p>
                                                </div>

                                                <div className="space-y-1">
                                                    <p className="text-xs font-bold uppercase text-muted-foreground tracking-wide">Topic</p>
                                                    <p className="text-sm font-medium text-foreground leading-relaxed">{selectedPost.topic || 'N/A'}</p>
                                                </div>

                                                <div className="space-y-1 pt-2 border-t border-border/50">
                                                    <p className="text-xs font-bold uppercase text-muted-foreground tracking-wide">Caption Hook</p>
                                                    <p className="text-sm text-foreground leading-relaxed italic">{selectedPost.captionHook || 'N/A'}</p>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <article className="prose prose-sm dark:prose-invert max-w-none prose-table:border-collapse prose-th:px-4 prose-th:py-2 prose-td:px-4 prose-td:py-2 prose-tr:border-b prose-th:text-primary prose-th:uppercase prose-th:text-xs prose-th:font-bold prose-th:bg-muted/50 rounded-lg border">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            table: ({ children }) => <table className="w-full text-sm">{children}</table>,
                                            thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
                                            tr: ({ children }) => <tr className="border-b transition-colors hover:bg-muted/50">{children}</tr>,
                                            th: ({ children }) => <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">{children}</th>,
                                            td: ({ children }) => <td className="p-4 align-middle">{children}</td>,
                                        }}
                                    >
                                        {calendar}
                                    </ReactMarkdown>
                                </article>
                            )}
                        </CardContent>
                    </Card>
                ) : (
                    <div className="flex items-center justify-center p-8 sm:p-12 border-2 border-dashed rounded-xl bg-gradient-to-br from-muted/50 to-muted/20 h-full min-h-[400px]">
                        <div className="text-center space-y-4 max-w-sm">
                            <div className="flex justify-center">
                                <div className="p-3 rounded-lg bg-primary/10 border border-primary/20">
                                    <CalendarIcon className="w-8 h-8 text-primary" />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <h3 className="font-bold text-lg">No Calendar Generated Yet</h3>
                                <p className="text-muted-foreground text-sm leading-relaxed">
                                    Fill in your niche, goals, and content formats on the left, then click <span className="font-semibold text-foreground">"Generate Plan"</span> to create your AI-curated month-long strategy.
                                </p>
                            </div>
                            <div className="flex items-center justify-center gap-2 pt-4">
                                <ArrowRight className="w-4 h-4 text-primary animate-pulse" />
                                <span className="text-sm text-primary font-semibold">Start from today →</span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
            </div>
        </DashboardLayout>
    );
};

export default ContentCalendar;
