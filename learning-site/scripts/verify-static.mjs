import assert from 'node:assert/strict';
import { readFileSync, statSync } from 'node:fs';
import { resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const out = fileURLToPath(new URL('../out/', import.meta.url));
const html = readFileSync(resolve(out, 'index.html'), 'utf8');
assert.match(html, /市场情报系统源码导读/);
assert.match(html, /id="labs"/);
assert.match(html, /\/learn\/_next\/static\/[^" ]+\.css/);
assert.match(html, /\/learn\/_next\/static\/[^" ]+\.js/);
assert.match(html, /\/learn\/favicon\.svg/);
assert.match(html, /\/learn\/market-intel-og\.png/);
assert.ok(statSync(resolve(out, '404.html')).isFile());

// Inspect HTML attributes, not embedded RSC data or example code snippets.
const paths = new Set();
for (const [, reference] of html.matchAll(/(?:src|href)="([^"#]+)"/g)) {
  if (!reference.startsWith('/')) continue;
  assert.ok(reference.startsWith('/learn/'), `Asset escaped /learn: ${reference}`);
  paths.add(reference);
}
paths.add('/learn/market-intel-og.png');
for (const reference of paths) {
  const path = resolve(out, decodeURIComponent(reference.slice('/learn/'.length).split('?')[0]));
  assert.ok(path.startsWith(out.endsWith(sep) ? out : out + sep));
  assert.ok(statSync(path).isFile(), `Missing exported asset: ${reference}`);
}
console.log(`PASS: static HTML, 404, /learn prefix and ${paths.size} exported assets.`);
