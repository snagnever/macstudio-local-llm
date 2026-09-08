import { describe, expect, it } from 'vitest';
import { parseSeedLabel } from './session';

describe('parseSeedLabel', () => {
  it('parses base36 labels case-insensitively', () => {
    expect(parseSeedLabel('3F')).toBe(123);
    expect(parseSeedLabel('3f')).toBe(123);
  });
  it('returns undefined for missing or invalid labels', () => {
    expect(parseSeedLabel(undefined)).toBeUndefined();
    expect(parseSeedLabel('')).toBeUndefined();
    expect(parseSeedLabel('!!')).toBeUndefined();
  });
});
