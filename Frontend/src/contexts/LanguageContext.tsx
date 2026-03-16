import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ALLOWED_LANGUAGE_CODES } from '@/constants/languages';
import { translationAPI } from '@/services/api';

type LanguageCode = (typeof ALLOWED_LANGUAGE_CODES)[number];

interface LanguageContextType {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  autoTranslateUI: boolean;
  setAutoTranslateUI: (enabled: boolean) => void;
  languageName: string;
  fontClass: string;
  t: (key: string, fallback?: string) => string;
}

const languageNames: Record<LanguageCode, string> = {
  en: 'English',
  te: 'తెలుగు',
  or: 'ଓଡ଼ିଆ',
  ta: 'தமிழ்',
  bn: 'বাংলা',
  kn: 'ಕನ್ನಡ',
  hi: 'हिंदी',
  ml: 'മലയാളം',
  gu: 'ગુજરાતી',
};

const fontClasses: Record<LanguageCode, string> = {
  en: 'font-english',
  te: 'font-telugu',
  or: 'font-odia',
  ta: 'font-tamil',
  bn: 'font-bangla',
  kn: 'font-kannada',
  hi: 'font-hindi',
  ml: 'font-malayalam',
  gu: 'font-gujarati',
};

const translations: Record<LanguageCode, Record<string, string>> = {
  en: {},
  hi: {
    'nav.creatorStudio': 'क्रिएटर स्टूडियो',
    'nav.intelligenceHub': '⚡ इंटेलिजेंस हब',
    'nav.novelLab': '🚀 नोवेल एआई लैब',
    'nav.competitorIntel': 'प्रतिद्वंदी इंटेल',
    'nav.contentCalendar': 'कंटेंट कैलेंडर',
    'nav.moderation': 'मॉडरेशन',
    'nav.schedule': 'शेड्यूल',
    'nav.settings': 'सेटिंग्स',
    'nav.logout': 'लॉगआउट',
    'nav.dashboard': 'डैशबोर्ड',
    'settings.title': 'सेटिंग्स',
    'settings.subtitle': 'अपने खाते और रूप-रंग को प्रबंधित करें।',
    'settings.tabs.profile': 'प्रोफ़ाइल',
    'settings.tabs.appearance': 'रूप-रंग',
    'settings.tabs.account': 'खाता',
    'settings.interfaceLanguage': 'इंटरफ़ेस भाषा',
    'settings.selectLanguage': 'भाषा चुनें',
    'settings.saveProfile': 'प्रोफ़ाइल सहेजें',
    'settings.personalInfo': 'व्यक्तिगत जानकारी',
    'settings.updateAccount': 'अपने खाते का विवरण अपडेट करें',
    'settings.fullName': 'पूरा नाम',
    'settings.emailAddress': 'ईमेल पता',
  },
  te: {
    'nav.creatorStudio': 'క్రియేటర్ స్టూడియో',
    'nav.intelligenceHub': '⚡ ఇంటెలిజెన్స్ హబ్',
    'nav.novelLab': '🚀 నవల్ AI ల్యాబ్',
    'nav.settings': 'సెట్టింగ్స్',
    'nav.logout': 'లాగ్ అవుట్',
    'settings.title': 'సెట్టింగ్స్',
    'settings.interfaceLanguage': 'ఇంటర్‌ఫేస్ భాష',
    'settings.saveProfile': 'ప్రొఫైల్ సేవ్ చేయండి',
  },
  or: {},
  ta: {
    'nav.creatorStudio': 'கிரியேட்டர் ஸ்டுடியோ',
    'nav.intelligenceHub': '⚡ இண்டலிஜென்ஸ் ஹப்',
    'nav.novelLab': '🚀 நோவல் AI லேப்',
    'nav.settings': 'அமைப்புகள்',
    'nav.logout': 'வெளியேறு',
    'settings.title': 'அமைப்புகள்',
    'settings.interfaceLanguage': 'இடைமுக மொழி',
    'settings.saveProfile': 'சுயவிவரத்தை சேமி',
  },
  bn: {},
  kn: {},
  ml: {},
  gu: {},
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);
const originalTextNodes = new Map<Text, string>();
const translatedCache = new Map<string, string>();
const originalElementAttributes = new Map<Element, Map<string, string>>();
const failedTranslationAttempts = new Map<string, number>();
const TRANSLATION_CACHE_KEY = 'ui-translation-cache-v1';
const MAX_TRANSLATION_CACHE_ENTRIES = 800;
const MAX_TRANSLATION_RETRIES = 3;
const RETRY_SCAN_DELAY_MS = 1200;
const TRANSLATABLE_ATTRIBUTES = ['placeholder', 'title', 'aria-label'] as const;

const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'INPUT', 'CODE', 'PRE']);

