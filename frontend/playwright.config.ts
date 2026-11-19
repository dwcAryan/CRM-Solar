import { defineConfig, devices } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const testDir = fs.existsSync(path.resolve('frontend/tests'))
  ? path.resolve('frontend/tests')
  : path.resolve('tests');

export default defineConfig({
  testDir,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 1,
  workers: 4,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 30000,
  },
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'desktop-chrome',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    {
      name: 'mobile-390',
      dependencies: ['setup'],
      use: {
        viewport: { width: 390, height: 844 },
        isMobile: true,
      },
    },
  ],
});
