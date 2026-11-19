/**
 * Internationalization formatting utilities for Solar CRM.
 * Provides locale-aware date, time, number, relative-time, and currency formatting.
 */

export interface FormatOptions {
  locale?: string;
}

/**
 * Format date in locale-aware format (e.g. "19 Nov 2026" or "19 नवं 2026")
 */
export function formatDate(
  dateInput: string | number | Date | null | undefined,
  locale = 'en',
  options?: Intl.DateTimeFormatOptions
): string {
  if (!dateInput) return '';
  const date = typeof dateInput === 'string' || typeof dateInput === 'number' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return '';

  const defaultOptions: Intl.DateTimeFormatOptions = {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...options,
  };

  try {
    return new Intl.DateTimeFormat(locale, defaultOptions).format(date);
  } catch {
    return new Intl.DateTimeFormat('en', defaultOptions).format(date);
  }
}

/**
 * Format datetime in locale-aware format with time
 */
export function formatDateTime(
  dateInput: string | number | Date | null | undefined,
  locale = 'en',
  timeZone?: string
): string {
  if (!dateInput) return '';
  const date = typeof dateInput === 'string' || typeof dateInput === 'number' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return '';

  const options: Intl.DateTimeFormatOptions = {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  };
  if (timeZone) {
    options.timeZone = timeZone;
  }

  try {
    return new Intl.DateTimeFormat(locale, options).format(date);
  } catch {
    return new Intl.DateTimeFormat('en', options).format(date);
  }
}

/**
 * Format relative time (e.g., "5 minutes ago", "in 2 hours", "5 मिनट पहले")
 */
export function formatRelativeTime(
  dateInput: string | number | Date | null | undefined,
  locale = 'en'
): string {
  if (!dateInput) return '';
  const date = typeof dateInput === 'string' || typeof dateInput === 'number' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return '';

  const now = Date.now();
  const diffInSeconds = Math.round((date.getTime() - now) / 1000);

  const units: { unit: Intl.RelativeTimeFormatUnit; seconds: number }[] = [
    { unit: 'year', seconds: 31536000 },
    { unit: 'month', seconds: 2592000 },
    { unit: 'day', seconds: 86400 },
    { unit: 'hour', seconds: 3600 },
    { unit: 'minute', seconds: 60 },
    { unit: 'second', seconds: 1 },
  ];

  try {
    const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
    for (const { unit, seconds } of units) {
      if (Math.abs(diffInSeconds) >= seconds || unit === 'second') {
        const val = Math.round(diffInSeconds / seconds);
        return rtf.format(val, unit);
      }
    }
  } catch {
    // Fallback simple English
    const minutes = Math.round(Math.abs(diffInSeconds) / 60);
    return diffInSeconds < 0 ? `${minutes}m ago` : `in ${minutes}m`;
  }
  return '';
}

/**
 * Format numbers with locale grouping (e.g., Indian lakh grouping 1,00,000 vs standard 100,000)
 */
export function formatNumber(
  num: number | null | undefined,
  locale = 'en',
  options?: Intl.NumberFormatOptions
): string {
  if (num === null || num === undefined || isNaN(num)) return '0';
  try {
    return new Intl.NumberFormat(locale, options).format(num);
  } catch {
    return new Intl.NumberFormat('en', options).format(num);
  }
}

/**
 * Format currency with locale and currency code (INR -> ₹, AUD -> $)
 * Uses Indian number system grouping for INR / en-IN / hi
 */
export function formatCurrency(
  amount: number | null | undefined,
  currencyCode = 'INR',
  locale = 'en'
): string {
  if (amount === null || amount === undefined || isNaN(amount)) return '-';

  // For INR in Indian or Hindi context, use en-IN / hi-IN grouping
  let effectiveLocale = locale;
  if (currencyCode === 'INR') {
    effectiveLocale = locale.startsWith('hi') ? 'hi-IN' : 'en-IN';
  } else if (currencyCode === 'AUD') {
    effectiveLocale = 'en-AU';
  }

  try {
    return new Intl.NumberFormat(effectiveLocale, {
      style: 'currency',
      currency: currencyCode,
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    }).format(amount);
  } catch {
    const symbol = currencyCode === 'INR' ? '₹' : '$';
    return `${symbol}${amount.toLocaleString()}`;
  }
}

