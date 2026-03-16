import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Calendar as CalendarIcon, Download } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as XLSX from 'xlsx';
import api, { APIError } from '@/services/api';
import { toast } from 'sonner';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

const CONTENT_FORMAT_OPTIONS = ['reel', 'video', 'live', 'blog', 'story'] as const;
type ContentFormatOption = typeof CONTENT_FORMAT_OPTIONS[number];

type CalendarIdeaPayload = {
    title: string;
    format: string;
    whyItWins: string;
    tag?: string;
    niche?: string;
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

const ContentCalendar: React.FC = () => {
    const location = useLocation();
    const prefillAppliedRef = useRef(false);
    const [month, setMonth] = useState('March');
    const [year, setYear] = useState('2026');
    const [niche, setNiche] = useState('');
    const [goals, setGoals] = useState('Engage with audience and promote services');
    const [contentFormats, setContentFormats] = useState<string[]>([...CONTENT_FORMAT_OPTIONS]);
    const [postsPerMonth, setPostsPerMonth] = useState('12');
    const [loading, setLoading] = useState(false);
    const [calendar, setCalendar] = useState<string | null>(null);

    useEffect(() => {
        if (prefillAppliedRef.current) return;
        prefillAppliedRef.current = true;

        const routeState = location.state as
            | { calendarIdea?: CalendarIdeaPayload; calendarSuggestedFormats?: string[] }
            | null;

        let idea: CalendarIdeaPayload | null = routeState?.calendarIdea ?? null;
        let suggestedFormats = routeState?.calendarSuggestedFormats ?? [];

        if (!idea) {
            const raw = localStorage.getItem('calendar-idea-prefill');
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
        localStorage.removeItem('calendar-idea-prefill');
        toast.success(`Idea "${idea.title}" added. Review and generate your calendar.`);
    }, [location.state, niche]);

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
        setCalendar(null);

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

    return (
        <DashboardLayout>
            <div className="space-y-8 animate-fade-in">
            <div className="flex flex-col space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">AI Content Calendar</h1>
                <p className="text-muted-foreground">
                    Generate a month-long content strategy tailored to Indian festivals and your niche.
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-[1fr_2fr]">
                <Card>
                    <CardHeader>
                        <CardTitle>Plan Your Month</CardTitle>
                        <CardDescription>Select the timeframe and goals.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleGenerate} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="month">Month</Label>
                                <Select value={month} onValueChange={setMonth}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select Month" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {['January', 'February', 'March', 'April', 'May', 'June', 
                                          'July', 'August', 'September', 'October', 'November', 'December'].map(m => (
                                            <SelectItem key={m} value={m}>{m}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            
                            <div className="space-y-2">
                                <Label htmlFor="year">Year</Label>
                                <Input 
                                    id="year" 
                                    type="number" 
                                    value={year} 
                                    onChange={(e) => setYear(e.target.value)} 
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="niche">My Niche</Label>
                                <Input 
                                    id="niche" 
                                    placeholder="e.g. Finance for Millennials" 
                                    value={niche}
                                    onChange={(e) => setNiche(e.target.value)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="goals">Content Goals</Label>
                                <Input 
                                    id="goals" 
                                    placeholder="e.g. Increase engagement" 
                                    value={goals}
                                    onChange={(e) => setGoals(e.target.value)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label>Content Formats</Label>
                                <div className="grid grid-cols-2 gap-2">
                                    {CONTENT_FORMAT_OPTIONS.map((format) => {
                                        const selected = contentFormats.includes(format);
                                        return (
                                            <Button
                                                key={format}
                                                type="button"
                                                variant={selected ? "default" : "outline"}
                                                onClick={() => toggleFormat(format)}
                                                className="capitalize"
                                            >
                                                {format}
                                            </Button>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="posts-per-month">Posts Per Month</Label>
                                <Input
                                    id="posts-per-month"
                                    type="number"
                                    min={1}
                                    max={120}
                                    value={postsPerMonth}
                                    onChange={(e) => setPostsPerMonth(e.target.value)}
                                />
                            </div>

                            <Button type="submit" className="w-full" disabled={loading}>
                                {loading ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <CalendarIcon className="mr-2 h-4 w-4" />
                                        Generate Plan
                                    </>
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {calendar ? (
                    <Card className="h-full">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Your Calendar</CardTitle>
                            <Button variant="outline" size="sm" onClick={handleDownload}>
                                <Download className="mr-2 h-4 w-4" />
                                Download .xlsx
                            </Button>
                        </CardHeader>
                        <CardContent className="max-h-[600px] overflow-y-auto">
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
                        </CardContent>
                    </Card>
                ) : (
                    <div className="flex items-center justify-center p-12 border-2 border-dashed rounded-lg bg-muted/50 h-full">
                        <div className="text-center space-y-2">
                            <CalendarIcon className="w-12 h-12 text-muted-foreground mx-auto" />
                            <h3 className="font-medium text-lg">No Calendar Generated</h3>
                            <p className="text-muted-foreground text-sm">
                                Fill in the details and click "Generate Plan" to see your AI-curated schedule.
                            </p>
                        </div>
                    </div>
                )}
            </div>
            </div>
        </DashboardLayout>
    );
};

export default ContentCalendar;
