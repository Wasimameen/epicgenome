// Downloads the two typefaces into public/fonts so renders never touch
// the network. Run once; re-run only to pick up a new Google Fonts
// revision.
//
//   node scripts/fetch-fonts.mjs
//
// @remotion/google-fonts is used purely to resolve the current URLs —
// the render itself loads the local files through @remotion/fonts.

import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {getInfo: soraInfo} = require('@remotion/google-fonts/Sora');
const {getInfo: bebasInfo} = require('@remotion/google-fonts/BebasNeue');

const OUT = path.join(process.cwd(), 'public', 'fonts');
fs.mkdirSync(OUT, {recursive: true});

const targets = [
	{
		name: 'Sora-variable.woff2',
		url: soraInfo().fonts.normal['400'].latin,
		note: 'Sora is a variable font: one file covers 100–800.',
	},
	{
		name: 'BebasNeue-400.woff2',
		url: bebasInfo().fonts.normal['400'].latin,
		note: 'Bebas Neue ships a single 400 weight.',
	},
];

for (const target of targets) {
	const res = await fetch(target.url);
	if (!res.ok) {
		throw new Error(`${target.name}: ${res.status} ${res.statusText} for ${target.url}`);
	}
	const buf = Buffer.from(await res.arrayBuffer());
	fs.writeFileSync(path.join(OUT, target.name), buf);
	console.log(`[fonts] ${target.name}  ${buf.length} bytes  — ${target.note}`);
}

console.log('[fonts] done — src/theme.ts loads these via @remotion/fonts');
