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
    L.text = {
      text: node.text.replace(/\n/g, '\r'),
      transform: [k, 0, 0, k, node.x, node.y],
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
    // Photoshop stores the rendered fill for the whole canvas; RLE makes it tiny.
    L.left = 0; L.top = 0; L.right = W; L.bottom = H;
    L.imageData = solid(W, H, node.color);
  } else {
    throw new Error('unknown node type ' + node.type);
  }
  if (node.mask) L.mask = buildMask(node.mask);
  return L;
}

const children = manifest.layers.map(build);
const composite = readPng(manifest.composite);
// composite.png is RGB; pngjs gives RGBA with alpha 255 — exactly what PSD wants.

// thumbnail (160 px max side) from the composite, nearest-neighbour box average
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
    thumbnailRaw: thumb(composite, 160),
    versionInfo: { hasRealMergedData: true, writerName: 'psdkit + ag-psd', readerName: 'psdkit', fileVersion: 1 },
  },
};
// the ICC profile (image resource 1039) is inserted by finalize.py after writing: ag-psd has no writer for it

const buf = writePsdBuffer(psd, { generateThumbnail: false, trimImageData: false, compress: useZip, logMissingFeatures: true });
fs.writeFileSync(outPath, buf);
console.log(JSON.stringify({ out: outPath, bytes: buf.length, mb: +(buf.length / 1048576).toFixed(1), ...stats }));
