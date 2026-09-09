# Verification record

Verified on 2026-09-06 in America/Sao_Paulo.

## Automated checks

| Check | Result |
| --- | --- |
| TypeScript checks | Passed |
| Production build | Passed |
| Vitest | 36 tests passed |
| Playwright | 14 browser tests; final result recorded after completion |
| Asset inspection | Model JSON and audio files parse successfully |
| Code review | Important findings corrected; scoped review has no remaining important findings |

The browser tests use Chromium 153.0.8010.12.
They run against the production preview at port 4173.

## Performance

The performance script sends real keyboard events and reads diagnostics.
It keeps the player in a safe lane for 125 seconds.
The script does not modify gameplay state.

| Measurement | Observed value |
| --- | --- |
| Graphics processor | Apple M5 Pro through ANGLE Metal |
| Viewport | 1440 × 900 pixels |
| Quality | High |
| Duration | 125.076 seconds |
| Distance | 3043.53 meters |
| Mean sampled frame rate | 60.00 frames per second |
| Median frame time | 16.70 milliseconds |
| 95th-percentile frame time | 17.10 milliseconds |
| Scene mesh count | 1199 throughout the sample |
| Maximum active mesh count | 966 |
| Draw calls per frame | 137–169 |
| Reported resource transfer | 2,886,555 bytes |
| Uncaught page errors | None |

Read [performance.json](performance.json) for the machine-readable sample.
Run `node scripts/performance.mjs` to repeat the measurement.
Browser cache and compression can change transfer measurements.
The reported measurement includes resources requested by this test page.

## Acceptance coverage

| ID | Result | Evidence |
| --- | --- | --- |
| A01 | Passed | Browser start, pause, resume, collision, and restart test |
| A02 | Passed | Lane bounds, repeat suppression, and focused-button tests |
| A03 | Passed | Command-driven jump and slide collision tests |
| A04 | Passed | Unprotected blocker tests and browser game-over flow |
| A05 | Passed | One-time energy scoring, shield refresh, and immunity tests |
| A06 | Passed | Active-time score and capped-speed tests |
| A07 | Passed | Seeded patterns, safe trails, and simulated opposite escape lanes |
| A08 | Passed | Pause and blur tests; visibility handler uses the same pause path |
| A09 | Passed | Ten browser restarts and constant mesh counts during the performance sample |
| A10 | Passed | Score reload, invalid storage, and denied-storage tests |
| A11 | Passed in emulation | 390 × 844 viewport, swipe events, and touch buttons |
| A12 | Passed | Actual desktop and mobile screenshots inspected |
| A13 | Partial | Delayed audio reaches the engine's playing state; audible output is unverified |
| A14 | Passed | Production preview and local asset requests |
| A15 | Passed on desktop | Recorded two-minute sample; physical mobile performance is unverified |
| A16 | Passed | Missing model, missing audio, unavailable graphics, and denied storage tests |
| A17 | Passed | Preference tests, visible focus, and reduced-motion implementation review |

## Corrected findings

The initial renderer allocated object pools during early runs.
The renderer now allocates those pools during loading.
Ten restart cycles retain a bounded scene.

The initial audio setup could miss an early Start action.
The audio controller now accepts that action before sound downloads finish.
A delayed-download regression verifies that the ambient loop starts.

Mobile initialization initially overwrote a saved high-quality preference.
Device defaults now apply only when stored preferences are absent.

A persisted page initially disposed the game during history navigation.
The page now preserves resources when `pagehide.persisted` is true.
The regression dispatches that lifecycle event; it does not prove every browser's history-cache eligibility.

## Visual evidence

- [Ready screen](screenshots/ready.png)
- [Running game](screenshots/running.png)
- [Paused game](screenshots/paused.png)
- [Game-over screen](screenshots/gameover.png)
- [Mobile ready screen](screenshots/mobile-ready.png)
- [Mobile running game](screenshots/mobile-running.png)
- [Mobile game-over screen](screenshots/mobile-gameover.png)

## Limits

Physical mobile hardware, Safari, Firefox, and audible speaker output are unverified.
Chromium mobile emulation verifies layout and input behavior, not mobile graphics performance.
The game has no public deployment or backend.
