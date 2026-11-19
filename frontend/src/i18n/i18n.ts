import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Base English
import enCommon from '../locales/en/common.json';
import enAuth from '../locales/en/auth.json';
import enLeads from '../locales/en/leads.json';
import enSurveys from '../locales/en/surveys.json';
import enQuotes from '../locales/en/quotes.json';
import enActivities from '../locales/en/activities.json';
import enTour from '../locales/en/tour.json';
import enHelpbot from '../locales/en/helpbot.json';
import enAdmin from '../locales/en/admin.json';
import enErrors from '../locales/en/errors.json';
import enDashboard from '../locales/en/dashboard.json';
import enToday from '../locales/en/today.json';

// Hindi
import hiCommon from '../locales/hi/common.json';
import hiAuth from '../locales/hi/auth.json';
import hiLeads from '../locales/hi/leads.json';
import hiSurveys from '../locales/hi/surveys.json';
import hiQuotes from '../locales/hi/quotes.json';
import hiActivities from '../locales/hi/activities.json';
import hiTour from '../locales/hi/tour.json';
import hiHelpbot from '../locales/hi/helpbot.json';
import hiAdmin from '../locales/hi/admin.json';
import hiErrors from '../locales/hi/errors.json';
import hiDashboard from '../locales/hi/dashboard.json';
import hiToday from '../locales/hi/today.json';

// Regional Variants & Pseudo-locales
import auQuotes from '../locales/en-AU/quotes.json';
import auLeads from '../locales/en-AU/leads.json';
import inLeads from '../locales/en-IN/leads.json';
import xaCommon from '../locales/en-XA/common.json';
import xbCommon from '../locales/ar-XB/common.json';

export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English', nativeName: 'English', dir: 'ltr' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', dir: 'ltr' },
  { code: 'en-AU', name: 'English (AU)', nativeName: 'English (Australia)', dir: 'ltr' },
  { code: 'en-IN', name: 'English (IN)', nativeName: 'English (India)', dir: 'ltr' },
  { code: 'en-XA', name: 'Pseudo English (+40%)', nativeName: '[!!! English-XA !!!]', dir: 'ltr' },
  { code: 'ar-XB', name: 'Pseudo RTL', nativeName: 'عربي (RTL Test)', dir: 'rtl' },
];

export const resources = {
  en: {
    common: enCommon,
    auth: enAuth,
    leads: enLeads,
    surveys: enSurveys,
    quotes: enQuotes,
    activities: enActivities,
    tour: enTour,
    helpbot: enHelpbot,
    admin: enAdmin,
    errors: enErrors,
    dashboard: enDashboard,
    today: enToday,
  },
  hi: {
    common: hiCommon,
    auth: hiAuth,
    leads: hiLeads,
    surveys: hiSurveys,
    quotes: hiQuotes,
    activities: hiActivities,
    tour: hiTour,
    helpbot: hiHelpbot,
    admin: hiAdmin,
    errors: hiErrors,
    dashboard: hiDashboard,
    today: hiToday,
  },
  'en-AU': {
    common: enCommon,
    quotes: { ...enQuotes, ...auQuotes },
    leads: { ...enLeads, ...auLeads },
  },
  'en-IN': {
    common: enCommon,
    leads: { ...enLeads, ...inLeads },
  },
  'en-XA': {
    common: { ...enCommon, ...xaCommon },
  },
  'ar-XB': {
    common: { ...enCommon, ...xbCommon },
  },
};

const detectorOptions = {
  order: ['localStorage', 'navigator'],
  lookupLocalStorage: 'solar_crm_lang',
  caches: ['localStorage'],
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: ['en', 'hi', 'en-AU', 'en-IN', 'en-XA', 'ar-XB'],
    defaultNS: 'common',
    ns: ['common', 'auth', 'leads', 'surveys', 'quotes', 'activities', 'tour', 'helpbot', 'admin', 'errors', 'dashboard', 'today'],
    detection: detectorOptions,
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    react: {
      useSuspense: false,
    },
  });

/**
 * Switch language cleanly across i18n, HTML DOM (lang, dir), and sync with backend profile if authenticated.
 */
export async function changeAppLanguage(langCode: string, syncWithServer = true): Promise<void> {
  const langConfig = SUPPORTED_LANGUAGES.find((l) => l.code === langCode) || SUPPORTED_LANGUAGES[0];

  await i18n.changeLanguage(langCode);

  if (typeof document !== 'undefined') {
    document.documentElement.lang = langCode;
    document.documentElement.dir = langConfig.dir;
  }

  localStorage.setItem('solar_crm_lang', langCode);

  // Dynamically load any backend translation bundle updates (pure data updates)
  try {
    const res = await fetch(`/api/masters/translations/bundle/?lang=${langCode}`);
    if (res.ok) {
      const serverBundle = await res.json();
      for (const [ns, keys] of Object.entries(serverBundle)) {
        i18n.addResourceBundle(langCode, ns, keys, true, true);
      }
    }
  } catch {
    // Fallback gracefully to bundled assets if offline or API unavailable
  }

  // If user is authenticated, sync preferred language to server profile
  if (syncWithServer) {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        await fetch('/api/me/', {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ preferred_language: langCode }),
        });
      } catch {
        // Safe ignore
      }
    }
  }
}

// Initial sync of document attributes
if (typeof document !== 'undefined') {
  const currentLang = i18n.language || 'en';
  const cfg = SUPPORTED_LANGUAGES.find((l) => l.code === currentLang) || SUPPORTED_LANGUAGES[0];
  document.documentElement.lang = currentLang;
  document.documentElement.dir = cfg.dir;
}

export default i18n;
