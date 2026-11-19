import { test, expect } from '@playwright/test';

test.describe('PDF Downloads Verification (Phase 14M)', () => {
  test.use({ storageState: 'frontend/playwright/.auth/admin.json' });

  test('quotes page: download quote PDF via downloadPdfBlob', async ({ page }) => {
    await page.goto('/quotes');
    await page.waitForLoadState('networkidle');

    // Find the first PDF button in the quotes table
    const pdfButtons = page.locator('button', { hasText: 'PDF' });
    const count = await pdfButtons.count();

    if (count > 0) {
      // Set up download listener
      const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
      await pdfButtons.first().click();
      const download = await downloadPromise;

      expect(download.suggestedFilename()).toMatch(/quote_.*\.pdf/);
      const path = await download.path();
      expect(path).toBeDefined();
    }
  });

  test('lead detail page: download DSAR privacy dossier PDF', async ({ page }) => {
    await page.goto('/leads');
    await page.waitForLoadState('networkidle');

    // Click first lead
    const firstLead = page.locator('table tbody tr td').first();
    if (await firstLead.isVisible()) {
      await firstLead.click();
      await page.waitForLoadState('networkidle');

      // Check if DSAR Dossier (PDF) button exists
      const dsarBtn = page.getByRole('button', { name: /DSAR Dossier/i });
      if (await dsarBtn.isVisible()) {
        const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
        await dsarBtn.click();
        const download = await downloadPromise;

        expect(download.suggestedFilename()).toMatch(/privacy_dossier_.*\.pdf/);
        const path = await download.path();
        expect(path).toBeDefined();
      }
    }
  });
});
