#!/usr/bin/env node
/**
 * Derives the piece's timing from the recorded voice-over.
 *
 *   node scripts/transcribe-vo.mjs          (or: npm run vo)
 *
 * Drop the final VO at `assets-in/vo.mp3` and run this. It copies the file into
 * `public/`, converts it to the 16 kHz mono WAV whisper.cpp wants, transcribes
 * it with word-level timestamps, and writes `src/timing/vo-words.json`.
 *
 * `src/timing/beats.ts` picks its sync points out of that file by word, so
 * every scene re-times with no other edit. If the file is missing or the
 * transcription cannot supply all 20 key words, nothing is overwritten and the
 * spec §4.2 fallback table stays in force.
 */

import {execFileSync} from 'node:child_process';
import {copyFileSync, existsSync, mkdirSync, writeFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {
  downloadWhisperModel,
  installWhisperCpp,
  toCaptions,
  transcribe,
} from '@remotion/install-whisper-cpp';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const MODEL = 'medium.en';
const WHISPER_VERSION = '1.5.5';

/** Every sync point `beats.ts` needs, so we can warn before overwriting. */
const REQUIRED = [
  'adjuster', 'youre', 'forty', 'percent', 'fault',
  'thats', 'opening', 'position', 'not', 'legal', 'finding',
  'awesome', 'matches', 'directly', 'phoenix', 'injury', 'attorney',
  'matched', 'paid',
];

const src = resolve(root, 'assets-in/vo.mp3');
if (!existsSync(src)) {
  console.log(
    `[vo] assets-in/vo.mp3 not found — keeping the fallback timing table.\n` +
      `[vo] Drop the final voice-over there and re-run to sync to the real read.`,
  );
  process.exit(0);
}

mkdirSync(resolve(root, 'public'), {recursive: true});
const mp3 = resolve(root, 'public/vo.mp3');
copyFileSync(src, mp3);
console.log('[vo] copied assets-in/vo.mp3 -> public/vo.mp3');

// Remotion ships its own ffmpeg; no system install required.
const wav = resolve(root, 'public/vo16.wav');
execFileSync(
  'npx',
  ['remotion', 'ffmpeg', '-y', '-i', mp3, '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', wav],
  {cwd: root, stdio: 'inherit'},
);
console.log('[vo] wrote public/vo16.wav (16 kHz mono)');

const whisperPath = resolve(root, 'whisper.cpp');
await installWhisperCpp({to: whisperPath, version: WHISPER_VERSION});
await downloadWhisperModel({model: MODEL, folder: whisperPath});

const output = await transcribe({
  model: MODEL,
  whisperPath,
  whisperCppVersion: WHISPER_VERSION,
  inputPath: wav,
  tokenLevelTimestamps: true,
});

const {captions} = toCaptions({whisperCppOutput: output});
const words = captions
  .map((c) => ({
    word: c.text.trim(),
    start: c.startMs / 1000,
    end: c.endMs / 1000,
  }))
  .filter((w) => w.word.length > 0);

if (words.length === 0) {
  console.error('[vo] transcription produced no words — keeping the fallback table.');
  process.exit(1);
}

// Warn loudly rather than silently shipping half-synced timing.
const seen = new Set(words.map((w) => w.word.toLowerCase().replace(/[^a-z0-9]/g, '')));
const missing = REQUIRED.filter((r) =>
  r === 'awesome'
    ? ![...seen].some((s) => s.startsWith('awesome'))
    : !seen.has(r),
);
if (missing.length > 0) {
  console.warn(
    `[vo] WARNING: these key words were not found in the transcription: ${missing.join(', ')}.\n` +
      `[vo] beats.ts will fall back to the §4.2 table wholesale rather than half-sync.`,
  );
}

const payload = {
  source: 'whisper',
  note: `Transcribed from assets-in/vo.mp3 with whisper.cpp ${WHISPER_VERSION}, model ${MODEL}, token-level timestamps.`,
  audioFile: 'vo.mp3',
  durationSec: words[words.length - 1].end,
  words,
};

const dest = resolve(root, 'src/timing/vo-words.json');
writeFileSync(dest, `${JSON.stringify(payload, null, 2)}\n`);
console.log(
  `[vo] wrote src/timing/vo-words.json — ${words.length} words, ` +
    `${payload.durationSec.toFixed(2)}s of speech.`,
);
console.log('[vo] next: node scripts/sync-sheet.mjs, then re-render.');
