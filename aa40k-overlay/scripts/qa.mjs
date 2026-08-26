#!/usr/bin/env node
/**
 * QA harness for the alpha overlay.
 *
 *   node scripts/qa.mjs probe   <mov>                      pixel format + alpha report
 *   node scripts/qa.mjs frames  <mov> <offset> <f1,f2,..> <outdir>
 *   node scripts/qa.mjs cover   <mov> <offset> <f1,f2,..> <outdir>   (contact sheet)
 *
 * `frames` writes, for every requested timeline frame N:
 *   fN.png        the raw RGBA frame straight out of the .mov
 *   fN_gray.png   composited over mid-grey  (the everyday case)
 *   fN_white.png  composited over white     (the hardest case for white type)
 *   fN_black.png  composited over near-black
 *   fN_alpha.png  the alpha channel alone, as a matte
 *
 * `offset` is the timeline frame that file-frame 0 corresponds to, so partial
 * renders (`--frames=40-70`) can be checked with real timeline numbers.
 *
 * Uses the full static ffmpeg from node_modules — Remotion's bundled build is
 * compiled with `--disable-filters` and has neither `alphaextract` nor
 * `overlay`.
 */

import {execFileSync} from 'node:child_process';
import {mkdirSync} from 'node:fs';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';

const require = createRequire(import.meta.url);
const FFMPEG = require('ffmpeg-static');
const FFPROBE = require('ffprobe-static').path;

const run = (bin, args) => execFileSync(bin, args, {encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']});

const [, , cmd, movArg, ...rest] = process.argv;
const mov = movArg ? resolve(movArg) : null;

const PLATES = {
  gray: '0x808080',
  white: '0xFFFFFF',
  black: '0x0A0A0C',
};

const size = (path) => {
  const out = run(FFPROBE, [
    '-v', 'error',
    '-select_streams', 'v:0',
    '-show_entries', 'stream=width,height,pix_fmt,nb_frames,r_frame_rate',
    '-of', 'default=nw=1',
    path,
  ]);
  const get = (k) => (out.match(new RegExp(`^${k}=(.*)$`, 'm')) ?? [])[1];
  return {
    width: Number(get('width')),
    height: Number(get('height')),
    pixFmt: get('pix_fmt'),
    frames: get('nb_frames'),
    rate: get('r_frame_rate'),
  };
};

if (cmd === 'probe') {
  const s = size(mov);
  const ALPHA_OK = ['yuva444p10le', 'yuva444p12le', 'yuva420p', 'yuva444p'];

  // VP9 in WebM does not carry alpha in the stream's pixel format — the alpha
  // plane is a separate container-level layer flagged by the `alpha_mode` tag,
  // and the stream still reports yuv420p. Reading pix_fmt alone reports a
  // perfectly good alpha webm as opaque.
  const tags = run(FFPROBE, [
    '-v', 'error', '-select_streams', 'v:0',
    '-show_entries', 'stream_tags=alpha_mode',
    '-of', 'default=nw=1', mov,
  ]);
  const alphaMode = /alpha_mode=1/.test(tags);

  const ok = ALPHA_OK.includes(s.pixFmt) || alphaMode;
  console.log(`file      ${mov}`);
  console.log(`size      ${s.width}x${s.height} @ ${s.rate}`);
  console.log(`frames    ${s.frames}`);
  console.log(
    `pix_fmt   ${s.pixFmt}${alphaMode ? ' + alpha_mode=1 (VP9 container alpha)' : ''}   ` +
      `${ok ? 'ALPHA OK' : '*** NO ALPHA ***'}`,
  );
  if (alphaMode) {
    console.log(
      `note      decode this with \`-c:v libvpx-vp9\` — ffmpeg's native VP9\n` +
        `          decoder silently ignores the alpha layer.`,
    );
  }
  process.exit(ok ? 0 : 1);
}

if (cmd === 'frames' || cmd === 'cover') {
  const [offsetArg, framesArg, outArg] = rest;
  const offset = Number(offsetArg);
  const frames = framesArg.split(',').map((n) => Number(n.trim()));
  const outDir = resolve(outArg);
  mkdirSync(outDir, {recursive: true});
  const s = size(mov);

  for (const f of frames) {
    const n = f - offset;
    if (n < 0) {
      console.error(`frame ${f} is before this file's offset (${offset}) — skipped`);
      continue;
    }
    const sel = `select='eq(n\\,${n})'`;

    // raw RGBA
    run(FFMPEG, ['-y', '-loglevel', 'error', '-i', mov, '-vf', sel,
      '-fps_mode', 'passthrough', '-frames:v', '1', '-pix_fmt', 'rgba',
      resolve(outDir, `f${f}.png`)]);

    // alpha matte
    run(FFMPEG, ['-y', '-loglevel', 'error', '-i', mov,
      '-vf', `${sel},format=rgba,alphaextract`,
      '-fps_mode', 'passthrough', '-frames:v', '1',
      resolve(outDir, `f${f}_alpha.png`)]);

    if (cmd === 'frames') {
      for (const [name, colour] of Object.entries(PLATES)) {
        run(FFMPEG, ['-y', '-loglevel', 'error',
          '-f', 'lavfi', '-i', `color=c=${colour}:s=${s.width}x${s.height}`,
          '-i', mov,
          '-filter_complex', `[1:v]${sel},setpts=N/FRAME_RATE/TB[fg];[0:v][fg]overlay=format=auto`,
          '-frames:v', '1',
          resolve(outDir, `f${f}_${name}.png`)]);
      }
    }
    process.stdout.write(`.`);
  }
  console.log(`\nwrote ${frames.length} frame set(s) to ${outDir}`);
  process.exit(0);
}

console.error('usage: qa.mjs probe|frames|cover <mov> [offset] [frames] [outdir]');
process.exit(2);
