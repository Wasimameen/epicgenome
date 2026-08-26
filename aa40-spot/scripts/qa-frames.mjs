// Renders a set of frames from a composition in one bundle pass — much
// faster than N invocations of `npx remotion still`.
//
//   node scripts/qa-frames.mjs <compositionId> <scale> <frame> [frame...]
//   node scripts/qa-frames.mjs AA40-9x16 0.5 30 71 115 166
//
// Output: qa/frames/<compositionId>_<frame>.png

import path from 'node:path';
import fs from 'node:fs';
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';

const [, , compositionId = 'AA40-9x16', scaleArg = '0.5', ...frameArgs] = process.argv;
const scale = Number(scaleArg);
const frames = frameArgs.map(Number);

if (frames.length === 0) {
	console.error('usage: node scripts/qa-frames.mjs <comp> <scale> <frame...>');
	process.exit(1);
}

const ROOT = process.cwd();
const OUT = path.join(ROOT, 'qa', 'frames');
fs.mkdirSync(OUT, {recursive: true});

const browserExecutable =
	process.env.REMOTION_BROWSER ??
	'/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';

console.log('[qa] bundling…');
const serveUrl = await bundle({
	entryPoint: path.join(ROOT, 'src', 'index.ts'),
	onProgress: () => undefined,
});

const composition = await selectComposition({
	serveUrl,
	id: compositionId,
	browserExecutable,
});

console.log(
	`[qa] ${composition.id} ${composition.width}x${composition.height} ` +
		`${composition.durationInFrames}f @${composition.fps}fps, scale ${scale}`,
);

for (const frame of frames) {
	const output = path.join(OUT, `${compositionId}_${String(frame).padStart(4, '0')}.png`);
	await renderStill({
		composition,
		serveUrl,
		output,
		frame,
		scale,
		browserExecutable,
		imageFormat: 'png',
		overwrite: true,
		chromiumOptions: {gl: 'angle'},
	});
	console.log(
		`[qa] frame ${String(frame).padStart(4)}  ${(frame / composition.fps).toFixed(2)}s  ->  ${path.relative(
			ROOT,
			output,
		)}`,
	);
}

console.log('[qa] done');
process.exit(0);
