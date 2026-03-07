import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ALLOWED_LANGUAGE_CODES } from '@/constants/languages';

type LanguageCode = (typeof ALLOWED_LANGUAGE_CODES)[number];

interface LanguageContextType {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  languageName: string;
  fontClass: string;
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

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<LanguageCode>('en');

  useEffect(() => {
    const savedLang = localStorage.getItem('app-language') as LanguageCode;
    if (savedLang && languageNames[savedLang]) {
      setLanguage(savedLang);
    }
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

  const value = {
    language,
    setLanguage,
    languageName: languageNames[language],
    fontClass: fontClasses[language],
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
