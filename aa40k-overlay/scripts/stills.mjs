#!/usr/bin/env node
/**
 * Renders the three reference stills — the "40%" impact, the "DIRECTLY" moment
 * and the end card — plus a grey-composited copy of each so the look can be
 * judged without an alpha-aware viewer.
 *
 *   node scripts/stills.mjs      (or: npm run stills)
 *
 * Frames are derived from `src/timing/beats.ts`, so they follow the voice-over
 * if you re-transcribe rather than needing to be looked up again.
 */

import esbuild from 'esbuild';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {mkdirSync, readFileSync, rmSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
const FFMPEG = require('ffmpeg-static');
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const FPS = Number(
  readFileSync(resolve(root, 'src/Root.tsx'), 'utf8').match(
    /export const FPS\s*=\s*(\d+(?:\.\d+)?)/,
  )[1],
);

const tmp = resolve(root, '.stills.tmp.mjs');
await esbuild.build({
  entryPoints: [resolve(root, 'src/timing/beats.ts')],
  bundle: true,
  format: 'esm',
  platform: 'node',
  outfile: tmp,
  logLevel: 'silent',
});
const {LEAD_FRAMES, TOTAL_SEC, t} = await import(pathToFileURL(tmp).href);
rmSync(tmp, {force: true});

const hit = (sec) => Math.round(sec * FPS) - LEAD_FRAMES;

const SHOTS = [
  // The literal impact frame catches the lockup half-built — "AT FAULT" does
  // not wipe in until `t.fault`. This is the same beat a dozen frames later,
  // where the whole "40% AT FAULT" stamp is on screen and worth judging.
  {name: 'still_01_forty_stamp', frame: hit(t.fault) + 12, what: 'the "40% AT FAULT" stamp, complete'},
  {name: 'still_02_directly', frame: hit(t.directly) + 12, what: '"DIRECTLY" travelling the match line'},
  {name: 'still_03_end_card', frame: Math.round(TOTAL_SEC * FPS) - 30, what: 'the end card, still'},
];

const outDir = resolve(root, 'out/stills');
mkdirSync(outDir, {recursive: true});

for (const shot of SHOTS) {
  const png = resolve(outDir, `${shot.name}.png`);
  execFileSync(
    'npx',
    ['remotion', 'still', 'AA40K-9x16', png, `--frame=${shot.frame}`, '--image-format=png', '--log=error'],
    {cwd: root, stdio: 'inherit'},
  );
  // a grey-composited twin, so the frame reads without an alpha-aware viewer
  execFileSync(FFMPEG, [
    '-y', '-loglevel', 'error',
    '-f', 'lavfi', '-i', 'color=c=0x808080:s=1080x1920',
    '-i', png,
    '-filter_complex', '[0:v][1:v]overlay=format=auto',
    '-frames:v', '1',
    resolve(outDir, `${shot.name}_over_grey.png`),
  ]);
  console.log(`[stills] frame ${shot.frame}  ${shot.name}  — ${shot.what}`);
}
console.log(`[stills] wrote ${SHOTS.length} stills (+ grey composites) to out/stills/`);
