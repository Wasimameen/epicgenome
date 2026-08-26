// Pulls frames out of a rendered file by timestamp — used for the
// legibility / safe-zone pass (§9.2) and for scrubbing a move frame by
// frame (§9.3).
//
//   node scripts/qa-extract.mjs out/aa40_9x16.mp4 1.0 4.8 6.5
//   node scripts/qa-extract.mjs out/aa40_9x16.mp4 --frames 30 31 32 33
//
// Output: qa/extract/<tag>_<frame>.png

import path from 'node:path';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';

const argv = process.argv.slice(2);
const file = argv.shift();
const byFrame = argv[0] === '--frames';
if (byFrame) argv.shift();
const values = argv.map(Number);
const FPS = 30;

if (!file || values.length === 0) {
	console.error('usage: node scripts/qa-extract.mjs <file> [--frames] <n...>');
	process.exit(1);
}

const ROOT = process.cwd();
const OUT = path.join(ROOT, 'qa', 'extract');
fs.mkdirSync(OUT, {recursive: true});
const tag = path.basename(file).replace(/\.[^.]+$/, '');

for (const v of values) {
	const frame = byFrame ? v : Math.round(v * FPS);
	const out = path.join(OUT, `${tag}_${String(frame).padStart(4, '0')}.png`);
	const res = spawnSync(
		'npx',
		[
			'remotion', 'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
			'-i', file,
			'-ss', String((frame - 0.4) / FPS),
			'-frames:v', '1',
			out,
		],
		{encoding: 'utf8'},
	);
	const ok = res.status === 0 && fs.existsSync(out);
	console.log(
		`  frame ${String(frame).padStart(4)}  ${(frame / FPS).toFixed(2)}s  ${
			ok ? path.relative(ROOT, out) : 'FAILED'
		}`,
	);
}
