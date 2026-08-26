#!/usr/bin/env node
/**
 * Checks the 40px/frame rule (spec §2.8 / §6) numerically instead of by eye.
 *
 *   node scripts/motion-check.mjs [9x16|16x9]
 *
 * The stage's motion is deterministic and pure, so it can be evaluated straight
 * out of `flight.ts` without rendering a single frame. For every frame of the
 * piece this reports the screen-space speed of the stage (camera travel plus the
 * hints contributed by elements that move on their own) and the `trailOpacity`
 * `SpeedTrail` would apply at that speed.
 *
 * It fails if any frame moves faster than 40px/frame while carrying no blur.
 */

import esbuild from 'esbuild';
import {readFileSync, rmSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const aspect = process.argv[2] === '16x9' ? '16x9' : '9x16';

const FPS = Number(
  readFileSync(resolve(root, 'src/Root.tsx'), 'utf8').match(
    /export const FPS\s*=\s*(\d+(?:\.\d+)?)/,
  )[1],
);

// One entry point that re-exports everything the check needs, bundled together
// so the maths under test is exactly the maths that renders.
const shim = resolve(root, '.motion-check.entry.mjs');
const tmp = resolve(root, '.motion-check.tmp.mjs');
const {writeFileSync} = await import('node:fs');
writeFileSync(
  shim,
  `export {flightFor, driftsFor, hintSpeed} from './src/stage/flight';
export {stageSpeed} from './src/stage/Camera3D';
export {BLUR_FLOOR, BLUR_CEILING} from './src/overlays/lib';
export {layoutFor} from './src/theme';
export {TOTAL_SEC} from './src/timing/beats';
`,
);

await esbuild.build({
  entryPoints: [shim],
  bundle: true,
  format: 'esm',
  platform: 'node',
  outfile: tmp,
  logLevel: 'silent',
  // React only appears in type positions here; stub it so the bundle is pure JS.
  external: ['react', 'react/jsx-runtime', 'remotion', '@remotion/motion-blur'],
});

const mod = await import(pathToFileURL(tmp).href);
rmSync(tmp, {force: true});
rmSync(shim, {force: true});

const {flightFor, driftsFor, hintSpeed, stageSpeed, BLUR_FLOOR, BLUR_CEILING, layoutFor, TOTAL_SEC} = mod;

const layout = layoutFor(aspect);
const keys = flightFor(layout, FPS);
const drifts = driftsFor(FPS);
const total = Math.round(TOTAL_SEC * FPS);

const LIMIT = 40;
let maxSpeed = 0;
let maxFrame = 0;
const unblurred = [];
const fast = [];

for (let f = 0; f < total; f++) {
  const sec = f / FPS;
  const cam = stageSpeed(sec, Math.max(0, sec - 1 / FPS), keys, layout, drifts);
  const hint = hintSpeed(sec, FPS, layout);
  const speed = Math.max(cam, hint);
  const trailOpacity =
    speed <= BLUR_FLOOR
      ? 0
      : Math.min(1, (speed - BLUR_FLOOR) / (BLUR_CEILING - BLUR_FLOOR)) * 0.85;

  if (speed > maxSpeed) {
    maxSpeed = speed;
    maxFrame = f;
  }
  if (speed > LIMIT) {
    fast.push({f, sec, speed, trailOpacity});
    if (trailOpacity <= 0) unblurred.push({f, sec, speed});
  }
}

console.log(`${aspect} @ ${FPS} fps, ${total} frames\n`);
console.log(`fastest frame       ${maxFrame} (${(maxFrame / FPS).toFixed(2)}s) at ${maxSpeed.toFixed(1)} px/frame`);
console.log(`frames over ${LIMIT}px    ${fast.length}`);
console.log(`blur floor          ${BLUR_FLOOR} px/frame (trailOpacity starts ramping here)\n`);

if (fast.length > 0) {
  const lo = Math.min(...fast.map((x) => x.trailOpacity));
  console.log(`every frame over ${LIMIT}px carries trailOpacity >= ${lo.toFixed(3)}`);
  const groups = [];
  let cur = null;
  for (const x of fast) {
    if (cur && x.f === cur.end + 1) cur.end = x.f;
    else {
      cur = {start: x.f, end: x.f};
      groups.push(cur);
    }
  }
  console.log(`\nfast moves (frame ranges):`);
  for (const g of groups) {
    const peak = Math.max(...fast.filter((x) => x.f >= g.start && x.f <= g.end).map((x) => x.speed));
    console.log(
      `  ${String(g.start).padStart(4)}..${String(g.end).padEnd(4)}  ` +
        `${(g.start / FPS).toFixed(2)}s..${(g.end / FPS).toFixed(2)}s   peak ${peak.toFixed(0)} px/frame`,
    );
  }
}

console.log(
  `\n${unblurred.length === 0
    ? `PASS — no frame moves faster than ${LIMIT}px without motion blur`
    : `FAIL — ${unblurred.length} unblurred frame(s) over ${LIMIT}px: ${unblurred
        .slice(0, 10)
        .map((x) => x.f)
        .join(', ')}`}`,
);
process.exit(unblurred.length === 0 ? 0 : 1);
