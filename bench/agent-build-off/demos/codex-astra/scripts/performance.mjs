import { chromium } from '@playwright/test';
import { writeFile, mkdir } from 'node:fs/promises';

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=metal'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
await page.goto('http://127.0.0.1:4173');
await page.getByRole('button', { name: 'Start run', exact: true }).waitFor();
await page.waitForTimeout(1000);
await mkdir('docs/screenshots', { recursive: true });
await page.screenshot({ path: 'docs/screenshots/ready.png' });
await page.getByRole('button', { name: 'Start run', exact: true }).click();
const started = Date.now();
const samples = [];
let captured = false;
while (Date.now() - started < 125000) {
  const state = await page.evaluate(() => window.__hyperRunner);
  if (state.phase !== 'running') throw new Error(`Performance run stopped: ${state.phase}`);
  const hazards = state.objects.filter(object => ['barrier', 'gate', 'blocker'].includes(object.kind) && object.z > -1);
  const nearest = hazards.sort((a, b) => a.z - b.z)[0];
  if (nearest && nearest.z < 28 && nearest.z > 1) {
    const blocked = hazards.filter(object => Math.abs(object.z - nearest.z) < 1).map(object => object.lane);
    if (blocked.includes(state.runner.lane)) {
      const lane = [-1, 0, 1].filter(lane => !blocked.includes(lane)).sort((a, b) => Math.abs(a - state.runner.lane) - Math.abs(b - state.runner.lane))[0];
      const key = lane > state.runner.lane ? 'ArrowRight' : 'ArrowLeft';
      for (let step = 0; step < Math.abs(lane - state.runner.lane); step++) await page.keyboard.press(key);
    }
  }
  if (Date.now() - started > 5000) samples.push({ fps: state.fps, meshes: state.meshes, activeMeshes: state.activeMeshes, drawCalls: state.drawCalls });
  if (!captured && state.distance > 190) { await page.screenshot({ path: 'docs/screenshots/running.png' }); captured = true; }
  await page.waitForTimeout(80);
}
const state = await page.evaluate(() => window.__hyperRunner);
const frames = state.frameTimes.slice(300).sort((a, b) => a - b);
const sum = values => values.reduce((a, b) => a + b, 0);
const result = {
  date: new Date().toISOString(), browser: await browser.version(), gpu: state.gpu,
  viewport: { width: 1440, height: 900 }, quality: state.preferences.quality,
  durationSeconds: (Date.now() - started) / 1000, distanceMeters: state.distance,
  meanSampleFps: sum(samples.map(sample => sample.fps)) / samples.length,
  medianFrameMs: frames[Math.floor(frames.length * 0.5)], p95FrameMs: frames[Math.floor(frames.length * 0.95)],
  meshRange: [Math.min(...samples.map(sample => sample.meshes)), Math.max(...samples.map(sample => sample.meshes))],
  maxActiveMeshes: Math.max(...samples.map(sample => sample.activeMeshes)),
  drawCallRange: [Math.min(...samples.map(sample => sample.drawCalls)), Math.max(...samples.map(sample => sample.drawCalls))],
  transferBytes: await page.evaluate(() => performance.getEntriesByType('resource').reduce((n, item) => n + item.transferSize, 0)),
  errors,
};
await writeFile('docs/performance.json', JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result, null, 2));
await page.keyboard.press('Escape');
await page.screenshot({ path: 'docs/screenshots/paused.png' });
await browser.close();
