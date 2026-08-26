// Transcribes public/vo.mp3 with word-level timestamps and writes
// src/timing/vo-words.json.
//
// Re-run this after dropping in a new vo.mp3:
//   node scripts/transcribe.mjs
//
// Everything downstream (beats.ts, composition duration, every sync
// point) re-derives from the JSON this produces. No component holds a
// frame number.
//
// Two details that matter for tight sync:
//   1. whisper.cpp's `t_dtw` is a token's END timestamp, not its start.
//      A word therefore runs from the previous token's t_dtw to its own.
//   2. Doing only that puts a word's "start" at the beginning of the
//      pause in front of it. So every onset that lands inside a silence
//      detected by ffmpeg is snapped forward to where speech actually
//      resumes. That is what makes hits land on the attack of the word.

import path from 'node:path';
import fs from 'node:fs';
import {execFileSync, spawnSync} from 'node:child_process';
import {
	downloadWhisperModel,
	installWhisperCpp,
	transcribe,
	toCaptions,
} from '@remotion/install-whisper-cpp';

const ROOT = process.cwd();
const WHISPER_DIR = path.join(ROOT, 'whisper.cpp');
const WHISPER_VERSION = '1.7.4';
const MODEL = 'medium.en';

const VO_MP3 = path.join(ROOT, 'public', 'vo.mp3');
const VO_WAV = path.join(ROOT, 'vo16.wav');
const OUT_DIR = path.join(ROOT, 'src', 'timing');
const OUT_JSON = path.join(OUT_DIR, 'vo-words.json');

const remotionFfmpeg = (args, {capture = false} = {}) =>
	execFileSync('npx', ['remotion', 'ffmpeg', ...args], {
		stdio: capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
		encoding: 'utf8',
	});

if (!fs.existsSync(VO_MP3)) {
	console.error('[transcribe] public/vo.mp3 missing — nothing to transcribe.');
	console.error('[transcribe] beats.ts will fall back to the §4 timing table.');
	process.exit(2);
}

/* -------------------------------------------------------------- *
 * 1. whisper.cpp + model
 * -------------------------------------------------------------- */

console.log('[transcribe] installing whisper.cpp', WHISPER_VERSION);
await installWhisperCpp({to: WHISPER_DIR, version: WHISPER_VERSION, printOutput: true});

console.log('[transcribe] downloading model', MODEL);
await downloadWhisperModel({model: MODEL, folder: WHISPER_DIR, printOutput: true});

console.log('[transcribe] converting vo.mp3 -> 16 kHz mono wav');
remotionFfmpeg(['-y', '-i', VO_MP3, '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', VO_WAV]);

/* -------------------------------------------------------------- *
 * 2. Audio facts: duration + where the speech actually pauses
 * -------------------------------------------------------------- */

const audioDurationMs = Math.round(
	Number(
		execFileSync(
			'npx',
			[
				'remotion',
				'ffprobe',
				'-v',
				'error',
				'-show_entries',
				'format=duration',
				'-of',
				'default=noprint_wrappers=1:nokey=1',
				VO_MP3,
			],
			{encoding: 'utf8'},
		).trim(),
	) * 1000,
);

const detectSilences = () => {
	// ffmpeg writes the silencedetect report to stderr even on success, so
	// spawnSync (not execFileSync) is required to read it back.
	const res = spawnSync(
		'npx',
		[
			'remotion',
			'ffmpeg',
			'-hide_banner',
			'-i',
			VO_MP3,
			'-af',
			'silencedetect=noise=-38dB:d=0.15',
			'-f',
			'null',
			'-',
		],
		{encoding: 'utf8'},
	);
	const stderr = `${res.stderr ?? ''}${res.stdout ?? ''}`;
	const out = [];
	const re = /silence_start:\s*([0-9.]+)[\s\S]*?silence_end:\s*([0-9.]+)/g;
	let m;
	while ((m = re.exec(stderr)) !== null) {
		out.push({startMs: Number(m[1]) * 1000, endMs: Number(m[2]) * 1000});
	}
	return out;
};

const silences = detectSilences();
console.log('[transcribe] detected', silences.length, 'silences');

/* -------------------------------------------------------------- *
 * 3. Transcribe
 * -------------------------------------------------------------- */

