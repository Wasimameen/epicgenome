#!/usr/bin/env node
/**
 * Writes `out/sync-sheet.md` — every key word, the second it is spoken, and the
 * frame its visual actually lands on, so alignment can be checked in the editor
 * without scrubbing.
 *
 *   node scripts/sync-sheet.mjs      (or: npm run sync-sheet)
 *
 * It reads the same `src/timing/beats.ts` the render does (compiled on the fly
 * with esbuild) and the single `FPS` constant out of `src/Root.tsx`, so the
 * sheet can never drift from the video.
 */

import esbuild from 'esbuild';
import {mkdirSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/* the one fps constant, read from where it is declared -------------- */
const rootTsx = readFileSync(resolve(root, 'src/Root.tsx'), 'utf8');
const fpsMatch = rootTsx.match(/export const FPS\s*=\s*(\d+(?:\.\d+)?)/);
if (!fpsMatch) {
  console.error('[sync-sheet] could not find `export const FPS = ...` in src/Root.tsx');
  process.exit(1);
}
const FPS = Number(fpsMatch[1]);

/* compile beats.ts so there is exactly one source of truth ---------- */
const tmp = resolve(root, '.sync-sheet.tmp.mjs');
await esbuild.build({
  entryPoints: [resolve(root, 'src/timing/beats.ts')],
  bundle: true,
  format: 'esm',
  platform: 'node',
  outfile: tmp,
  logLevel: 'silent',
});
const beats = await import(pathToFileURL(tmp).href);
rmSync(tmp, {force: true});

const {BEATS, KEY_WORDS, LEAD_FRAMES, TOTAL_SEC, VO_SOURCE, t} = beats;

const fr = (sec) => Math.round(sec * FPS);
const tc = (sec) => {
  const total = Math.max(0, sec);
  const m = Math.floor(total / 60);
  const s = Math.floor(total % 60);
  const f = Math.round((total - Math.floor(total)) * FPS);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
};

const rows = KEY_WORDS.map(({key, spoken, beat}) => {
  const sec = t[key];
  const spokenFrame = fr(sec);
  const visualFrame = key === 'end' ? spokenFrame : spokenFrame - LEAD_FRAMES;
  return `| ${beat} | \`${key}\` | ${spoken} | ${sec.toFixed(2)}s | ${tc(sec)} | ${spokenFrame} | **${visualFrame}** |`;
}).join('\n');

const beatRows = [
  ['1 — deflated', BEATS.b1],
  ['2 — knowing', BEATS.b2],
  ['3 — warm, energetic', BEATS.b3],
  ['4 — decisive + end card', BEATS.b4],
]
  .map(([name, w]) =>
    `| ${name} | ${w.start.toFixed(2)}s | ${w.end.toFixed(2)}s | ${fr(w.start)} | ${fr(w.end)} | ${w.duration.toFixed(2)}s |`,
  )
  .join('\n');

const md = `# Sync sheet — "40% At Fault" overlay

Frame **0 of the .mov is the first frame of the voice-over**. Line the overlay's
in-point up with the VO's in-point in your timeline and everything below is
where it says it is.

- **Frame rate:** ${FPS} fps (\`FPS\` in \`src/Root.tsx\` — change it there and nothing else)
- **Total length:** ${TOTAL_SEC.toFixed(2)}s = ${fr(TOTAL_SEC)} frames
- **Lead:** every visual lands **${LEAD_FRAMES} frames before** its word is spoken
- **Timing source:** ${
  VO_SOURCE === 'whisper'
    ? 'whisper transcription of `assets-in/vo.mp3`'
    : '**fallback table (spec §4.2)** — no `assets-in/vo.mp3` was supplied. Drop the final VO there, run `npm run vo`, then re-render; every beat re-derives with no other edit.'
}

## Key words

| Beat | Key | Spoken | Time | TC (mm:ss:ff) | Spoken frame | **Visual lands** |
|---|---|---|---|---|---|---|
${rows}

## Beat windows

| Beat | Start | End | Start frame | End frame | Length |
|---|---|---|---|---|---|
${beatRows}

## Checking alignment in the editor

1. Put the overlay \`.mov\` on the track above your footage, both starting on the
   VO's first frame.
2. Park on a **Visual lands** frame from the table. The move for that word should
   have *started* on it and be settled about six frames later.
3. If the whole thing reads late or early, your VO in-point is off by that many
   frames — nudge the overlay, don't re-render.
`;

mkdirSync(resolve(root, 'out'), {recursive: true});
writeFileSync(resolve(root, 'out/sync-sheet.md'), md);
console.log(`[sync-sheet] wrote out/sync-sheet.md (${FPS} fps, ${fr(TOTAL_SEC)} frames, source: ${VO_SOURCE})`);
