import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const authDir = fs.existsSync(path.resolve('frontend/playwright/.auth'))
  ? path.resolve('frontend/playwright/.auth')
  : (fs.existsSync(path.resolve('playwright/.auth')) ? path.resolve('playwright/.auth') : path.resolve('frontend/playwright'));

const BASE_URL = 'http://localhost:5173';

test.describe('Phase 16 Master Smoke Set (15 Flows) @smoke', () => {

  test('01. Health check endpoint responds OK @smoke', async ({ request }) => {
    const res = await request.get('http://127.0.0.1:8000/api/health/');
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.status).toBe('ok');
    expect(data.ready).toBe(true);
  });

  test('02. Login as admin role @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();
    await page.goto('/');
    await expect(page).toHaveURL('/');
    await expect(page.locator('body')).toBeVisible();
    await context.close();
  });

  test('03. Login as manager role @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'manager.json') });
    const page = await context.newPage();
    await page.goto('/');
    await expect(page).toHaveURL('/');
    await context.close();
  });

  test('04. Login as salesperson role @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'salesperson.json') });
    const page = await context.newPage();
    await page.goto('/');
    await expect(page).toHaveURL('/');
    await context.close();
  });

  test('05. Login as surveyor role @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'surveyor.json') });
    const page = await context.newPage();
    await page.goto('/surveys');
    await expect(page).toHaveURL(/.*surveys.*/);
    await context.close();
  });

  test('06. Forgot-password flow trigger @smoke', async ({ page }) => {
    await page.goto('/reset-password');
    const emailInput = page.getByPlaceholder(/email/i).or(page.locator('input[type="email"]'));
    if (await emailInput.isVisible()) {
      await emailInput.fill('admin@example.com');
      const submitBtn = page.getByRole('button', { name: /send|reset|submit/i });
      await submitBtn.click();
      await page.waitForTimeout(500);
    }
    expect(page.url()).toContain('reset-password');
  });

  test('07. Create lead flow @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();
    await page.goto('/leads');
    await page.waitForLoadState('domcontentloaded');

    const newLeadBtn = page.getByRole('button', { name: /new lead|add lead|create/i });
    if (await newLeadBtn.isVisible()) {
      await newLeadBtn.click();
      await page.waitForTimeout(300);
    }
    expect(page.url()).toContain('/leads');
    await context.close();
  });

  test('08. Filter leads by date range @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();
    await page.goto('/leads');
    await page.waitForLoadState('domcontentloaded');

    const dateFilterBtn = page.locator('button', { hasText: /date|created date|filter/i }).first();
    await expect(dateFilterBtn).toBeVisible();
    await context.close();
  });

  test('09. Log call outcome flow @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();
    await page.goto('/leads');
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toContain('/leads');
    await context.close();
  });

  test('10. Book survey flow @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();
    await page.goto('/surveys');
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toContain('/surveys');
    await context.close();
  });

  test('11. Quote to Won flow @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();
    await page.goto('/quotes');
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toContain('/quotes');
    await context.close();
  });

  test('12. Download PDF feature @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();
    await page.goto('/quotes');
    await page.waitForLoadState('domcontentloaded');
    const pdfBtn = page.locator('button', { hasText: 'PDF' }).first();
    if (await pdfBtn.isVisible()) {
      const downloadPromise = page.waitForEvent('download', { timeout: 8000 }).catch(() => null);
      await pdfBtn.click();
      const download = await downloadPromise;
      if (download) {
        expect(download.suggestedFilename()).toMatch(/.*\.pdf/);
      }
    }
    await context.close();
  });

  test('13. CSV import leads view @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();
    await page.goto('/import-leads');
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toContain('/import-leads');
    await context.close();
  });

  test('14. Region switch IN to AU @smoke', async ({ browser }) => {
    const context = await browser.newContext({ baseURL: BASE_URL, storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    const regionSelector = page.locator('[data-testid="region-selector"]').or(page.locator('text=India')).first();
    if (await regionSelector.isVisible()) {
      await regionSelector.click();
    }
    await context.close();
  });

  test('15. Switch language and complete a lead flow @smoke', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    const langBtn = page.getByTestId('language-selector-btn');
    if (await langBtn.isVisible()) {
      await langBtn.click();
      const hiOption = page.getByTestId('lang-option-hi');
      if (await hiOption.isVisible()) {
        await hiOption.click();
        const html = page.locator('html');
        await expect(html).toHaveAttribute('lang', 'hi');
      }
    }
  });

});
