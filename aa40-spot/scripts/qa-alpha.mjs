// Alpha verification (§9.5).
//
//   node scripts/qa-alpha.mjs
//
// Checks that every overlay deliverable actually carries alpha, then
// extracts the matte at frames 60 / 180 / 300 / 400 so it can be looked
// at. The matte must show foreground elements only — no gradient sky,
// no vignette, no grain.
//
// The ffmpeg Remotion ships is compiled with a small filter whitelist
// that has no `alphaextract` (and no `select`), so the matte is built
// here: ffmpeg writes an RGBA PNG, and the alpha channel is lifted into
// a greyscale PNG in Node.

import path from 'node:path';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {PNG} from 'pngjs';

const ROOT = process.cwd();
const OUT = path.join(ROOT, 'qa', 'alpha');
const FRAMES = [60, 180, 300, 400];
const FPS = 30;

/*
 * What "has alpha" actually looks like per container, which is not what
 * the render flags suggest:
 *
 *   ProRes 4444 — `prores_ks` promotes the stream to 12-bit whatever
 *   `--pixel-format=yuva444p10le` asks for, because ProRes 4444 IS a
 *   12-bit format. `yuva444p12le` is the correct, expected result; the
 *   leading "yuva" is the part that matters.
 *
 *   VP9 in WebM — alpha does not live in the pixel format at all. The
 *   coded video track is plain `yuv420p` and the alpha travels beside it
 *   in BlockAdditional, flagged by the container tag `alpha_mode=1`.
 *   Asserting `yuva420p` here fails on a perfectly good file.
 *
 * So the string checks are loose and the real proof is empirical: decode
 * a frame to RGBA and require genuinely transparent pixels.
 */
const TARGETS = [
	{file: 'out/aa40_9x16_alpha.mov', pixFmtRe: /^yuva444p(10|12)le$/, matte: true},
	{
		file: 'out/aa40_9x16_alpha.webm',
		pixFmtRe: /^yuva?420p$/,
		needsAlphaMode: true,
		matte: true,
		decoder: 'libvpx-vp9',
	},
	{file: 'out/aa40_16x9_alpha.mov', pixFmtRe: /^yuva444p(10|12)le$/, matte: true},
	{
		file: 'out/aa40_16x9_alpha.webm',
		pixFmtRe: /^yuva?420p$/,
		needsAlphaMode: true,
		matte: true,
		decoder: 'libvpx-vp9',
	},
];

/** A frame of this spot is mostly empty; anything less means no alpha. */
const MIN_TRANSPARENT_PCT = 20;

fs.rmSync(OUT, {recursive: true, force: true});
fs.mkdirSync(OUT, {recursive: true});

const ffprobe = (args) =>
	spawnSync('npx', ['remotion', 'ffprobe', '-v', 'error', ...args], {
		encoding: 'utf8',
	});

let failures = 0;

for (const target of TARGETS) {
	const file = path.join(ROOT, target.file);
	if (!fs.existsSync(file)) {
		console.log(`✗ ${target.file}: missing`);
		failures++;
		continue;
	}

	const streams = ffprobe([
		'-select_streams', 'v:0',
		'-show_entries', 'stream=pix_fmt,codec_name,width,height',
		'-show_entries', 'stream_tags=alpha_mode',
		'-of', 'default=noprint_wrappers=1',
		file,
	]).stdout;

	const pixFmt = /pix_fmt=(\S+)/.exec(streams)?.[1];
	const codec = /codec_name=(\S+)/.exec(streams)?.[1];
	const alphaMode = /TAG:alpha_mode=(\S+)/.exec(streams)?.[1] ??
		/alpha_mode=(\S+)/.exec(streams)?.[1];

	const pixOk = target.pixFmtRe.test(pixFmt ?? '');
	const alphaOk = target.needsAlphaMode ? alphaMode === '1' : true;

	if (!pixOk || !alphaOk) failures++;
	console.log(
		`${pixOk && alphaOk ? '✓' : '✗'} ${target.file}  codec=${codec}  pix_fmt=${pixFmt}` +
			`${alphaMode ? `  alpha_mode=${alphaMode}` : ''}` +
			`${pixOk ? '' : `  EXPECTED ${target.pixFmtRe}`}` +
			`${alphaOk ? '' : '  EXPECTED alpha_mode=1'}`,
	);

	if (!target.matte) continue;

	const tag = path.basename(target.file).replace(/\.[^.]+$/, '');
	for (const frame of FRAMES) {
		const rgbaPath = path.join(OUT, `${tag}_${frame}_rgba.png`);
		const res = spawnSync(
			'npx',
			[
				'remotion', 'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
				// ffmpeg's NATIVE vp9 decoder silently discards the alpha that
				// WebM carries in BlockAdditional — it returns a fully opaque
				// frame and nothing warns you. libvpx-vp9 is the decoder that
				// reads it. Without this the matte comes back 100% opaque and
				// looks like a broken render rather than a broken read.
				...(target.decoder ? ['-c:v', target.decoder] : []),
				'-i', file,
				// Frame-accurate: seek after the input so ffmpeg decodes to the
				// timestamp rather than to the nearest keyframe.
				'-ss', String((frame - 0.4) / FPS),
				'-frames:v', '1',
				'-pix_fmt', 'rgba',
				rgbaPath,
			],
			{encoding: 'utf8'},
		);
		if (res.status !== 0 || !fs.existsSync(rgbaPath)) {
			console.log(`  ! frame ${frame}: extraction failed`);
			failures++;
			continue;
		}

		const png = PNG.sync.read(fs.readFileSync(rgbaPath));
		const matte = new PNG({width: png.width, height: png.height});
		let opaque = 0;
		let transparent = 0;
		for (let i = 0; i < png.data.length; i += 4) {
			const a = png.data[i + 3];
			matte.data[i] = a;
			matte.data[i + 1] = a;
			matte.data[i + 2] = a;
			matte.data[i + 3] = 255;
			if (a === 0) transparent++;
			else if (a === 255) opaque++;
		}
		const total = png.data.length / 4;
		const transparentPct = (transparent / total) * 100;
		const mattePath = path.join(OUT, `${tag}_${frame}_matte.png`);
		fs.writeFileSync(mattePath, PNG.sync.write(matte));
		fs.rmSync(rgbaPath);

		// The real proof: a decoded frame has to contain actually
		// transparent pixels. A file that lost its alpha comes back 0%.
		const carriesAlpha = transparentPct >= MIN_TRANSPARENT_PCT;
		if (!carriesAlpha) failures++;
		console.log(
			`  ${carriesAlpha ? '✓' : '✗'} frame ${String(frame).padStart(3)}  transparent ${transparentPct.toFixed(
				1,
			)}%  opaque ${((opaque / total) * 100).toFixed(1)}%  → ${path.relative(
				ROOT,
				mattePath,
			)}`,
		);
	}
}

console.log(failures === 0 ? '\n[alpha] all checks passed' : `\n[alpha] ${failures} failure(s)`);
process.exit(failures === 0 ? 0 : 1);
