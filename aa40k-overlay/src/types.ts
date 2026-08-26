import type {Poses} from './stage/flight';
import type {Layout, Palette, Tone, TypeScale} from './theme';

/** Everything a beat needs. Beats never read global config themselves. */
export type BeatProps = {
  readonly layout: Layout;
  readonly type: TypeScale;
  readonly palette: Palette;
  readonly tone: Tone;
  readonly poses: Poses;
  /** false removes the opaque plates; the same type then plays over footage */
  readonly cards: boolean;
  readonly disclaimer: string;
};

export type OverlayProps = {
  readonly aspect: '9x16' | '16x9';
  readonly cards: boolean;
  readonly tone: Tone;
  readonly disclaimer: string;
  readonly accent?: string;
};
