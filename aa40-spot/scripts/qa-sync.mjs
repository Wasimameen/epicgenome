// Sync check (§9.1): for every sync word, pull the frame at
// wordFrame - LEAD and the frame 6 later out of the RENDERED file, so
// what gets inspected is the deliverable and not the Studio.
//
//   node scripts/qa-sync.mjs out/aa40_9x16.mp4 [fps]
//
// Output: qa/sync/<key>_a_<frame>.png (should have STARTED)
//         qa/sync/<key>_b_<frame>.png (should have LANDED)

import path from 'node:path';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';

const [, , file = 'out/aa40_9x16.mp4', fpsArg = '30'] = process.argv;
const fps = Number(fpsArg);
const ROOT = process.cwd();
const OUT = path.join(ROOT, 'qa', 'sync');

const mapPath = path.join(ROOT, 'qa', 'sync-map.json');
if (!fs.existsSync(mapPath)) {
	console.error('qa/sync-map.json missing — run `node scripts/print-beats.mjs` first.');
	process.exit(1);
}
const map = JSON.parse(fs.readFileSync(mapPath, 'utf8'));

fs.rmSync(OUT, {recursive: true, force: true});
fs.mkdirSync(OUT, {recursive: true});

const GAP = 6; // frames between "started" and "landed"
const tag = path.basename(file).replace(/\.[^.]+$/, '');

// The ffmpeg Remotion ships has a small filter whitelist with no
// `select`, so frames come out by seeking. `-ss` placed AFTER `-i`
// decodes from the start and stops on the requested timestamp, which is
// frame-accurate; half a frame of offset lands mid-frame, safely away
// from either boundary.
const extract = (frame, out) => {
	const res = spawnSync(
		'npx',
		[
			'remotion',
			'ffmpeg',
			'-hide_banner',
			'-loglevel',
			'error',
			'-y',
			'-i',
			file,
			'-ss',
			String((frame + 0.5) / fps),
			'-frames:v',
			'1',
			out,
		],
		{encoding: 'utf8'},
	);
	if (res.status !== 0) {
		console.error(`  ! frame ${frame}: ${(res.stderr ?? '').trim().split('\n').pop()}`);
		return false;
	}
	return fs.existsSync(out);
};

// Sync points only — line1/line2 are structural, not hits.
const SKIP = new Set(['line1', 'line2', 'end']);

console.log(`[sync] ${file} @ ${fps}fps  (LEAD = ${map.lead} frames, gap ${GAP})`);
let n = 0;
for (const row of map.sync) {
	if (SKIP.has(row.key)) continue;
	const a = row.hitFrame;
	const b = row.hitFrame + GAP;
	const fa = path.join(OUT, `${tag}_${row.key}_a_${String(a).padStart(4, '0')}.png`);
	const fb = path.join(OUT, `${tag}_${row.key}_b_${String(b).padStart(4, '0')}.png`);
	const ok = extract(a, fa) && extract(b, fb);
	if (ok) n++;
	console.log(
		`  ${row.key.padEnd(12)} word ${String(row.frame).padStart(4)}  ` +
			`hit ${String(a).padStart(4)} → ${String(b).padStart(4)}  ${ok ? '' : 'FAILED'}`,
	);
}
console.log(`[sync] wrote ${n * 2} frames to qa/sync`);
