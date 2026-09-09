import { expect, test } from '@playwright/test';

test('start, pause, resume and restart form a complete flow', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button', { name: 'Start run', exact: true }).click();
  await expect(page.getByTestId('distance')).not.toHaveText('0 m');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
  const distance = await page.getByTestId('distance').textContent();
  await page.waitForTimeout(350);
  await expect(page.getByTestId('distance')).toHaveText(distance!);
  await page.getByRole('button', { name: 'Resume', exact: true }).click();
  await expect(page.getByTestId('distance')).not.toHaveText(distance!);
  await expect(page.getByRole('button', { name: 'Restart', exact: true })).toBeVisible({ timeout: 20000 });
  await page.getByRole('button', { name: 'Restart', exact: true }).click();
  await expect(page.getByTestId('distance')).toHaveText(/^[0-9] m$/);
  expect(errors).toEqual([]);
});

test('audio loaded after Start joins the active run', async ({ page }) => {
  await page.route('**/assets/audio/**', async route => {
    await new Promise(resolve => setTimeout(resolve, 1200));
    await route.continue();
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Start run', exact: true }).click();
  await expect.poll(() => page.evaluate(() => (window as any).__hyperRunner.audio?.loopState)).toBe(3);
});

test('mobile reload preserves a chosen high quality setting', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  await page.goto('/');
  await page.getByRole('button', { name: 'Start run', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Quality low', exact: true }).click();
  await page.reload();
  await page.getByRole('button', { name: 'Start run', exact: true }).waitFor();
  await expect(page.getByRole('button', { name: 'Quality high', exact: true })).toBeVisible();
  await context.close();
});

test('a persisted page retains the game on history restoration', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Start run', exact: true }).waitFor();
  await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: true })));
  await expect(page.getByRole('button', { name: 'Start run', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Start run', exact: true }).click();
  await expect(page.getByTestId('distance')).not.toHaveText('0 m');
});

test('a final best score survives page reload', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Start run', exact: true }).click();
  await page.getByRole('button', { name: 'Restart', exact: true }).waitFor({ timeout: 20000 });
  const best = await page.locator('[data-value="final-best"]').textContent();
  expect(Number(best?.replaceAll(',', ''))).toBeGreaterThan(0);
  await page.reload();
  await page.getByRole('button', { name: 'Start run', exact: true }).waitFor();
  await expect(page.locator('[data-value="ready-best"]')).toHaveText(best!);
});

test('unavailable graphics shows a usable failure screen', async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, kind: string, ...args: any[]) {
      if (kind.includes('webgl')) return null;
      return original.call(this, kind as any, ...args);
    } as typeof original;
  });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Retry', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'The game could not start.', exact: true })).toBeVisible();
});

test('missing audio preserves silent gameplay', async ({ page }) => {
  await page.route('**/assets/audio/**', route => route.abort());
  await page.goto('/');
  await page.getByRole('button', { name: 'Start run', exact: true }).click();
  await expect(page.getByTestId('distance')).not.toHaveText('0 m');
  await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeVisible();
});
