import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const authDir = fs.existsSync(path.resolve('frontend/playwright/.auth'))
  ? path.resolve('frontend/playwright/.auth')
  : path.resolve('playwright/.auth');

test.describe('Product Tour & Walkthroughs @smoke', () => {
  test('Tour targets and Tour Center drawer', async ({ browser }) => {
    const context = await browser.newContext({
      storageState: path.join(authDir, 'salesperson.json'),
    });
    const page = await context.newPage();

    await page.goto('/');
    await expect(page).toHaveURL('/');

    // 1. Verify stable data-tour attributes are present in layout
    await expect(page.locator('[data-tour="sidebar-nav"]')).toBeVisible();
    await expect(page.locator('[data-tour="header-help"]')).toBeVisible();
    await expect(page.locator('[data-tour="helpbot-fab"]')).toBeVisible();

    // 2. Dashboard Get Started checklist card is visible
    await expect(page.locator('[data-tour="dashboard-checklist"]')).toBeVisible();
    await expect(page.locator('[data-tour="dashboard-checklist"]')).toContainText('Getting Started with Solar CRM');

    // 3. Open Tour Center drawer from header button
    await page.locator('[data-tour="header-help"]').click();
    await expect(page.locator('text=Product Tour Center')).toBeVisible();
    await expect(page.locator('text=Complete System Tour')).toBeVisible();
    await expect(page.getByText('Getting Started', { exact: true })).toBeVisible();

    // 4. Start Getting Started tour from Tour Center drawer
    const drawer = page.locator('.mantine-Drawer-content');
    const startButton = drawer.locator('button:has-text("Start"), button:has-text("Replay")').first();
    await startButton.click();
    // Tour driver popover should appear with progress
    const popover = page.locator('.driver-popover');
    await expect(popover).toBeVisible({ timeout: 10000 });
    await expect(popover).toContainText(/Navigation Sidebar|Core Workspaces/);

    // Close popover
    const closeBtn = page.locator('.driver-popover-close-btn');
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
    } else {
      await page.keyboard.press('Escape');
    }

    await context.close();
  });
});
