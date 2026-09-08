import { expect, test, type Page } from '@playwright/test';

type Diagnostics = {
  phase: string;
  distance: number;
  runner: { x: number; y: number; lane: number; slideRemaining: number };
  meshes: number;
  preferences: { muted: boolean; quality: 'high' | 'low'; reducedMotion: boolean };
  audioReady: boolean;
};

const diagnostics = (page: Page) => page.evaluate(() =>
  (window as typeof window & { __hyperRunner: Diagnostics }).__hyperRunner,
);

async function waitForReady(page: Page): Promise<void> {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Start run', exact: true })).toBeVisible({ timeout: 20_000 });
}

async function start(page: Page): Promise<void> {
  await waitForReady(page);
  await page.getByRole('button', { name: 'Start run', exact: true }).click();
  await expect.poll(async () => (await diagnostics(page)).phase).toBe('running');
}

test('keyboard lane input suppresses repeats and ignores focused buttons', async ({ page }) => {
  await start(page);
  await page.keyboard.down('ArrowRight');
  await page.keyboard.down('ArrowRight');
  await page.keyboard.up('ArrowRight');
  await expect.poll(async () => (await diagnostics(page)).runner.lane).toBe(1);

  await page.getByRole('button', { name: 'Pause', exact: true }).focus();
  await page.keyboard.press('ArrowLeft');
  expect((await diagnostics(page)).runner.lane).toBe(1);

  await page.locator('#game').focus();
  await page.keyboard.press('ArrowLeft');
  await expect.poll(async () => (await diagnostics(page)).runner.lane).toBe(0);
});

test.describe('mobile controls', () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

test('swipe and touch buttons send one command per gesture', async ({ page }) => {
  await start(page);
  const canvas = page.locator('#game');
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  const centerX = box!.x + box!.width / 2;
  const centerY = box!.y + box!.height / 2;

  await page.mouse.move(centerX, centerY);
  await page.mouse.down();
  await page.mouse.move(centerX - 45, centerY, { steps: 2 });
  await page.mouse.move(centerX - 100, centerY, { steps: 2 });
  await page.mouse.up();
  await expect.poll(async () => (await diagnostics(page)).runner.lane).toBe(-1);

  const right = page.getByRole('button', { name: 'Move right', exact: true });
  await expect(right).toBeVisible();
  expect((await right.boundingBox())!.height).toBeGreaterThanOrEqual(48);
  await right.click();
  await expect.poll(async () => (await diagnostics(page)).runner.lane).toBe(0);

  await page.keyboard.press('ArrowRight');
  expect((await diagnostics(page)).runner.lane).toBe(0);
  await canvas.focus();
  await page.keyboard.press('ArrowRight');
  await expect.poll(async () => (await diagnostics(page)).runner.lane).toBe(1);

  await page.getByRole('button', { name: 'Jump', exact: true }).click();
  await expect.poll(async () => (await diagnostics(page)).runner.y).toBeGreaterThan(0);
  await expect(page.getByRole('button', { name: 'Slide', exact: true })).toBeVisible();
});
});

test('sound, quality, and reduced motion preferences persist', async ({ page }) => {
  await waitForReady(page);
  await page.getByRole('button', { name: 'Sound on', exact: true }).click();
  await page.getByRole('button', { name: 'Quality high', exact: true }).click();
  await page.getByRole('button', { name: 'Motion full', exact: true }).click();
  await expect.poll(async () => (await diagnostics(page)).preferences).toEqual({
    muted: true, quality: 'low', reducedMotion: true,
  });

  await page.reload();
  await expect(page.getByRole('button', { name: 'Start run', exact: true })).toBeVisible({ timeout: 20_000 });
  expect((await diagnostics(page)).preferences).toEqual({ muted: true, quality: 'low', reducedMotion: true });
  await expect(page.getByRole('button', { name: 'Sound off', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Quality low', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Motion reduced', exact: true })).toBeVisible();
});

test('window blur pauses an active run', async ({ page }) => {
  await start(page);
  await page.evaluate(() => window.dispatchEvent(new Event('blur')));
  await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
  expect((await diagnostics(page)).phase).toBe('paused');
});

test('ten restart cycles retain a bounded scene without page reloads', async ({ page }) => {
  await start(page);
  const initialMeshes = (await diagnostics(page)).meshes;
  for (let cycle = 0; cycle < 10; cycle += 1) {
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button', { name: 'Resume', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Restart', exact: true }).click();
    await expect.poll(async () => (await diagnostics(page)).phase).toBe('running');
  }
  const final = await diagnostics(page);
  expect(final.meshes).toBeLessThanOrEqual(initialMeshes + 30);
  expect(final.distance).toBeLessThan(10);
});

test('blocked storage uses safe defaults and keeps the game playable', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(Storage.prototype, 'getItem', { configurable: true, value() { throw new Error('Access denied'); } });
    Object.defineProperty(Storage.prototype, 'setItem', { configurable: true, value() { throw new Error('Access denied'); } });
  });
  await start(page);
  expect((await diagnostics(page)).preferences).toEqual({ muted: false, quality: 'high', reducedMotion: false });
});

test('missing runner asset shows the retry screen', async ({ page }) => {
  await page.route('**/assets/models/runner.gltf', route => route.abort());
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Retry', exact: true })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText('Track unavailable', { exact: true })).toBeVisible();
  expect((await diagnostics(page)).phase).toBe('error');
});
