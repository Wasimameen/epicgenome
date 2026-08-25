/**
 * Shared look-and-feel tokens for the Awesome Attorneys spot.
 * Palette is money-toned: near-black grounds, aged-gold highlights,
 * with Walmart brand blue/yellow reserved for the logo beat only.
 */
export const THEME = {
  ink: '#08070a',
  inkSoft: '#141018',
  gold: '#d8b26a',
  goldBright: '#f5d98a',
  paper: '#f4efe4',
  walmartBlue: '#0071ce',
  walmartYellow: '#ffc220',
} as const;

export const VIDEO = {
  width: 1080,
  height: 1920,
  fps: 30,
  /** Scene 01 runs a flat 5 seconds. */
  hookDuration: 165,
} as const;