/**
 * Maps system status codes to localized display names
 */
const STATUS_TRANSLATIONS_HI: Record<string, string> = {
  'New': 'नई (New)',
  'new': 'नई (New)',
  'Attempting contact': 'संपर्क प्रयास',
  'attempting contact': 'संपर्क प्रयास',
  'Callback scheduled': 'कॉल-बैक निर्धारित',
  'callback scheduled': 'कॉल-बैक निर्धारित',
  'Invalid contact': 'अमान्य संपर्क',
  'invalid contact': 'अमान्य संपर्क',
  'Follow-up': 'फ़ॉलो-अप',
  'follow-up': 'फ़ॉलो-अप',
  'Interested': 'रुचि व्यक्त की',
  'interested': 'रुचि व्यक्त की',
  'Survey to schedule': 'सर्वेक्षण निर्धारित करना है',
  'survey to schedule': 'सर्वेक्षण निर्धारित करना है',
  'Survey scheduled': 'सर्वेक्षण निर्धारित',
  'survey scheduled': 'सर्वेक्षण निर्धारित',
  'Survey rescheduled': 'सर्वेक्षण पुनर्निर्धारित',
  'survey rescheduled': 'सर्वेक्षण पुनर्निर्धारित',
  'Survey missed': 'सर्वेक्षण छूटा',
  'survey missed': 'सर्वेक्षण छूटा',
  'Design pending': 'डिजाइन लंबित',
  'design pending': 'डिजाइन लंबित',
  'Alternative': 'वैकल्पिक समाधान',
  'alternative': 'वैकल्पिक समाधान',
  'Quote sent': 'कोटेशन भेजा गया',
  'quote sent': 'कोटेशन भेजा गया',
  'Revising quote': 'कोटेशन संशोधन',
  'revising quote': 'कोटेशन संशोधन',
  'Negotiation': 'बातचीत जारी',
  'negotiation': 'बातचीत जारी',
  'Won': 'सफल सौदा (Won)',
  'won': 'सफल सौदा (Won)',
  'Lost': 'विफल (Lost)',
  'lost': 'विफल (Lost)',
  'Nurture': 'नर्चर (Nurture)',
  'nurture': 'नर्चर (Nurture)',
  'Unreachable': 'संपर्क रहित',
  'unreachable': 'संपर्क रहित',
  'Do not contact': 'संपर्क न करें (DNC)',
  'do not contact': 'संपर्क न करें (DNC)',
  'Merged': 'मर्ज किया गया',
  'merged': 'मर्ज किया गया',
  'Lost approval pending': 'विफलता स्वीकृति लंबित',
  'lost approval pending': 'विफलता स्वीकृति लंबित',
  'booked': 'बुक किया गया (Booked)',
  'Booked': 'बुक किया गया (Booked)',
  'done': 'पूर्ण (Done)',
  'Done': 'पूर्ण (Done)',
  'rescheduled': 'पुनर्निर्धारित (Rescheduled)',
  'Rescheduled': 'पुनर्निर्धारित (Rescheduled)',
  'missed': 'छूटा हुआ (Missed)',
  'Missed': 'छूटा हुआ (Missed)',
  'cancelled': 'रद्द (Cancelled)',
  'Cancelled': 'रद्द (Cancelled)',
  'draft': 'प्रारूप (Draft)',
  'Draft': 'प्रारूप (Draft)',
  'sent': 'भेजा गया (Sent)',
  'Sent': 'भेजा गया (Sent)',
  'accepted': 'स्वीकृत (Accepted)',
  'Accepted': 'स्वीकृत (Accepted)',
  'rejected': 'अस्वीकृत (Rejected)',
  'Rejected': 'अस्वीकृत (Rejected)',
  'revised': 'संशोधित (Revised)',
  'Revised': 'संशोधित (Revised)',
};

export function translateStatus(status: string | null | undefined, locale?: string): string {
  if (!status) return '';
  const lang = locale || (typeof localStorage !== 'undefined' ? localStorage.getItem('solar_crm_lang') || 'en' : 'en');
  if (lang.startsWith('hi')) {
    return STATUS_TRANSLATIONS_HI[status] || STATUS_TRANSLATIONS_HI[status.toLowerCase()] || status;
  }
  return status;
}

