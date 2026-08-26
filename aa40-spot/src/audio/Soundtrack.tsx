/* ------------------------------------------------------------------ *
 * Soundtrack.tsx — VO is the spine.
 *
 * Music sits at −18 dB under the voice and swells to −10 dB from "Get
 * Matched" to the end. Every SFX fires LEAD frames before its word, the
 * same instant as its visual: sound and picture slightly anticipate
 * speech, which is what makes the sync feel tight.
 *
 * Slots for assets that are not in the project yet stay wired but
 * render nothing — see src/assets.ts and scripts/scan-assets.mjs.
 *
 * Overlay mode renders no audio at all.
 * ------------------------------------------------------------------ */

import React from 'react';
import {Sequence, interpolate, staticFile, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import {ASSETS, type SfxName} from '../assets';
import {matchTiming} from '../parts/MatchGraph';
import {ctaTiming} from '../beats/Beat4CTA';
import {beatWindows, LEAD, t, TOTAL_SEC} from '../timing/beats';
import {useSpot} from '../overlays/lib';

/**
 * Master gain on the voice-over.
 *
 * Measured, not guessed. At unity the rendered spot came back at
 * −12.10 LUFS integrated / −0.76 dBTP, so this is −3.90 dB, landing it
 * on the −16 LUFS target with true peak well under −1 dBTP. The VO file
 * itself is never normalised — only this value changes.
 *
 * Re-measure and reset this after adding the music bed:
 *   npx remotion ffmpeg -i out/aa40_9x16.mp4 -map 0:a -vn \
 *     -af loudnorm=I=-16:TP=-1:LRA=11:print_format=json -f null -
 */
export const VO_GAIN = 0.638;

/** dB → linear. */
const db = (v: number) => Math.pow(10, v / 20);

const MUSIC_BED_DB = -18;
const MUSIC_SWELL_DB = -10;

type Hit = {name: SfxName; sec: number; gain?: number; label: string};

/** Every SFX hit, in seconds, already LEAD-adjusted. */
export const sfxHits = (fps: number): Hit[] => {
	const lead = LEAD / fps;
	const m = matchTiming(fps);
	const cta = ctaTiming(fps);
	const w = beatWindows(fps);
	return [
		{name: 'stamp', sec: t.forty - lead, label: 'stamp impact on "forty"'},
		{name: 'whoosh', sec: t.opening - lead, label: 'strike-through on "opening"'},
		{
			name: 'connect',
			sec: m.arrival - lead,
			gain: 0.8,
			label: 'connect chime as the match lands',
		},
		{
			name: 'whoosh',
			sec: w.sweep.start,
			gain: 0.7,
			label: 'whoosh tail under the light sweep',
		},
		{name: 'slam', sec: cta.slam1, label: 'slam on "Get Matched"'},
		{name: 'slam', sec: cta.slam2, label: 'slam on "Get Paid"'},
		{name: 'rise', sec: cta.urlAt, gain: 0.75, label: 'rising shimmer under the URL'},
	];
};

export const Soundtrack: React.FC = () => {
	const {fps} = useVideoConfig();
	const {mode} = useSpot();

	// Overlay renders are muted by definition — they get composited over
	// footage that carries its own audio.
	if (mode === 'overlay') return null;

	const cta = ctaTiming(fps);

	return (
		<>
			{/* Voice-over — the spine. */}
			{ASSETS.vo ? <Audio src={staticFile(ASSETS.vo)} volume={VO_GAIN} /> : null}

			{/*
			 * Music bed. TODO: drop a licensed 20s+ bed into
			 * assets-in/music.mp3 and re-run `node scripts/scan-assets.mjs`.
			 * Until then this slot renders nothing rather than 404-ing the
			 * render; the ducking curve below is already the one it will use.
			 */}
			{ASSETS.music ? (
				<Audio
					src={staticFile(ASSETS.music)}
					volume={(f) => {
						const sec = f / fps;
						const bed = db(MUSIC_BED_DB);
						const swell = db(MUSIC_SWELL_DB);
						// Fade up under beat 1, swell from "Get Matched",
						// resolve into the end card.
						const intro = interpolate(sec, [0, 0.8], [0, bed], {
							extrapolateLeft: 'clamp',
							extrapolateRight: 'clamp',
						});
						const lifted = interpolate(
							sec,
							[cta.slam1 - 0.15, cta.slam1 + 0.6],
							[intro, swell],
							{extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
						);
						return interpolate(sec, [TOTAL_SEC - 1.6, TOTAL_SEC], [lifted, 0], {
							extrapolateLeft: 'clamp',
							extrapolateRight: 'clamp',
						});
					}}
				/>
			) : null}

			{/* Sound design. Missing files are skipped, never synthesised. */}
			{sfxHits(fps).map((hit, i) => {
				const file = ASSETS.sfx[hit.name];
				if (!file) return null;
				return (
					<Sequence
						key={`${hit.name}-${i}`}
						name={`sfx: ${hit.label}`}
						from={Math.round(hit.sec * fps)}
						layout="none"
					>
						<Audio src={staticFile(file)} volume={hit.gain ?? 1} />
					</Sequence>
				);
			})}
		</>
	);
};
