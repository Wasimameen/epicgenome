import {continueRender, delayRender, staticFile} from 'remotion';

/**
 * Fonts are self-hosted from public/fonts rather than pulled from Google's CDN.
 * The render browser does not trust this environment's proxy CA, and a spot that
 * silently falls back to DejaVu is worse than one that cannot render at all —
 * self-hosting removes the network from the critical path entirely.
 */
const FACES = [
  {family: 'Anton', file: 'fonts/anton-latin.woff2', weight: '400'},
  {family: 'Archivo', file: 'fonts/archivo-latin.woff2', weight: '100 900'},
];

let loaded: Promise<void> | null = null;

export const loadFonts = () => {
  if (loaded) return loaded;

  const handle = delayRender('Loading self-hosted display fonts');

  loaded = Promise.all(
    FACES.map(async ({family, file, weight}) => {
      const face = new FontFace(family, `url(${staticFile(file)}) format('woff2')`, {
        weight,
        style: 'normal',
      });
      await face.load();
      document.fonts.add(face);
    }),
  ).then(() => {
    continueRender(handle);
  });

  return loaded;
};

export const FONT_STACK = {
  display: "'Anton', Impact, 'Arial Narrow Bold', sans-serif",
  body: "'Archivo', 'Helvetica Neue', Arial, sans-serif",
} as const;
