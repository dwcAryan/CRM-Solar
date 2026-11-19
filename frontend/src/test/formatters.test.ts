import { describe, it, expect } from 'vitest'
import {
  formatDate,
  formatCurrency,
  formatNumber,
  formatRelativeTime,
} from '../i18n/formatters'

describe('I18n Formatters', () => {
  it('formats dates across english and hindi locales', () => {
    const date = new Date('2026-11-19T10:00:00Z')
    const formattedEn = formatDate(date, 'en')
    expect(formattedEn).toContain('2026')
    expect(formattedEn).toMatch(/Nov|19/)

    const formattedHi = formatDate(date, 'hi')
    expect(formattedHi).toContain('2026')
  })

  it('formats currency correctly for INR and AUD', () => {
    const inr = formatCurrency(50000, 'INR', 'en-IN')
    expect(inr).toContain('50,000')

    const aud = formatCurrency(12500, 'AUD', 'en-AU')
    expect(aud).toContain('12,500')
  })

  it('formats numbers with locale grouping', () => {
    const numEn = formatNumber(1000000, 'en')
    expect(numEn).toContain('1,000,000')
  })

  it('formats relative time', () => {
    const past = new Date(Date.now() - 3600 * 1000)
    const rel = formatRelativeTime(past, 'en')
    expect(rel).toMatch(/hour|1h|ago/)
  })

  it('handles invalid inputs gracefully without throwing', () => {
    expect(formatDate(null)).toBe('')
    expect(formatDate(undefined)).toBe('')
    expect(formatDate('invalid-date')).toBe('')
    expect(formatCurrency(NaN, 'INR', 'en')).toBe('-')
  })
})
