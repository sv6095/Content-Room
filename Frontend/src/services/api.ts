/**
 * Content Room API Client
 *
 * All requests use relative paths (/api/v1/...) so the backend origin
 * is never exposed in the browser's Network DevTools panel.
 */

// Relative path — Vite proxy (dev) or reverse-proxy (prod) routes this
// to the backend. No raw backend URL is visible in the browser.
const API_V1 = '/api/v1';

// ============================================
// Types & Interfaces
// ============================================

// Auth Types
export interface User {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
  preferred_language?: string;
  created_at: string;
}

// Competitor Types
export interface CompetitorRequest {
  url: string;
  niche: string;
}

export interface CompetitorResponse {
  analysis: string;
  url_found: boolean;
}

// Calendar Types
export interface CalendarRequest {
  month: string;
  year: number;
  niche: string;
  goals: string;
}

export interface CalendarResponse {
  calendar_markdown: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
}

export interface CookieData {
  name: string;
  value: string;
  domain?: string;
  path?: string;
  [key: string]: unknown;
}

// Creation Types
export interface GenerateRequest {
  content: string;
  content_type?: string;
  language?: string;
}

export interface GenerateResponse {
  result: string;
  provider: string;
  fallback_used: boolean;
}

export interface HashtagsResponse {
  hashtags: string[];
  provider: string;
}

// Moderation Types
export interface ModerationRequest {
  text: string;
  language?: string;
}

export interface ModerationResponse {
  decision: 'ALLOW' | 'FLAG' | 'ESCALATE';
  safety_score: number;
  confidence: number;
  explanation: string;
  flags: string[];
  provider: string;
  processing_time_ms: number;
}

export interface MultimodalModerationResponse {
  decision: 'ALLOW' | 'FLAG' | 'ESCALATE';
  overall_safety_score: number;
  combined_flags: string[];
  results: {
    text?: ModerationResponse;
    image?: {
      is_safe: boolean;
      safety_score: number;
      labels: string[];
    };
    audio?: {
      transcript: string;
      safety_score: number;
      flags: string[];
    };
  };
}

// Content (My Content pipeline) Types
export interface ContentItem {
  id: number;
  content_type: string;
  original_text?: string;
  caption?: string;
  summary?: string;
  hashtags?: { items?: string[] } | string[];
  translated_text?: string;
  source_language?: string;
  target_language?: string;
  moderation_status: string;
  safety_score?: number;
  moderation_explanation?: string;
  workflow_status: 'draft' | 'moderated' | 'translated' | 'scheduled';
  is_scheduled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ContentCreate {
  content_type?: string;
  original_text?: string;
  caption?: string;
  summary?: string;
  hashtags?: string[];
  file_path?: string;
}

// Scheduler Types
export interface ScheduleRequest {
  title: string;
  description?: string;
  scheduled_at: string;
  platform?: string;
  user_id?: number;
  content_id?: number;
  media_url?: string;
  skip_moderation?: boolean;
}

export interface ScheduledPost {
  id: number;
  title: string;
  description?: string;
  scheduled_at: string;
  status: string;
  platform?: string;
  ai_optimized: boolean;
  moderation_passed: boolean;
  moderation_reason?: string;
  media_url?: string;
  created_at: string;
}

// Analytics Types
export interface DashboardMetrics {
  total_content: number;
  content_this_week: number;
  moderation_safe: number;
  moderation_flagged: number;
  scheduled_posts: number;
  published_posts: number;
}

export interface ModerationStats {
  total_moderated: number;
  safe_count: number;
  warning_count: number;
  unsafe_count: number;
  escalated_count: number;
  average_safety_score: number;
}

export interface ProviderStats {
  current_providers: {
    llm: string;
    vision: string;
    speech: string;
    translation: string;
  };
  aws_configured: boolean;
  fallback_chain: Record<string, string[]>;
}

// Translation Types
export interface TranslateRequest {
  text: string;
  target_language: string;
  source_language?: string;
}

export interface TranslateResponse {
  original_text: string;
  translated_text: string;
  source_language: string;
  target_language: string;
  provider: string;
}

// ============================================
// API Error Handling
// ============================================

export class APIError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      errorData.detail || errorData.message || `Error ${response.status}`,
      response.status,
      errorData
    );
  }
  return response.json();
}

// ============================================
// Token Management
// ============================================

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('auth-token', token);
  } else {
    localStorage.removeItem('auth-token');
  }
}

