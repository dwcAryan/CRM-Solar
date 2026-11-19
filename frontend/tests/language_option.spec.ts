import { test, expect } from '@playwright/test';

test.describe('Phase 14L: Multi-Language Support (i18n)', () => {
  test('login page has language selector and switches interface to Hindi and back', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');

    // 1. Language selector button is visible on login page
    const langBtn = page.getByTestId('language-selector-btn');
    await expect(langBtn).toBeVisible();

    // 2. Open dropdown and switch to Hindi
    await langBtn.click();
    const hiOption = page.getByTestId('lang-option-hi');
    await expect(hiOption).toBeVisible();
    await hiOption.click();

    // 3. Document language attribute updated
    const html = page.locator('html');
    await expect(html).toHaveAttribute('lang', 'hi');

    // 4. Input placeholders and button text are translated into Hindi
    const usernameInput = page.getByPlaceholder(/उपयोगकर्ता नाम/i);
    await expect(usernameInput).toBeVisible();

    const signInBtn = page.getByRole('button', { name: /लॉगिन करें/i });
    await expect(signInBtn).toBeVisible();

    // 5. Switch back to English
    await langBtn.click();
    const enOption = page.getByTestId('lang-option-en');
    await expect(enOption).toBeVisible();
    await enOption.click();

    await expect(html).toHaveAttribute('lang', 'en');
    await expect(page.getByRole('button', { name: /Sign In/i })).toBeVisible();
  });

  test('pseudo-RTL locale activates dir="rtl" on document', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');

    const langBtn = page.getByTestId('language-selector-btn');
    await langBtn.click();

    const rtlOption = page.getByTestId('lang-option-ar-XB');
    await expect(rtlOption).toBeVisible();
    await rtlOption.click();

    const html = page.locator('html');
    await expect(html).toHaveAttribute('dir', 'rtl');

    // Switch back to English LTR
    await langBtn.click();
    await page.getByTestId('lang-option-en').click();
    await expect(html).toHaveAttribute('dir', 'ltr');
  });

  test('pseudo-locale en-XA expands text length without breaking', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');

    const langBtn = page.getByTestId('language-selector-btn');
    await langBtn.click();

    const xaOption = page.getByTestId('lang-option-en-XA');
    await expect(xaOption).toBeVisible();
    await xaOption.click();

    const html = page.locator('html');
    await expect(html).toHaveAttribute('lang', 'en-XA');

    // Title shows expanded text
    const title = page.locator('text=/Ssoooolaaaar/i');
    await expect(title).toBeVisible();

    // Switch back
    await langBtn.click();
    await page.getByTestId('lang-option-en').click();
    await expect(html).toHaveAttribute('lang', 'en');
  });
});
