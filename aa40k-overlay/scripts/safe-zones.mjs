#!/usr/bin/env node
/**
 * Measures, rather than eyeballs, whether anything strays outside the safe area.
 *
 *   node scripts/safe-zones.mjs <mov> <9x16|16x9> [frame,frame,...]
 *
 * For each frame it pulls the alpha channel as raw gray8 and finds the bounding
 * box of *solid* pixels (alpha >= 0.85). That threshold is chosen so the
 * ambient particles (peak alpha 0.77) and the soft shadows fall out of the
 * measurement and only real type and icons are counted.
 *
 * A frame whose solid coverage is ~100% is a card beat: the plate legitimately
 * fills the frame, so the bounding-box test is skipped and only the fact that it
 * *is* a full plate is reported.
 *
 * Safe areas (spec §3):
 *   9x16 — clear of the top 14% and the bottom 22%, 6% at the sides
 *   16x9 — 5% on all sides
 */

import {execFileSync, spawnSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';

const require = createRequire(import.meta.url);
const FFMPEG = require('ffmpeg-static');
const FFPROBE = require('ffprobe-static').path;

const [, , movArg, aspectArg, framesArg] = process.argv;
if (!movArg || !aspectArg) {
  console.error('usage: safe-zones.mjs <mov> <9x16|16x9> [frames]');
  process.exit(2);
}
const mov = resolve(movArg);

const SAFE = {
  '9x16': {w: 1080, h: 1920, top: 0.14, bottom: 0.22, side: 0.06},
  '16x9': {w: 1920, h: 1080, top: 0.05, bottom: 0.05, side: 0.05},
};
const cfg = SAFE[aspectArg];
if (!cfg) {
  console.error(`unknown aspect "${aspectArg}"`);
  process.exit(2);
}

const probe = execFileSync(FFPROBE, [
  '-v', 'error', '-select_streams', 'v:0',
  '-show_entries', 'stream=width,height,nb_frames',
  '-of', 'default=nw=1', mov,
], {encoding: 'utf8'});
const W = Number(probe.match(/^width=(\d+)$/m)[1]);
const H = Number(probe.match(/^height=(\d+)$/m)[1]);
const N = Number(probe.match(/^nb_frames=(\d+)$/m)[1]);

const bounds = {
  left: Math.round(W * cfg.side),
  right: Math.round(W * (1 - cfg.side)),
  top: Math.round(H * cfg.top),
  bottom: Math.round(H * (1 - cfg.bottom)),
};

// Default sweep: the times §11.5 calls out, plus the first and last frame.
const DEFAULT_SECONDS = [1.0, 2.0, 4.6, 6.2, 8.7, 9.4, 10.5, 12.6, 13.8, 15.0, 17.5];
const fps = 30;
const frames = framesArg
  ? framesArg.split(',').map((n) => Number(n.trim()))
  : [0, ...DEFAULT_SECONDS.map((s) => Math.round(s * fps)), N - 1].filter((f) => f < N);

const THRESHOLD = Math.round(0.85 * 255);

let failures = 0;
console.log(`${mov}`);
console.log(`${W}x${H}, ${N} frames — safe box x[${bounds.left}..${bounds.right}] y[${bounds.top}..${bounds.bottom}]\n`);

for (const f of frames) {
  const {stdout} = spawnSync(
    FFMPEG,
    ['-v', 'error', '-i', mov,
      '-vf', `select='eq(n\\,${f})',format=rgba,alphaextract`,
      '-fps_mode', 'passthrough', '-frames:v', '1',
      '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
    {maxBuffer: 1 << 30},
  );
  const buf = stdout;
  if (!buf || buf.length < W * H) {
    console.log(`frame ${String(f).padStart(4)}  — could not read alpha`);
    continue;
  }

  let minX = W, minY = H, maxX = -1, maxY = -1, solid = 0;
  for (let y = 0; y < H; y++) {
    const row = y * W;
    for (let x = 0; x < W; x++) {
      if (buf[row + x] >= THRESHOLD) {
        solid++;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }

  const coverage = solid / (W * H);
  const label = `frame ${String(f).padStart(4)} (${(f / fps).toFixed(2)}s)`;

  if (solid === 0) {
    console.log(`${label}  EMPTY — fully transparent`);
    continue;
  }
  if (coverage > 0.985) {
    console.log(`${label}  CARD  — solid plate, ${(coverage * 100).toFixed(1)}% coverage`);
    continue;
  }

  const bad = [];
  if (minX < bounds.left) bad.push(`left by ${bounds.left - minX}px`);
  if (maxX > bounds.right) bad.push(`right by ${maxX - bounds.right}px`);
  if (minY < bounds.top) bad.push(`top by ${bounds.top - minY}px`);
  if (maxY > bounds.bottom) bad.push(`bottom by ${maxY - bounds.bottom}px`);

  const box = `x[${minX}..${maxX}] y[${minY}..${maxY}]`;
  if (bad.length === 0) {
    console.log(`${label}  ok    ${box}`);
  } else {
    failures++;
    console.log(`${label}  OUT   ${box}  -> ${bad.join(', ')}`);
  }
}

console.log(`\n${failures === 0 ? 'PASS — nothing outside the safe area' : `${failures} frame(s) outside the safe area`}`);
process.exit(failures === 0 ? 0 : 1);
