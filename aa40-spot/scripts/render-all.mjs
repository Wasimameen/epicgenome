// Renders every deliverable: two full H.264 spots, four alpha overlays
// (ProRes 4444 + VP9), and the two end-card thumbnails.
//
//   node scripts/render-all.mjs [only]
//
// `only` filters by substring, e.g. `node scripts/render-all.mjs overlay`.

import path from 'node:path';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {build} from 'esbuild';
import {pathToFileURL} from 'node:url';

const ROOT = process.cwd();
const OUT = path.join(ROOT, 'out');
fs.mkdirSync(OUT, {recursive: true});

const browser =
	process.env.REMOTION_BROWSER ??
	'/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';

// Resolve the end-card frame from beats.ts rather than hard-coding it.
const tmp = path.join(ROOT, 'node_modules', '.cache', 'beats-render.mjs');
await build({
	entryPoints: [path.join(ROOT, 'src', 'timing', 'beats.ts')],
	outfile: tmp,
	bundle: true,
	format: 'esm',
	platform: 'node',
	logLevel: 'error',
});
const {t} = await import(pathToFileURL(tmp).href);
const FPS = 30;
const THUMB_FRAME = Math.round((t.end + 1.4) * FPS);

const only = process.argv[2];

const JOBS = [
	{
		name: 'full 9x16',
		args: ['render', 'AA40-9x16', 'out/aa40_9x16.mp4', '--codec=h264', '--crf=16', '--audio-bitrate=320k'],
	},
	{
		name: 'full 16x9',
		args: ['render', 'AA40-16x9', 'out/aa40_16x9.mp4', '--codec=h264', '--crf=16', '--audio-bitrate=320k'],
	},
	{
		name: 'alpha 9x16 prores',
		args: [
			'render', 'AA40-9x16-overlay', 'out/aa40_9x16_alpha.mov',
			'--codec=prores', '--prores-profile=4444', '--image-format=png',
			'--pixel-format=yuva444p10le', '--muted',
		],
	},
	{
		name: 'alpha 9x16 webm',
		args: [
			'render', 'AA40-9x16-overlay', 'out/aa40_9x16_alpha.webm',
			'--codec=vp9', '--pixel-format=yuva420p', '--image-format=png', '--muted',
		],
	},
	{
		name: 'alpha 16x9 prores',
		args: [
			'render', 'AA40-16x9-overlay', 'out/aa40_16x9_alpha.mov',
			'--codec=prores', '--prores-profile=4444', '--image-format=png',
			'--pixel-format=yuva444p10le', '--muted',
		],
	},
	{
		name: 'alpha 16x9 webm',
		args: [
			'render', 'AA40-16x9-overlay', 'out/aa40_16x9_alpha.webm',
			'--codec=vp9', '--pixel-format=yuva420p', '--image-format=png', '--muted',
		],
	},
	{
		name: 'thumb 9x16',
		args: ['still', 'AA40-9x16', 'out/thumb_9x16.png', `--frame=${THUMB_FRAME}`],
	},
	{
		name: 'thumb 16x9',
		args: ['still', 'AA40-16x9', 'out/thumb_16x9.png', `--frame=${THUMB_FRAME}`],
	},
];

console.log(`[render] end-card thumbnail frame = ${THUMB_FRAME} (${(THUMB_FRAME / FPS).toFixed(2)}s)`);

let failed = 0;
for (const job of JOBS) {
	if (only && !job.name.includes(only)) continue;
	const started = process.hrtime.bigint();
	process.stdout.write(`[render] ${job.name}… `);
	const res = spawnSync(
		'npx',
		['remotion', ...job.args, `--browser-executable=${browser}`, '--log=error'],
		{encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']},
	);
	const secs = Number(process.hrtime.bigint() - started) / 1e9;
	if (res.status !== 0) {
		failed++;
		console.log(`FAILED (${secs.toFixed(0)}s)`);
		console.log((res.stderr ?? '').split('\n').slice(-14).join('\n'));
		continue;
	}
	const outFile = path.join(ROOT, job.args[2]);
	const size = fs.existsSync(outFile) ? fs.statSync(outFile).size : 0;
	console.log(`ok  ${(size / 1e6).toFixed(1)} MB  ${secs.toFixed(0)}s`);
}

process.exit(failed > 0 ? 1 : 0);