export function getAuthToken(): string | null {
  if (!authToken) {
    authToken = localStorage.getItem('auth-token');
  }
  return authToken;
}

function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ============================================
// Auth API
// ============================================

export const authAPI = {
  async register(data: RegisterData): Promise<TokenResponse> {
    const response = await fetch(`${API_V1}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await handleResponse<TokenResponse>(response);
    setAuthToken(result.access_token);
    return result;
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_V1}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    const result = await handleResponse<TokenResponse>(response);
    setAuthToken(result.access_token);
    return result;
  },

  async getProfile(): Promise<User> {
    const response = await fetch(`${API_V1}/auth/profile`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<User>(response);
  },

  async logout(): Promise<void> {
    await fetch(`${API_V1}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    setAuthToken(null);
    localStorage.removeItem('auth-user');
  },
};

// ============================================
// Creation API
// ============================================

export const creationAPI = {
  async generateCaption(content: string, contentType = 'text', maxLength?: number, platform?: string): Promise<GenerateResponse> {
    const response = await fetch(`${API_V1}/create/caption`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        content, 
        content_type: contentType,
        max_length: maxLength,
        platform: platform
      }),
    });
    return handleResponse<GenerateResponse>(response);
  },

  async generateSummary(content: string, maxLength?: number): Promise<GenerateResponse> {
    const response = await fetch(`${API_V1}/create/summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, max_length: maxLength }),
    });
    return handleResponse<GenerateResponse>(response);
  },

  async generateHashtags(content: string, count = 5): Promise<HashtagsResponse> {
    const response = await fetch(`${API_V1}/create/hashtags`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, count }),
    });
    return handleResponse<HashtagsResponse>(response);
  },

  async rewriteTone(content: string, tone: string): Promise<{ original: string; rewritten: string; tone: string; provider: string }> {
    const formData = new FormData();
    formData.append('content', content);
    formData.append('tone', tone);

    const response = await fetch(`${API_V1}/create/rewrite`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(response);
  },
};

// ============================================
// Moderation API
// ============================================

export const moderationAPI = {
  async moderateText(text: string, language = 'en'): Promise<ModerationResponse> {
    const response = await fetch(`${API_V1}/moderate/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ text, language }),
    });
    return handleResponse<ModerationResponse>(response);
  },

  async moderateImage(file: File): Promise<{ filename: string } & Partial<ModerationResponse>> {
    const formData = new FormData();
    formData.append('image', file);

    const response = await fetch(`${API_V1}/moderate/image`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    });
    return handleResponse(response);
  },

  async moderateAudio(file: File): Promise<{ filename: string; transcript?: string } & Partial<ModerationResponse>> {
    const formData = new FormData();
    formData.append('audio', file);

    const response = await fetch(`${API_V1}/moderate/audio`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    });
    return handleResponse(response);
  },

  async moderateVideo(file: File): Promise<{ 
    filename: string; 
    video_info?: { duration_seconds: number; total_frames: number; frames_analyzed: number };
    frame_results?: Array<{ frame_index: number; timestamp: number; safety_score: number; flags: string[] }>;
  } & Partial<ModerationResponse>> {
    const formData = new FormData();
    formData.append('video', file);

    const response = await fetch(`${API_V1}/moderate/video`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    });
    return handleResponse(response);
  },

  async moderateMultimodal(
    text?: string,
    image?: File,
    audio?: File
  ): Promise<MultimodalModerationResponse> {
    const formData = new FormData();
    if (text) formData.append('text', text);
    if (image) formData.append('image', image);
    if (audio) formData.append('audio', audio);

    const response = await fetch(`${API_V1}/moderate/multimodal`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: formData,
    });
    return handleResponse<MultimodalModerationResponse>(response);
  },
};

// ============================================
// Content API (My Content pipeline)
// ============================================

