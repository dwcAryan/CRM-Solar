import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const authDir = fs.existsSync(path.resolve('frontend/playwright/.auth'))
  ? path.resolve('frontend/playwright/.auth')
  : path.resolve('playwright/.auth');

test.describe('Helpbot Assistant & Insights @smoke', () => {
  test('Helpbot chat interactions, scope refusal, and feedback', async ({ browser }) => {
    const context = await browser.newContext({
      storageState: path.join(authDir, 'salesperson.json'),
    });
    const page = await context.newPage();

    await page.goto('/');
    await expect(page).toHaveURL('/');

    // 1. Verify FAB is visible and click to open
    const fab = page.locator('[data-tour="helpbot-fab"]');
    await expect(fab).toBeVisible();
    await fab.click();

    // 2. Chat modal should open with title and PII disclaimer
    await expect(page.locator('text=Solar CRM Help Assistant').first()).toBeVisible();
    await expect(page.locator('text=Specialized in Solar CRM features only')).toBeVisible();

    // 3. Ask an in-scope question
    const input = page.locator('input[placeholder*="Ask about call outcomes"]');
    await expect(input).toBeVisible();
    await input.fill('What is the CRM golden rule?');
    await page.locator('button[aria-label="Help Assistant"]').or(page.locator('button:has(.tabler-icon-send)')).last().click();

    // 4. Verify assistant response appears
    await expect(page.locator('text=Every customer interaction MUST be logged')).toBeVisible({ timeout: 10000 });

    // 5. Ask an out-of-scope question and verify refusal
    await input.fill('Tell me a funny joke');
    await page.locator('button:has(.tabler-icon-send)').last().click();
    await expect(page.locator('text=I am the Solar CRM Help Assistant. I can only answer questions about using this CRM')).toBeVisible({
      timeout: 10000,
    });

    // 6. Close modal using Escape
    await page.keyboard.press('Escape');

    await context.close();
  });

  test('Admin Help Assistant Insights Tab', async ({ browser }) => {
    const context = await browser.newContext({
      storageState: path.join(authDir, 'admin.json'),
    });
    const page = await context.newPage();

    await page.goto('/admin');
    await expect(page).toHaveURL('/admin');

    // Verify Help Assistant Insights tab exists and click it
    const insightsTab = page.locator('button[role="tab"]:has-text("Help Assistant Insights")');
    await expect(insightsTab).toBeVisible();
    await insightsTab.click();

    // Check KPI cards
    await expect(page.locator('text=Total Queries')).toBeVisible();
    await expect(page.locator('text=Helpful Rating')).toBeVisible();
    await expect(page.locator('text=Rebuild Knowledge Index')).toBeVisible();

    await context.close();
  });
});
