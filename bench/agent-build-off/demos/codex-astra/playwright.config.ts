import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: { timeout: 10000 },
  use: { baseURL: 'http://127.0.0.1:4173', viewport: { width: 1440, height: 900 }, screenshot: 'only-on-failure', launchOptions: { args: ['--use-gl=angle', '--use-angle=metal'] } },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } }],
  webServer: { command: 'npm run preview -- --port 4173', url: 'http://127.0.0.1:4173', reuseExistingServer: true },
});
