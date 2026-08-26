import React from 'react';
import {Composition, Folder} from 'remotion';
import {DEFAULT_DISCLAIMER, Spot, type SpotProps} from './Spot';
import {ASSETS} from './assets';
import {t, totalFrames} from './timing/beats';

const FPS = 30;
const DURATION = totalFrames(FPS);

const base: SpotProps = {
	aspect: '9x16',
	mode: 'full',
	disclaimer: DEFAULT_DISCLAIMER,
	brand: ASSETS.brand,
};

/** The end-card frame used for the thumbnails. */
const THUMB_FRAME = Math.round((t.end + 1.4) * FPS);

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Folder name="Full">
				<Composition
					id="AA40-9x16"
					component={Spot}
					durationInFrames={DURATION}
					fps={FPS}
					width={1080}
					height={1920}
					defaultProps={{...base, aspect: '9x16', mode: 'full'}}
				/>
				<Composition
					id="AA40-16x9"
					component={Spot}
					durationInFrames={DURATION}
					fps={FPS}
					width={1920}
					height={1080}
					defaultProps={{...base, aspect: '16x9', mode: 'full'}}
				/>
			</Folder>

			<Folder name="Overlay">
				<Composition
					id="AA40-9x16-overlay"
					component={Spot}
					durationInFrames={DURATION}
					fps={FPS}
					width={1080}
					height={1920}
					defaultProps={{...base, aspect: '9x16', mode: 'overlay'}}
				/>
				<Composition
					id="AA40-16x9-overlay"
					component={Spot}
					durationInFrames={DURATION}
					fps={FPS}
					width={1920}
					height={1080}
					defaultProps={{...base, aspect: '16x9', mode: 'overlay'}}
				/>
			</Folder>

		</>
	);
};

/**
 * Thumbnails are stills of the full compositions at THUMB_FRAME, not
 * separate compositions:
 *   npx remotion still AA40-9x16 out/thumb_9x16.png --frame=<THUMB_FRAME>
 */
export {THUMB_FRAME};