export const contentAPI = {
  async list(statusFilter?: string): Promise<ContentItem[]> {
    const params = statusFilter ? `?status_filter=${statusFilter}` : '';
    const response = await fetch(`${API_V1}/content${params}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<ContentItem[]>(response);
  },

  async get(id: number): Promise<ContentItem> {
    const response = await fetch(`${API_V1}/content/${id}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<ContentItem>(response);
  },

  async create(data: ContentCreate): Promise<ContentItem> {
    const response = await fetch(`${API_V1}/content/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(data),
    });
    return handleResponse<ContentItem>(response);
  },
};

// ============================================
// Scheduler API
// ============================================

export const schedulerAPI = {
  async createPost(data: ScheduleRequest): Promise<ScheduledPost> {
    const response = await fetch(`${API_V1}/schedule/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(data),
    });
    return handleResponse<ScheduledPost>(response);
  },

  async createPostWithMedia(
    title: string,
    scheduledAt: string,
    file: File,
    description?: string,
    platform?: string
  ): Promise<{ post: ScheduledPost; media: unknown; moderation_passed: boolean }> {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('scheduled_at', scheduledAt);
    formData.append('file', file);
    if (description) formData.append('description', description);
    if (platform) formData.append('platform', platform);

    const response = await fetch(`${API_V1}/schedule/with-media`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(response);
  },

  async listPosts(status?: string, platform?: string, userId = 1): Promise<ScheduledPost[]> {
    const params = new URLSearchParams({ user_id: userId.toString() });
    if (status) params.append('status', status);
    if (platform) params.append('platform', platform);

    const response = await fetch(`${API_V1}/schedule/?${params}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<ScheduledPost[]>(response);
  },

  async getPost(postId: number): Promise<ScheduledPost> {
    const response = await fetch(`${API_V1}/schedule/${postId}`);
    return handleResponse<ScheduledPost>(response);
  },

  async cancelPost(postId: number): Promise<{ message: string }> {
    const response = await fetch(`${API_V1}/schedule/${postId}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },

  async checkModeration(text?: string, file?: File): Promise<{
    passed: boolean;
    is_safe: boolean;
    confidence: number;
    reason?: string;
    labels: string[];
  }> {
    const formData = new FormData();
    if (text) formData.append('text', text);
    if (file) formData.append('file', file);

    const response = await fetch(`${API_V1}/schedule/check-moderation`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(response);
  },
};

// ============================================
// Analytics API
// ============================================

export const analyticsAPI = {
  async getDashboard(userId?: number, platform?: string): Promise<DashboardMetrics> {
    let url = `${API_V1}/analytics/dashboard`;
    const params = new URLSearchParams();
    if (platform && platform !== 'all') {
      params.append('platform', platform);
    }
    const paramStr = params.toString();
    if (paramStr) url += `?${paramStr}`;
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<DashboardMetrics>(response);
  },

  async getModerationStats(userId?: number, platform?: string): Promise<ModerationStats> {
    let url = `${API_V1}/analytics/moderation`;
    const params = new URLSearchParams();
    if (platform && platform !== 'all') {
      params.append('platform', platform);
    }
    const paramStr = params.toString();
    if (paramStr) url += `?${paramStr}`;
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<ModerationStats>(response);
  },

  async getProviderStats(): Promise<ProviderStats> {
    const response = await fetch(`${API_V1}/analytics/providers`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<ProviderStats>(response);
  },
};

// ============================================
// Translation API
// ============================================

export const translationAPI = {
  async translate(text: string, targetLanguage: string, sourceLanguage?: string): Promise<TranslateResponse> {
    const response = await fetch(`${API_V1}/translate/text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        target_lang: targetLanguage,
        source_lang: sourceLanguage,
      }),
    });
    return handleResponse<TranslateResponse>(response);
  },

  async detectLanguage(text: string): Promise<{ language: string; confidence: number }> {
    const response = await fetch(`${API_V1}/translate/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const result = await handleResponse<{ detected_language: string; confidence: number }>(response);
    return { language: result.detected_language, confidence: result.confidence };
  },

  async getLanguages(): Promise<{ languages: { code: string; name: string; native?: string }[] }> {
    const response = await fetch(`${API_V1}/translate/languages`);
    const result = await handleResponse<{ code: string; name: string; native: string }[]>(response);
    // Backend returns array directly, wrap in object
    return { languages: result };
  },
};


// ============================================
// History API
// ============================================

export interface HistoryItem {
  id: number;
  item_type: 'content' | 'scheduled';
  title: string;
  description?: string;
  status: string;
  platform?: string;
  safety_score?: number;
  created_at: string;
  updated_at?: string;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface HistoryStats {
  total_content: number;
  total_scheduled: number;
  published_count: number;
  moderated_count: number;
  this_week_content: number;
  this_week_scheduled: number;
}

export const historyAPI = {
  async getHistory(
    itemType?: 'content' | 'scheduled',
    timeRange?: 'today' | 'week' | 'month',
    page = 1,
    pageSize = 20
  ): Promise<HistoryResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (itemType) params.append('item_type', itemType);
    if (timeRange) params.append('time_range', timeRange);

    const response = await fetch(`${API_V1}/history?${params}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<HistoryResponse>(response);
  },

  async getStats(): Promise<HistoryStats> {
    const response = await fetch(`${API_V1}/history/stats`, {
      headers: getAuthHeaders(),
    });
    return handleResponse<HistoryStats>(response);
  },
};

// ============================================
// Health Check
// ============================================

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_V1}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// ============================================
// Competitor API
// ============================================

export const competitorAPI = {
  async analyze(url: string, niche: string): Promise<CompetitorResponse> {
    const response = await fetch(`${API_V1}/competitor/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ url, niche }),
    });
    return handleResponse<CompetitorResponse>(response);
  },
};

// ============================================
// Calendar API
// ============================================

export const calendarAPI = {
  async generate(data: CalendarRequest): Promise<CalendarResponse> {
    const response = await fetch(`${API_V1}/calendar/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify(data),
    });
    return handleResponse<CalendarResponse>(response);
  },
};

// ============================================
// Intelligence Hub API (12 Novel Features)
// ============================================

export interface CultureRewriteResponse {
  original: string;
  rewritten: string;
  region: string;
  persona_applied: string;
  festival?: string;
  // RL + LLM hybrid scores
  alignment_score?: number;
  llm_score?: number;
  rule_alignment_score?: number;
  weights?: { llm: number; rule_engine: number };
  matched_hooks?: string[];
  violations?: string[];
  festival_keywords?: string[];
  provider: string;
  rule_provider?: string;
  fallback_used: boolean;
}

export interface RiskReachResponse {
  original: string;
  generated: string;
  risk_level: number;
  tone_label: string;
  platform?: string;
  safety_score: number;
  sentiment: string;
  toxicity_score: number;
  estimated_engagement_probability: number;
  moderation_risk_percent: number;
  llm_provider: string;
  audit_provider: string;
  fallback_used: boolean;
}

export interface DNAAnalysisResponse {
  similarity_score: number;
  drift_detected: boolean;
  drift_severity: 'HIGH' | 'MEDIUM' | 'NONE';
  content_dna_traits: string;
  realignment_suggestion: string;
  posts_analyzed: number;
  embedding_provider: string;
  llm_provider: string;
}

export interface HeatmapToken {
  word: string;
  risk: 'red' | 'yellow' | 'safe';
  tooltip?: string;
}

export interface AntiCancelResponse {
  risk_score: number;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
  local_flags: { keyword: string; category: string; risk: string; severity?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'; tier?: string }[];
  universal_flags?: { keyword: string; category: string; severity: string }[];
  india_flags?: { keyword: string; category: string; severity: string }[];
  detected_entities: { text: string; type: string; score: number }[];
  heatmap: HeatmapToken[];
  safe_alternatives: string[];
  target_regions: string[];
  comprehend_provider: string;
  recommendation: string;
  has_critical_threat?: boolean;
}


export interface MentalHealthResponse {
  burnout_score: number;
  burnout_risk: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_DATA';
  linguistic_entropy: number;
  entropy_interpretation: string;
  sentiment_polarity: number;
  sentiment_trend: string;
  repetitive_phrases_detected: string[];
  recommendations: string;
  posts_analyzed: number;
  sentiment_provider: string;
  advisory_provider: string;
}

export interface AssetItem {
  asset_type: string;
  platform: string;
  content: string;
  provider: string;
  rule_provider?: string;
  quality_score?: number;
  llm_score?: number;
  compliance_score?: number;
  compliance_issues?: string[];
  weights?: { llm: number; rule_engine: number };
  success: boolean;
}

export interface AssetExplosionResponse {
  seed_content: string;
  niche?: string;
  total_assets: number;
  successful_assets: number;
  failed_assets: string[];
  assets: AssetItem[];
}

export interface ShadowbanResponse {
  shadowban_probability: number;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
  risk_factors: string[];
  risky_hashtags: string[];
  platform: string;
  recommendation: string;
  analysis?: string;
  rule_safety_score?: number;  // 100=completely clean, lower=rule violations found
  rule_score?: number;         // inverted: 0=clean risk contribution, higher=more rule risk
  llm_score?: number;
  provider: string;
  fallback_used?: boolean;
}

export const intelligenceAPI = {
  async cultureRewrite(content: string, region: string, festival?: string, niche?: string, targetLanguage?: string): Promise<CultureRewriteResponse> {
    const response = await fetch(`${API_V1}/intel/culture/rewrite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, region, festival, content_niche: niche, target_language: targetLanguage }),
    });
    return handleResponse<CultureRewriteResponse>(response);
  },

  async getRegions(): Promise<{ id: string; name: string; emoji: string }[]> {
    const response = await fetch(`${API_V1}/intel/culture/regions`);
    return handleResponse(response);
  },

  async getFestivals(): Promise<{ id: string; name: string }[]> {
    const response = await fetch(`${API_V1}/intel/culture/festivals`);
    return handleResponse(response);
  },

  async riskReachGenerate(content: string, riskLevel: number, platform?: string, niche?: string): Promise<RiskReachResponse> {
    const response = await fetch(`${API_V1}/intel/risk-reach/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, risk_level: riskLevel, platform, niche }),
    });
    return handleResponse<RiskReachResponse>(response);
  },

  async dnaAnalyze(newContent: string, postHistory: string[], userId = 1): Promise<DNAAnalysisResponse> {
    const response = await fetch(`${API_V1}/intel/dna/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_content: newContent, post_history: postHistory, user_id: userId }),
    });
    return handleResponse<DNAAnalysisResponse>(response);
  },

  async antiCancelAnalyze(text: string, targetRegions?: string[]): Promise<AntiCancelResponse> {
    const response = await fetch(`${API_V1}/intel/anti-cancel/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, target_regions: targetRegions }),
    });
    return handleResponse<AntiCancelResponse>(response);
  },

  async getHeatmap(text: string): Promise<{ heatmap: HeatmapToken[]; total_words: number }> {
    const response = await fetch(`${API_V1}/intel/anti-cancel/heatmap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    return handleResponse(response);
  },

  async mentalHealthAnalyze(posts: string[], userId = 1): Promise<MentalHealthResponse> {
    const response = await fetch(`${API_V1}/intel/mental-health/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ posts, user_id: userId }),
    });
    return handleResponse<MentalHealthResponse>(response);
  },

  async explodeAssets(seedContent: string, niche?: string, selectedAssets?: string[]): Promise<AssetExplosionResponse> {
    const response = await fetch(`${API_V1}/intel/explode/assets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seed_content: seedContent, niche, selected_assets: selectedAssets }),
    });
    return handleResponse<AssetExplosionResponse>(response);
  },

  async getAssetTypes(): Promise<{ asset_types: { key: string; platform: string; persona: string }[] }> {
    const response = await fetch(`${API_V1}/intel/explode/asset-types`);
    return handleResponse(response);
  },

  async predictShadowban(content: string, hashtags?: string[], platform?: string): Promise<ShadowbanResponse> {
    const response = await fetch(`${API_V1}/intel/shadowban/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, hashtags, platform }),
    });
    return handleResponse<ShadowbanResponse>(response);
  },
};

// ============================================
// Pre-Flight Pipeline API (Scheduler Integration)
// ============================================

export interface PreFlightRequest {
  content: string;
  region?: string;
  target_language?: string;
  platform?: string;
  niche?: string;
  risk_level?: number;
  festival?: string;
}

export interface PreFlightSummary {
  culture_adapted: boolean;
  alignment_score?: number;
  risk_tone: string;
  safety_score?: number;
  cancel_risk: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';
  shadowban_probability?: number;
  content_sentiment: string;
  assets_generated: number;
  overall_pass: boolean;
  errors_count: number;
}

export interface PreFlightResponse {
  culture: CultureRewriteResponse | null;
  risk_reach: RiskReachResponse | null;
  anti_cancel: AntiCancelResponse | null;
  shadowban: ShadowbanResponse | null;
  mental_health: {
    sentiment: string;
    tone_advice: string;
    provider: string;
  } | null;
  assets: {
    assets: AssetItem[];
    total_generated: number;
  } | null;
  errors: Record<string, string>;
  passed: boolean;
  summary: PreFlightSummary;
}

export const pipelineAPI = {
  async analyze(request: PreFlightRequest): Promise<PreFlightResponse> {
    const response = await fetch(`${API_V1}/pipeline/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    return handleResponse<PreFlightResponse>(response);
  },

  async getSupportedLanguages(): Promise<{ languages: string[] }> {
    const response = await fetch(`${API_V1}/pipeline/languages`);
    return handleResponse<{ languages: string[] }>(response);
  },
};

