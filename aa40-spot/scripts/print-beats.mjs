// Prints the resolved sync map — word -> seconds -> frame — exactly as
// the compositions see it. Used by the QA pass and by out/README.md.
//
//   node scripts/print-beats.mjs [fps]

import {build} from 'esbuild';
import path from 'node:path';
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';

const fps = Number(process.argv[2] ?? 30);
const ROOT = process.cwd();
const tmp = path.join(ROOT, 'node_modules', '.cache', 'beats.mjs');

await build({
	entryPoints: [path.join(ROOT, 'src', 'timing', 'beats.ts')],
	outfile: tmp,
	bundle: true,
	format: 'esm',
	platform: 'node',
	logLevel: 'error',
});

const mod = await import(pathToFileURL(tmp).href);
const {t, LEAD, END_HOLD, TOTAL_SEC, BEAT, timingSource, timingMatched, timingMissed} =
	mod;

const rows = Object.entries(t).sort((a, b) => a[1] - b[1]);

const out = {
	source: timingSource,
	fps,
	lead: LEAD,
	endHold: END_HOLD,
	totalSec: Number(TOTAL_SEC.toFixed(3)),
	totalFrames: Math.round(TOTAL_SEC * fps),
	matched: timingMatched,
	missed: timingMissed,
	beats: Object.fromEntries(
		Object.entries(BEAT)
			.filter(([, v]) => v && typeof v === 'object')
			.map(([k, v]) => [
				k,
				{startSec: Number(v.start.toFixed(3)), endSec: Number(v.end.toFixed(3))},
			]),
	),
	sync: rows.map(([key, sec]) => ({
		key,
		sec: Number(sec.toFixed(3)),
		frame: Math.round(sec * fps),
		hitFrame: Math.round(sec * fps) - LEAD,
	})),
};

fs.mkdirSync(path.join(ROOT, 'qa'), {recursive: true});
fs.writeFileSync(path.join(ROOT, 'qa', 'sync-map.json'), JSON.stringify(out, null, 2));

console.log(`timing source : ${out.source}`);
console.log(`duration      : ${out.totalSec}s = ${out.totalFrames} frames @ ${fps}fps`);
if (out.missed.length) console.log(`missed anchors: ${out.missed.join(', ')}`);
console.log('');
console.log('key           seconds   frame   hit(-LEAD)');
for (const r of out.sync) {
	console.log(
		`${r.key.padEnd(12)}  ${String(r.sec).padStart(7)}   ${String(r.frame).padStart(5)}   ${String(
			r.hitFrame,
		).padStart(5)}`,
	);
}
console.log('');
for (const [k, v] of Object.entries(out.beats)) {
	console.log(`beat ${k.padEnd(6)} ${v.startSec}s → ${v.endSec}s`);
}
