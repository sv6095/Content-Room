import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { EmptyState } from '@/components/shared/EmptyState';
import { Calendar, Clock, Plus, Trash2, Loader2, AlertCircle } from 'lucide-react';
import { schedulerAPI, type ScheduledPost, APIError } from '@/services/api';

export default function Scheduler() {
  const [searchParams] = useSearchParams();
  const contentIdParam = searchParams.get('contentId');
  const contentId = useMemo(() => {
    if (!contentIdParam) return undefined;
    const n = parseInt(contentIdParam, 10);
    return Number.isNaN(n) ? undefined : n;
  }, [contentIdParam]);

  const [posts, setPosts]           = useState<ScheduledPost[]>([]);
  const [isLoading, setIsLoading]   = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [form, setForm] = useState({
    title: '',
    notes: '',
    date: '',
    time: '',
  });

  useEffect(() => { fetchPosts(); }, []);

  const fetchPosts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      setPosts(await schedulerAPI.listPosts());
    } catch (err) {
      setError(err instanceof APIError ? err.message : 'Failed to load scheduled items.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!form.title.trim() || !form.date || !form.time) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const scheduledAt = new Date(`${form.date}T${form.time}`).toISOString();
      const created = await schedulerAPI.createPost({
        title: form.title.trim(),
        description: form.notes.trim() || undefined,
        scheduled_at: scheduledAt,
        content_id: contentId,
      });
      setPosts(prev => [...prev, created].sort(
        (a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime()
      ));
      setForm({ title: '', notes: '', date: '', time: '' });
      setIsCreating(false);
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
              Plan your content creation schedule. No social media publishing — just your personal calendar.
            </p>
          </div>
          <Button variant="hero" onClick={() => { setIsCreating(true); setError(null); }}>
            <Plus className="h-4 w-4 mr-2" />
            Add to Schedule
          </Button>
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

        {/* Add Form */}
        {isCreating && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">New Scheduled Item</CardTitle>
              <CardDescription>Add a content task or reminder to your calendar.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="sch-title">Title *</Label>
                <Input
                  id="sch-title"
                  placeholder="e.g. Film reel for Diwali campaign"
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
                  Add
                </Button>
                <Button variant="outline" onClick={() => setIsCreating(false)} disabled={isSubmitting}>
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Calendar View */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : Object.keys(grouped).length > 0 ? (
          <div className="space-y-6">
            {Object.entries(grouped).map(([day, dayPosts]) => (
              <div key={day}>
                {/* Day header */}
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
                description="Click 'Add to Schedule' to plan your first content task."
              />
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
