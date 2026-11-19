import { chromium } from '../frontend/node_modules/@playwright/test/index.mjs';
import fs from 'fs';
import path from 'path';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const ROOT_DIR = path.resolve('.');
const EN_DIR = path.join(ROOT_DIR, 'docs', 'manual_assets', 'en');
const HI_DIR = path.join(ROOT_DIR, 'docs', 'manual_assets', 'hi');
const AUTH_DIR = path.join(ROOT_DIR, 'frontend', 'playwright', '.auth');

fs.mkdirSync(EN_DIR, { recursive: true });
fs.mkdirSync(HI_DIR, { recursive: true });

async function run() {
  console.log('[CaptureHarness] Launching browser...');
  const browser = await chromium.launch({ headless: true });

  const desktopViewport = { width: 1440, height: 900 };
  const mobileViewport = { width: 390, height: 844 };

  // Helper for authenticated context
  async function getAuthContext(role, lang = 'en', isMobile = false) {
    const authFile = path.join(AUTH_DIR, `${role}.json`);
    const vp = isMobile ? mobileViewport : desktopViewport;
    const context = await browser.newContext({
      storageState: authFile,
      viewport: vp,
      isMobile: isMobile,
    });
    if (lang === 'hi') {
      await context.addInitScript(() => {
        localStorage.setItem('solar_crm_lang', 'hi');
        localStorage.setItem('i18nextLng', 'hi');
      });
    } else {
      await context.addInitScript(() => {
        localStorage.setItem('solar_crm_lang', 'en');
        localStorage.setItem('i18nextLng', 'en');
      });
    }
    return context;
  }

  // 1. Unauthenticated Login (English & Hindi, Desktop & Mobile)
  {
    console.log('[CaptureHarness] Capturing Login screens...');
    // Desktop English
    let context = await browser.newContext({ viewport: desktopViewport });
    let page = await context.newPage();
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(EN_DIR, '01_login_desktop.png') });
    await context.close();

    // Mobile English
    context = await browser.newContext({ viewport: mobileViewport, isMobile: true });
    page = await context.newPage();
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(EN_DIR, '01_login_mobile.png') });
    await context.close();

    // Desktop Hindi
    context = await browser.newContext({ viewport: desktopViewport });
    page = await context.newPage();
    await page.addInitScript(() => {
      localStorage.setItem('solar_crm_lang', 'hi');
      localStorage.setItem('i18nextLng', 'hi');
    });
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(HI_DIR, '01_login_desktop.png') });
    await context.close();

    // Mobile Hindi
    context = await browser.newContext({ viewport: mobileViewport, isMobile: true });
    page = await context.newPage();
    await page.addInitScript(() => {
      localStorage.setItem('solar_crm_lang', 'hi');
      localStorage.setItem('i18nextLng', 'hi');
    });
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(HI_DIR, '01_login_mobile.png') });
    await context.close();
  }

  // 2. Dashboards (Admin, Manager, Salesperson, Surveyor)
  for (const lang of ['en', 'hi']) {
    const outDir = lang === 'hi' ? HI_DIR : EN_DIR;
    console.log(`[CaptureHarness] Capturing role dashboards (${lang.toUpperCase()})...`);

    // Admin Dashboard
    let ctx = await getAuthContext('admin', lang);
    let p = await ctx.newPage();
    await p.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(outDir, '02_home_admin.png') });
    await ctx.close();

    // Manager Dashboard
    ctx = await getAuthContext('manager', lang);
    p = await ctx.newPage();
    await p.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(outDir, '03_home_manager.png') });
    await ctx.close();

    // Salesperson Dashboard
    ctx = await getAuthContext('salesperson', lang);
    p = await ctx.newPage();
    await p.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(outDir, '04_home_salesperson.png') });
    await ctx.close();

    // Surveyor Dashboard / Portal
    ctx = await getAuthContext('surveyor', lang);
    p = await ctx.newPage();
    await p.goto(`${BASE_URL}/my-surveys`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(outDir, '05_home_surveyor.png') });
    await ctx.close();
  }

  // 3. Operational Pages (Today, Leads, Detail, Modals, Surveys, Quotes, Import, Admin)
  for (const lang of ['en', 'hi']) {
    const outDir = lang === 'hi' ? HI_DIR : EN_DIR;
    console.log(`[CaptureHarness] Capturing operational workflow pages (${lang.toUpperCase()})...`);

    // Today list
    let ctx = await getAuthContext('salesperson', lang);
    let p = await ctx.newPage();
    await p.goto(`${BASE_URL}/today`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(outDir, '06_today_followups.png') });

    // Leads Pipeline
    await p.goto(`${BASE_URL}/leads`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(800);
    await p.screenshot({ path: path.join(outDir, '07_leads_pipeline.png') });

    // Click first lead in table to navigate to real lead detail
    try {
      const nameText = p.locator('table tbody tr text').first();
      if (await nameText.isVisible()) {
        await nameText.click();
        await p.waitForSelector('button:has-text("Log Outcome"), button:has-text("परिणाम दर्ज करें")', { timeout: 6000 });
        await p.waitForTimeout(500);
        await p.screenshot({ path: path.join(outDir, '08_lead_detail.png') });

        // Log Outcome Modal
        const logBtn = p.locator('button:has-text("Log Outcome"), button:has-text("परिणाम दर्ज करें")').first();
        if (await logBtn.isVisible()) {
          await logBtn.click();
          await p.waitForTimeout(600);
          await p.screenshot({ path: path.join(outDir, '09_log_outcome_modal.png') });
          await p.keyboard.press('Escape');
          await p.waitForTimeout(300);
        }

        // AI Suggestions Card
        try {
          const aiCard = p.locator('[data-tour="ai-suggestions"]').first();
          if (await aiCard.isVisible()) {
            await aiCard.screenshot({ path: path.join(outDir, '14_ai_suggestions.png') });
          }
        } catch {
          // ignore
        }
      }
    } catch (e) {
      console.warn('Could not open lead detail:', e.message);
    }

    // Surveys Schedule
    await p.goto(`${BASE_URL}/surveys`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(outDir, '10_surveys_schedule.png') });

    // Quote Proposals
    await p.goto(`${BASE_URL}/quotes`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(outDir, '11_quote_proposals.png') });

    // Helpbot Chat Modal
    try {
      const helpFab = p.locator('[data-tour="helpbot-fab"]').first();
      if (await helpFab.isVisible()) {
        await helpFab.click();
        await p.waitForTimeout(600);
        await p.screenshot({ path: path.join(outDir, '15_helpbot_chat.png') });
        await p.keyboard.press('Escape');
        await p.waitForTimeout(300);
      }
    } catch (e) {
      console.warn('Could not open Helpbot modal:', e.message);
    }

    // Notifications menu
    try {
      const notifBtn = p.locator('[data-tour="header-notifications"] button').first();
      if (await notifBtn.isVisible()) {
        await notifBtn.click();
        await p.waitForTimeout(500);
        await p.screenshot({ path: path.join(outDir, '13_notifications.png') });
        await p.keyboard.press('Escape');
        await p.waitForTimeout(300);
      }
    } catch (e) {
      console.warn('Could not open notifications:', e.message);
    }

    await ctx.close();

    // Admin & Import pages (as Admin)
    ctx = await getAuthContext('admin', lang);
    p = await ctx.newPage();
    await p.goto(`${BASE_URL}/import-leads`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(outDir, '12_import_leads.png') });

    await p.goto(`${BASE_URL}/admin`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(800);
    await p.screenshot({ path: path.join(outDir, '16_admin_policy.png') });

    // Region selector in header
    try {
      const regSelect = p.locator('[data-tour="header-region-selector"] input, [data-tour="header-region-selector"]').first();
      if (await regSelect.isVisible()) {
        await regSelect.click();
        await p.waitForTimeout(400);
        await p.screenshot({ path: path.join(outDir, '17_region_selector.png') });
        await p.keyboard.press('Escape');
      }
    } catch (e) {
      console.warn('Could not open region selector:', e.message);
    }

    await ctx.close();

    // Mobile View (Salesperson, 390px)
    ctx = await getAuthContext('salesperson', lang, true);
    p = await ctx.newPage();
    await p.goto(`${BASE_URL}/leads`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(600);
    await p.screenshot({ path: path.join(outDir, '18_mobile_lead_view.png') });
    await ctx.close();
  }

  await browser.close();
  console.log('[CaptureHarness] All screenshots captured successfully in docs/manual_assets/!');
}

run().catch(err => {
  console.error('[CaptureHarness] Error capturing screens:', err);
  process.exit(1);
});
