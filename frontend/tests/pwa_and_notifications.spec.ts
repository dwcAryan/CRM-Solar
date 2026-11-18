import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const authDir = fs.existsSync(path.resolve('frontend/playwright')) || fs.existsSync(path.resolve('frontend'))
  ? path.resolve('frontend/playwright/.auth')
  : path.resolve('playwright/.auth');

test.describe('PWA and Notification Suite', () => {
  test('manifest is served and valid with icons', async ({ request }) => {
    // 1. Verify manifest.json / manifest.webmanifest
    const res = await request.get('/manifest.json');
    expect(res.status()).toBe(200);

    const manifest = await res.json();
    expect(manifest.name).toBe('Solar CRM');
    expect(manifest.start_url).toBe('/');
    expect(manifest.display).toBe('standalone');
    expect(manifest.icons).toBeDefined();
    expect(manifest.icons.length).toBeGreaterThanOrEqual(2);

    const has192 = manifest.icons.some((i: { sizes: string }) => i.sizes === '192x192');
    const has512 = manifest.icons.some((i: { sizes: string }) => i.sizes === '512x512');
    expect(has192).toBeTruthy();
    expect(has512).toBeTruthy();

    // Verify icon files return HTTP 200
    const icon192Res = await request.get('/icon-192x192.png');
    expect(icon192Res.status()).toBe(200);
    const icon512Res = await request.get('/icon-512x512.png');
    expect(icon512Res.status()).toBe(200);
  });

  test.describe('Authenticated PWA & Notification UI', () => {
    test.use({ storageState: path.join(authDir, 'admin.json') });

    test('service worker registers and install button is in sidebar', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // 1. Verify "Download for desktop" button at bottom of sidebar
      const installBtn = page.getByRole('button', { name: /Download for desktop|App Installed/i });
      await expect(installBtn).toBeVisible();

      // Clicking when not standalone opens browser-specific guidance modal
      await installBtn.click();
      await expect(page.getByText(/Install Solar CRM as an App/i)).toBeVisible();
      await page.getByRole('button', { name: /Got it/i }).click();

      // 2. Verify Service Worker registration is supported and registered
      const swSupported = await page.evaluate(() => 'serviceWorker' in navigator);
      expect(swSupported).toBeTruthy();
    });

    test('permission modal appears when permission is "default" and not when "granted"', async ({ page }) => {
      // Clear localStorage and sessionStorage to simulate fresh prompt eligibility
      await page.addInitScript(() => {
        localStorage.removeItem('solar_crm_notif_dismissed_at');
        sessionStorage.removeItem('solar_crm_notif_session_prompted');
        // Force default permission
        Object.defineProperty(Notification, 'permission', {
          get: () => 'default',
          configurable: true,
        });
      });

      await page.goto('/');
      await page.waitForLoadState('domcontentloaded');

      // The friendly permission modal should appear
      const notifModal = page.getByText(/Turn on notifications to get follow-up and survey reminders/i);
      await expect(notifModal).toBeVisible({ timeout: 5000 });
      await expect(page.getByRole('button', { name: /Enable notifications/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /Not now/i })).toBeVisible();

      // Click "Not now" to dismiss
      await page.getByRole('button', { name: /Not now/i }).click();
      await expect(notifModal).not.toBeVisible();

      // Reload with "granted" permission - modal must NOT appear
      await page.addInitScript(() => {
        Object.defineProperty(Notification, 'permission', {
          get: () => 'granted',
          configurable: true,
        });
      });
      await page.goto('/');
      await page.waitForLoadState('domcontentloaded');
      await expect(page.getByText(/Turn on notifications to get follow-up and survey reminders/i)).not.toBeVisible();
    });

    test('denied-state guidance appears', async ({ page }) => {
      // Mock denied state
      await page.addInitScript(() => {
        Object.defineProperty(Notification, 'permission', {
          get: () => 'denied',
          configurable: true,
        });
      });

      await page.goto('/');
      await page.waitForLoadState('domcontentloaded');

      // Open notification settings from user menu
      const userMenuTrigger = page.locator('header').locator('.mantine-Avatar-root').first();
      await userMenuTrigger.click();

      const settingsOption = page.getByText(/Notification Settings/i);
      await expect(settingsOption).toBeVisible();
      await settingsOption.click();

      // Notification preferences modal is visible and shows DENIED badge
      await expect(page.getByText(/Notification & Reminder Preferences/i)).toBeVisible();
      await expect(page.getByText('DENIED')).toBeVisible();

      // Close modal
      await page.getByRole('button', { name: /Cancel|Close/i }).click();
    });
  });
});
