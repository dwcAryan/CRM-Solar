import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const authDir = fs.existsSync(path.resolve('frontend/playwright')) || fs.existsSync(path.resolve('frontend'))
  ? path.resolve('frontend/playwright/.auth')
  : path.resolve('playwright/.auth');

test.describe('RBAC Smoke Tests @smoke', () => {
  test('Admin navigation and access', async ({ browser }) => {
    const context = await browser.newContext({ storageState: path.join(authDir, 'admin.json') });
    const page = await context.newPage();

    await page.goto('/');
    await expect(page).toHaveURL('/');

    // Admin should see Admin Hub and Roles Matrix in navigation
    await expect(page.locator('nav, .mantine-AppShell-navbar')).toContainText('Admin Hub');
    await expect(page.locator('nav, .mantine-AppShell-navbar')).toContainText('Roles Matrix');

    // Admin can navigate to roles matrix
    await page.goto('/roles-matrix');
    await expect(page).toHaveURL('/roles-matrix');
    await expect(page.locator('h2')).toContainText('Roles & Permissions Matrix');

    await context.close();
  });

  test('Manager attention queue and team view', async ({ browser }) => {
    const context = await browser.newContext({ storageState: path.join(authDir, 'manager.json') });
    const page = await context.newPage();

    await page.goto('/');
    await expect(page).toHaveURL('/');

    // Manager should see Manager Attention in nav
    await expect(page.locator('nav, .mantine-AppShell-navbar')).toContainText('Manager Attention');

    // Manager navigates to /manager-attention
    await page.goto('/manager-attention');
    await expect(page).toHaveURL('/manager-attention');
    await expect(page.locator('h2')).toContainText('Manager Attention Queue');

    await context.close();
  });

  test('Salesperson restricted from assignment and import', async ({ browser }) => {
    const context = await browser.newContext({ storageState: path.join(authDir, 'salesperson.json') });
    const page = await context.newPage();

    await page.goto('/leads');
    await expect(page).toHaveURL('/leads');

    // Salesperson should NOT see Import Leads or Manager Attention in nav
    await expect(page.locator('nav, .mantine-AppShell-navbar')).not.toContainText('Import Leads');
    await expect(page.locator('nav, .mantine-AppShell-navbar')).not.toContainText('Manager Attention');

    // Navigating to /import-leads should show Access Denied
    await page.goto('/import-leads');
    await expect(page.locator('body')).toContainText('Access Denied');

    await context.close();
  });

  test('Surveyor restricted from leads list and quotes', async ({ browser }) => {
    const context = await browser.newContext({ storageState: path.join(authDir, 'surveyor.json') });
    const page = await context.newPage();

    await page.goto('/');

    // Surveyor should see "My Site Surveys" and NOT "All Leads" or "Quotations"
    await expect(page.locator('nav, .mantine-AppShell-navbar')).toContainText('My Site Surveys');
    await expect(page.locator('nav, .mantine-AppShell-navbar')).not.toContainText('All Leads');
    await expect(page.locator('nav, .mantine-AppShell-navbar')).not.toContainText('Quotations');

    // Navigating to /leads directly should show Access Denied
    await page.goto('/leads');
    await expect(page.locator('body')).toContainText('Access Denied');

    // Navigating to /my-surveys succeeds
    await page.goto('/my-surveys');
    await expect(page).toHaveURL('/my-surveys');
    await expect(page.locator('h2')).toContainText('Field Surveyor Portal');

    await context.close();
  });
});
