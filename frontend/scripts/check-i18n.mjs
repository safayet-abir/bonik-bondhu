// CI: bn.json and en.json must have exactly the same keys, and no empty
// values (FR-I18N-01). Exit code 1 on any difference.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const dir = join(dirname(fileURLToPath(import.meta.url)), "..", "src", "i18n");
const load = (lang) => JSON.parse(readFileSync(join(dir, `${lang}.json`), "utf8"));
const bn = load("bn");
const en = load("en");

const problems = [];
for (const k of Object.keys(bn)) if (!(k in en)) problems.push(`missing in en.json: ${k}`);
for (const k of Object.keys(en)) if (!(k in bn)) problems.push(`missing in bn.json: ${k}`);
for (const [lang, obj] of [["bn", bn], ["en", en]]) {
  for (const [k, v] of Object.entries(obj)) {
    if (typeof v !== "string" || !v.trim()) problems.push(`empty value in ${lang}.json: ${k}`);
  }
}

if (problems.length) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log(`i18n OK: ${Object.keys(bn).length} keys in bn and en`);