// ============================================
// NOVEL HUB APIs
// ============================================

export interface SignalIntelAgent {
  name: string;
  output: string;
  provider: string;
}

export interface SignalIntelResponse {
  competitor_handles: string[];
  niche: string;
  region: string;
  agents: {
    scraper: SignalIntelAgent;
    analyst: SignalIntelAgent;
    strategist: SignalIntelAgent;
  };
  provider_chain: string[];
  timestamp: string;
}

export interface TrendInjectionResponse {
  original_content: string;
  region: string;
  niche: string;
  region_context: { languages: string[]; festivals: string[]; local_topics: string[] };
  trending_topics: string;
  enhanced_content: string;
  trend_provider: string;
  injection_provider: string;
  timestamp: string;
}

export interface MultimodalProduction {
  format_key: string;
  format_name: string;
  content: string;
  provider: string;
  success: boolean;
}

export interface MultimodalResponse {
  seed_content: string;
  niche: string;
  target_language: string;
  total_formats: number;
  successful: number;
  productions: MultimodalProduction[];
  timestamp: string;
}

export interface PlatformPreview {
  platform: string;
  optimized_content: string;
  provider: string;
  specs: Record<string, unknown>;
  recommended_time: string | null;
  status: string;
  success: boolean;
}

export interface PlatformAdaptResponse {
  original_content: string;
  platforms: string[];
  niche: string;
  schedule_time: string | null;
  previews: PlatformPreview[];
  total_platforms: number;
  successful: number;
  timestamp: string;
}

