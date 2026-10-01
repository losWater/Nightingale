import { readFileSync, writeFileSync } from 'node:fs';
const lib = readFileSync(new URL('./box_lib.mjs', import.meta.url), 'utf8');
const mod = await import('data:text/javascript;base64,' + Buffer.from(lib + '\ninit_combo();\nexport { comboFeelData, fingerLoad };').toString('base64'));
writeFileSync('combo.json', JSON.stringify(mod.comboFeelData));
writeFileSync('finger_load.json', JSON.stringify(mod.fingerLoad));
console.log(Object.keys(mod.comboFeelData).length, Object.keys(mod.fingerLoad).length, JSON.stringify(mod.fingerLoad).slice(0, 300));
