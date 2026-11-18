import { test, expect } from '@playwright/test';

test.describe('Clean Production Login Page (Phase 14 Regression)', () => {
  test('login page has empty inputs, standard placeholders, and zero demo buttons', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');

    // 1. Inputs must start empty with standard placeholders
    const usernameInput = page.getByPlaceholder('Username');
    await expect(usernameInput).toBeVisible();
    await expect(usernameInput).toHaveValue('');

    const passwordInput = page.getByPlaceholder('Password');
    await expect(passwordInput).toBeVisible();
    await expect(passwordInput).toHaveValue('');

    // 2. Zero demo autofill buttons or credentials shortcuts
    const demoButtons = page.locator('button', { hasText: /demo|quick login|fill/i });
    await expect(demoButtons).toHaveCount(0);

    const demoText = page.locator('text=/Use demo account|Quick login|Fill demo credentials/i');
    await expect(demoText).toHaveCount(0);

    // 3. Normal Sign In button is present
    const signInButton = page.getByRole('button', { name: /Sign in/i });
    await expect(signInButton).toBeVisible();

    // 4. "Forgot password?" link exists and functions
    const forgotPasswordLink = page.getByRole('link', { name: /Forgot password\?/i });
    await expect(forgotPasswordLink).toBeVisible();
    await forgotPasswordLink.click();
    await expect(page).toHaveURL(/.*reset-password|.*forgot-password/);
  });
});
