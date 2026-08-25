/**
 * Fails loudly if a supposedly-transparent render has no alpha plane.
 *
 * Two silent-failure modes prompted this:
 *  - Remotion will write a ProRes file that reports profile 4444 while
 *    carrying pixel format yuv422p12le — profile right, alpha absent.
 *  - QuickTime Animation exposes no stream-level pix_fmt at all ("unknown"),
 *    and Remotion's bundled ffprobe cannot decode qtrle, so only a
 *    full-featured ffprobe can prove the alpha by decoding a frame.
 *
 * Strategy: try stream-level pix_fmt first; if inconclusive, decode one frame
 * with each available ffprobe (system first, Remotion's compositor as
 * fallback) and check the decoded frame's pixel format.
 */
import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';

const file = process.argv[2];
if (!file || !existsSync(file)) {
  console.error(`verify-alpha: no such file: ${file ?? '(none given)'}`);
  process.exit(1);
}

const ALPHA_FMTS = (fmt) =>
  fmt.startsWith('yuva') ||
  fmt.includes('rgba') ||
  fmt.includes('argb') ||
  fmt.includes('bgra') ||
  fmt.includes('gbrap') ||
  fmt.includes('ya8') ||
  fmt.includes('ya16');

const candidates = [
  'ffprobe', // full-featured system build, when present
  ...['linux-x64-gnu', 'linux-x64-musl', 'darwin-x64', 'darwin-arm64', 'win32-x64'].map(
    (p) => `node_modules/@remotion/compositor-${p}/ffprobe`,
  ),
];

const run = (bin, args) => {
  try {
    return execFileSync(bin, args, {stdio: ['ignore', 'pipe', 'ignore']}).toString().trim();
  } catch {
    return null;
  }
};

let streamInfo = null;
let usable = [];
for (const bin of candidates) {
  if (bin !== 'ffprobe' && !existsSync(bin)) continue;
  const out = run(bin, [
    '-v', 'error',
    '-select_streams', 'v:0',
    '-show_entries', 'stream=codec_name,pix_fmt',
    '-of', 'csv=p=0',
    file,
  ]);
  if (out) {
    usable.push(bin);
    if (!streamInfo) streamInfo = out;
  }
}

if (!streamInfo) {
  console.error('verify-alpha: no working ffprobe found to inspect the file.');
  process.exit(1);
}

const [codec, pixFmt = 'unknown'] = streamInfo.split(',');

if (ALPHA_FMTS(pixFmt)) {
  console.log(`verify-alpha: OK — ${file} (codec ${codec}, pix_fmt "${pixFmt}") has alpha.`);
  process.exit(0);
}

// Stream level was inconclusive or negative; the decoded frame is the truth.
for (const bin of usable) {
  const frames = run(bin, [
    '-v', 'error',
    '-select_streams', 'v:0',
    '-show_frames',
    '-show_entries', 'frame=pix_fmt',
    '-of', 'csv=p=0',
    '-read_intervals', '%+2',
    file,
  ]);
  const frameFmt = frames?.split('\n')[0]?.split(',')[0]?.trim();
  if (frameFmt) {
    if (ALPHA_FMTS(frameFmt)) {
      console.log(
        `verify-alpha: OK — ${file} (codec ${codec}) decodes to "${frameFmt}" (alpha present).`,
      );
      process.exit(0);
    }
    console.error(
      `verify-alpha: FAIL — ${file} (codec ${codec}) decodes to "${frameFmt}", which carries no alpha.`,
    );
    console.error('For ProRes, re-render with --pixel-format=yuva444p10le; for qtrle, use -pix_fmt argb.');
    process.exit(1);
  }
}

console.error(
  `verify-alpha: FAIL — ${file} (codec ${codec}, pix_fmt "${pixFmt}"): stream reports no alpha and no available ffprobe could decode a frame to prove otherwise.`,
);
process.exit(1);
