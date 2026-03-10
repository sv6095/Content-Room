import { useState, useRef } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { EmptyState } from '@/components/shared/EmptyState';
import { Shield, Upload, CheckCircle, AlertTriangle, XCircle, Loader2, FileImage, Music, Video, X, Cpu } from 'lucide-react';
import { moderationAPI, APIError, ModerationResponse, MultimodalModerationResponse } from '@/services/api';

interface ModerationResult {
  explanation: string;
  flaggedContent: string;
  flags: string[];
  status: 'safe' | 'warning' | 'unsafe';
  decision: string;
  provider?: string;
  processingTime?: number;
  fileResults?: {
    image?: { is_safe: boolean; labels: string[] };
    audio?: { transcript: string; flags: string[] };
  };
}

export default function Moderation() {
  const [content, setContent] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ModerationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  
  const imageInputRef = useRef<HTMLInputElement>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
    }
  };

  const handleAudioUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAudioFile(file);
    }
  };

  const [videoFile, setVideoFile] = useState<File | null>(null);

  const decisionToStatus = (decision?: string): 'safe' | 'warning' | 'unsafe' =>
    decision === 'ALLOW' ? 'safe' : decision === 'FLAG' ? 'warning' : 'unsafe';

  const handleVideoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setVideoFile(file);
    }
  };

  const transformResult = (
    apiResult: ModerationResponse | MultimodalModerationResponse,
    isMultimodal = false
  ): ModerationResult => {
    if (isMultimodal) {
      const multiRes = apiResult as MultimodalModerationResponse;
      // Derive status from decision
      const status: 'safe' | 'warning' | 'unsafe' = 
        multiRes.decision === 'ALLOW' ? 'safe' :
        multiRes.decision === 'FLAG' ? 'warning' : 'unsafe';
      
      return {
        explanation: `Multimodal content analyzed. Decision: ${multiRes.decision}`,
        flaggedContent: '',
        flags: multiRes.combined_flags,
        status,
        decision: multiRes.decision,
        fileResults: {
          image: multiRes.results.image ? {
            is_safe: multiRes.results.image.is_safe,
            labels: multiRes.results.image.labels || [],
          } : undefined,
          audio: multiRes.results.audio ? {
            transcript: multiRes.results.audio.transcript || '',
            flags: multiRes.results.audio.flags || [],
          } : undefined,
        },
      };
    }

    const singleRes = apiResult as ModerationResponse;
    // Derive status from decision
    const status: 'safe' | 'warning' | 'unsafe' = 
      singleRes.decision === 'ALLOW' ? 'safe' :
      singleRes.decision === 'FLAG' ? 'warning' : 'unsafe';
    
    return {
      explanation: singleRes.explanation || 'Content analyzed.',
      flaggedContent: (singleRes as ModerationResponse & { flagged_content?: string }).flagged_content || '',
      flags: singleRes.flags,
      status,
      decision: singleRes.decision,
      provider: singleRes.provider,
      processingTime: singleRes.processing_time_ms,
    };
  };

  const handleAnalyze = async () => {
    if (!content.trim() && !imageFile && !audioFile && !videoFile) return;

    setIsAnalyzing(true);
    setError(null);
    
    try {
      let apiResult;

      if (videoFile && (content.trim() || imageFile || audioFile)) {
        setError('Video cannot be combined in multimodal analysis right now.');
        return;
      }

      // Determine if we need multimodal analysis
      const hasMultipleInputs = (content.trim() ? 1 : 0) + (imageFile ? 1 : 0) + (audioFile ? 1 : 0) + (videoFile ? 1 : 0) > 1;
      
      if (hasMultipleInputs) {
        // Use multimodal endpoint
        apiResult = await moderationAPI.moderateMultimodal(
          content.trim() || undefined,
          imageFile || undefined,
          audioFile || undefined
        );
        setResult(transformResult(apiResult, true));
      } else if (videoFile) {
        setError('Video moderation is currently unavailable.');
      } else if (imageFile) {
        // Image only
        const imageRes = await moderationAPI.moderateImage(imageFile);
        const decision = (imageRes as unknown as { decision?: string }).decision || 'ALLOW';
        setResult({
          explanation: `Image "${imageFile.name}" analyzed.`,
          flaggedContent: '',
          flags: (imageRes as unknown as { flags?: string[] }).flags || [],
          status: decisionToStatus(decision),
          decision,
          provider: (imageRes as unknown as { provider?: string }).provider,
        });
      } else if (audioFile) {
        // Audio only
        const audioRes = await moderationAPI.moderateAudio(audioFile);
        const decision = (audioRes as unknown as { decision?: string }).decision || 'ALLOW';
        setResult({
          explanation: audioRes.transcript 
            ? `Audio transcribed: "${audioRes.transcript.substring(0, 100)}${audioRes.transcript.length > 100 ? '...' : ''}"`
            : `Audio "${audioFile.name}" analyzed.`,
          flaggedContent: '',
          flags: (audioRes as unknown as { flags?: string[] }).flags || [],
          status: decisionToStatus(decision),
          decision,
          provider: (audioRes as unknown as { provider?: string }).provider,
        });
      } else {
        // Text only
        apiResult = await moderationAPI.moderateText(content);
        setResult(transformResult(apiResult));
      }
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to analyze content. Please try again.');
      }
      console.error('Moderation error:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleClear = () => {
    setContent('');
    setResult(null);
    setError(null);
    setImageFile(null);
    setAudioFile(null);
    setVideoFile(null);
  };

  const getStatusIcon = (status: ModerationResult['status']) => {
    switch (status) {
      case 'safe':
        return <CheckCircle className="h-6 w-6 text-emerald-500" />;
      case 'warning':
        return <AlertTriangle className="h-6 w-6 text-amber-500" />;
      case 'unsafe':
        return <XCircle className="h-6 w-6 text-rose-500" />;
    }
  };

  const getStatusLabel = (status: ModerationResult['status']) => {
    switch (status) {
      case 'safe':
        return 'Content Approved';
      case 'warning':
        return 'Review Recommended';
      case 'unsafe':
        return 'Content Flagged';
    }
  };

  const getStatusColor = (status: ModerationResult['status']) => {
    switch (status) {
      case 'safe':
        return 'bg-emerald-500/10 border-emerald-500/20';
      case 'warning':
        return 'bg-amber-500/10 border-amber-500/20';
      case 'unsafe':
        return 'bg-rose-500/10 border-rose-500/20';
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 animate-fade-in">
        <div>
          <h2 className="text-2xl font-bold mb-2">Content Moderation</h2>
          <p className="text-muted-foreground">
            Analyze your content for safety and policy compliance using AI.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive">
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        {/* Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Content to Analyze</CardTitle>
            <CardDescription>
              Enter text, upload images, audio, or video for comprehensive moderation analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="moderation-content">Text Content</Label>
              <Textarea
                id="moderation-content"
                placeholder="Enter the content you want to analyze..."
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={6}
                className="resize-none"
              />
            </div>

            {/* File Upload Areas */}
            <div className="grid sm:grid-cols-2 gap-4">
              {/* Image Upload */}
              <div 
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${
                  imageFile 
                    ? 'border-primary bg-primary/5' 
                    : 'border-primary/20 hover:border-primary/40'
                }`}
                onClick={() => imageInputRef.current?.click()}
              >
                <input
                  ref={imageInputRef}
                  type="file"
                  className="hidden"
                  accept="image/*"
                  onChange={handleImageUpload}
                  aria-label="Upload image file"
                />
                {imageFile ? (
                  <div className="relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute -top-2 -right-2 h-6 w-6 p-0 rounded-full"
                      onClick={(e) => {
                        e.stopPropagation();
                        setImageFile(null);
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                    <FileImage className="h-8 w-8 mx-auto mb-2 text-primary" />
                    <p className="text-sm font-medium truncate">{imageFile.name}</p>
                  </div>
                ) : (
                  <>
                    <FileImage className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground mb-2">Upload Image</p>
                    <Button variant="outline" size="sm">Browse</Button>
                  </>
                )}
              </div>

              {/* Audio Upload */}
              <div 
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${
                  audioFile 
                    ? 'border-primary bg-primary/5' 
                    : 'border-primary/20 hover:border-primary/40'
                }`}
                onClick={() => audioInputRef.current?.click()}
              >
                <input
                  ref={audioInputRef}
                  type="file"
                  className="hidden"
                  accept="audio/*"
                  onChange={handleAudioUpload}
                  aria-label="Upload audio file"
                />
                {audioFile ? (
                  <div className="relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute -top-2 -right-2 h-6 w-6 p-0 rounded-full"
                      onClick={(e) => {
                        e.stopPropagation();
                        setAudioFile(null);
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                    <Music className="h-8 w-8 mx-auto mb-2 text-primary" />
                    <p className="text-sm font-medium truncate">{audioFile.name}</p>
                  </div>
                ) : (
                  <>
                    <Music className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground mb-2">Upload Audio</p>
                    <Button variant="outline" size="sm">Browse</Button>
                  </>
                )}
              </div>
            </div>

            {/* Video Upload */}
            <div className="mt-4">
              <div 
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${
                  videoFile 
                    ? 'border-primary bg-primary/5' 
                    : 'border-primary/20 hover:border-primary/40'
                }`}
                onClick={() => videoInputRef.current?.click()}
              >
                <input
                  ref={videoInputRef}
                  type="file"
                  className="hidden"
                  accept="video/*"
                  onChange={handleVideoUpload}
                  aria-label="Upload video file"
                />
                {videoFile ? (
                  <div className="relative inline-block">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute -top-2 -right-2 h-6 w-6 p-0 rounded-full"
                      onClick={(e) => {
                        e.stopPropagation();
                        setVideoFile(null);
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                    <Video className="h-8 w-8 mx-auto mb-2 text-primary" />
                    <p className="text-sm font-medium truncate">{videoFile.name}</p>
                  </div>
                ) : (
                  <>
                    <Video className="h-8 w-8 mx-auto mb-3 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground mb-2">Upload Video</p>
                    <p className="text-xs text-muted-foreground mb-2">(Video moderation extracts frames for analysis)</p>
                    <Button variant="outline" size="sm">Browse</Button>
                  </>
                )}
              </div>
            </div>

            <div className="flex gap-3">
              <Button
                variant="hero"
                onClick={handleAnalyze}
                disabled={isAnalyzing || (!content.trim() && !imageFile && !audioFile && !videoFile)}
              >
                {isAnalyzing && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Analyze Content
              </Button>
              {(content || result || imageFile || audioFile || videoFile) && (
                <Button variant="outline" onClick={handleClear}>
                  Clear All
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Results Section */}
        {result && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Moderation Results</CardTitle>
              <CardDescription>
                Analysis results for your submitted content
                {result.processingTime && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({result.processingTime}ms)
                  </span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Status */}
              <div className={`flex items-center gap-4 p-4 rounded-xl border ${getStatusColor(result.status)}`}>
                {getStatusIcon(result.status)}
                <div className="flex-1">
                  <p className="font-semibold">{getStatusLabel(result.status)}</p>
                  <p className="text-sm text-muted-foreground">
                    Decision: {result.decision}
                  </p>
                </div>
              </div>

              {/* Flagged Content (if any) */}
              {result.flaggedContent && (
                <div>
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">Flagged Content</Label>
                  <div className="mt-2 p-4 rounded-xl bg-destructive/10 border border-destructive/20">
                    <p className="text-sm text-destructive font-medium">
                      {result.flaggedContent}
                    </p>
                  </div>
                </div>
              )}


              {/* Explanation */}
              <div>
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">AI Analysis</Label>
                <p className="mt-2 text-sm p-4 rounded-xl bg-primary/5">
                  {result.explanation}
                </p>
              </div>

              {/* File-specific results */}
              {result.fileResults?.audio?.transcript && (
                <div>
                  <Label className="text-xs uppercase tracking-wide text-muted-foreground">Audio Transcript</Label>
                  <p className="mt-2 text-sm p-4 rounded-xl bg-primary/5 italic">
                    "{result.fileResults.audio.transcript}"
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {!result && !content && !imageFile && !audioFile && !videoFile && (
          <EmptyState
            icon={<Shield className="h-8 w-8" />}
            title="No content to analyze"
            description="Enter text or upload content above to run AI-powered moderation analysis."
          />
        )}
      </div>
    </DashboardLayout>
  );
}
