import { useEffect } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { LanguageProvider } from "@/contexts/LanguageContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

/**
 * Validate that critical environment variables are set correctly.
 * This helps catch configuration issues before they cause runtime failures.
 */
function validateEnvironment() {
  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim();
  
  if (!apiBaseUrl) {
    console.error(
      '[ENV] VITE_API_BASE_URL is not configured. ' +
      'Media loading and API calls will fail. ' +
      'Set VITE_API_BASE_URL in Frontend/.env file.'
    );
    return;
  }
  
  // Test if API is reachable (non-fatal if it fails in offline mode)
  fetch(`${apiBaseUrl}/health`, { method: 'HEAD' })
    .then(response => {
      if (!response.ok) {
        console.warn(`[ENV] API health check failed: ${response.status}. Backend may be offline.`);
      } else {
        console.debug('[ENV] API is reachable and responding');
      }
    })
    .catch(error => {
      console.warn('[ENV] Could not reach API endpoint. Backend may be offline or CORS not configured.', error);
    });
}

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
    
    // Validate critical environment variables at app startup
    validateEnvironment();
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
              
              {/* Protected Routes (Authentication Required) */}
              <Route path="/studio" element={<ProtectedRoute><Studio /></ProtectedRoute>} />
              <Route path="/moderation" element={<ProtectedRoute><Moderation /></ProtectedRoute>} />
              <Route path="/scheduler" element={<ProtectedRoute><Scheduler /></ProtectedRoute>} />
              <Route path="/competitor" element={<ProtectedRoute><CompetitorAnalysis /></ProtectedRoute>} />
              <Route path="/calendar" element={<ProtectedRoute><ContentCalendar /></ProtectedRoute>} />
              <Route path="/intelligence" element={<ProtectedRoute><IntelligenceHub /></ProtectedRoute>} />
              <Route path="/novel" element={<ProtectedRoute><NovelHub /></ProtectedRoute>} />
              <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
              
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
