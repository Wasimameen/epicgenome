/**
 * Master beat map for the 48-second reel.
 *
 * Durations are tuned to a brisk ad read of the supplied script. When the real
 * voiceover lands, retime here — every scene reads its own length from this
 * table, so nothing else needs touching.
 */
export const SCENES = [
  {id: 'hook', frames: 165, line: 'Nearly seventeen million dollars… because a grandmother went shopping at Walmart.'},
  {id: 'crazier', frames: 105, line: 'And honestly — how it happened is even crazier than the number.'},
  {id: 'impact', frames: 180, line: 'So security tries to stop a shoplifter — the guy BOLTS — runs straight into her shopping cart — and her granddaughter is sitting in that cart.'},
  {id: 'down', frames: 150, line: 'The little girl was completely fine — but grandma went down hard, and the cart came down right on top of her.'},
  {id: 'surgeries', frames: 150, line: "She needed multiple surgeries. She's been in the hospital more than twenty times."},
  {id: 'court', frames: 180, line: "So she takes Walmart to court — and she WINS — but Walmart isn't done — they appeal it all the way to the state Supreme Court —"},
  {id: 'online', frames: 120, line: 'and now every single dollar is on the line.'},
  {id: 'verdict', frames: 180, line: 'The court said… the verdict stands. All of it — nearly seventeen million dollars — upheld by the highest court in the state.'},
  {id: 'cta', frames: 210, line: "That's what happens when the facts hold up. Awesome Attorneys matches you directly with a Phoenix injury attorney. Get Matched. Get Paid. AwesomeAttorneys dot com."},
] as const;

export const TOTAL_FRAMES = SCENES.reduce((n, s) => n + s.frames, 0);
