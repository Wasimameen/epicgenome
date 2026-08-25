/**
 * Fails loudly if a supposedly-transparent render has no alpha plane.
 *
 * Remotion will happily write a file that reports ProRes profile 4444 while
 * carrying pixel format yuv422p12le — the profile looks right, the alpha is
 * simply absent, and the file is silently opaque. Run this before shipping.
 */
import {execFileSync} from 'node:child_process';
import {existsSync} from 'node:fs';

const file = process.argv[2];
if (!file || !existsSync(file)) {
  console.error(`verify-alpha: no such file: ${file ?? '(none given)'}`);
  process.exit(1);
}

const probe = ['linux-x64-gnu', 'linux-x64-musl', 'darwin-x64', 'darwin-arm64', 'win32-x64']
  .map((p) => `node_modules/@remotion/compositor-${p}/ffprobe`)
  .find(existsSync) ?? 'ffprobe';

const pixFmt = execFileSync(probe, [
  '-v', 'error',
  '-select_streams', 'v:0',
  '-show_entries', 'stream=pix_fmt',
  '-of', 'csv=p=0',
  file,
]).toString().trim();

if (!pixFmt.startsWith('yuva') && !pixFmt.includes('rgba') && !pixFmt.includes('argb')) {
  console.error(`verify-alpha: FAIL — ${file} has pix_fmt "${pixFmt}", which carries no alpha.`);
  console.error('Re-render with --pixel-format=yuva444p10le');
  process.exit(1);
}

console.log(`verify-alpha: OK — ${file} has pix_fmt "${pixFmt}" (alpha present).`);
