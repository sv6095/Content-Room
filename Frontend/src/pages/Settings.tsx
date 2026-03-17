import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useToast } from '@/hooks/use-toast';
import { analyticsAPI, APIError, type LLMUsageStats } from '@/services/api';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { 
  Moon, Sun, Bell, Mail, AlertTriangle, User, Palette, 
  Loader2
} from 'lucide-react';

export default function Settings() {
  const navigate = useNavigate();
  const { user, logout, updateProfile } = useAuth();
  const { t } = useLanguage();
  const { toast } = useToast();
  
  // Profile state
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [isProfileLoading, setIsProfileLoading] = useState(false);
  
  // Appearance state - load from localStorage
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    // Default to dark mode (true) unless explicitly set to 'false'
    return saved !== 'false';
  });
  
  // Notification state
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(true);
  const [llmUsage, setLlmUsage] = useState<LLMUsageStats | null>(null);
  const [llmUsageLoading, setLlmUsageLoading] = useState(false);

  // Apply dark mode on mount and when isDarkMode changes
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode);
  }, [isDarkMode]);

  useEffect(() => {
    let mounted = true;
    const loadUsage = async () => {
      setLlmUsageLoading(true);
      try {
        const usage = await analyticsAPI.getLLMUsage();
        if (mounted) setLlmUsage(usage);
      } catch (err) {
        if (err instanceof APIError) {
          console.warn('LLM usage fetch failed:', err.message);
        } else {
          console.warn('LLM usage fetch failed');
        }
      } finally {
        if (mounted) setLlmUsageLoading(false);
      }
    };
    void loadUsage();
    return () => {
      mounted = false;
    };
  }, []);

  const handleProfileSave = async () => {
    setIsProfileLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 500));
    
    updateProfile({ name, email });
    toast({
      title: 'Profile updated',
      description: 'Your changes have been saved successfully.',
    });
    setIsProfileLoading(false);
  };

  const handleThemeToggle = (checked: boolean) => {
    setIsDarkMode(checked);
    document.documentElement.classList.toggle('dark', checked);
    localStorage.setItem('darkMode', String(checked));
    toast({
      title: 'Theme updated',
      description: `Switched to ${checked ? 'dark' : 'light'} mode.`,
    });
  };

  const handleDeleteAccount = () => {
    logout();
    toast({
      title: 'Account deleted',
      description: 'Your account has been permanently deleted.',
    });
    navigate('/');
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 animate-fade-in max-w-3xl">
        <div>
          <h2 className="text-2xl font-bold mb-2">{t('settings.title', 'Settings')}</h2>
          <p className="text-muted-foreground">
            {t('settings.subtitle', 'Manage your account and appearance.')}
          </p>
        </div>

        <Tabs defaultValue="profile" className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="profile" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">{t('settings.tabs.profile', 'Profile')}</span>
            </TabsTrigger>
            <TabsTrigger value="appearance" className="flex items-center gap-2">
              <Palette className="h-4 w-4" />
              <span className="hidden sm:inline">{t('settings.tabs.appearance', 'Appearance')}</span>
            </TabsTrigger>

            <TabsTrigger value="danger" className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              <span className="hidden sm:inline">{t('settings.tabs.account', 'Account')}</span>
            </TabsTrigger>
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">{t('settings.personalInfo', 'Personal Information')}</CardTitle>
                <CardDescription>{t('settings.updateAccount', 'Update your account details')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="profile-name">{t('settings.fullName', 'Full Name')}</Label>
                  <Input
                    id="profile-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={t('settings.fullName', 'Full Name')}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="profile-email">{t('settings.emailAddress', 'Email Address')}</Label>
                  <Input
                    id="profile-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t('settings.emailAddress', 'Email Address')}
                  />
                </div>
                <Button variant="hero" onClick={handleProfileSave} disabled={isProfileLoading}>
                  {isProfileLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  {t('settings.saveProfile', 'Save Profile')}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">LLM Usage & Budget</CardTitle>
                <CardDescription>Track your LLM usage and remaining budget.</CardDescription>
              </CardHeader>
              <CardContent>
                {llmUsageLoading ? (
                  <div className="flex items-center text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading usage...
                  </div>
                ) : llmUsage ? (
                  <div className="space-y-3">
                    <div className="rounded-lg border p-3">
                      <p className="text-xs text-muted-foreground mb-1">Your usage</p>
                      <p className="text-sm font-semibold">${llmUsage.user_cost_usd.toFixed(4)}</p>
                      <p className="text-xs text-muted-foreground">
                        Remaining: ${llmUsage.user_remaining_usd.toFixed(4)} / ${llmUsage.user_budget_usd.toFixed(2)}
                      </p>
                      <p className="text-xs text-muted-foreground">Calls: {llmUsage.user_call_count}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Usage data unavailable.</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Appearance Tab */}
          <TabsContent value="appearance" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Theme</CardTitle>
                <CardDescription>Customize how the application looks</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {isDarkMode ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
                    <div>
                      <Label htmlFor="dark-mode" className="text-sm font-medium">
                        Dark Mode
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        Switch between light and dark themes
                      </p>
                    </div>
                  </div>
                  <Switch
                    id="dark-mode"
                    checked={isDarkMode}
                    onCheckedChange={handleThemeToggle}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Notifications</CardTitle>
                <CardDescription>Configure how you receive notifications</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Mail className="h-5 w-5" />
                    <div>
                      <Label htmlFor="email-notifications" className="text-sm font-medium">
                        Email Notifications
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        Receive updates via email
                      </p>
                    </div>
                  </div>
                  <Switch
                    id="email-notifications"
                    checked={emailNotifications}
                    onCheckedChange={setEmailNotifications}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Bell className="h-5 w-5" />
                    <div>
                      <Label htmlFor="push-notifications" className="text-sm font-medium">
                        Push Notifications
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        Receive browser notifications
                      </p>
                    </div>
                  </div>
                  <Switch
                    id="push-notifications"
                    checked={pushNotifications}
                    onCheckedChange={setPushNotifications}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>



          {/* Danger Zone Tab */}
          <TabsContent value="danger" className="space-y-4">
            <Card className="border-destructive/30">
              <CardHeader>
                <CardTitle className="text-lg text-destructive">Danger Zone</CardTitle>
                <CardDescription>Irreversible account actions</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-5 w-5 text-destructive" />
                    <div>
                      <p className="text-sm font-medium">Delete Account</p>
                      <p className="text-xs text-muted-foreground">
                        Permanently delete your account and all data
                      </p>
                    </div>
                  </div>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive" size="sm">
                        Delete Account
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This action cannot be undone. This will permanently delete your
                          account and remove all your data from our servers.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={handleDeleteAccount}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          Delete Account
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}
