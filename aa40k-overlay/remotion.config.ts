import {Config} from '@remotion/cli/config';

/**
 * Alpha-overlay defaults (spec §7).
 *
 * PNG frames carry a real alpha channel, `yuva444p10le` keeps it through the
 * encoder, and ProRes 4444 is the profile that stores it. These are the Studio
 * / bare-`remotion render` defaults; the commands in out/README.md pass the
 * same flags explicitly so the deliverable never depends on this file.
 */
Config.setVideoImageFormat('png');
Config.setPixelFormat('yuva444p10le');
Config.setCodec('prores');

// NOTE: the ProRes profile is deliberately *not* set here. Remotion throws if a
// ProRes profile is set while the codec is anything else, and a config-file
// value cannot be unset from the command line — which broke the VP9 fallback
// render. The profile lives in each composition's `calculateMetadata` instead,
// and every render command passes `--prores-profile=4444` explicitly.

// The overlay carries no audio — the voice-over is used for timing only.
Config.setMuted(true);

// Transparent checkerboard in the Studio preview so alpha is always visible.
Config.setChromiumOpenGlRenderer('angle');
Config.setConcurrency(null);
Config.overrideWebpackConfig((c) => c);
