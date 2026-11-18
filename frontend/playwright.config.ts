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
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'smoke',
      testMatch: /.*\.spec\.ts/,
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
});
