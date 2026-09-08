import { useGame } from './store';
import { resumeAudio } from './audio';

export function parseSeedLabel(label?: string): number | undefined {
  if (!label) return undefined;
  const trimmed = label.trim();
  if (!/^[0-9a-z]+$/i.test(trimmed)) return undefined;
  const n = parseInt(trimmed, 36);
  if (!Number.isFinite(n) || n < 0) return undefined;
  return n >>> 0;
}

export function startRun(seedLabel?: string): void {
  resumeAudio();
  useGame.getState().confirm(parseSeedLabel(seedLabel));
}
