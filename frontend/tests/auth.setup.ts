import { test as setup } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const authDir = fs.existsSync(path.resolve('frontend/playwright')) || fs.existsSync(path.resolve('frontend'))
  ? path.resolve('frontend/playwright/.auth')
  : path.resolve('playwright/.auth');

if (!fs.existsSync(authDir)) {
  fs.mkdirSync(authDir, { recursive: true });
}

const roles = [
  { name: 'admin', username: 'demo_admin', password: 'Admin@Demo2026!' },
  { name: 'manager', username: 'demo_manager', password: 'Manager@Demo2026!' },
  { name: 'salesperson', username: 'demo_sales_in', password: 'Sales@Demo2026!' },
  { name: 'surveyor', username: 'demo_surveyor_in', password: 'Surveyor@Demo2026!' },
];

for (const role of roles) {
  setup(`authenticate as ${role.name}`, async ({ request, page }) => {
    const res = await request.post('http://127.0.0.1:8000/api/token/', {
      data: {
        username: role.username,
        password: role.password,
      },
    });

    const data = await res.json();
    if (!data.access) {
      throw new Error(`Failed to obtain JWT token for ${role.username}: ${JSON.stringify(data)}`);
    }

    // Set localStorage tokens in context
    await page.goto('/');
    await page.evaluate(({ access, refresh }) => {
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem('solar_crm_has_seen_tour', 'true');
    }, { access: data.access, refresh: data.refresh });

    // Reload page to verify authenticated state
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const statePath = path.join(authDir, `${role.name}.json`);
    await page.context().storageState({ path: statePath });
  });
}
