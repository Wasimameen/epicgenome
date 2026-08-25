import {createContext, useContext} from 'react';

/**
 * True while rendering the alpha-channel pass (the `ReelAlpha` composition).
 *
 * Scenes and plates read this to drop everything that only exists to be a
 * background: ground fills, the money plate, live footage, the vignette and the
 * grain. Additive passes — glows, bloom, rays, dust, flashes — are kept, since
 * they are part of the graphics rather than the ground behind them.
 */
export const TransparentContext = createContext(false);

export const useTransparent = () => useContext(TransparentContext);
