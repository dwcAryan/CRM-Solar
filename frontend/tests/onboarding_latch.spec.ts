import { test, expect } from '@playwright/test';

const CORS_HEADERS = {
  'access-control-allow-origin': 'http://localhost:5173',
  'access-control-allow-credentials': 'true',
  'access-control-allow-headers': 'authorization,content-type,x-app-language,accept-language',
  'access-control-allow-methods': 'GET,POST,OPTIONS',
};

test.describe('Onboarding Checklist & One-Way Completion Latch', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('no-flicker: delayed onboarding API renders nothing while loading, then renders card only when needed', async ({ page }) => {
    await page.route('**/api/me/onboarding/**', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 200, headers: CORS_HEADERS });
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 800));
      await route.fulfill({
        status: 200,
        headers: CORS_HEADERS,
        contentType: 'application/json',
        body: JSON.stringify({
          visible: true,
          items: [
            { id: 'tour', label: 'Complete the interactive Product Tour', done: false },
            { id: 'leads', label: 'Review your leads pipeline and customer details', done: false },
            { id: 'quote', label: 'Create your first solar pricing proposal', done: false },
            { id: 'tour_center', label: 'Explore specialized workflows in the Tour Center', done: false },
          ],
          completed_at: null,
          dismissed_at: null,
          is_collapsed: false,
        }),
      });
    });

    await page.goto('/');

    // While request is pending, onboarding card MUST NOT exist in DOM (no skeleton, no card)
    const cardBefore = page.locator('[data-testid="onboarding-card"]');
    await expect(cardBefore).toHaveCount(0);

    // After response resolves, the card renders cleanly
    await expect(cardBefore).toBeVisible({ timeout: 10000 });
    await expect(cardBefore).toContainText('Getting Started with Solar CRM');
  });

  test('no-flicker & latched: completed user never renders card before or after response', async ({ page }) => {
    await page.route('**/api/me/onboarding/**', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 200, headers: CORS_HEADERS });
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 600));
      await route.fulfill({
        status: 200,
        headers: CORS_HEADERS,
        contentType: 'application/json',
        body: JSON.stringify({
          visible: false,
          items: [],
          completed_at: '2026-11-19T10:00:00Z',
          dismissed_at: null,
          is_collapsed: false,
        }),
      });
    });

    await page.goto('/');

    // Card must never appear in DOM
    const card = page.locator('[data-testid="onboarding-card"]');
    await expect(card).toHaveCount(0);
    await page.waitForTimeout(1000);
    await expect(card).toHaveCount(0);

    // Dashboard main content renders without gaps
    await expect(page.locator('text=Sales Overview')).toBeVisible();
  });

  test('one-way latch: complete onboarding shows all done and persists across reload, mobile, and cleared storage', async ({ page }) => {
    let latched = false;
    await page.route('**/api/me/onboarding/**', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 200, headers: CORS_HEADERS });
        return;
      }

      if (route.request().method() === 'POST') {
        latched = true;
        await route.fulfill({
          status: 200,
          headers: CORS_HEADERS,
          contentType: 'application/json',
          body: JSON.stringify({
            visible: false,
            just_completed: true,
            items: [
              { id: 'tour', label: 'Complete the interactive Product Tour', done: true },
              { id: 'leads', label: 'Review your leads pipeline and customer details', done: true },
              { id: 'quote', label: 'Create your first solar pricing proposal', done: true },
              { id: 'tour_center', label: 'Explore specialized workflows in the Tour Center', done: true },
            ],
            completed_at: '2026-11-19T10:00:00Z',
            dismissed_at: null,
            is_collapsed: false,
          }),
        });
        return;
      }

      if (latched) {
        await route.fulfill({
          status: 200,
          headers: CORS_HEADERS,
          contentType: 'application/json',
          body: JSON.stringify({
            visible: false,
            items: [],
            completed_at: '2026-11-19T10:00:00Z',
            dismissed_at: null,
            is_collapsed: false,
          }),
        });
        return;
      }

      // Initial state
      await route.fulfill({
        status: 200,
        headers: CORS_HEADERS,
        contentType: 'application/json',
        body: JSON.stringify({
          visible: true,
          items: [
            { id: 'tour', label: 'Complete the interactive Product Tour', done: true },
            { id: 'leads', label: 'Review your leads pipeline and customer details', done: true },
            { id: 'quote', label: 'Create your first solar pricing proposal', done: true },
            { id: 'tour_center', label: 'Explore specialized workflows in the Tour Center', done: false },
          ],
          completed_at: null,
          dismissed_at: null,
          is_collapsed: false,
        }),
      });
    });

    await page.goto('/');
    const card = page.locator('[data-testid="onboarding-card"]');
    await expect(card).toBeVisible({ timeout: 10000 });

    // Trigger the final item action
    await page.locator('button:has-text("Tour Center")').click();

    // Verify "All done!" state displays
    await expect(page.locator('text=All done! Getting Started checklist completed')).toBeVisible({ timeout: 4000 });

    // Wait for the 3s disappearance transition
    await expect(card).toHaveCount(0, { timeout: 6000 });

    // 1. Reload verification
    await page.reload();
    await expect(page.locator('[data-testid="onboarding-card"]')).toHaveCount(0);

    // 2. Cleared localStorage and sessionStorage
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.reload();
    await expect(page.locator('[data-testid="onboarding-card"]')).toHaveCount(0);

    // 3. Mobile 390px viewport check
    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload();
    await expect(page.locator('[data-testid="onboarding-card"]')).toHaveCount(0);
  });

  test('dismiss action (Close X) latches card permanently', async ({ page }) => {
    let dismissed = false;
    await page.route('**/api/me/onboarding/**', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 200, headers: CORS_HEADERS });
        return;
      }

      if (route.request().method() === 'POST') {
        dismissed = true;
        await route.fulfill({
          status: 200,
          headers: CORS_HEADERS,
          contentType: 'application/json',
          body: JSON.stringify({
            visible: false,
            items: [],
            completed_at: null,
            dismissed_at: '2026-11-19T10:00:00Z',
            is_collapsed: false,
          }),
        });
        return;
      }

      await route.fulfill({
        status: 200,
        headers: CORS_HEADERS,
        contentType: 'application/json',
        body: JSON.stringify({
          visible: !dismissed,
          items: dismissed ? [] : [
            { id: 'tour', label: 'Complete the interactive Product Tour', done: false },
            { id: 'leads', label: 'Review your leads pipeline and customer details', done: false },
          ],
          completed_at: null,
          dismissed_at: dismissed ? '2026-11-19T10:00:00Z' : null,
          is_collapsed: false,
        }),
      });
    });

    await page.goto('/');
    const card = page.locator('[data-testid="onboarding-card"]');
    await expect(card).toBeVisible({ timeout: 10000 });

    // Click Dismiss (IconX)
    await page.locator('button[aria-label="Dismiss checklist"]').click();
    await expect(card).toHaveCount(0);

    // Reload persists dismissal
    await page.reload();
    await expect(card).toHaveCount(0);
  });
});