const ROLE_TRANSLATIONS_HI: Record<string, string> = {
  admin: 'व्यवस्थापक (Admin)',
  manager: 'प्रबंधक (Manager)',
  salesperson: 'विक्रेता (Sales)',
  surveyor: 'सर्वेक्षक (Surveyor)',
};

export function translateRole(role: string | null | undefined, locale?: string): string {
  if (!role) return '';
  const lang = locale || (typeof localStorage !== 'undefined' ? localStorage.getItem('solar_crm_lang') || 'en' : 'en');
  if (lang.startsWith('hi')) {
    return ROLE_TRANSLATIONS_HI[role.toLowerCase()] || role;
  }
  return role.charAt(0).toUpperCase() + role.slice(1);
}

const STAGE_TRANSLATIONS_HI: Record<string, string> = {
  call: 'कॉल (Call)',
  survey: 'साइट सर्वे (Survey)',
  quote: 'कोटेशन (Quote)',
};

export function translateStage(stage: string | null | undefined, locale?: string): string {
  if (!stage) return '';
  const lang = locale || (typeof localStorage !== 'undefined' ? localStorage.getItem('solar_crm_lang') || 'en' : 'en');
  if (lang.startsWith('hi')) {
    return STAGE_TRANSLATIONS_HI[stage.toLowerCase()] || stage;
  }
  return stage.charAt(0).toUpperCase() + stage.slice(1);
}

const ROOF_TRANSLATIONS_HI: Record<string, string> = {
  'rcc': 'आरसीसी समतल छत (RCC Flat)',
  'rcc flat': 'आरसीसी समतल छत (RCC Flat)',
  'metal sheet': 'धातु की चादर (Metal Sheet)',
  'tin shade': 'टिन शेड (Tin Shade)',
  'tiled': 'टाइल वाली छत (Tiled)',
  'pitched': 'ढलान वाली छत (Pitched)',
  'colorbond': 'कलरबॉन्ड धातु (Colorbond)',
  'asbestos': 'एस्बेस्टस शीट',
  'other': 'अन्य प्रकार की छत',
};

export function translateRoofType(roof: string | null | undefined, locale?: string): string {
  if (!roof) return '';
  const lang = locale || (typeof localStorage !== 'undefined' ? localStorage.getItem('solar_crm_lang') || 'en' : 'en');
  if (lang.startsWith('hi')) {
    return ROOF_TRANSLATIONS_HI[roof.toLowerCase()] || roof;
  }
  return roof;
}

const PROPERTY_TRANSLATIONS_HI: Record<string, string> = {
  'residential': 'आवासीय (Residential)',
  'commercial': 'व्यावसायिक (Commercial)',
  'industrial': 'औद्योगिक (Industrial)',
  'agricultural': 'कृषि संबंधी (Agricultural)',
  'other': 'अन्य',
};

export function translatePropertyType(prop: string | null | undefined, locale?: string): string {
  if (!prop) return '';
  const lang = locale || (typeof localStorage !== 'undefined' ? localStorage.getItem('solar_crm_lang') || 'en' : 'en');
  if (lang.startsWith('hi')) {
    return PROPERTY_TRANSLATIONS_HI[prop.toLowerCase()] || prop;
  }
  return prop;
}

const SOURCE_TRANSLATIONS_HI: Record<string, string> = {
  'website form': 'वेबसाइट फॉर्म',
  'meta ads': 'मेटा (फेसबुक/इंस्टा) विज्ञापन',
  'google ads': 'गूगल विज्ञापन',
  'referral': 'रेफरल (सिफारिश)',
  'walk-in': 'सीधे संपर्क (Walk-in)',
  'other': 'अन्य स्रोत',
};

export function translateLeadSource(source: string | null | undefined, locale?: string): string {
  if (!source) return '';
  const lang = locale || (typeof localStorage !== 'undefined' ? localStorage.getItem('solar_crm_lang') || 'en' : 'en');
  if (lang.startsWith('hi')) {
    return SOURCE_TRANSLATIONS_HI[source.toLowerCase()] || source;
  }
  return source;
}

