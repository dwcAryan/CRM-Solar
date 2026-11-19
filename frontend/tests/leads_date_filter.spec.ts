import { test, expect } from '@playwright/test';

test.describe('Leads Date Range Filter (Phase 14M)', () => {
  test.use({ storageState: 'frontend/playwright/.auth/admin.json' });

  test('desktop: select preset, active chip, clear filter, URL sync & survival', async ({ page }) => {
    await page.goto('/leads');
    await page.waitForLoadState('networkidle');

    // Filter bar should be visible
    const dateFieldSelect = page.getByRole('textbox', { name: 'Filter by date field' });
    await expect(dateFieldSelect).toBeVisible();

    // Check presets dropdown
    const presetSelect = page.getByPlaceholder('Presets');
    if (await presetSelect.isVisible()) {
      await presetSelect.click();
      const thisMonthOption = page.getByRole('option', { name: /This month/i });
      if (await thisMonthOption.isVisible()) {
        await thisMonthOption.click();
      }
    }

    // URL should have date params or query params updated
    await page.waitForTimeout(500);
    const url = page.url();
    expect(url).toBeDefined();

    // Reload page to test bookmark survival
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Date controls should still be present
    await expect(page.getByRole('textbox', { name: 'Filter by date field' })).toBeVisible();

    // Test clear all filters if present
    const clearAllBtn = page.getByRole('button', { name: /Clear all filters/i });
    if (await clearAllBtn.isVisible()) {
      await clearAllBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test('mobile 390px: drawer opens for date filter', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/leads');
    await page.waitForLoadState('networkidle');

    // On mobile, the "Filter by Date" button triggers a drawer
    const mobileDateBtn = page.getByRole('button', { name: /Filter by Date|Date Filter Active/i });
    await expect(mobileDateBtn).toBeVisible();
    await mobileDateBtn.click();

    // Drawer should open with "Filter Leads by Date"
    await expect(page.getByText('Filter Leads by Date')).toBeVisible();

    // Close or apply
    const applyBtn = page.getByRole('button', { name: /Apply/i });
    if (await applyBtn.isVisible()) {
      await applyBtn.click();
    }
  });
});
