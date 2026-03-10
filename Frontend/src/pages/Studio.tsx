import { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { EmptyState } from '@/components/shared/EmptyState';
import { Upload, FileText, Image, Music, Video, Wand2, Hash, FileSignature, Loader2, Sparkles, Copy, Check, Save, ArrowRight, Languages } from 'lucide-react';
import { creationAPI, contentAPI, translationAPI, APIError } from '@/services/api';

type ContentType = 'text' | 'image' | 'audio' | 'video' | null;

interface GeneratedContent {
  caption?: string;
  summary?: string;
  hashtags?: string[];
  provider?: string;
}

// Indian languages for translation
const INDIAN_LANGUAGES = [
  { code: 'en', name: 'English', native: 'English' },
  { code: 'hi', name: 'Hindi', native: 'हिंदी' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ' },
  { code: 'ml', name: 'Malayalam', native: 'മലയാളം' },
  { code: 'gu', name: 'Gujarati', native: 'ગુજરાતી' },
  { code: 'or', name: 'Odia', native: 'ଓଡ଼ିଆ' },
];

export default function Studio() {
  const [selectedType, setSelectedType] = useState<ContentType>(null);
  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingType, setProcessingType] = useState<string | null>(null);
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [savingToContent, setSavingToContent] = useState(false);
  const [savedContentId, setSavedContentId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Translation state
  const [targetLanguage, setTargetLanguage] = useState('hi');
  const [translatedCaption, setTranslatedCaption] = useState<string | null>(null);
  const [translatedSummary, setTranslatedSummary] = useState<string | null>(null);
  const [isTranslating, setIsTranslating] = useState(false);

  // Customization state
  const [targetPlatform, setTargetPlatform] = useState<'twitter' | 'instagram' | 'facebook' | 'linkedin' | 'custom'>('twitter');
  const [captionLength, setCaptionLength] = useState(280);
  const [hashtagCount, setHashtagCount] = useState(5);

  // Media-only mode state
  const [mediaOnlyMode, setMediaOnlyMode] = useState(false);
  const [extractedContent, setExtractedContent] = useState<string | null>(null);

  // Platform presets
  const platformPresets = {
    twitter: { length: 280, name: 'Twitter/X' },
    instagram: { length: 2200, name: 'Instagram' },
    facebook: { length: 63206, name: 'Facebook' },
    linkedin: { length: 3000, name: 'LinkedIn' },
    custom: { length: captionLength, name: 'Custom' },
  };

  // Update caption length when platform changes
  const handlePlatformChange = (platform: typeof targetPlatform) => {
    setTargetPlatform(platform);
    if (platform !== 'custom') {
      setCaptionLength(platformPresets[platform].length);
    }
  };

  const contentTypes = [
    { type: 'text' as const, icon: FileText, label: 'Text', description: 'Articles, posts, captions' },
    { type: 'image' as const, icon: Image, label: 'Image', description: 'Photos, graphics' },
    { type: 'audio' as const, icon: Music, label: 'Audio', description: 'Podcasts, recordings' },
    { type: 'video' as const, icon: Video, label: 'Video', description: 'Clips, reels' },
  ];

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFile(file);
    }
  };

  const handleGenerate = async (generationType: 'caption' | 'summary' | 'hashtags') => {
    if (!inputText.trim()) return;
    
    setIsProcessing(true);
    setProcessingType(generationType);
    setError(null);
    setTranslatedCaption(null);
    setTranslatedSummary(null);
    
    try {
      let result;
      
      switch (generationType) {
        case 'caption': {
          const captionRes = await creationAPI.generateCaption(inputText, selectedType || 'text', captionLength, targetPlatform);
          result = { caption: captionRes.result, provider: captionRes.provider };
          break;
        }
        case 'summary': {
          const summaryRes = await creationAPI.generateSummary(inputText, 150);
          result = { summary: summaryRes.result, provider: summaryRes.provider };
          break;
        }
        case 'hashtags': {
          const hashtagsRes = await creationAPI.generateHashtags(inputText, hashtagCount);
          result = { hashtags: hashtagsRes.hashtags, provider: hashtagsRes.provider };
          break;
        }
      }

      setGeneratedContent((prev) => ({
        ...prev,
        ...result,
      }));
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to generate content. Please try again.');
      }
      console.error('Generation error:', err);
    } finally {
      setIsProcessing(false);
      setProcessingType(null);
    }
  };

  const handleGenerateAll = async () => {
    if (!inputText.trim()) return;
    
    setIsProcessing(true);
    setProcessingType('all');
    setError(null);
    setTranslatedCaption(null);
    setTranslatedSummary(null);
    
    try {
      const [captionRes, summaryRes, hashtagsRes] = await Promise.all([
        creationAPI.generateCaption(inputText, selectedType || 'text', captionLength, targetPlatform),
        creationAPI.generateSummary(inputText, 150),
        creationAPI.generateHashtags(inputText, hashtagCount),
      ]);

      setGeneratedContent({
        caption: captionRes.result,
        summary: summaryRes.result,
        hashtags: hashtagsRes.hashtags,
        provider: captionRes.provider,
      });
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to generate content. Please try again.');
      }
      console.error('Generation error:', err);
    } finally {
      setIsProcessing(false);
      setProcessingType(null);
    }
  };

  const handleAnalyzeMedia = async () => {
    if (!uploadedFile) {
      setError('Please upload a media file first');
      return;
    }
    if (selectedType === 'video') {
      setError('Video extraction is currently unavailable.');
      return;
    }

    setIsProcessing(true);
    setProcessingType('media-analysis');
    setError(null);
    setExtractedContent(null);
    setGeneratedContent(null);

    try {
      const mediaType = selectedType as 'image' | 'audio' | 'video';
      const data = await creationAPI.extractAndGenerate(uploadedFile, mediaType);
      
      // Set extracted content
      setExtractedContent(data.extracted_content || 'Media analyzed successfully');
      
      // Set generated content
      setGeneratedContent({
        caption: data.caption,
        summary: data.summary,
        hashtags: data.hashtags,
        provider: data.provider,
      });

      // Optionally set as input text for further processing
      if (data.extracted_content) {
        setInputText(data.extracted_content);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze media');
      console.error('Media analysis error:', err);
    } finally {
      setIsProcessing(false);
      setProcessingType(null);
    }
  };

  const handleTranslate = async () => {
    if (!generatedContent?.caption && !generatedContent?.summary) return;
    
    setIsTranslating(true);
    setError(null);
    
    try {
      const translations = await Promise.all([
        generatedContent.caption 
          ? translationAPI.translate(generatedContent.caption, targetLanguage)
          : Promise.resolve(null),
        generatedContent.summary 
          ? translationAPI.translate(generatedContent.summary, targetLanguage)
          : Promise.resolve(null),
      ]);
      
      if (translations[0]) setTranslatedCaption(translations[0].translated_text);
      if (translations[1]) setTranslatedSummary(translations[1].translated_text);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to translate. Please try again.');
      }
    } finally {
      setIsTranslating(false);
    }
  };

  const handleCopy = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleSave = () => {
    setGeneratedContent(null);
    setInputText('');
    setSelectedType(null);
    setUploadedFile(null);
    setSavedContentId(null);
    setTranslatedCaption(null);
    setTranslatedSummary(null);
  };

  const handleSaveToMyContent = async () => {
    if (!inputText.trim() && !generatedContent?.caption && !generatedContent?.summary) return;
    setSavingToContent(true);
    setError(null);
    try {
      const hashtags = generatedContent?.hashtags;
      const item = await contentAPI.create({
        content_type: selectedType || 'text',
        original_text: inputText.trim() || undefined,
        caption: generatedContent?.caption,
        summary: generatedContent?.summary,
        hashtags: Array.isArray(hashtags) ? hashtags : undefined,
      });
      setSavedContentId(item.id);
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else setError('Failed to save to My Content');
    } finally {
      setSavingToContent(false);
    }
  };

  const handleClear = () => {
    setGeneratedContent(null);
    setError(null);
    setTranslatedCaption(null);
    setTranslatedSummary(null);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 animate-fade-in">
        <div>
          <h2 className="text-2xl font-bold mb-2">Creator Studio</h2>
          <p className="text-muted-foreground">
            Create, generate, and translate AI-powered content in one place.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive">
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        {/* Content Type Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Select Content Type</CardTitle>
            <CardDescription>Choose the type of content you want to process</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {contentTypes.map(({ type, icon: Icon, label, description }) => (
                <button
                  key={type}
                  onClick={() => {
                    setSelectedType(type);
                    setUploadedFile(null);
                  }}
                  className={`p-4 rounded-xl border transition-all text-left ${
                    selectedType === type
                      ? 'border-primary bg-primary/5 shadow-soft'
                      : 'border-primary/10 hover:border-primary/30 hover:bg-primary/5'
                  }`}
                >
                  <Icon className="h-6 w-6 mb-2" />
                  <span className="text-sm font-medium block">{label}</span>
                  <span className="text-xs text-muted-foreground">{description}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Input Area */}
        {selectedType && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Upload {selectedType.charAt(0).toUpperCase() + selectedType.slice(1)}</CardTitle>
              <CardDescription>
                {selectedType === 'text' 
                  ? 'Enter or paste your text content below'
                  : `Upload your ${selectedType} file and add a description`}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedType !== 'text' && (
                <div 
                  className="border-2 border-dashed border-primary/20 rounded-xl p-8 text-center hover:border-primary/40 transition-colors cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept={
                      selectedType === 'image' ? 'image/*' :
                      selectedType === 'audio' ? 'audio/*' :
                      selectedType === 'video' ? 'video/*' : '*'
                    }
                    onChange={handleFileUpload}
                    aria-label={`Upload ${selectedType} file`}
                  />
                  {uploadedFile ? (
                    <>
                      <Check className="h-10 w-10 mx-auto mb-4 text-primary" />
                      <p className="text-sm font-medium mb-2">{uploadedFile.name}</p>
                      <p className="text-xs text-muted-foreground">Click to change file</p>
                    </>
                  ) : (
                    <>
                      <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground mb-2">
                        Drag and drop your {selectedType} file here
                      </p>
                      <Button variant="outline" size="sm">
                        Browse files
                      </Button>
                    </>
                  )}
                </div>
              )}

              {/* Media-Only Mode Toggle */}
              {selectedType !== 'text' && uploadedFile && (
                <div className="flex items-center justify-between p-3 rounded-lg bg-primary/5 border border-primary/20">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <span className="text-sm font-medium">AI Media Analysis Mode</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={mediaOnlyMode}
                      onChange={(e) => setMediaOnlyMode(e.target.checked)}
                      aria-label="Toggle AI Media Analysis Mode"
                      title="Enable media-only analysis without text input"
                    />
                    <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                  </label>
                </div>
              )}

              {/* Extracted Content Display */}
              {extractedContent && (
                <div className="space-y-2">
                  <Label>📸 Extracted from Media</Label>
                  <div className="p-4 rounded-lg bg-muted/50 border border-border">
                    <p className="text-sm whitespace-pre-wrap">{extractedContent}</p>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="content">
                  {selectedType === 'text' ? 'Content' : mediaOnlyMode ? 'Additional Context (Optional)' : 'Description / Context'}
                </Label>
                <Textarea
                  id="content"
                  placeholder={
                    mediaOnlyMode 
                      ? 'Add extra context or leave empty for AI-only analysis...'
                      : selectedType === 'text'
                      ? 'Enter your text content here...'
                      : 'Describe your content for better AI generation...'
                  }
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  rows={6}
                  className="resize-none"
                />
              </div>

              {/* Customization Controls */}
              <div className="space-y-4 p-4 rounded-lg bg-muted/30 border border-border/50">
                <h4 className="text-sm font-medium">Content Customization</h4>
                <div className="grid sm:grid-cols-3 gap-4">
                  {/* Platform Selection */}
                  <div className="space-y-2">
                    <Label htmlFor="platform">Target Platform</Label>
                    <Select value={targetPlatform} onValueChange={(value: typeof targetPlatform) => handlePlatformChange(value)}>
                      <SelectTrigger id="platform">
                        <SelectValue placeholder="Select platform" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="twitter">🐦 Twitter/X (280)</SelectItem>
                        <SelectItem value="instagram">📸 Instagram (2200)</SelectItem>
                        <SelectItem value="facebook">📘 Facebook (63206)</SelectItem>
                        <SelectItem value="linkedin">💼 LinkedIn (3000)</SelectItem>
                        <SelectItem value="custom">⚙️ Custom</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Caption Length */}
                  <div className="space-y-2">
                    <Label htmlFor="caption-length">
                      Caption Length: {captionLength} chars
                    </Label>
                    <input
                      id="caption-length"
                      type="range"
                      min="100"
                      max="3000"
                      step="10"
                      value={captionLength}
                      onChange={(e) => {
                        setCaptionLength(parseInt(e.target.value));
                        setTargetPlatform('custom');
                      }}
                      title="Adjust caption length"
                      aria-label="Caption length slider"
                      className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer slider"
                    />
                  </div>

                  {/* Hashtag Count */}
                  <div className="space-y-2">
                    <Label htmlFor="hashtag-count">
                      Hashtags: {hashtagCount}
                    </Label>
                    <input
                      id="hashtag-count"
                      type="range"
                      min="3"
                      max="20"
                      step="1"
                      value={hashtagCount}
                      onChange={(e) => setHashtagCount(parseInt(e.target.value))}
                      title="Adjust hashtag count"
                      aria-label="Hashtag count slider"
                      className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer slider"
                    />
                  </div>
                </div>
              </div>

              {/* Generation Actions */}
              <div className="flex flex-wrap gap-3 pt-4">
                {/* Media-Only Mode: Analyze Media Button */}
                {mediaOnlyMode && selectedType !== 'text' && (
                  <Button
                    variant="hero"
                    onClick={handleAnalyzeMedia}
                    disabled={isProcessing || !uploadedFile}
                  >
                    {processingType === 'media-analysis' ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4 mr-2" />
                    )}
                    Analyze Media
                  </Button>
                )}

                {/* Standard Mode: Generate Buttons */}
                {!mediaOnlyMode && (
                  <>
                    <Button
                      variant="hero"
                      onClick={handleGenerateAll}
                      disabled={isProcessing || !inputText.trim()}
                    >
                      {processingType === 'all' ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Sparkles className="h-4 w-4 mr-2" />
                      )}
                      Generate All
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleGenerate('caption')}
                      disabled={isProcessing || !inputText.trim()}
                    >
                      {processingType === 'caption' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                      Caption
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleGenerate('summary')}
                      disabled={isProcessing || !inputText.trim()}
                    >
                  {processingType === 'summary' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileSignature className="h-4 w-4 mr-2" />}
                  Summary
                </Button>
                <Button
                  variant="outline"
                  onClick={() => handleGenerate('hashtags')}
                  disabled={isProcessing || !inputText.trim()}
                >
                  {processingType === 'hashtags' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Hash className="h-4 w-4 mr-2" />}
                  Hashtags
                </Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Generated Outputs */}
        {generatedContent && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Generated Content</CardTitle>
                  <CardDescription>
                    Review, translate, and save your AI-generated content
                  </CardDescription>
                </div>
                <Button variant="ghost" size="sm" onClick={handleClear}>
                  Clear
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {generatedContent.caption && (
                <div className="p-4 rounded-xl bg-primary/5 group">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs uppercase tracking-wide text-muted-foreground">Caption</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity h-8"
                      onClick={() => handleCopy(generatedContent.caption!, 'caption')}
                    >
                      {copiedField === 'caption' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{generatedContent.caption}</p>
                </div>
              )}
              {generatedContent.summary && (
                <div className="p-4 rounded-xl bg-primary/5 group">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs uppercase tracking-wide text-muted-foreground">Summary</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity h-8"
                      onClick={() => handleCopy(generatedContent.summary!, 'summary')}
                    >
                      {copiedField === 'summary' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{generatedContent.summary}</p>
                </div>
              )}
              {generatedContent.hashtags && generatedContent.hashtags.length > 0 && (
                <div className="p-4 rounded-xl bg-primary/5 group">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs uppercase tracking-wide text-muted-foreground">Hashtags</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity h-8"
                      onClick={() => handleCopy(generatedContent.hashtags!.join(' '), 'hashtags')}
                    >
                      {copiedField === 'hashtags' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {generatedContent.hashtags.map((tag, index) => (
                      <span key={index} className="text-sm px-3 py-1 rounded-lg bg-primary/10 hover:bg-primary/20 transition-colors cursor-pointer">
                        {tag.startsWith('#') ? tag : `#${tag}`}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Translation Section */}
              {(generatedContent.caption || generatedContent.summary) && (
                <div className="p-4 rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
                  <div className="flex items-center gap-2 mb-3">
                    <Languages className="h-5 w-5 text-primary" />
                    <Label className="text-sm font-medium">Translate to Indian Languages</Label>
                  </div>
                  <div className="flex flex-wrap gap-3 items-center">
                    <Select value={targetLanguage} onValueChange={setTargetLanguage}>
                      <SelectTrigger className="w-48">
                        <SelectValue placeholder="Select language" />
                      </SelectTrigger>
                      <SelectContent>
                        {INDIAN_LANGUAGES.filter(l => l.code !== 'en').map((lang) => (
                          <SelectItem key={lang.code} value={lang.code}>
                            {lang.name} ({lang.native})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="outline"
                      onClick={handleTranslate}
                      disabled={isTranslating}
                    >
                      {isTranslating ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Languages className="h-4 w-4 mr-2" />
                      )}
                      Translate
                    </Button>
                  </div>

                  {/* Translated content */}
                  {(translatedCaption || translatedSummary) && (
                    <div className="mt-4 space-y-3">
                      {translatedCaption && (
                        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 group">
                          <div className="flex items-center justify-between mb-2">
                            <Label className="text-xs uppercase tracking-wide text-emerald-600">
                              Translated Caption ({INDIAN_LANGUAGES.find(l => l.code === targetLanguage)?.native})
                            </Label>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="opacity-0 group-hover:opacity-100 transition-opacity h-7"
                              onClick={() => handleCopy(translatedCaption, 'translated-caption')}
                            >
                              {copiedField === 'translated-caption' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                            </Button>
                          </div>
                          <p className="text-sm whitespace-pre-wrap">{translatedCaption}</p>
                        </div>
                      )}
                      {translatedSummary && (
                        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 group">
                          <div className="flex items-center justify-between mb-2">
                            <Label className="text-xs uppercase tracking-wide text-emerald-600">
                              Translated Summary ({INDIAN_LANGUAGES.find(l => l.code === targetLanguage)?.native})
                            </Label>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="opacity-0 group-hover:opacity-100 transition-opacity h-7"
                              onClick={() => handleCopy(translatedSummary, 'translated-summary')}
                            >
                              {copiedField === 'translated-summary' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                            </Button>
                          </div>
                          <p className="text-sm whitespace-pre-wrap">{translatedSummary}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="flex flex-wrap gap-3 pt-2">
                <Button variant="hero" onClick={handleSave}>
                  Save Content
                </Button>
                <Button
                  variant="outline"
                  onClick={handleSaveToMyContent}
                  disabled={savingToContent}
                >
                  {savingToContent ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4 mr-2" />
                  )}
                  Save to My Content
                </Button>
                {savedContentId != null && (
                  <Button variant="link" asChild className="text-primary">
                    <Link to={`/content?contentId=${savedContentId}`}>
                      View in My Content
                      <ArrowRight className="h-4 w-4 ml-1" />
                    </Link>
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {!selectedType && (
          <EmptyState
            icon={<Wand2 className="h-8 w-8" />}
            title="No content selected"
            description="Select a content type above to start generating AI-powered captions, summaries, and hashtags."
          />
        )}
      </div>
    </DashboardLayout>
  );
}

