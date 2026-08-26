/* ------------------------------------------------------------------ *
 * Spot.tsx — one component, four deliverables.
 *
 * `aspect` swaps layout tokens, never the components. `mode` decides
 * whether the spot brings its own world (full) or is meant to be
 * composited over someone else's footage (overlay): overlay drops the
 * background, the texture and the audio, and switches every piece of
 * type to the two-part shadow.
 *
 * Stacking order matters. Beat 3 mounts BEHIND the cold act so the
 * light sweep can reveal it rather than cover a dissolve; the sweep
 * itself sits above both and carries the mask that removes the cold
 * scene along its own edge.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {Beat, ramp, SpotProvider, useClock, useSpot} from './overlays/lib';
import {Background} from './scene/Background';
import {Camera} from './scene/Camera';
import {Texture} from './scene/Texture';
import {Soundtrack} from './audio/Soundtrack';
import {Beat1Verdict} from './beats/Beat1Verdict';
import {Beat2Reframe} from './beats/Beat2Reframe';
import {Beat3Match} from './beats/Beat3Match';
import {Beat4CTA} from './beats/Beat4CTA';
import {LightSweep, sweepCutoutMask} from './parts/LightSweep';
import {beatWindows} from './timing/beats';
import {EASE} from './theme';
import type {Aspect, Brand, Mode} from './theme';

export type SpotProps = {
	aspect: Aspect;
	mode: Mode;
	disclaimer: string;
	brand?: Brand | null;
};

export const DEFAULT_DISCLAIMER =
	'Attorney matching service. Not a law firm. Not legal advice.';

/** Removes the cold act along the sweep edge, so the sweep does the reveal. */
const ColdAct: React.FC<{readonly children: React.ReactNode}> = ({children}) => {
	const {sec, fps} = useClock();
	const w = beatWindows(fps);
	const p = ramp(sec, w.sweep.start, w.sweep.end, EASE.expoInOut);
	const mask = p > 0 ? sweepCutoutMask(p) : undefined;
	return (
		<AbsoluteFill style={{maskImage: mask, WebkitMaskImage: mask}}>{children}</AbsoluteFill>
	);
};

const SpotScene: React.FC = () => {
	const {fps} = useVideoConfig();
	const {mode, palette} = useSpot();
	const w = beatWindows(fps);

	return (
		<AbsoluteFill
			style={{
				backgroundColor: mode === 'full' ? palette.ink : 'transparent',
				overflow: 'hidden',
			}}
		>
			{mode === 'full' ? <Background /> : null}

			{/* Warm act, already in place behind the sweep. */}
			<Beat name="Beat 3 — The match" startSec={w.three.start} endSec={w.three.end}>
				<Camera act="three">
					<Beat3Match />
				</Camera>
			</Beat>

			{/* Cold act: beats 1 and 2 are one continuous scene. */}
			<Beat name="Beats 1–2 — Verdict / Reframe" startSec={0} endSec={w.cold.end}>
				<ColdAct>
					<Camera act="cold">
						<Beat1Verdict />
						<Beat2Reframe />
					</Camera>
				</ColdAct>
			</Beat>

			{/* The reveal itself. */}
			<LightSweep startSec={w.sweep.start} endSec={w.sweep.end} />

			{/* Hard cut into the CTA. */}
			<Beat name="Beat 4 — CTA" startSec={w.four.start} endSec={w.four.end}>
				<Camera act="four">
					<Beat4CTA />
				</Camera>
			</Beat>

			{mode === 'full' ? <Texture /> : null}
			<Soundtrack />
		</AbsoluteFill>
	);
};

export const Spot: React.FC<SpotProps> = ({aspect, mode, disclaimer, brand}) => (
	<SpotProvider aspect={aspect} mode={mode} brand={brand} disclaimer={disclaimer}>
		<SpotScene />
	</SpotProvider>
);
