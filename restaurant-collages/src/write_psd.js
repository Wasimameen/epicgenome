#!/usr/bin/env node
// write_psd.js <build_dir> <out.psd> [--icc srgb.icc] [--zip]
// Turns a psdkit manifest (manifest.json + layer PNGs + composite.png) into a
// layered Photoshop document: groups, pixel layers, layer masks, clipping masks,
// solid-colour fill layers, blend modes, opacity, colour labels, 300 ppi, sRGB.
'use strict';
const fs = require('fs');
const path = require('path');
const NM = path.join(__dirname, '..', 'tools', 'node_modules');
const { writePsdBuffer } = require(path.join(NM, 'ag-psd'));
const { PNG } = require(path.join(NM, 'pngjs'));

const args = process.argv.slice(2);
const buildDir = args[0];
const outPath = args[1];
const iccIdx = args.indexOf('--icc');
const iccPath = iccIdx >= 0 ? args[iccIdx + 1] : null;
const useZip = args.includes('--zip');

const manifest = JSON.parse(fs.readFileSync(path.join(buildDir, 'manifest.json'), 'utf8'));
const W = manifest.width, H = manifest.height;

function readPng(rel) {
  const png = PNG.sync.read(fs.readFileSync(path.join(buildDir, rel)));
  return { width: png.width, height: png.height,
           data: new Uint8ClampedArray(png.data.buffer, png.data.byteOffset, png.data.length) };
}

function pngSize(rel) {           // width / height straight from the IHDR chunk
  const fd = fs.openSync(path.join(buildDir, rel), 'r');
  const b = Buffer.alloc(24);
  fs.readSync(fd, b, 0, 24, 0);
  fs.closeSync(fd);
  return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) };
}

function solid(w, h, rgb) {
  const data = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < data.length; i += 4) {
    data[i] = rgb[0]; data[i + 1] = rgb[1]; data[i + 2] = rgb[2]; data[i + 3] = 255;
  }
  return { width: w, height: h, data };
}

let nextId = 1;
const stats = { groups: 0, pixel: 0, fill: 0, masks: 0, clipped: 0 };

function buildMask(m) {
  const img = readPng(m.png); // pngjs expands L -> RGBA; ag-psd reads channel 0
  stats.masks++;
  return { top: m.y, left: m.x, bottom: m.y + img.height, right: m.x + img.width,
           defaultColor: m.default, imageData: img };
}

const PX_TO_PT = 72 / manifest.dpi;      // Photoshop type is set in points; the transform scales to pixels

function build(node) {
  const L = { name: node.name, id: nextId++, opacity: node.opacity, hidden: !!node.hidden };
  if (node.label) L.layerColor = node.label;
  if (node.locked) L.protected = { transparency: false, composite: true, position: true };
  if (node.type === 'text') {
    stats.text = (stats.text || 0) + 1;
    const k = 1 / PX_TO_PT;
    const style = {
      font: { name: node.font },
      fontSize: +(node.size * PX_TO_PT).toFixed(3),
      fillColor: { r: node.color[0], g: node.color[1], b: node.color[2] },
      tracking: node.tracking || 0,
    };
    if (node.leading) { style.autoLeading = false; style.leading = +(node.leading * PX_TO_PT).toFixed(3); }
    L.blendMode = 'normal';
    const a = -(node.angle || 0) * Math.PI / 180;      // page y points down: CCW on the page = negative
    L.text = {
      text: node.text.replace(/\n/g, '\r'),
      transform: [k * Math.cos(a), k * Math.sin(a), -k * Math.sin(a), k * Math.cos(a), node.x, node.y],
      antiAlias: 'smooth',
      style,
      paragraphStyle: { justification: node.justification || 'left' },
    };
    return L;
  }
  if (node.type === 'group') {
    stats.groups++;
    L.blendMode = 'pass through';
    L.opened = !!node.opened;
    L.children = node.children.map(build);
    return L;
  }
  L.blendMode = node.blend;
  if (node.clip) { L.clipping = true; stats.clipped++; }
  if (node.type === 'pixel') {
    stats.pixel++;
    if (node.png) {
      const img = readPng(node.png);
      L.left = node.x; L.top = node.y; L.right = node.x + img.width; L.bottom = node.y + img.height;
      L.imageData = img;
    }
  } else if (node.type === 'fill') {
    stats.fill++;
    L.vectorFill = { type: 'color', color: { r: node.color[0], g: node.color[1], b: node.color[2] } };
    // Photoshop regenerates a fill from vectorFill; the stored pixels are only a cache for other readers.
    // A masked fill (mask default 0) is invisible outside its mask rectangle, so the cache only needs
    // that rectangle (a full-canvas RLE cache costs ~1 MB per fill). Unmasked fills cache the canvas.
    let fx0 = 0, fy0 = 0, fx1 = W, fy1 = H;
    if (node.mask && !node.mask.default) {
      const dims = pngSize(node.mask.png);
      fx0 = Math.max(0, node.mask.x); fy0 = Math.max(0, node.mask.y);
      fx1 = Math.min(W, node.mask.x + dims.width); fy1 = Math.min(H, node.mask.y + dims.height);
      if (fx1 <= fx0 || fy1 <= fy0) { fx0 = 0; fy0 = 0; fx1 = 1; fy1 = 1; }
    }
    L.left = fx0; L.top = fy0; L.right = fx1; L.bottom = fy1;
    L.imageData = solid(fx1 - fx0, fy1 - fy0, node.color);
  } else {
    throw new Error('unknown node type ' + node.type);
  }
  if (node.mask) L.mask = buildMask(node.mask);
  return L;
}

