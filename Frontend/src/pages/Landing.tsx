import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import DisplayCards from "@/components/ui/display-cards";
import { StepCard } from '@/components/shared/StepCard';
import { Wand2, Shield, ArrowRight, Monitor, Database, Globe, Layers, TrendingUp, CalendarDays, Zap } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { schedulerAPI, type ScheduledPost } from '@/services/api';

function SchedulePlan() {
  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    schedulerAPI.listPosts()
      .then(setPosts)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-8">Loading schedule...</div>;

  if (posts.length === 0) return <div className="text-center py-8 text-muted-foreground">No posts scheduled yet.</div>;

  return (
    <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
      {posts.map(post => (
         <div key={post.id} className="flex flex-col text-left p-4 rounded-xl border border-border bg-background">
           <div className="font-semibold">{post.title}</div>
           <div className="text-sm text-muted-foreground mt-1">
             {new Date(post.scheduled_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
           </div>
         </div>
      ))}
    </div>
  );
}



const steps = [
  {
    number: 1,
    title: 'Draft & Enhance',
    description: 'Input your idea. Our AI Studio generates captions, hashtags, and summaries instantly.',
  },
  {
    number: 2,
    title: 'Deep Moderation',
    description: 'Intelligent systems analyze your content for safety and compliance automatically.',
  },
  {
    number: 3,
    title: 'Content Workflow',
    description: 'Plan and manage your content workflow for continuous publishing across your channels.',
  },
];

export default function Landing() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      
      <main className="flex-1">
        {/* Hero Section */}
        <section className="py-20 lg:py-32">
          <div className="container-wide">
            <div className="max-w-3xl mx-auto text-center animate-slide-up">
              <h1 className="text-4xl lg:text-6xl font-bold mb-6 tracking-tight">
                Content Room 
              </h1>
              <p className="text-lg lg:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
                Create, moderate, and schedule content with intelligent AI assistance. 
                Streamline your creation process and reach audiences in their native language.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button asChild variant="hero" size="xl">
                  <Link to="/register">
                    Get Started
                    <ArrowRight className="h-5 w-5 ml-1" />
                  </Link>
                </Button>
                <Button asChild variant="hero-outline" size="xl">
                  <Link to="/login">Login</Link>
                </Button>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-20 border-t border-primary/10">
          <div className="container-wide">
            <div className="text-center mb-16">
              <h2 className="text-3xl lg:text-4xl font-bold mb-4">
                Everything You Need for Content Excellence
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                A complete suite of AI-powered tools to transform how your team creates and manages content.
              </p>
            </div>
            <div className="flex min-h-[400px] w-full items-center justify-center py-10">
              <div className="w-full max-w-3xl">
                <DisplayCards cards={[
                  {
                    icon: <Wand2 className="size-5 text-blue-300" />,
                    title: "Intelligence Hub",
                    description: "Generate captions & more",
                    date: "New",
                    iconClassName: "text-blue-500",
                    titleClassName: "text-blue-500",
                    className: "[grid-area:stack] hover:-translate-y-10 before:absolute before:w-[100%] before:outline-1 before:rounded-xl before:outline-border before:h-[100%] before:content-[''] before:bg-blend-overlay before:bg-background/50 grayscale-[100%] hover:before:opacity-0 before:transition-opacity before:duration-700 hover:grayscale-0 before:left-0 before:top-0",
                  },
                  {
                    icon: <Layers className="size-5 text-purple-300" />,
                    title: "Content Workflow",
                    description: "Manage your pipeline",
                    date: "Featured",
                    iconClassName: "text-purple-500",
                    titleClassName: "text-purple-500",
                    className: "[grid-area:stack] translate-x-12 translate-y-10 hover:-translate-y-1 before:absolute before:w-[100%] before:outline-1 before:rounded-xl before:outline-border before:h-[100%] before:content-[''] before:bg-blend-overlay before:bg-background/50 grayscale-[100%] hover:before:opacity-0 before:transition-opacity before:duration-700 hover:grayscale-0 before:left-0 before:top-0",
                  },
                  {
                    icon: <Shield className="size-5 text-emerald-400" />,
                    title: "Smart Moderation",
                    description: "Automated safety checks",
                    date: "Real-time",
                    iconClassName: "text-emerald-500",
                    titleClassName: "text-emerald-500",
                    className: "[grid-area:stack] translate-x-24 translate-y-20 hover:translate-y-10",
                  },
                ]} />
              </div>
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="py-20 border-t border-primary/10">
          <div className="container-wide">
            <div className="text-center mb-16">
              <h2 className="text-3xl lg:text-4xl font-bold mb-4">
                How It Works
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                From idea to publishing, in three simple steps.
              </p>
            </div>
            <div className="max-w-2xl mx-auto space-y-8">
              {steps.map((step) => (
                <StepCard
                  key={step.number}
                  number={step.number}
                  title={step.title}
                  description={step.description}
                />
              ))}
            </div>
          </div>
        </section>

        {/* Powered by Technology Section */}
        <section className="py-20 border-t border-primary/10">
          <div className="container-wide">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div>
                <h2 className="text-3xl lg:text-4xl font-bold mb-6">
                  Intelligent Capabilities
                </h2>
                <p className="text-lg text-muted-foreground mb-8">
                  Built to empower your team with intelligent assistance at every step of your content journey.
                </p>
                <div className="space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="p-2 rounded-lg bg-primary/10 text-primary mt-1">
                      <Database className="size-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">Secure Processing</h3>
                      <p className="text-muted-foreground">Your content is handled securely with enterprise-grade privacy.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4">
                     <div className="p-2 rounded-lg bg-primary/10 text-primary mt-1">
                      <Globe className="size-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">Local Intelligence</h3>
                      <p className="text-muted-foreground">Offline-first moderation and translation engines.</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex justify-center">
                <div className="p-6 rounded-2xl bg-muted/30 border border-primary/10 w-full">
                  {/* Architecture visual */}
                  <div className="flex flex-col items-center gap-3">
                    <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">Creation Engine</div>
                    <div className="flex gap-3 flex-wrap justify-center">
                      {["Studio", "Safety", "Lang", "Social"].map((label) => (
                        <span key={label} className="text-xs px-3 py-1.5 rounded-full border border-primary/30 bg-primary/5 text-primary font-medium">{label}</span>
                      ))}
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <div className="h-0.5 w-10 bg-primary/30" />
                      <div className="rounded-full bg-primary/10 border border-primary/30 px-4 py-2 flex items-center gap-2">
                        <Zap className="h-4 w-4 text-primary" />
                        <span className="text-sm font-semibold">Sync</span>
                      </div>
                      <div className="h-0.5 w-10 bg-primary/30" />
                    </div>
                    <div className="flex gap-3">
                      {["Web", "Mobile"].map((label) => (
                        <span key={label} className="text-xs px-3 py-1.5 rounded-full border border-border bg-muted text-muted-foreground font-medium">{label}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
             </div>
          </div>
        </section>

        {/* Dashboard Preview Section */}
        {user && (
          <section className="py-20 border-t border-primary/10">
            <div className="container-wide">
              <div className="text-center mb-12">
                <h2 className="text-3xl lg:text-4xl font-bold mb-4">
                  Welcome, {user.name}
                </h2>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                  Your upcoming schedule plan.
                </p>
              </div>
              <div className="max-w-4xl mx-auto">
                <div className="rounded-2xl border border-primary/10 bg-card shadow-large p-6 min-h-[200px] flex flex-col justify-center">
                   <SchedulePlan />
                </div>
              </div>
            </div>
          </section>
        )}

        {/* CTA Section */}
        <section className="py-20 border-t border-primary/10">
          <div className="container-wide">
            <div className="max-w-2xl mx-auto text-center">
              <h2 className="text-3xl lg:text-4xl font-bold mb-4">
                Ready to Transform Your Content Creation?
              </h2>
              <p className="text-lg text-muted-foreground mb-8">
                Join teams who are already using Content Room to streamline their content operations.
              </p>
              <Button asChild variant="hero" size="xl">
                <Link to="/register">
                  Get Started Free
                  <ArrowRight className="h-5 w-5 ml-1" />
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
