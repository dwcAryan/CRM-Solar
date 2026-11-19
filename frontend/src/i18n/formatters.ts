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