const children = manifest.layers.map(build);
const composite = readPng(manifest.composite);
// composite.png is RGB; pngjs gives RGBA with alpha 255 — exactly what PSD wants.

function thumbJpeg() {
  const buf = fs.readFileSync(path.join(buildDir, 'thumb.jpg'));
  // SOF0/SOF2 marker carries the size
  let i = 2;
  while (i < buf.length) {
    const marker = buf.readUInt16BE(i);
    const len = buf.readUInt16BE(i + 2);
    if (marker === 0xFFC0 || marker === 0xFFC2) {
      return { width: buf.readUInt16BE(i + 7), height: buf.readUInt16BE(i + 5), data: new Uint8Array(buf) };
    }
    i += 2 + len;
  }
  throw new Error('thumb.jpg: no SOF marker');
}

// (legacy) raw thumbnail from the composite, nearest-neighbour box average
function thumb(img, maxSide) {
  const s = maxSide / Math.max(img.width, img.height);
  const tw = Math.max(1, Math.round(img.width * s)), th = Math.max(1, Math.round(img.height * s));
  const out = new Uint8Array(tw * th * 4);
  for (let y = 0; y < th; y++) {
    const sy0 = Math.floor(y / s), sy1 = Math.min(img.height, Math.floor((y + 1) / s));
    for (let x = 0; x < tw; x++) {
      const sx0 = Math.floor(x / s), sx1 = Math.min(img.width, Math.floor((x + 1) / s));
      let r = 0, g = 0, b = 0, n = 0;
      for (let yy = sy0; yy < sy1; yy += 2) for (let xx = sx0; xx < sx1; xx += 2) {
        const i = (yy * img.width + xx) * 4; r += img.data[i]; g += img.data[i + 1]; b += img.data[i + 2]; n++;
      }
      const o = (y * tw + x) * 4; out[o] = r / n; out[o + 1] = g / n; out[o + 2] = b / n; out[o + 3] = 255;
    }
  }
  return { width: tw, height: th, data: out };
}

const psd = {
  width: W, height: H, channels: 3, bitsPerChannel: 8, colorMode: 3,
  children,
  imageData: composite,
  imageResources: {
    resolutionInfo: {
      horizontalResolution: manifest.dpi, horizontalResolutionUnit: 'PPI', widthUnit: 'Centimeters',
      verticalResolution: manifest.dpi, verticalResolutionUnit: 'PPI', heightUnit: 'Centimeters',
    },
    // resource 1036 is a JPEG thumbnail (format 1); finalize.py writes thumb.jpg next to the manifest
    thumbnailRaw: thumbJpeg(),
    versionInfo: { hasRealMergedData: true, writerName: 'psdkit + ag-psd', readerName: 'psdkit', fileVersion: 1 },
  },
};
// the ICC profile (image resource 1039) is inserted by finalize.py after writing: ag-psd has no writer for it

const buf = writePsdBuffer(psd, { generateThumbnail: false, trimImageData: false, compress: useZip, logMissingFeatures: true });
fs.writeFileSync(outPath, buf);
console.log(JSON.stringify({ out: outPath, bytes: buf.length, mb: +(buf.length / 1048576).toFixed(1), ...stats }));
