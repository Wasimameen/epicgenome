/* ------------------------------------------------------------------ *
 * Beat 2 — "Reframe"  (~3.6 → ~7.2s)  ·  knowing, confident
 *
 * The turn happens on "opening". A gold line cuts through the stamp;
 * the red desaturates toward steel, the stamp drops and tilts, and the
 * label above the form is renamed twice: the adjuster's verdict becomes
 * their opening position, then not a legal finding at all.
 *
 * On "not" a warm edge enters (Background handles the light) and the
 * struck stamp comes apart. A gold rule widens under the form — in 16:9
 * that rule is the horizon beat 3 builds on.
 *
 * The light-sweep transition out is rendered by <Spot>, because it has
 * to sit above this act while masking it away.
 * ------------------------------------------------------------------ */

import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useVideoConfig} from 'remotion';
import {FormLabel} from '../parts/ClaimForm';
import {StrikeThrough} from '../parts/StrikeThrough';
import {Shards} from '../parts/Shards';
import {useStampState} from '../parts/Stamp';
import {EASE} from '../theme';
import {ramp, useClock, useSpot} from '../overlays/lib';
import {LEAD, t} from '../timing/beats';

export const Beat2Reframe: React.FC = () => {
	const {sec} = useClock();
	const {fps} = useVideoConfig();
	const {palette: c, layout} = useSpot();
	const stamp = useStampState();
	const lead = LEAD / fps;

	const strikeAt = t.opening - lead;
	const findingAt = t.finding - lead;

	/* The gold rule widens from centre to full width. */
	const rule = ramp(sec, findingAt + 0.1, findingAt + 0.62, EASE.expoOut);

	return (
		<AbsoluteFill>
			<StrikeThrough state={stamp} />
			<Shards state={stamp} />

			<FormLabel
				text="Their Opening Position"
				color={c.gold}
				inSec={strikeAt + 0.08}
				replacedAt={findingAt + 0.06}
				direction="up"
			/>
			<FormLabel
				text="Not a Legal Finding"
				color={c.white}
				inSec={findingAt + 0.06}
				direction="up"
				underline
				underlineColor={c.gold}
			/>

			{/* Gold rule below the form — beat 3 continues it as the horizon. */}
			{rule > 0 ? (
				<div
					style={{
						position: 'absolute',
						top: layout.ruleY,
						left: 0,
						width: layout.width,
						display: 'flex',
						justifyContent: 'center',
					}}
				>
					<div
						style={{
							width: layout.width * rule,
							height: 3,
							background: `linear-gradient(90deg, rgba(228,184,90,0) 0%, ${c.gold} 22%, ${c.gold} 78%, rgba(228,184,90,0) 100%)`,
						}}
					/>
				</div>
			) : null}
		</AbsoluteFill>
	);
};
