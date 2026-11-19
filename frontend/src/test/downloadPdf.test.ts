import { describe, it, expect } from 'vitest'

describe('PDF Download Utility Helpers', () => {
  it('parses RFC 5987 content-disposition header accurately', () => {
    const header = "attachment; filename*=UTF-8''Quote_Q-2026-0001_%E0%A4%B0%E0%A4%BE%E0%A4%AE.pdf"
    let extracted = 'download.pdf'
    if (header.includes("filename*=UTF-8''")) {
      const parts = header.split("filename*=UTF-8''")
      if (parts[1]) {
        extracted = decodeURIComponent(parts[1].split(';')[0].trim())
      }
    }
    expect(extracted).toBe('Quote_Q-2026-0001_राम.pdf')
  })

  it('falls back to standard filename when UTF-8 variant is absent', () => {
    const header = 'attachment; filename="privacy_export.pdf"'
    let extracted = 'download.pdf'
    const match = header.match(/filename="?([^";]+)"?/)
    if (match && match[1]) {
      extracted = match[1]
    }
    expect(extracted).toBe('privacy_export.pdf')
  })
})
