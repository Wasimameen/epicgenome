#!/usr/bin/env node
/**
 * Reads `assets-in/`, copies what it finds into `public/`, and regenerates
 * `src/brand.generated.ts` (and, through `vendor-fonts.mjs`, `src/font.ts`).
 *
 *   node scripts/prepare-assets.mjs      (or: npm run assets)
 *
 * Nothing here is required — every input has a documented default, and the
 * script reports exactly which placeholders are still in play so the render
 * report can be honest about it.
 *
 *   assets-in/vo.mp3        final voice-over      -> fallback timing table
 *   assets-in/bg/*          4 backdrop photos     -> procedural gradients
 *   assets-in/endcard.*     signature end card    -> typographic end card
 *   assets-in/logo.svg|png  wordmark              -> typographic wordmark
 *   assets-in/brand.json    {font, gold, ink}     -> spec §3 defaults
 *   assets-in/reference.mp4 style reference       -> spec §2 as written
 *   assets-in/broll/*.mp4   legibility QA only    -> flat plates in QA
 */

import {execFileSync} from 'node:child_process';
import {copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {dirname, extname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const inDir = resolve(root, 'assets-in');
const pubDir = resolve(root, 'public');

const DEFAULTS = {font: 'Manrope', gold: '#E4B85A', ink: '#0B1220'};
const DEFAULT_END_CARD_BG = '#8A1F26';
const IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.webp'];

/** Backdrop roles, in the order the shot list plays them (timing/backdrops.ts). */
const ROLES = [
  {key: 'adjuster', what: 'beat 1 — the adjuster sizing you up'},
  {key: 'silenced', what: 'beat 2 — what their "opening position" really does'},
  {key: 'court', what: 'beat 2/3 — what an actual legal finding looks like'},
  {key: 'counsel', what: 'beat 3 — the attorney you get matched with'},
];

mkdirSync(pubDir, {recursive: true});
mkdirSync(inDir, {recursive: true});

const found = [];
const placeholders = [];

/* brand.json ------------------------------------------------------- */
let brand = {...DEFAULTS};
const brandPath = resolve(inDir, 'brand.json');
if (existsSync(brandPath)) {
  try {
    const parsed = JSON.parse(readFileSync(brandPath, 'utf8'));
    brand = {
      font: typeof parsed.font === 'string' && parsed.font.trim() ? parsed.font.trim() : DEFAULTS.font,
      gold: /^#[0-9a-f]{6}$/i.test(parsed.gold ?? '') ? parsed.gold : DEFAULTS.gold,
      ink: /^#[0-9a-f]{6}$/i.test(parsed.ink ?? '') ? parsed.ink : DEFAULTS.ink,
    };
    copyFileSync(brandPath, resolve(pubDir, 'brand.json'));
    found.push(`brand.json  -> font "${brand.font}", gold ${brand.gold}, ink ${brand.ink}`);
  } catch (err) {
    placeholders.push(`brand.json could not be parsed (${err.message}) — using §3 defaults`);
  }
} else {
  placeholders.push('brand colours + typeface: spec §3 defaults (Manrope / #E4B85A / #0B1220)');
}

/* backdrops -------------------------------------------------------- */
const bgDir = resolve(inDir, 'bg');
let backdrops = null;
if (existsSync(bgDir)) {
  const files = readdirSync(bgDir)
    .filter((f) => IMAGE_EXT.includes(extname(f).toLowerCase()))
    .sort();

  const pick = (role) => {
    // by role name first ("court.jpg"), otherwise by sort order ("03-*.jpg")
    const named = files.find((f) => f.toLowerCase().startsWith(role.key));
    if (named) return named;
    const index = ROLES.findIndex((r) => r.key === role.key);
    return files[index];
  };

  const chosen = {};
  let complete = true;
  for (const role of ROLES) {
    const file = pick(role);
    if (!file) {
      complete = false;
      break;
    }
    chosen[role.key] = file;
  }

  if (complete) {
    mkdirSync(resolve(pubDir, 'bg'), {recursive: true});
    backdrops = {};
    for (const role of ROLES) {
      const file = chosen[role.key];
      copyFileSync(resolve(bgDir, file), resolve(pubDir, 'bg', file));
      backdrops[role.key] = `bg/${file}`;
      found.push(`bg/${file}  -> ${role.key}  (${role.what})`);
    }
  } else {
    placeholders.push(
      `backdrops: procedural gradients — assets-in/bg/ has ${files.length} image(s), needs 4 ` +
        `(${ROLES.map((r) => r.key).join(', ')})`,
    );
  }
} else {
  placeholders.push(
    'backdrops: procedural gradients — no assets-in/bg/. Drop 4 images named ' +
      `${ROLES.map((r) => r.key).join(', ')} (or 01..04) to use the real photography.`,
  );
}

/* signature end card ----------------------------------------------- */
let endCard = null;
let endCardBg = DEFAULT_END_CARD_BG;
for (const ext of IMAGE_EXT) {
  const p = resolve(inDir, `endcard${ext}`);
  if (existsSync(p)) {
    const name = `endcard${ext}`;
    copyFileSync(p, resolve(pubDir, name));
    endCard = name;

    // Sample the card's own background so the "GET PAID." plate is painted the
    // same colour and the plate-to-card join is invisible. A corner patch, not
    // an average — an average is dragged around by the cream type.
    try {
      const FFMPEG = require('ffmpeg-static');
      const raw = execFileSync(
        FFMPEG,
        ['-v', 'error', '-i', p, '-vf', 'crop=iw*0.06:ih*0.04:iw*0.02:ih*0.02,scale=1:1',
          '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
        {maxBuffer: 1 << 20},
      );
      if (raw.length >= 3) {
        endCardBg =
          '#' + [raw[0], raw[1], raw[2]].map((n) => n.toString(16).padStart(2, '0')).join('');
      }
    } catch {
      /* keep the default; not worth failing the build over */
    }

    found.push(`${name}  -> signature end card  (background sampled as ${endCardBg})`);
    break;
  }
}
if (!endCard) {
  placeholders.push(
    'end card: typographic fallback — drop the signature card at assets-in/endcard.png',
  );
}

/* logo ------------------------------------------------------------- */
let logo = null;
for (const name of ['logo.svg', 'logo.png', 'logo.webp']) {
  const p = resolve(inDir, name);
  if (existsSync(p)) {
    copyFileSync(p, resolve(pubDir, name));
    logo = name;
    found.push(`${name}  -> public/${name}`);
    break;
  }
}
if (!logo) {
  placeholders.push('wordmark: typographic (AWESOME white 800 / ATTORNEYS gold 800), no logo supplied');
}

/* voice-over ------------------------------------------------------- */
const voPath = resolve(inDir, 'vo.mp3');
const hasVo = existsSync(voPath);
if (hasVo) {
  copyFileSync(voPath, resolve(pubDir, 'vo.mp3'));
  found.push('vo.mp3  -> public/vo.mp3  (run `npm run vo` to derive timing)');
} else {
  placeholders.push('timing: spec §4.2 fallback table — no vo.mp3 to transcribe');
}

/* reference / b-roll ---------------------------------------------- */
if (existsSync(resolve(inDir, 'reference.mp4'))) {
  found.push('reference.mp4 present — build a contact sheet before design changes');
} else {
  placeholders.push('style reference: spec §2 followed as written, no reference.mp4');
}
const brollDir = resolve(inDir, 'broll');
if (existsSync(brollDir) && readdirSync(brollDir).some((f) => f.endsWith('.mp4'))) {
  found.push('broll/*.mp4 present — QA will composite over it as well as flat plates');
} else {
  placeholders.push('legibility QA: flat grey / white / near-black plates only, no b-roll supplied');
}

/* write brand.generated.ts ---------------------------------------- */
const backdropLiteral = backdrops
  ? `{\n${ROLES.map((r) => `    ${r.key}: '${backdrops[r.key]}',`).join('\n')}\n  } as BackdropFiles | null`
  : 'null as BackdropFiles | null';

const source = `/**
 * GENERATED by \`node scripts/prepare-assets.mjs\` — do not edit by hand.
 *
 * Re-run that script after dropping files into \`assets-in/\`; it copies them
 * into \`public/\` and rewrites this file from \`assets-in/brand.json\`.
 */

export type BackdropFiles = {
  adjuster: string;
  silenced: string;
  court: string;
  counsel: string;
};

export const BRAND = {
  /** Google Font family name. Must expose weights 500, 700 and 800. */
  font: '${brand.font}',
  gold: '${brand.gold}',
  ink: '${brand.ink}',
  /** public/ filename when a logo is supplied, else null. */
  logo: ${logo ? `'${logo}'` : 'null'} as string | null,
  /** True when assets-in/vo.mp3 was copied into public/. */
  hasVoiceOver: ${hasVo},
  /**
   * The four photographic backdrops, by role. Null until images are dropped
   * into \`assets-in/bg/\` — the backdrop then plays procedural gradients so the
   * moves and the timing can still be judged.
   */
  backdrops: ${backdropLiteral},
  /** public/ filename for the signature end card, else null. */
  endCard: ${endCard ? `'${endCard}'` : 'null'} as string | null,
  /**
   * Background colour of the signature end card, sampled from the card itself
   * so the "GET PAID." plate is painted the same colour and the plate-to-card
   * join is invisible.
   */
  endCardBg: '${endCardBg}',
} as const;
`;
writeFileSync(resolve(root, 'src/brand.generated.ts'), source);

/* fonts ------------------------------------------------------------ */
execFileSync('node', [resolve(root, 'scripts/vendor-fonts.mjs')], {cwd: root, stdio: 'inherit'});

console.log('\n--- assets found ---');
if (found.length === 0) console.log('  (none — assets-in/ is empty)');
found.forEach((f) => console.log(`  ${f}`));
console.log('\n--- placeholders still in use ---');
placeholders.forEach((p) => console.log(`  ${p}`));
console.log('');
