import { ReactNode, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import {
  Wand2,
  Shield,
  CalendarDays,
  Settings,
  LogOut,
  Menu,
  X,
  TrendingUp,
  Zap,
  Rocket,
  CircleHelp,
  Sparkles,
  Compass,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { t } = useLanguage();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hideQuickStart, setHideQuickStart] = useState(false);
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const [quickHelpOpen, setQuickHelpOpen] = useState(false);
  const [tourActive, setTourActive] = useState(false);
  const [tourStepIndex, setTourStepIndex] = useState(0);

  const sidebarItems = [
    { icon: Wand2, label: t('nav.creatorStudio', 'Creator Studio'), path: '/studio' },
    { icon: Zap, label: t('nav.intelligenceHub', 'Intelligence Hub'), path: '/intelligence' },
    { icon: Rocket, label: t('nav.novelLab', 'Novel AI Lab'), path: '/novel' },
    { icon: TrendingUp, label: t('nav.competitorIntel', 'Competitor Intel'), path: '/competitor' },
    { icon: CalendarDays, label: t('nav.contentCalendar', 'Content Calendar'), path: '/calendar' },
    { icon: Shield, label: t('nav.moderation', 'Moderation'), path: '/moderation' },
    { icon: CalendarDays, label: t('nav.schedule', 'Schedule'), path: '/scheduler' },
    { icon: Settings, label: t('nav.settings', 'Settings'), path: '/settings' },
  ];

  const tourSteps = useMemo(() => ([
    {
      path: '/studio',
      title: 'Creator Studio',
      description: 'Start here to create your core content package from text or media.',
    },
    {
      path: '/intelligence',
      title: 'Intelligence Hub',
      description: 'Run strategic checks like culture adaptation, risk, and safety before publishing.',
    },
    {
      path: '/novel',
      title: 'Novel AI Lab',
      description: 'Use advanced multi-agent tools for trend injection and multimodal expansion.',
    },
    {
      path: '/competitor',
      title: 'Competitor Intel',
      description: 'Analyze competitor patterns and turn insights into better content ideas.',
    },
    {
      path: '/calendar',
      title: 'Content Calendar',
      description: 'Generate an execution-ready plan with timing, formats, and themes.',
    },
    {
      path: '/moderation',
      title: 'Moderation',
      description: 'Check text, image, audio, and video content for policy and safety risks.',
    },
    {
      path: '/scheduler',
      title: 'Scheduler',
      description: 'Run pre-flight checks, approve content, and schedule posts confidently.',
    },
    {
      path: '/settings',
      title: 'Settings',
      description: 'Manage profile, usage budget, and app preferences.',
    },
  ]), []);

  const currentTourStep = tourSteps[tourStepIndex];

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const guides = useMemo(() => ({
    '/studio': {
      title: 'Creator Studio',
      quickStart: 'Add your content or media first, then run one generation action at a time.',
      steps: [
        'Paste text or upload a file.',
        'Generate caption/summary/hashtags, then review output.',
        'Use Intelligence Pack only after base content is ready.',
      ],
    },
    '/intelligence': {
      title: 'Intelligence Hub',
      quickStart: 'Pick region and language clearly, then run one tool before full strategy passes.',
      steps: [
        'Start with Culture or Risk to validate direction.',
        'Run Anti-Cancel and Shadowban before publishing.',
        'Use Asset Explosion last for distribution formats.',
      ],
    },
    '/novel': {
      title: 'Novel AI Lab',
      quickStart: 'Keep inputs specific to avoid noisy outputs from multi-agent features.',
      steps: [
        'Use Signal Intelligence with 2-3 competitor handles.',
        'Inject trends only after niche and region are set.',
        'Run Multimodal/Adapter once your core message is stable.',
      ],
    },
    '/scheduler': {
      title: 'Scheduler',
      quickStart: 'Run pre-flight analysis before scheduling to reduce moderation and delivery risks.',
      steps: [
        'Paste final content and set platform/language.',
        'Review pre-flight report and approve.',
        'Set date/time and publish plan.',
      ],
    },
    '/moderation': {
      title: 'Moderation',
      quickStart: 'Check risky drafts early, then revise before final scheduling.',
      steps: [
        'Choose text/image/audio/video moderation.',
        'Review flagged phrases or labels.',
        'Apply fixes, then re-run for confidence.',
      ],
    },
    '/competitor': {
      title: 'Competitor Intel',
      quickStart: 'Use a focused niche and one competitor URL for best first-pass analysis.',
      steps: [
        'Enter URL and your niche.',
        'Read gaps and winning patterns.',
        'Turn insights into calendar-ready ideas.',
      ],
    },
    '/calendar': {
      title: 'Content Calendar',
      quickStart: 'Set realistic post volume and formats before generating your monthly plan.',
      steps: [
        'Choose month/year and niche.',
        'Select formats and post count.',
        'Generate, review, then refine goals.',
      ],
    },
    '/settings': {
      title: 'Settings',
      quickStart: 'Keep profile details current and use dark mode for visual comfort.',
      steps: [
        'Update profile info.',
        'Review usage budget details.',
        'Adjust theme preferences.',
      ],
    },
  }), []);

  const currentGuide = guides[location.pathname as keyof typeof guides];

  useEffect(() => {
    setHideQuickStart(false);
  }, [location.pathname]);

  useEffect(() => {
    const hasSeenOnboarding = localStorage.getItem('content-room-onboarding-seen-v1') === 'true';
    if (!hasSeenOnboarding) {
      setOnboardingOpen(true);
    }
  }, []);

  useEffect(() => {
    const shouldOpenHelp = localStorage.getItem('content-room-open-quick-help-once') === 'true';
    if (shouldOpenHelp && currentGuide) {
      setQuickHelpOpen(true);
      localStorage.removeItem('content-room-open-quick-help-once');
    }
  }, [currentGuide, location.pathname]);

  useEffect(() => {
    if (!tourActive || !currentTourStep) return;
    if (location.pathname !== currentTourStep.path) {
      navigate(currentTourStep.path);
    }
  }, [tourActive, tourStepIndex, currentTourStep, location.pathname, navigate]);

  const closeOnboarding = () => {
    localStorage.setItem('content-room-onboarding-seen-v1', 'true');
    setOnboardingOpen(false);
  };

  const handleStartInStudio = () => {
    closeOnboarding();
    navigate('/studio');
  };

  const handleGuidedTour = () => {
    closeOnboarding();
    setTourStepIndex(0);
    setTourActive(true);
    navigate('/studio');
  };

  const handleSkipTour = () => {
    setTourActive(false);
    localStorage.setItem('content-room-tour-seen-v1', 'true');
  };

  const handleNextTour = () => {
    if (tourStepIndex >= tourSteps.length - 1) {
      handleSkipTour();
      return;
    }
    setTourStepIndex((prev) => prev + 1);
  };

  const handleBackTour = () => {
    setTourStepIndex((prev) => Math.max(0, prev - 1));
  };

  return (
    <div className="min-h-screen flex w-full">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-foreground/20 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed lg:sticky top-0 left-0 z-50 h-screen w-64 bg-sidebar border-r border-sidebar-border flex flex-col transition-transform duration-200 lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-sidebar-border">
          <Link to="/" className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">CR</span>
            </div>
            <span className="font-semibold text-base">Content Room</span>
          </Link>
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-sidebar-accent"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {sidebarItems.map((item) => {
            const isActive = location.pathname === item.path;
            const isTourTarget = tourActive && currentTourStep?.path === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center space-x-3 px-3 py-2.5 rounded-xl text-[0.95rem] font-medium transition-colors",
                  isTourTarget && "ring-2 ring-primary ring-offset-2 ring-offset-sidebar animate-pulse",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent"
                )}
              >
                <item.icon className="h-5 w-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-sidebar-border">
          <div className="flex items-center space-x-3 mb-4">
            <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-medium">{user?.name?.charAt(0).toUpperCase()}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-sm text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            className="w-full justify-start text-muted-foreground hover:text-foreground"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4 mr-2" />
            {t('nav.logout', 'Logout')}
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 border-b border-primary/10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 flex items-center px-4 lg:px-8">
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-primary/5 mr-4"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>
          <h1 className="text-xl font-semibold">
            {sidebarItems.find((item) => item.path === location.pathname)?.label || t('nav.dashboard', 'Dashboard')}
          </h1>
          {currentGuide && (
            <div className="ml-auto">
              <Dialog open={quickHelpOpen} onOpenChange={setQuickHelpOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2">
                    <CircleHelp className="h-4 w-4" />
                    Quick Help
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>{currentGuide.title} Guide</DialogTitle>
                    <DialogDescription>
                      3 short steps to keep this workflow simple and low-stress.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-2">
                    {currentGuide.steps.map((step, idx) => (
                      <div key={step} className="ui-note">
                        <span className="font-semibold text-foreground mr-2">Step {idx + 1}.</span>
                        {step}
                      </div>
                    ))}
                  </div>
                  <div className="pt-2">
                    <Button
                      variant="hero"
                      className="w-full"
                      onClick={() => {
                        setQuickHelpOpen(false);
                        setTourStepIndex(0);
                        setTourActive(true);
                        navigate('/studio');
                      }}
                    >
                      Start Full Guided Tour
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-8">
          {currentGuide && !hideQuickStart && (
            <div className="ui-note mb-4 flex items-start justify-between gap-3">
              <p>
                <span className="font-semibold text-foreground mr-2">Quick Start:</span>
                {currentGuide.quickStart}
              </p>
              <button
                type="button"
                className="text-muted-foreground hover:text-foreground"
                onClick={() => setHideQuickStart(true)}
                aria-label="Dismiss quick start hint"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          {children}
        </main>
      </div>

      {tourActive && currentTourStep && (
        <div className="fixed bottom-4 right-4 z-[70] w-[min(92vw,420px)] rounded-xl border border-primary/30 bg-background shadow-large p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold">Guided Tour</p>
            <span className="text-xs text-muted-foreground">
              {tourStepIndex + 1}/{tourSteps.length}
            </span>
          </div>
          <div className="space-y-1">
            <p className="text-base font-semibold">{currentTourStep.title}</p>
            <p className="text-sm text-muted-foreground">{currentTourStep.description}</p>
          </div>
          <div className="flex gap-2 pt-1">
            <Button variant="outline" onClick={handleBackTour} disabled={tourStepIndex === 0}>
              Back
            </Button>
            <Button variant="ghost" onClick={handleSkipTour}>
              Skip
            </Button>
            <Button variant="hero" className="ml-auto" onClick={handleNextTour}>
              {tourStepIndex === tourSteps.length - 1 ? 'Done' : 'Next'}
            </Button>
          </div>
        </div>
      )}

      <Dialog open={onboardingOpen} onOpenChange={(open) => {
        if (!open) closeOnboarding();
        else setOnboardingOpen(true);
      }}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Welcome to Content Room
            </DialogTitle>
            <DialogDescription>
              You can start creating immediately, or take a quick guided setup so the app feels easier from the first minute.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="ui-note">
              <span className="font-semibold text-foreground mr-2">Fast start:</span>
              Jump into Creator Studio and create your first content package.
            </div>
            <div className="ui-note">
              <span className="font-semibold text-foreground mr-2">Guided tour:</span>
              We open Studio plus contextual Quick Help so you can follow clear step-by-step instructions.
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 sm:justify-end pt-2">
            <Button variant="outline" onClick={handleStartInStudio}>
              Start in Studio
            </Button>
            <Button variant="hero" onClick={handleGuidedTour} className="gap-2">
              <Compass className="h-4 w-4" />
              Take Guided Tour
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