console.log('[transcribe] transcribing with token-level timestamps');
const whisperCppOutput = await transcribe({
	inputPath: VO_WAV,
	whisperPath: WHISPER_DIR,
	whisperCppVersion: WHISPER_VERSION,
	model: MODEL,
	tokenLevelTimestamps: true,
	language: 'en',
	printOutput: true,
});

const {captions} = toCaptions({whisperCppOutput});

/* -------------------------------------------------------------- *
 * 4. Tokens -> words
 * -------------------------------------------------------------- */

const rawTokens = [];
for (const item of whisperCppOutput.transcription) {
	for (const tok of item.tokens ?? []) {
		const text = tok.text ?? '';
		if (text.trim() === '') continue;
		if (/^\[.*\]$/.test(text.trim())) continue; // [_BEG_], [_TT_123]
		rawTokens.push({
			text,
			dtwMs: typeof tok.t_dtw === 'number' && tok.t_dtw >= 0 ? tok.t_dtw * 10 : null,
			fromMs: tok.offsets.from,
			toMs: tok.offsets.to,
			p: tok.p,
		});
	}
}

// A token's end is its DTW timestamp; its start is the previous end.
let cursor = 0;
for (const tk of rawTokens) {
	const end = tk.dtwMs ?? tk.toMs;
	tk.endMs = Math.max(end, cursor);
	tk.startMs = cursor;
	cursor = tk.endMs;
}

// Group sub-word tokens into words. A token that does not begin with a
// space continues the previous word.
const words = [];
for (const tk of rawTokens) {
	const startsNew = tk.text.startsWith(' ') || words.length === 0;
	if (startsNew) {
		words.push({word: tk.text.trim(), startMs: tk.startMs, endMs: tk.endMs});
	} else {
		const prev = words[words.length - 1];
		prev.word += tk.text.trim();
		prev.endMs = Math.max(prev.endMs, tk.endMs);
	}
}

// Punctuation-only tokens belong to the word before them.
const merged = [];
for (const w of words) {
	if (/^[^\p{L}\p{N}]+$/u.test(w.word) && merged.length > 0) {
		const prev = merged[merged.length - 1];
		prev.word += w.word;
		prev.endMs = Math.max(prev.endMs, w.endMs);
		continue;
	}
	merged.push(w);
}

// The word that restarts speech after a pause begins exactly where that
// pause ends. Whisper's token boundaries drift either side of it (the
// punctuation token swallows part of the pause), so pin it to the audio.
const SNAP_PAD_MS = 10;
let snapped = 0;
for (const s of silences) {
	const w = merged.find((x) => x.startMs >= s.startMs - 30);
	if (!w) continue;
	const onset = Math.min(s.endMs + SNAP_PAD_MS, w.endMs - 60);
	if (Math.abs(onset - w.startMs) > 1) {
		w.startMs = onset;
		snapped++;
	}
}
for (const w of merged) {
	w.startMs = Math.max(0, Math.min(w.startMs, w.endMs - 40));
}
console.log('[transcribe] pinned', snapped, 'post-pause onsets to the audio');

if (merged.length > 0) {
	const last = merged[merged.length - 1];
	last.endMs = Math.min(Math.max(last.endMs, last.startMs + 120), audioDurationMs);
}

/* -------------------------------------------------------------- *
 * 5. Write
 * -------------------------------------------------------------- */

fs.mkdirSync(OUT_DIR, {recursive: true});
fs.writeFileSync(
	OUT_JSON,
	JSON.stringify(
		{
			source: 'whisper',
			model: MODEL,
			whisperCppVersion: WHISPER_VERSION,
			audio: 'public/vo.mp3',
			audioDurationMs,
			text: whisperCppOutput.transcription.map((t) => t.text).join('').trim(),
			words: merged.map((w) => ({
				word: w.word,
				startMs: Math.round(w.startMs),
				endMs: Math.round(w.endMs),
			})),
			silences: silences.map((s) => ({
				startMs: Math.round(s.startMs),
				endMs: Math.round(s.endMs),
			})),
			captions,
		},
		null,
		2,
	),
);

console.log('[transcribe] wrote', path.relative(ROOT, OUT_JSON));
console.log('[transcribe] words:', merged.length);
for (const w of merged) {
	console.log(
		`  ${(w.startMs / 1000).toFixed(3).padStart(7)} → ${(w.endMs / 1000)
			.toFixed(3)
			.padStart(7)}  ${w.word}`,
	);
}
