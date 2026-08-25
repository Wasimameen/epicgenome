/**
 * Beat map, derived from the supplied voiceover rather than estimated.
 *
 * Scene boundaries were taken from the long pauses in the read (silence
 * detection at -34dB), so every cut lands in a breath instead of over a word.
 * Frame counts below are those boundaries at 30fps; the VO runs 62.04s.
 *
 * Retime by editing only this table — scenes read their own length from it.
 */
export const SCENES = [
  {id: 'hook', frames: 183, at: '0.00–6.11'},
  {id: 'crazier', frames: 128, at: '6.11–10.36'},
  {id: 'impact', frames: 335, at: '10.36–21.52'},
  {id: 'down', frames: 208, at: '21.52–28.45'},
  {id: 'surgeries', frames: 208, at: '28.45–35.41'},
  {id: 'court', frames: 261, at: '35.41–44.09'},
  {id: 'online', frames: 74, at: '44.09–46.55'},
  {id: 'verdict', frames: 253, at: '46.55–54.99'},
  {id: 'cta', frames: 211, at: '54.99–62.04'},
] as const;

export const TOTAL_FRAMES = SCENES.reduce((n, s) => n + s.frames, 0);