export interface BurnoutAnalysis {
  burnout_score: number;
  signals: string[];
  entropy: number;
  sentiment_drift: number;
  repetition_index: number;
  length_decline?: number;
  burnout_keywords_found?: number;
  total_posts_analyzed?: number;
}

export interface BurnoutResponse {
  burnout_analysis: BurnoutAnalysis;
  workload_mode: string;
  mode_description: string;
  original_target: number;
  adjusted_target: number;
  adapted_schedule: string;
  schedule_provider: string;
  niche: string;
  timestamp: string;
}

export interface ProductionFormat {
  key: string;
  name: string;
  description: string;
}

export const novelAPI = {
  async signalIntelligence(handles: string[], niche: string, region?: string, platforms?: string[]): Promise<SignalIntelResponse> {
    const response = await fetch(`${API_V1}/novel/signal-intelligence`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ competitor_handles: handles, niche, region: region || 'pan-india', platforms }),
    });
    return handleResponse<SignalIntelResponse>(response);
  },

  async trendInjection(content: string, region: string, niche: string): Promise<TrendInjectionResponse> {
    const response = await fetch(`${API_V1}/novel/trend-injection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, region, niche, inject_trends: true }),
    });
    return handleResponse<TrendInjectionResponse>(response);
  },

  async multimodalProduction(seedContent: string, formats: string[], niche: string, targetLanguage?: string): Promise<MultimodalResponse> {
    const response = await fetch(`${API_V1}/novel/multimodal-production`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seed_content: seedContent, formats, niche, target_language: targetLanguage || 'Hindi' }),
    });
    return handleResponse<MultimodalResponse>(response);
  },

  async getProductionFormats(): Promise<{ formats: ProductionFormat[] }> {
    const response = await fetch(`${API_V1}/novel/production-formats`);
    return handleResponse(response);
  },

  async platformAdapt(content: string, platforms: string[], niche: string, scheduleTime?: string): Promise<PlatformAdaptResponse> {
    const response = await fetch(`${API_V1}/novel/auto-publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, platforms, niche, schedule_time: scheduleTime }),
    });
    return handleResponse<PlatformAdaptResponse>(response);
  },

  async burnoutPredict(posts: string[], niche: string, weeklyTarget?: number): Promise<BurnoutResponse> {
    const response = await fetch(`${API_V1}/novel/burnout-predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ posts, niche, weekly_target: weeklyTarget || 7 }),
    });
    return handleResponse<BurnoutResponse>(response);
  },
};

// Default export for convenience
const api = {
  auth: authAPI,
  creation: creationAPI,
  moderation: moderationAPI,
  scheduler: schedulerAPI,
  analytics: analyticsAPI,
  translation: translationAPI,
  history: historyAPI,
  competitor: competitorAPI,
  calendar: calendarAPI,
  intelligence: intelligenceAPI,
  novel: novelAPI,
  pipeline: pipelineAPI,
  checkHealth: checkBackendHealth,
  setAuthToken,
  getAuthToken,
};

export default api;
