import { useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { LanguageProvider } from "@/contexts/LanguageContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";

import Studio from "./pages/Studio";
import Moderation from "./pages/Moderation";
import Scheduler from "./pages/Scheduler";
import Settings from "./pages/Settings";

import CompetitorAnalysis from "./pages/CompetitorAnalysis";
import ContentCalendar from "./pages/ContentCalendar";
import IntelligenceHub from "./pages/IntelligenceHub";
import NovelHub from "./pages/NovelHub";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => {
  useEffect(() => {
    // Default to dark mode if no preference is saved
    const isDark = localStorage.getItem('darkMode') !== 'false';
    document.documentElement.classList.toggle('dark', isDark);
  }, []);

  return (
  <QueryClientProvider client={queryClient}>
    <LanguageProvider>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              
              {/* Open Routes (No Authentication Required) */}
              <Route path="/studio" element={<Studio />} />
              <Route path="/moderation" element={<Moderation />} />
              <Route path="/scheduler" element={<Scheduler />} />
              <Route path="/competitor" element={<CompetitorAnalysis />} />
              <Route path="/calendar" element={<ContentCalendar />} />
              <Route path="/intelligence" element={<IntelligenceHub />} />
              <Route path="/novel" element={<NovelHub />} />
              <Route path="/settings" element={<Settings />} />
              
              {/* Redirects for removed pages */}
              <Route path="/dashboard" element={<Navigate to="/studio" replace />} />
              <Route path="/history" element={<Navigate to="/studio" replace />} />
              <Route path="/analytics" element={<Navigate to="/studio" replace />} />
              <Route path="/content" element={<Navigate to="/studio" replace />} />
              <Route path="/profile" element={<Navigate to="/settings" replace />} />
              <Route path="/platforms" element={<Navigate to="/settings" replace />} />
              <Route path="/translation" element={<Navigate to="/studio" replace />} />
              
              
              {/* 404 */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </LanguageProvider>
  </QueryClientProvider>
  );
};

export default App;