function shouldTranslateNode(node: Text): boolean {
  const parent = node.parentElement;
  if (!parent) return false;
  if (SKIP_TAGS.has(parent.tagName)) return false;
  if (parent.closest('[data-no-auto-translate="true"]')) return false;
  if (parent.closest('[contenteditable="true"]')) return false;

  const text = (node.nodeValue || '').trim();
  if (!text) return false;
  if (text.length > 180) return false; // avoid translating large generated content blocks
  if (!/[A-Za-z]/.test(text)) return false; // likely already non-English or numeric
  return true;
}

function collectTextNodes(root: ParentNode): Text[] {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  let current = walker.nextNode();
  while (current) {
    const textNode = current as Text;
    if (shouldTranslateNode(textNode)) nodes.push(textNode);
    current = walker.nextNode();
  }
  return nodes;
}

type AttributeTarget = {
  element: Element;
  attr: (typeof TRANSLATABLE_ATTRIBUTES)[number];
  original: string;
};

function getElementRoot(root: ParentNode): Element | null {
  if (root instanceof Document) {
    return root.body;
  }
  if (root instanceof Element) {
    return root;
  }
  return null;
}

function collectAttributeTargets(root: ParentNode): AttributeTarget[] {
  const rootEl = getElementRoot(root);
  if (!rootEl) return [];

  const targets: AttributeTarget[] = [];
  const elements = [rootEl, ...Array.from(rootEl.querySelectorAll('*'))];
  elements.forEach((element) => {
    if (SKIP_TAGS.has(element.tagName)) return;
    if (element.closest('[data-no-auto-translate="true"]')) return;

    TRANSLATABLE_ATTRIBUTES.forEach((attr) => {
      const value = (element.getAttribute(attr) || '').trim();
      if (!value) return;
      if (value.length > 180) return;
      if (!/[A-Za-z]/.test(value)) return;
      targets.push({ element, attr, original: value });
    });
  });
  return targets;
}

