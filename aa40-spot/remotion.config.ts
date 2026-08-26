import {Config} from '@remotion/cli/config';

// Full (non-alpha) defaults. The alpha/overlay renders override codec,
// image format and pixel format on the command line — see out/README.md.
Config.setVideoImageFormat('jpeg');
Config.setCodec('h264');
Config.setChromiumOpenGlRenderer('angle');
Config.setOverwriteOutput(true);
Config.setConcurrency(4);

// NOTE: CRF is deliberately NOT set here. It is an H.264/VP9 setting and
// ProRes rejects it outright, so a global default would break the alpha
// renders. The H.264 jobs pass `--crf=16` on the command line instead —
// see out/README.md.
