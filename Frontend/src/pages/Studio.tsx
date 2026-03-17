import { useCallback, useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { EmptyState } from '@/components/shared/EmptyState';
import { Upload, FileText, Image, Music, Video, Wand2, Hash, FileSignature, Loader2, Sparkles, Copy, Check, Save, ArrowRight, Languages, Brain, ShieldCheck, Eye, Layers } from 'lucide-react';
import { creationAPI, contentAPI, translationAPI, intelligenceAPI, motionAPI, APIError } from '@/services/api';
import type { CultureRewriteResponse, RiskReachResponse, AntiCancelResponse, AssetExplosionResponse, MentalHealthResponse, ShadowbanResponse, ContentItem as SavedAssetItem } from '@/services/api';
import { useLanguage } from '@/contexts/LanguageContext';

type ContentType = 'text' | 'image' | 'audio' | 'video' | null;
const FIXED_TEXT_MODEL = 'us.amazon.nova-lite-v1:0';
type ImageEngine = 'titan' | 'nova_canvas';

interface GeneratedContent {
  caption?: string;
  summary?: string;
  hashtags?: string[];
  transcript?: string;
  script?: string;
  ideas?: string[];
  provider?: string;
}

interface GeneratedImageAsset {
  image_url: string;
  preview_url?: string;
  engine: string;
  model_id: string;
  provider: string;
  prompt: string;
}

function extractMediaConvertOutputUri(details: unknown): string | undefined {
  if (!Array.isArray(details)) return undefined;
  for (const group of details) {
    const outputs = typeof group === 'object' && group && 'OutputDetails' in group
      ? (group as { OutputDetails?: unknown[] }).OutputDetails
      : undefined;
    if (!Array.isArray(outputs)) continue;
    for (const output of outputs) {
      const paths = typeof output === 'object' && output && 'OutputFilePaths' in output
        ? (output as { OutputFilePaths?: unknown[] }).OutputFilePaths
        : undefined;
      if (!Array.isArray(paths)) continue;
      for (const path of paths) {
        if (typeof path !== 'string') continue;
        if (path.toLowerCase().endsWith('.mp4')) return path;
      }
      const first = paths.find((p): p is string => typeof p === 'string');
      if (first) return first;
    }
  }
  return undefined;
}

function isConcreteMediaUri(value?: string): boolean {
  if (!value) return false;
  const v = value.trim().toLowerCase();
  if (!v) return false;
  if (v.endsWith('/')) return false;
  return (
    v.endsWith('.mp4') ||
    v.endsWith('.mov') ||
    v.endsWith('.m4v') ||
    v.endsWith('.webm') ||
    v.includes('.mp4?') ||
    v.includes('.mov?') ||
    v.includes('.m4v?') ||
    v.includes('.webm?')
  );
}

interface IntelligencePackResult {
  culture?: CultureRewriteResponse;
  risk?: RiskReachResponse;
  cancel?: AntiCancelResponse;
  assets?: AssetExplosionResponse;
  mental?: MentalHealthResponse;
  shadow?: ShadowbanResponse;
}

type ExecutionPreset = 'fast' | 'balanced' | 'best_quality';

interface CreatorTool {
  name: string;
  scope: string;
  details?: string;
  note?: string;
  tier: 'fast' | 'balanced' | 'best_quality';
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

const TOOLKIT_BY_TYPE: Record<Exclude<ContentType, null>, CreatorTool[]> = {
  text: [
    {
      name: 'Amazon Nova Lite',
      scope: 'Copywriting, scripts, ideation',
      details: 'Bedrock Nova Lite model is fixed for Studio text generation.',
      note: 'Creator Studio uses Nova Lite by default for all text generation.',
      tier: 'fast',
    },
  ],
  image: [
    {
      name: 'Amazon Titan Image Generator v2',
      scope: 'Visual assets and graphics',
      details: 'General-purpose image generation',
      note: 'Fast image generation for everyday creator workflows.',
      tier: 'fast',
    },
    {
      name: 'Amazon Nova Canvas',
      scope: 'Visual assets and graphics',
      details: 'Balanced quality visual generation',
      tier: 'balanced',
    },
  ],
  audio: [
    {
      name: 'Amazon Polly (Standard TTS)',
      scope: 'Voiceover generation',
      details: 'Voiceover generation',
      note: 'Reliable narration generation for voice workflows.',
      tier: 'fast',
    },
    {
      name: 'Amazon Translate',
      scope: 'Localization',
      details: 'Localization and language conversion',
      tier: 'balanced',
    },
    {
      name: 'Amazon Transcribe',
      scope: 'Captions and speech-to-text',
      details: 'Speech-to-text and subtitle extraction',
      note: 'Works well for subtitle and speech extraction pipelines.',
      tier: 'best_quality',
    },
  ],
  video: [
    {
      name: 'AWS Elemental MediaConvert',
      scope: 'Transcoding and formatting',
      details: 'Video transcoding and formatting',
      note: 'Great for production formatting and export workflows.',
      tier: 'fast',
    },
    {
      name: 'Amazon Nova Reel',
      scope: 'Generative video clips',
      details: 'Generative short video clip creation',
      tier: 'best_quality',
    },
    {
      name: 'Amazon Transcribe',
      scope: 'Subtitle generation',
      details: 'Subtitle generation from audio track',
      tier: 'balanced',
    },
  ],
};

export default function Studio() {
  const { language } = useLanguage();
  const [selectedType, setSelectedType] = useState<ContentType>(null);
  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingType, setProcessingType] = useState<string | null>(null);
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [savingToContent, setSavingToContent] = useState(false);
  const [savedContentId, setSavedContentId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Translation state
  const [targetLanguage, setTargetLanguage] = useState('hi');
  const [translatedCaption, setTranslatedCaption] = useState<string | null>(null);
  const [translatedSummary, setTranslatedSummary] = useState<string | null>(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcriptionLanguage, setTranscriptionLanguage] = useState('en');

  // Customization state
  const [targetPlatform, setTargetPlatform] = useState<'twitter' | 'instagram' | 'facebook' | 'linkedin' | 'custom'>('twitter');
  const [captionLength, setCaptionLength] = useState(280);
  const [hashtagCount, setHashtagCount] = useState(5);

  const [extractedContent, setExtractedContent] = useState<string | null>(null);
  const [workflowSteps, setWorkflowSteps] = useState<string[]>([]);
  const [showManualActions, setShowManualActions] = useState(false);
  const [executionPreset, setExecutionPreset] = useState<ExecutionPreset>('fast');

  // Intelligence pack state
  const [intelRegion, setIntelRegion] = useState('general');
  const [intelFestival, setIntelFestival] = useState('');
  const [intelNiche, setIntelNiche] = useState('');
  const [intelLanguage, setIntelLanguage] = useState('English');
  const [intelRiskLevel, setIntelRiskLevel] = useState(50);
  const [isRunningIntelligence, setIsRunningIntelligence] = useState(false);
  const [intelligenceResult, setIntelligenceResult] = useState<IntelligencePackResult | null>(null);
  const [novaReelPrompt, setNovaReelPrompt] = useState('');
  const [novaReelDuration, setNovaReelDuration] = useState(6);
  const [mediaConvertJob, setMediaConvertJob] = useState<{ id: string; status: string; output?: string } | null>(null);
  const [novaReelJob, setNovaReelJob] = useState<{ arn: string; status: string; output?: string } | null>(null);
  const [videoActionLoading, setVideoActionLoading] = useState<string | null>(null);
  const [imagePrompt, setImagePrompt] = useState('');
  const [imageEngine, setImageEngine] = useState<ImageEngine>('titan');
  const [imageActionLoading, setImageActionLoading] = useState<string | null>(null);
  const [generatedImage, setGeneratedImage] = useState<GeneratedImageAsset | null>(null);
  const [generatedImagePreviewFailed, setGeneratedImagePreviewFailed] = useState(false);
  const [uploadedPreviewUrl, setUploadedPreviewUrl] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [savedAssets, setSavedAssets] = useState<SavedAssetItem[]>([]);
  const [isLoadingAssets, setIsLoadingAssets] = useState(false);
  const [savedAssetsError, setSavedAssetsError] = useState<string | null>(null);

  const loadSavedAssets = useCallback(async () => {
    setIsLoadingAssets(true);
    setSavedAssetsError(null);
    try {
      const items = await contentAPI.list();
      setSavedAssets(items.slice(0, 12));
    } catch (err: unknown) {
      console.error('Failed to load saved assets:', err);
      if (err instanceof APIError && err.status === 401) {
        setSavedAssetsError('Please log in again to load saved assets.');
      } else if (err instanceof APIError) {
        setSavedAssetsError(err.message || 'Failed to load saved assets.');
      } else {
        setSavedAssetsError('Failed to load saved assets.');
      }
    } finally {
      setIsLoadingAssets(false);
    }
  }, []);

  useEffect(() => {
    void loadSavedAssets();
  }, [loadSavedAssets]);

  useEffect(() => {
    if (!uploadedFile || selectedType === 'text') {
      setUploadedPreviewUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(uploadedFile);
    setUploadedPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [uploadedFile, selectedType]);

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

  const handleGenerateAll = async () => {
    if (!selectedType) return;
    const hasTextInput = inputText.trim().length > 0;
    const hasMediaUpload = selectedType !== 'text' && uploadedFile !== null;
    if (!hasTextInput && !hasMediaUpload) return;
    
    setIsProcessing(true);
    setProcessingType('all');
    setError(null);
    setTranslatedCaption(null);
    setTranslatedSummary(null);
    setWorkflowSteps([]);
    
    try {
      let processingText = inputText.trim();
      let nextCaption: string | undefined;
      let nextSummary: string | undefined;
      let nextHashtags: string[] | undefined;
      let nextProvider = '';
      const completed: string[] = [];
      const selectedTools = TOOLKIT_BY_TYPE[selectedType]
        .filter((tool) =>
          selectedType === 'image'
            ? true
            : tool.tier === executionPreset || executionPreset === 'balanced'
        )
        .map((tool) => tool.name);
      if (selectedTools.length) {
        completed.push(`Stack: ${selectedTools.join(' + ')}`);
      }

      if (hasMediaUpload && uploadedFile) {
        const mediaType = selectedType as 'image' | 'audio' | 'video';
        const mediaRes = await creationAPI.extractAndGenerate(uploadedFile, mediaType, language);
        completed.push('Media analyzed');
        setExtractedContent(mediaRes.extracted_content || null);

        const extracted = (mediaRes.extracted_content || '').trim();
        if (extracted) {
          processingText = hasTextInput
            ? `${extracted}\n\nCreator context: ${processingText}`
            : extracted;
        }

        nextCaption = mediaRes.caption;
        nextSummary = mediaRes.summary;
        nextHashtags = mediaRes.hashtags;
        nextProvider = mediaRes.provider;
      } else {
        setExtractedContent(null);
      }

      const [captionRes, summaryRes, hashtagsRes] = await Promise.all([
        creationAPI.generateCaption(
          processingText,
          selectedType || 'text',
          captionLength,
          targetPlatform,
          FIXED_TEXT_MODEL,
          language
        ),
        creationAPI.generateSummary(processingText, 150, FIXED_TEXT_MODEL, language),
        creationAPI.generateHashtags(processingText, hashtagCount, FIXED_TEXT_MODEL, language),
      ]);

      nextCaption = captionRes.result || nextCaption;
      nextSummary = summaryRes.result || nextSummary;
      nextHashtags = hashtagsRes.hashtags?.length ? hashtagsRes.hashtags : nextHashtags;
      nextProvider = [nextProvider, captionRes.provider, summaryRes.provider, hashtagsRes.provider]
        .filter(Boolean)
        .join(' + ');
      completed.push('Caption generated', 'Summary generated', 'Hashtags generated');

      setGeneratedContent({
        caption: nextCaption,
        summary: nextSummary,
        hashtags: nextHashtags,
        provider: nextProvider,
      });
      setWorkflowSteps(completed);
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

  const getManualSeedText = () => {
    const text = inputText.trim();
    if (text) return text;
    return extractedContent?.trim() || '';
  };

  const ensureManualSeedText = async () => {
    const existingSeed = getManualSeedText();
    if (existingSeed) return existingSeed;

    if (selectedType && selectedType !== 'text' && uploadedFile) {
      const mediaRes = await creationAPI.extractAndGenerate(
        uploadedFile,
        selectedType as 'image' | 'audio' | 'video',
        language
      );
      const extracted = (mediaRes.extracted_content || '').trim();
      if (extracted) {
        setExtractedContent(extracted);
        setWorkflowSteps((prev) => (prev.includes('Media analyzed') ? prev : [...prev, 'Media analyzed']));
        return extracted;
      }
    }

    return '';
  };

  const handleGenerate = async (generationType: 'caption' | 'summary' | 'hashtags') => {
    const seedText = await ensureManualSeedText();
    if (!seedText) return;

    setIsProcessing(true);
    setProcessingType(generationType);
    setError(null);
    setTranslatedCaption(null);
    setTranslatedSummary(null);

    try {
      let result;

      switch (generationType) {
        case 'caption': {
          const captionRes = await creationAPI.generateCaption(
            seedText,
            selectedType || 'text',
            captionLength,
            targetPlatform,
            FIXED_TEXT_MODEL,
            language
          );
          result = { caption: captionRes.result, provider: captionRes.provider };
          break;
        }
        case 'summary': {
          const summaryRes = await creationAPI.generateSummary(seedText, 150, FIXED_TEXT_MODEL, language);
          result = { summary: summaryRes.result, provider: summaryRes.provider };
          break;
        }
        case 'hashtags': {
          const hashtagsRes = await creationAPI.generateHashtags(seedText, hashtagCount, FIXED_TEXT_MODEL, language);
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

  const handleTranscribe = async () => {
    if (!uploadedFile || selectedType !== 'audio') return;

    setIsTranscribing(true);
    setError(null);
    try {
      const transcriptRes = await creationAPI.transcribeAudio(uploadedFile, transcriptionLanguage);
      setGeneratedContent((prev) => ({
        ...prev,
        transcript: transcriptRes.text,
        provider: [prev?.provider, transcriptRes.provider].filter(Boolean).join(' + '),
      }));
      setExtractedContent(transcriptRes.text || null);
      setWorkflowSteps((prev) => {
        if (prev.includes('Audio transcribed')) return prev;
        return [...prev, 'Audio transcribed'];
      });
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to transcribe audio. Please try again.');
      }
    } finally {
      setIsTranscribing(false);
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
    setExtractedContent(null);
    setWorkflowSteps([]);
    setTranscriptionLanguage('en');
    setIsTranscribing(false);
    setMediaConvertJob(null);
    setNovaReelJob(null);
    setNovaReelPrompt('');
    setGeneratedImage(null);
    setImagePrompt('');
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
      setSavedAssets((prev) => [item, ...prev.filter((p) => p.id !== item.id)].slice(0, 12));
      await loadSavedAssets();
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
    setWorkflowSteps([]);
    setIntelligenceResult(null);
  };

  const canRunCompleteWorkflow = selectedType === 'text'
    ? inputText.trim().length > 0
    : uploadedFile !== null || inputText.trim().length > 0;
  const canRunManualGeneration = selectedType === 'text'
    ? getManualSeedText().length > 0
    : getManualSeedText().length > 0 || uploadedFile !== null;
  const canRunIntelligencePack = selectedType === 'text'
    ? getIntelligenceSeedText().length > 0
    : getIntelligenceSeedText().length > 0 || uploadedFile !== null;
  const completeWorkflowDisabledHint = selectedType === 'text'
    ? 'Add text content to generate your package.'
    : 'Upload a file or add context text to analyze and generate.';

  const resolvePlatformForIntelligence = () =>
    targetPlatform === 'custom' ? 'instagram' : targetPlatform;

  const presetLabelMap: Record<ExecutionPreset, string> = {
    fast: 'Fast',
    balanced: 'Balanced',
    best_quality: 'Best Quality',
  };

  const getIntelligenceSeedText = () => {
    const primary = generatedContent?.caption?.trim()
      || generatedContent?.summary?.trim()
      || inputText.trim()
      || extractedContent?.trim()
      || '';
    return primary;
  };

  const ensureIntelligenceSeedText = async () => {
    const existingSeed = getIntelligenceSeedText();
    if (existingSeed) return existingSeed;

    if (selectedType && selectedType !== 'text' && uploadedFile) {
      const mediaRes = await creationAPI.extractAndGenerate(
        uploadedFile,
        selectedType as 'image' | 'audio' | 'video',
        language
      );
      const extracted = (mediaRes.extracted_content || '').trim();
      if (extracted) {
        setExtractedContent(extracted);
        setWorkflowSteps((prev) => (prev.includes('Media analyzed') ? prev : [...prev, 'Media analyzed']));
        return extracted;
      }
    }

    return '';
  };

  const handleRunIntelligencePack = async () => {
    const seedText = await ensureIntelligenceSeedText();
    if (!seedText) return;

    setIsRunningIntelligence(true);
    setError(null);
    setIntelligenceResult(null);

    try {
      const platform = resolvePlatformForIntelligence();
      const checks = await Promise.allSettled([
        intelligenceAPI.cultureRewrite(
          seedText,
          intelRegion.trim() || 'general',
          intelFestival.trim() || undefined,
          intelNiche.trim() || undefined,
          intelLanguage
        ),
        intelligenceAPI.riskReachGenerate(
          seedText,
          intelRiskLevel,
          platform,
          intelNiche.trim() || undefined
        ),
        intelligenceAPI.antiCancelAnalyze(seedText),
        intelligenceAPI.explodeAssets(seedText, intelNiche.trim() || undefined),
        intelligenceAPI.mentalHealthAnalyze([seedText]),
        intelligenceAPI.predictShadowban(seedText, generatedContent?.hashtags, platform),
      ]);
      const [cultureCheck, riskCheck, cancelCheck, assetsCheck, mentalCheck, shadowCheck] = checks;

      const partialResult: IntelligencePackResult = {
        culture: cultureCheck.status === 'fulfilled' ? cultureCheck.value : undefined,
        risk: riskCheck.status === 'fulfilled' ? riskCheck.value : undefined,
        cancel: cancelCheck.status === 'fulfilled' ? cancelCheck.value : undefined,
        assets: assetsCheck.status === 'fulfilled' ? assetsCheck.value : undefined,
        mental: mentalCheck.status === 'fulfilled' ? mentalCheck.value : undefined,
        shadow: shadowCheck.status === 'fulfilled' ? shadowCheck.value : undefined,
      };

      const succeededCount = Object.values(partialResult).filter(Boolean).length;
      const failedChecks = [
        cultureCheck.status === 'rejected' ? 'Culture' : null,
        riskCheck.status === 'rejected' ? 'Risk/Reach' : null,
        cancelCheck.status === 'rejected' ? 'Anti-Cancel' : null,
        assetsCheck.status === 'rejected' ? 'Asset Explosion' : null,
        mentalCheck.status === 'rejected' ? 'Mental Health' : null,
        shadowCheck.status === 'rejected' ? 'Shadowban' : null,
      ].filter((item): item is string => Boolean(item));

      if (succeededCount === 0) {
        setError('All intelligence checks failed. Please try again.');
        return;
      }

      setIntelligenceResult(partialResult);
      if (failedChecks.length > 0) {
        setError(`Some intelligence checks failed: ${failedChecks.join(', ')}.`);
      }
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to run Intelligence Pack. Please try again.');
      }
      console.error('Intelligence pack error:', err);
    } finally {
      setIsRunningIntelligence(false);
    }
  };

  const handleGenerateImage = async () => {
    const prompt = imagePrompt.trim() || inputText.trim();
    if (!prompt) {
      setError('Enter an image prompt first.');
      return;
    }
    setImageActionLoading('generate-image');
    setError(null);
    try {
      const res = await motionAPI.generateImage(prompt, imageEngine, 1024, 1024);
      setGeneratedImage({
        image_url: res.image_url,
        preview_url: res.preview_url,
        engine: res.engine,
        model_id: res.model_id,
        provider: res.provider,
        prompt: res.prompt,
      });
      setGeneratedImagePreviewFailed(false);
      setSuccessMessage('Image generated successfully.');
      setWorkflowSteps((prev) => (prev.includes('Image generated') ? prev : [...prev, 'Image generated']));
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else setError('Failed to generate image.');
    } finally {
      setImageActionLoading(null);
    }
  };

  const handleSaveGeneratedImage = async () => {
    if (!generatedImage) return;
    setSavingToContent(true);
    setError(null);
    try {
      const item = await contentAPI.create({
        content_type: 'image',
        original_text: generatedImage.prompt,
        file_path: generatedImage.image_url,
      });
      setSavedContentId(item.id);
      setSavedAssets((prev) => [item, ...prev.filter((p) => p.id !== item.id)].slice(0, 12));
      await loadSavedAssets();
      setSuccessMessage('Generated image saved to My Content.');
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else setError('Failed to save generated image.');
    } finally {
      setSavingToContent(false);
    }
  };

  const handleSaveMediaConvertOutput = async () => {
    if (!mediaConvertJob?.output) return;
    setSavingToContent(true);
    setError(null);
    try {
      const item = await contentAPI.create({
        content_type: 'video',
        original_text: inputText.trim() || undefined,
        file_path: mediaConvertJob.output,
      });
      setSavedContentId(item.id);
      setSavedAssets((prev) => [item, ...prev.filter((p) => p.id !== item.id)].slice(0, 12));
      await loadSavedAssets();
      setSuccessMessage('MediaConvert output saved to My Content.');
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else setError('Failed to save MediaConvert output.');
    } finally {
      setSavingToContent(false);
    }
  };

  const handleSaveNovaReelOutput = async () => {
    if (!novaReelJob?.output) return;
    setSavingToContent(true);
    setError(null);
    try {
      const item = await contentAPI.create({
        content_type: 'video',
        original_text: novaReelPrompt.trim() || inputText.trim() || undefined,
        file_path: novaReelJob.output,
      });
      setSavedContentId(item.id);
      setSavedAssets((prev) => [item, ...prev.filter((p) => p.id !== item.id)].slice(0, 12));
      await loadSavedAssets();
      setSuccessMessage('Nova Reel output saved to My Content.');
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else setError('Failed to save Nova Reel output.');
    } finally {
      setSavingToContent(false);
    }
  };

  const handleStartMediaConvert = async () => {
    if (!uploadedFile || selectedType !== 'video') return;
    setVideoActionLoading('mediaconvert');
    setError(null);
    try {
      const res = await motionAPI.startMediaConvert(uploadedFile);
      setMediaConvertJob({
        id: res.job_id,
        status: res.status,
        output: res.output_s3_uri,
      });
      setWorkflowSteps((prev) => (prev.includes('MediaConvert started') ? prev : [...prev, 'MediaConvert started']));
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else setError('Failed to start MediaConvert job.');
    } finally {
      setVideoActionLoading(null);
    }
  };

  const handleCheckMediaConvert = async () => {
    if (!mediaConvertJob?.id) return;
    setVideoActionLoading('mediaconvert-status');
    try {
      const res = await motionAPI.getMediaConvertStatus(mediaConvertJob.id);
      const resolvedOutput = extractMediaConvertOutputUri(res.output_group_details) || res.output_s3_uri;
      setMediaConvertJob((prev) => {
        if (!prev) return prev;
        const nextOutput = isConcreteMediaUri(resolvedOutput) ? resolvedOutput : (prev.output || resolvedOutput);
        return { ...prev, status: res.status, output: nextOutput };
      });
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else setError('Failed to fetch MediaConvert status.');
    } finally {
      setVideoActionLoading(null);
    }
  };

  const handleStartNovaReel = async () => {
    if (executionPreset !== 'best_quality') {
      setError('Nova Reel is available only in Best Quality preset.');
      return;
    }
    const prompt = novaReelPrompt.trim() || inputText.trim();
    if (!prompt) {
      setError('Enter a prompt for Nova Reel generation.');
      return;
    }
    setVideoActionLoading('nova-reel');
    setError(null);
    try {
      const res = await motionAPI.startNovaReel(prompt, novaReelDuration, '16:9');
      setNovaReelJob({
        arn: res.invocation_arn,
        status: res.status,
        output: res.output_s3_uri,
      });
      setWorkflowSteps((prev) => (prev.includes('Nova Reel started') ? prev : [...prev, 'Nova Reel started']));
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else setError('Failed to start Nova Reel job.');
    } finally {
      setVideoActionLoading(null);
    }
  };

  const handleCheckNovaReel = async () => {
    if (!novaReelJob?.arn) return;
    setVideoActionLoading('nova-reel-status');
    try {
      const res = await motionAPI.getNovaReelStatus(novaReelJob.arn);
      setNovaReelJob((prev) => {
        if (!prev) return prev;
        const nextOutput = isConcreteMediaUri(res.output_s3_uri) ? res.output_s3_uri : (prev.output || res.output_s3_uri);
        return { ...prev, status: res.status, output: nextOutput };
      });
    } catch (err) {
      if (err instanceof APIError) setError(err.message);
      else setError('Failed to fetch Nova Reel status.');
    } finally {
      setVideoActionLoading(null);
    }
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

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">Your Saved Assets</CardTitle>
                <CardDescription>Recent text, image, and video assets stored for your account.</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => void loadSavedAssets()} disabled={isLoadingAssets}>
                {isLoadingAssets ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {savedAssetsError && (
              <div className="mb-3 p-3 rounded-lg border border-destructive/20 bg-destructive/10 text-destructive text-sm">
                {savedAssetsError}
              </div>
            )}
            {savedAssets.length === 0 ? (
              <p className="text-sm text-muted-foreground">No saved assets yet. Save one from Creator Studio to see it here.</p>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {savedAssets.map((asset) => (
                  <div key={asset.id} className="rounded-lg border p-3 bg-background space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs uppercase px-2 py-1 rounded bg-muted">{asset.content_type}</span>
                      <span className="text-[11px] text-muted-foreground">{new Date(asset.created_at).toLocaleString()}</span>
                    </div>
                    {asset.caption && <p className="text-sm line-clamp-3">{asset.caption}</p>}
                    {!asset.caption && asset.summary && <p className="text-sm line-clamp-3">{asset.summary}</p>}
                    {!asset.caption && !asset.summary && asset.original_text && <p className="text-sm line-clamp-3">{asset.original_text}</p>}

                    {asset.file_path && asset.content_type === 'image' && (
                      <img src={asset.file_url || asset.file_path} alt="Saved asset" className="w-full rounded border border-border" />
                    )}
                    {asset.file_path && asset.content_type === 'video' && (
                      <video src={asset.file_url || asset.file_path} controls className="w-full rounded border border-border" />
                    )}
                    {asset.file_path && asset.content_type === 'audio' && (
                      <audio src={asset.file_url || asset.file_path} controls className="w-full" />
                    )}
                    {asset.file_path && !['image', 'video', 'audio'].includes(asset.content_type) && (
                      <a href={asset.file_path} target="_blank" rel="noreferrer" className="text-xs text-primary underline break-all">
                        {asset.file_path}
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive">
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}
        {successMessage && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700">
            <p className="text-sm font-medium">{successMessage}</p>
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
                    if (type === 'text') {
                      setExecutionPreset('fast');
                    }
                    if (type === 'image') {
                      setExecutionPreset('fast');
                    }
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

        {selectedType && selectedType !== 'text' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Creator Tool Stack</CardTitle>
              <CardDescription>
                Production model and service routing for {selectedType} workflows in Creator Studio.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedType !== 'image' && (
                <div className="grid sm:grid-cols-3 gap-2">
                  <button
                    onClick={() => setExecutionPreset('fast')}
                    className={`p-3 rounded-lg border text-left transition ${
                      executionPreset === 'fast' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30'
                    }`}
                  >
                    <p className="text-sm font-medium">Fast</p>
                    <p className="text-xs text-muted-foreground">Optimize for quick turnaround</p>
                  </button>
                  <button
                    onClick={() => setExecutionPreset('balanced')}
                    className={`p-3 rounded-lg border text-left transition ${
                      executionPreset === 'balanced' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30'
                    }`}
                  >
                    <p className="text-sm font-medium">Balanced</p>
                    <p className="text-xs text-muted-foreground">Best quality and speed mix</p>
                  </button>
                  <button
                    onClick={() => setExecutionPreset('best_quality')}
                    className={`p-3 rounded-lg border text-left transition ${
                      executionPreset === 'best_quality' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/30'
                    }`}
                  >
                    <p className="text-sm font-medium">Best Quality</p>
                    <p className="text-xs text-muted-foreground">Prioritize strongest outputs</p>
                  </button>
                </div>
              )}

              <div className="space-y-2">
                {TOOLKIT_BY_TYPE[selectedType].map((tool) => (
                  <div
                    key={`${tool.name}-${tool.scope}`}
                    className={`p-3 rounded-lg border ${
                      selectedType === 'image' || executionPreset === 'balanced' || tool.tier === executionPreset
                        ? 'border-primary/30 bg-primary/5'
                        : 'border-border/60 bg-muted/20'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">{tool.name}</p>
                      <span className="text-[10px] uppercase tracking-wide px-2 py-1 rounded bg-background border">
                        {tool.tier.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{tool.scope}</p>
                    {tool.details && <p className="text-xs mt-1">{tool.details}</p>}
                    {tool.note && <p className="text-xs text-muted-foreground mt-1">{tool.note}</p>}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Input Area */}
        {selectedType && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Create {selectedType.charAt(0).toUpperCase() + selectedType.slice(1)} Content</CardTitle>
              <CardDescription>
                {selectedType === 'text' 
                  ? 'Step 1: add your source text. Step 2: tune options. Step 3: generate complete package.'
                  : `Step 1: upload ${selectedType}. Step 2: add optional context. Step 3: generate complete package.`}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 rounded-lg border bg-muted/20">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className={`px-2 py-1 rounded ${selectedType ? 'bg-emerald-500/15 text-emerald-700' : 'bg-muted text-muted-foreground'}`}>
                    Content type selected
                  </span>
                  <span className={`px-2 py-1 rounded ${canRunCompleteWorkflow ? 'bg-emerald-500/15 text-emerald-700' : 'bg-muted text-muted-foreground'}`}>
                    Input ready
                  </span>
                  <span className={`px-2 py-1 rounded ${generatedContent ? 'bg-emerald-500/15 text-emerald-700' : 'bg-muted text-muted-foreground'}`}>
                    Package generated
                  </span>
                </div>
              </div>

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

              {uploadedFile && uploadedPreviewUrl && (
                <div className="space-y-2">
                  <Label>Uploaded Preview</Label>
                  <div className="p-3 rounded-lg bg-background border">
                    {selectedType === 'image' && (
                      <img
                        src={uploadedPreviewUrl}
                        alt={uploadedFile.name}
                        className="w-full max-w-xl rounded border border-border"
                      />
                    )}
                    {selectedType === 'video' && (
                      <video
                        src={uploadedPreviewUrl}
                        controls
                        className="w-full max-w-xl rounded border border-border"
                      />
                    )}
                    {selectedType === 'audio' && (
                      <audio src={uploadedPreviewUrl} controls className="w-full max-w-xl" />
                    )}
                  </div>
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
                  {selectedType === 'text' ? 'Content' : 'Description / Context (Optional)'}
                </Label>
                <Textarea
                  id="content"
                  placeholder={
                    selectedType === 'text'
                      ? 'Enter your text content here...'
                      : 'Add context, campaign goals, or audience note (optional)...'
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

              {selectedType === 'audio' && uploadedFile && (
                <div className="space-y-3 p-4 rounded-lg bg-blue-500/5 border border-blue-500/20">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h4 className="text-sm font-medium">Transcription</h4>
                      <p className="text-xs text-muted-foreground">
                        Generate a clean transcript before running content generation.
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      onClick={handleTranscribe}
                      disabled={isTranscribing}
                    >
                      {isTranscribing ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Music className="h-4 w-4 mr-2" />
                      )}
                      Transcribe Audio
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="transcription-language">Language hint</Label>
                    <Select value={transcriptionLanguage} onValueChange={setTranscriptionLanguage}>
                      <SelectTrigger id="transcription-language" className="w-48">
                        <SelectValue placeholder="Select language" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="en">English</SelectItem>
                        <SelectItem value="hi">Hindi</SelectItem>
                        <SelectItem value="ta">Tamil</SelectItem>
                        <SelectItem value="te">Telugu</SelectItem>
                        <SelectItem value="bn">Bengali</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              {selectedType === 'image' && (
                <div className="space-y-4 p-4 rounded-lg bg-sky-500/5 border border-sky-500/20">
                  <div>
                    <h4 className="text-sm font-medium">Image Generation</h4>
                    <p className="text-xs text-muted-foreground">
                      Generate visual assets directly from your prompt.
                    </p>
                  </div>
                  <div className="grid sm:grid-cols-3 gap-4">
                    <div className="sm:col-span-2 space-y-2">
                      <Label htmlFor="image-prompt">Prompt</Label>
                      <Textarea
                        id="image-prompt"
                        rows={3}
                        value={imagePrompt}
                        onChange={(e) => setImagePrompt(e.target.value)}
                        placeholder="Describe the visual you want to create..."
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="image-quality">Quality</Label>
                      <Select value={imageEngine} onValueChange={(value: ImageEngine) => setImageEngine(value)}>
                        <SelectTrigger id="image-quality">
                          <SelectValue placeholder="Select quality" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="titan">Standard (Titan)</SelectItem>
                          <SelectItem value="nova_canvas">High (Nova Canvas)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      onClick={handleGenerateImage}
                      disabled={imageActionLoading === 'generate-image'}
                    >
                      {imageActionLoading === 'generate-image' ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Image className="h-4 w-4 mr-2" />
                      )}
                      Generate Image
                    </Button>
                    {generatedImage && (
                      <Button
                        variant="outline"
                        onClick={handleSaveGeneratedImage}
                        disabled={savingToContent}
                      >
                        {savingToContent ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                        Save Generated Image
                      </Button>
                    )}
                  </div>
                  {generatedImage && (
                    <div className="p-3 rounded-lg bg-background border space-y-3">
                      {generatedImagePreviewFailed ? (
                        <div className="text-sm text-muted-foreground">
                          Preview unavailable. Open image directly:{' '}
                          <a
                            href={generatedImage.image_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-primary underline break-all"
                          >
                            {generatedImage.image_url}
                          </a>
                        </div>
                      ) : (
                        <img
                          src={generatedImage.preview_url || generatedImage.image_url}
                          alt="Generated asset"
                          className="w-full max-w-xl rounded-lg border border-border"
                          onError={() => setGeneratedImagePreviewFailed(true)}
                        />
                      )}
                      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                        <span className="px-2 py-1 rounded bg-muted">Engine: {generatedImage.engine}</span>
                        <span className="px-2 py-1 rounded bg-muted">Model: {generatedImage.model_id}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {selectedType === 'video' && (
                <div className="space-y-4 p-4 rounded-lg bg-violet-500/5 border border-violet-500/20">
                  <div>
                    <h4 className="text-sm font-medium">Motion & Video Production</h4>
                    <p className="text-xs text-muted-foreground">
                      Run production actions directly from Creator Studio.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      onClick={handleStartMediaConvert}
                      disabled={!uploadedFile || videoActionLoading === 'mediaconvert'}
                    >
                      {videoActionLoading === 'mediaconvert' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Video className="h-4 w-4 mr-2" />}
                      Run MediaConvert
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={handleCheckMediaConvert}
                      disabled={!mediaConvertJob || videoActionLoading === 'mediaconvert-status'}
                    >
                      {videoActionLoading === 'mediaconvert-status' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                      Check MediaConvert Status
                    </Button>
                  </div>
                  {mediaConvertJob && (
                    <div className="p-3 rounded-lg bg-background border">
                      <p className="text-xs"><span className="font-medium">Job:</span> {mediaConvertJob.id}</p>
                      <p className="text-xs"><span className="font-medium">Status:</span> {mediaConvertJob.status}</p>
                      {mediaConvertJob.output && <p className="text-xs break-all"><span className="font-medium">Output:</span> {mediaConvertJob.output}</p>}
                      {mediaConvertJob.output && (
                        <div className="mt-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleSaveMediaConvertOutput}
                            disabled={savingToContent || !isConcreteMediaUri(mediaConvertJob.output)}
                          >
                            {savingToContent ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                            Save Video Asset
                          </Button>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="nova-reel-prompt">Nova Reel Prompt</Label>
                    <Textarea
                      id="nova-reel-prompt"
                      rows={3}
                      placeholder="Describe the generated video scene..."
                      value={novaReelPrompt}
                      onChange={(e) => setNovaReelPrompt(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="nova-reel-duration">Nova Reel Duration (seconds)</Label>
                    <input
                      id="nova-reel-duration"
                      type="range"
                      min="3"
                      max="30"
                      step="1"
                      value={novaReelDuration}
                      onChange={(e) => setNovaReelDuration(parseInt(e.target.value))}
                      className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer slider"
                    />
                    <p className="text-xs text-muted-foreground">{novaReelDuration}s</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      onClick={handleStartNovaReel}
                      disabled={videoActionLoading === 'nova-reel' || executionPreset !== 'best_quality'}
                    >
                      {videoActionLoading === 'nova-reel' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                      Generate Nova Reel
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={handleCheckNovaReel}
                      disabled={!novaReelJob || videoActionLoading === 'nova-reel-status'}
                    >
                      {videoActionLoading === 'nova-reel-status' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                      Check Nova Reel Status
                    </Button>
                  </div>
                  {novaReelJob && (
                    <div className="p-3 rounded-lg bg-background border">
                      <p className="text-xs break-all"><span className="font-medium">Invocation ARN:</span> {novaReelJob.arn}</p>
                      <p className="text-xs"><span className="font-medium">Status:</span> {novaReelJob.status}</p>
                      {novaReelJob.output && <p className="text-xs break-all"><span className="font-medium">Output:</span> {novaReelJob.output}</p>}
                      {novaReelJob.output && (
                        <div className="mt-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleSaveNovaReelOutput}
                            disabled={savingToContent || !isConcreteMediaUri(novaReelJob.output)}
                          >
                            {savingToContent ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                            Save Video Asset
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-3 p-4 rounded-lg bg-muted/30 border border-border/50">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-medium">Manual Options (Advanced)</h4>
                    <p className="text-xs text-muted-foreground">
                      Generate one item at a time instead of the full package.
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowManualActions((prev) => !prev)}
                    disabled={isProcessing}
                  >
                    {showManualActions ? 'Hide' : 'Show'}
                  </Button>
                </div>
                {showManualActions && (
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        onClick={() => handleGenerate('caption')}
                        disabled={isProcessing || !canRunManualGeneration}
                      >
                        {processingType === 'caption' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                        Caption
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleGenerate('summary')}
                        disabled={isProcessing || !canRunManualGeneration}
                      >
                        {processingType === 'summary' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileSignature className="h-4 w-4 mr-2" />}
                        Summary
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleGenerate('hashtags')}
                        disabled={isProcessing || !canRunManualGeneration}
                      >
                        {processingType === 'hashtags' ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Hash className="h-4 w-4 mr-2" />}
                        Hashtags
                      </Button>
                    </div>
                    {!canRunManualGeneration && (
                      <p className="text-xs text-muted-foreground">
                        Add text or analyze media first to enable manual options.
                      </p>
                    )}
                  </div>
                )}
              </div>

              <div className="space-y-3 p-4 rounded-lg bg-muted/30 border border-border/50">
              {/* Primary Generation Action */}
              <div className="flex flex-wrap gap-3 pt-4">
                <Button
                  variant="hero"
                  onClick={handleGenerateAll}
                  disabled={isProcessing || !canRunCompleteWorkflow}
                >
                  {processingType === 'all' ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4 mr-2" />
                  )}
                  {selectedType === 'text'
                    ? 'Create Complete Content Package'
                    : selectedType === 'image'
                      ? 'Analyze Upload + Create Complete Package'
                    : `Analyze Upload + Create Complete Package (${presetLabelMap[executionPreset]})`}
                </Button>
              </div>
              {!canRunCompleteWorkflow && (
                <p className="text-xs text-muted-foreground">{completeWorkflowDisabledHint}</p>
              )}
              </div>
            </CardContent>
          </Card>
        )}

        {selectedType && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Intelligence Pack</CardTitle>
              <CardDescription>
                Run strategic checks after drafting context to improve quality, safety, and reach.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="ui-instruction">
                Fill region, language, and niche first. Then run the pack for clearer recommendations and fewer failed checks.
              </p>
              <div className="grid sm:grid-cols-4 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="intel-region">Region</Label>
                  <input
                    id="intel-region"
                    type="text"
                    value={intelRegion}
                    onChange={(e) => setIntelRegion(e.target.value)}
                    placeholder="general / Chennai / Delhi"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="intel-language">Language</Label>
                  <input
                    id="intel-language"
                    type="text"
                    value={intelLanguage}
                    onChange={(e) => setIntelLanguage(e.target.value)}
                    placeholder="English / Hindi / Tamil"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="intel-festival">Festival</Label>
                  <input
                    id="intel-festival"
                    type="text"
                    value={intelFestival}
                    onChange={(e) => setIntelFestival(e.target.value)}
                    placeholder="Optional"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="intel-niche">Niche</Label>
                  <input
                    id="intel-niche"
                    type="text"
                    value={intelNiche}
                    onChange={(e) => setIntelNiche(e.target.value)}
                    placeholder="Beauty / Finance / Fitness"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="intel-risk-level">Risk vs Reach Dial: {intelRiskLevel}</Label>
                <input
                  id="intel-risk-level"
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={intelRiskLevel}
                  onChange={(e) => setIntelRiskLevel(parseInt(e.target.value))}
                  title="Adjust intelligence risk level"
                  aria-label="Intelligence risk level slider"
                  className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer slider"
                />
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  variant="outline"
                  onClick={handleRunIntelligencePack}
                  disabled={isRunningIntelligence || !canRunIntelligencePack}
                >
                  {isRunningIntelligence ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Brain className="h-4 w-4 mr-2" />
                  )}
                  Run Full Intelligence Pack
                </Button>
                {!canRunIntelligencePack && (
                  <p className="text-xs text-muted-foreground">
                    Create content or add input first to enable intelligence checks.
                  </p>
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
              {workflowSteps.length > 0 && (
                <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
                  <Label className="text-xs uppercase tracking-wide text-emerald-700">Workflow completed</Label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {workflowSteps.map((step) => (
                      <span key={step} className="text-xs px-2 py-1 rounded-md bg-emerald-500/15 text-emerald-700">
                        {step}
                      </span>
                    ))}
                  </div>
                </div>
              )}

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
              {generatedContent.transcript && (
                <div className="p-4 rounded-xl bg-primary/5 group">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs uppercase tracking-wide text-muted-foreground">Transcript</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity h-8"
                      onClick={() => handleCopy(generatedContent.transcript!, 'transcript')}
                    >
                      {copiedField === 'transcript' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{generatedContent.transcript}</p>
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
                  Start New Draft
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
                    <Link to={`/scheduler?contentId=${savedContentId}`}>
                      Continue to Scheduler
                      <ArrowRight className="h-4 w-4 ml-1" />
                    </Link>
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {intelligenceResult && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Intelligence Pack Results</CardTitle>
              <CardDescription>
                Unified strategic insights from Culture, Risk, Safety, Asset Explosion, Wellbeing, and Shadowban checks.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {intelligenceResult.culture?.rewritten && (
                <div className="p-4 rounded-xl border border-primary/20 bg-primary/5 group">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs uppercase tracking-wide text-muted-foreground">Culture Engine Adaptation</Label>
                    <Button variant="ghost" size="sm" onClick={() => handleCopy(intelligenceResult.culture!.rewritten, 'intel-culture')}>
                      {copiedField === 'intel-culture' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{intelligenceResult.culture.rewritten}</p>
                </div>
              )}

              {intelligenceResult.risk && (
                <div className="p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 group">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-xs uppercase tracking-wide text-muted-foreground">Risk vs Reach Rewrite</Label>
                    <Button variant="ghost" size="sm" onClick={() => handleCopy(intelligenceResult.risk!.generated, 'intel-risk')}>
                      {copiedField === 'intel-risk' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    </Button>
                  </div>
                  <p className="text-sm whitespace-pre-wrap mb-2">{intelligenceResult.risk.generated}</p>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="px-2 py-1 rounded bg-background border">Safety: {intelligenceResult.risk.safety_score}</span>
                    <span className="px-2 py-1 rounded bg-background border">Engagement: {intelligenceResult.risk.estimated_engagement_probability}%</span>
                    <span className="px-2 py-1 rounded bg-background border">Moderation Risk: {intelligenceResult.risk.moderation_risk_percent}%</span>
                  </div>
                </div>
              )}

              <div className="grid sm:grid-cols-2 gap-3">
                {intelligenceResult.cancel && (
                  <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5">
                    <div className="flex items-center gap-2 mb-2">
                      <ShieldCheck className="h-4 w-4 text-red-500" />
                      <Label className="text-xs uppercase tracking-wide text-muted-foreground">Anti-Cancel Shield</Label>
                    </div>
                    <p className="text-sm font-medium mb-1">Risk: {intelligenceResult.cancel.risk_level}</p>
                    {intelligenceResult.cancel.recommendation && (
                      <p className="text-xs text-muted-foreground">{intelligenceResult.cancel.recommendation}</p>
                    )}
                  </div>
                )}

                {intelligenceResult.shadow && (
                  <div className="p-4 rounded-xl border border-orange-500/20 bg-orange-500/5">
                    <div className="flex items-center gap-2 mb-2">
                      <Eye className="h-4 w-4 text-orange-500" />
                      <Label className="text-xs uppercase tracking-wide text-muted-foreground">Shadowban Predictor</Label>
                    </div>
                    <p className="text-sm font-medium mb-1">
                      Probability: {intelligenceResult.shadow.shadowban_probability}% ({intelligenceResult.shadow.risk_level})
                    </p>
                    {intelligenceResult.shadow.recommendation && (
                      <p className="text-xs text-muted-foreground">{intelligenceResult.shadow.recommendation}</p>
                    )}
                  </div>
                )}
              </div>

              {intelligenceResult.assets && (
                <div className="p-4 rounded-xl border border-blue-500/20 bg-blue-500/5">
                  <div className="flex items-center gap-2 mb-2">
                    <Layers className="h-4 w-4 text-blue-500" />
                    <Label className="text-xs uppercase tracking-wide text-muted-foreground">Asset Explosion</Label>
                  </div>
                  <p className="text-sm mb-2">
                    Generated {intelligenceResult.assets.successful_assets} / {intelligenceResult.assets.total_assets} assets
                  </p>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {intelligenceResult.assets.assets.slice(0, 6).map((asset, idx) => (
                      <div key={`${asset.asset_type}-${idx}`} className="p-2 rounded-lg bg-background border">
                        <p className="text-xs font-medium mb-1">{asset.platform}</p>
                        <p className="text-xs text-muted-foreground line-clamp-3">{asset.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {intelligenceResult.mental && (
                <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
                  <div className="flex items-center gap-2 mb-2">
                    <Brain className="h-4 w-4 text-emerald-500" />
                    <Label className="text-xs uppercase tracking-wide text-muted-foreground">Creator Wellbeing Snapshot</Label>
                  </div>
                  <p className="text-sm mb-1">
                    Burnout Score: {intelligenceResult.mental.burnout_score}/100 ({intelligenceResult.mental.burnout_risk})
                  </p>
                  <p className="text-xs text-muted-foreground">{intelligenceResult.mental.recommendations}</p>
                </div>
              )}
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