function hydrateTranslationCache() {
  try {
    const raw = localStorage.getItem(TRANSLATION_CACHE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as Record<string, string>;
    Object.entries(parsed).forEach(([key, value]) => {
      if (typeof key === 'string' && typeof value === 'string') {
        translatedCache.set(key, value);
      }
    });
  } catch {
    // Ignore corrupted cache payloads.
  }
}

function persistTranslationCache() {
  try {
    // Keep cache bounded so localStorage usage stays reasonable.
    while (translatedCache.size > MAX_TRANSLATION_CACHE_ENTRIES) {
      const oldestKey = translatedCache.keys().next().value as string | undefined;
      if (!oldestKey) break;
      translatedCache.delete(oldestKey);
    }
    const payload = Object.fromEntries(translatedCache.entries());
    localStorage.setItem(TRANSLATION_CACHE_KEY, JSON.stringify(payload));
  } catch {
    // Ignore quota/storage errors silently.
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<LanguageCode>('en');
  const [autoTranslateUI, setAutoTranslateUI] = useState<boolean>(() => localStorage.getItem('auto-translate-ui') === 'true');

  useEffect(() => {
    const savedLang = localStorage.getItem('app-language') as LanguageCode;
    if (savedLang && languageNames[savedLang]) {
      setLanguage(savedLang);
    }
    hydrateTranslationCache();
  }, []);

  useEffect(() => {
    localStorage.setItem('app-language', language);
    const htmlEl = document.documentElement;
    const existingLangClasses = Array.from(htmlEl.classList).filter((cls) => cls.startsWith('lang-'));
    if (existingLangClasses.length > 0) {
      htmlEl.classList.remove(...existingLangClasses);
    }
    htmlEl.classList.add(`lang-${language}`);
    htmlEl.setAttribute('lang', language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem('auto-translate-ui', String(autoTranslateUI));
  }, [autoTranslateUI]);

  useEffect(() => {
    let observer: MutationObserver | null = null;
    let cancelled = false;
    let retryTimer: number | null = null;
    let periodicScanTimer: number | null = null;

    const restoreOriginalText = () => {
      originalTextNodes.forEach((original, node) => {
        if (node.isConnected) {
          node.nodeValue = original;
        }
      });

      originalElementAttributes.forEach((attrMap, element) => {
        if (!element.isConnected) return;
        attrMap.forEach((value, attr) => {
          element.setAttribute(attr, value);
        });
      });
    };

    const translateVisibleUI = async (root: ParentNode = document.body) => {
      if (!autoTranslateUI || language === 'en' || cancelled) return;

      const nodes = collectTextNodes(root);
      const attributeTargets = collectAttributeTargets(root);
      if (!nodes.length && !attributeTargets.length) return;

      const originals: string[] = [];
      nodes.forEach((node) => {
        if (!originalTextNodes.has(node)) {
          originalTextNodes.set(node, node.nodeValue || '');
        }
        const original = (originalTextNodes.get(node) || '').trim();
        if (original) originals.push(original);
      });
      attributeTargets.forEach(({ element, attr, original }) => {
        let attrMap = originalElementAttributes.get(element);
        if (!attrMap) {
          attrMap = new Map<string, string>();
          originalElementAttributes.set(element, attrMap);
        }
        if (!attrMap.has(attr)) {
          attrMap.set(attr, original);
        }
        originals.push(original);
      });

      const uniqueOriginals = Array.from(new Set(originals));
      let cacheUpdated = false;
      let pendingRetry = false;
      for (const original of uniqueOriginals) {
        const cacheKey = `${language}::${original}`;
        const cached = translatedCache.get(cacheKey);
        const shouldRetryStaleEnglish = cached === original && language !== 'en';
        if (!cached || shouldRetryStaleEnglish) {
          const attempts = failedTranslationAttempts.get(cacheKey) || 0;
          if (attempts >= MAX_TRANSLATION_RETRIES) {
            continue;
          }
          try {
            const translated = await translationAPI.translate(original, language, 'en');
            translatedCache.set(cacheKey, translated.translated_text || original);
            failedTranslationAttempts.delete(cacheKey);
            cacheUpdated = true;
          } catch {
            failedTranslationAttempts.set(cacheKey, attempts + 1);
            pendingRetry = true;
            // Don't cache failures as English text; retry on next pass.
          }
        }
      }
      if (cacheUpdated) {
        persistTranslationCache();
      }

      if (cancelled) return;
      nodes.forEach((node) => {
        const original = (originalTextNodes.get(node) || '').trim();
        if (!original) return;
        const translated = translatedCache.get(`${language}::${original}`) || original;
        node.nodeValue = translated;
      });

      attributeTargets.forEach(({ element, attr, original }) => {
        const translated = translatedCache.get(`${language}::${original}`);
        element.setAttribute(attr, translated || original);
      });

      // Re-scan shortly when transient failures happen, so UI doesn't stay half translated.
      if (pendingRetry && !cancelled) {
        if (retryTimer !== null) {
          window.clearTimeout(retryTimer);
        }
        retryTimer = window.setTimeout(() => {
          void translateVisibleUI(document.body);
        }, RETRY_SCAN_DELAY_MS);
      }
    };

    if (!autoTranslateUI || language === 'en') {
      restoreOriginalText();
      return () => {};
    }

    translateVisibleUI(document.body);
    periodicScanTimer = window.setInterval(() => {
      void translateVisibleUI(document.body);
    }, 5000);

    observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'characterData' && mutation.target.nodeType === Node.TEXT_NODE) {
          translateVisibleUI(document.body);
          continue;
        }

        if (
          mutation.type === 'attributes' &&
          mutation.target.nodeType === Node.ELEMENT_NODE &&
          TRANSLATABLE_ATTRIBUTES.includes(mutation.attributeName as (typeof TRANSLATABLE_ATTRIBUTES)[number])
        ) {
          translateVisibleUI(mutation.target as ParentNode);
          continue;
        }

        mutation.addedNodes.forEach((added) => {
          if (added.nodeType === Node.TEXT_NODE && shouldTranslateNode(added as Text)) {
            translateVisibleUI(document.body);
          } else if (added.nodeType === Node.ELEMENT_NODE) {
            translateVisibleUI(added as ParentNode);
          }
        });
      }
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: [...TRANSLATABLE_ATTRIBUTES],
    });

    return () => {
      cancelled = true;
      if (retryTimer !== null) {
        window.clearTimeout(retryTimer);
      }
      if (periodicScanTimer !== null) {
        window.clearInterval(periodicScanTimer);
      }
      observer?.disconnect();
      observer = null;
    };
  }, [language, autoTranslateUI]);

  const value = {
    language,
    setLanguage,
    autoTranslateUI,
    setAutoTranslateUI,
    languageName: languageNames[language],
    fontClass: fontClasses[language],
    t: (key: string, fallback?: string) =>
      translations[language]?.[key] || fallback || key,
  };

  return (
    <LanguageContext.Provider value={value}>
      <div className={fontClasses[language]}>
        {children}
      </div>
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}

export const languages: { code: LanguageCode; name: string }[] = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'हिंदी' },
  { code: 'te', name: 'తెలుగు' },
  { code: 'ta', name: 'தமிழ்' },
  { code: 'bn', name: 'বাংলা' },
  { code: 'kn', name: 'ಕನ್ನಡ' },
  { code: 'ml', name: 'മലയാളം' },
  { code: 'gu', name: 'ગુજરાતી' },
  { code: 'or', name: 'ଓଡ଼ିଆ' },
];
