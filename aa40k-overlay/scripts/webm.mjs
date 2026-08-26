#!/usr/bin/env node
/**
 * Builds the VP9 + alpha `.webm` fallback from the ProRes master.
 *
 *   node scripts/webm.mjs      (or: npm run render:webm)
 *
 * Why a transcode and not a second Remotion render:
 *
 * Remotion refuses to render when a ProRes profile is set and the codec is not
 * ProRes, and a profile set in `calculateMetadata` (which is what makes a
 * Studio export default to 4444, i.e. to *having alpha at all*) cannot be unset
 * from the command line. So `remotion render ... --codec=vp9` on these
 * compositions always throws.
 *
 * Transcoding is the better answer regardless: the webm comes out
 * frame-identical to the master rather than re-rendered, and it takes a fraction
 * of the time. Remotion's bundled ffmpeg decodes ProRes and encodes libvpx-vp9,
 * so there is nothing extra to install.
 */

import {execFileSync} from 'node:child_process';
import {existsSync, statSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const src = resolve(root, process.argv[2] ?? 'out/aa40k_9x16_30fps_alpha.mov');
const dest = resolve(root, process.argv[3] ?? 'out/aa40k_9x16_30fps_alpha.webm');

if (!existsSync(src)) {
  console.error(`[webm] ${src} not found — run \`npm run render:9x16\` first.`);
  process.exit(1);
}

console.log(`[webm] ${src}\n    -> ${dest}`);

execFileSync(
  'npx',
  [
    'remotion', 'ffmpeg', '-y',
    '-i', src,
    '-c:v', 'libvpx-vp9',
    // yuva420p is the alpha-carrying VP9 pixel format
    '-pix_fmt', 'yuva420p',
    '-b:v', '0',
    '-crf', '28',
    '-row-mt', '1',
    '-an',
    dest,
  ],
  {cwd: root, stdio: ['ignore', 'inherit', 'inherit']},
);

const {size} = statSync(dest);
console.log(`[webm] done — ${(size / 1024 / 1024).toFixed(1)} MB`);
