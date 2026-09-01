// Assemble .dc.html artboards from .src templates + the shared _style.inc.
// Artboards share nothing at runtime, so the console vocabulary is duplicated
// into each one rather than imported.
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
const css = readFileSync('_style.inc', 'utf8');
for (const f of readdirSync('.').filter((n) => n.endsWith('.src'))) {
  const out = f.replace(/\.src$/, '.dc.html');
  writeFileSync(out, readFileSync(f, 'utf8').replace('@@STYLE@@', css));
  console.log('built', out);
}
