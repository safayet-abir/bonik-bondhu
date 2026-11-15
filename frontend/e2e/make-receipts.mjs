// Renders the SYNTHETIC E2 receipt set (backend/tests/ai/e2_receipts.json) to JPEG files with
// headless Edge, so Bangla text is shaped correctly (Pillow here has no complex-script support).
// Usage: node e2e/make-receipts.mjs <outDir>
import { mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [out = "e2-receipts"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const { receipts } = JSON.parse(readFileSync(new URL("../../backend/tests/ai/e2_receipts.json", import.meta.url), "utf8"));

const FONTS = {
  thermal: "'Courier New', monospace", invoice: "'Segoe UI', Arial, sans-serif", bn: "'Nirmala UI', 'Vrinda', sans-serif",
  hand: "'Ink Free', 'Segoe Print', cursive", khata: "'Vrinda', 'Nirmala UI', sans-serif",
};
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ deviceScaleFactor: 2 });
for (const r of receipts) {
  const body = r.lines.map((l) => l === "--" ? "<hr>" : l.startsWith("## ") ? `<b>${esc(l.slice(3))}</b>` : `<div>${esc(l)}</div>`).join("");
  const width = r.style === "thermal" ? 330 : 520;
  const lined = r.style === "khata" ? "background: repeating-linear-gradient(#fdfbf2 0 31px, #9ec5e8 31px 32px);" : "background:#fff;";
  await page.setContent(`<html><body style="margin:0;padding:30px;background:#d9d6cf">
    <div id="r" style="width:${width}px;padding:22px;font:18px/1.6 ${FONTS[r.style]};color:${r.faded ? "#9a9a9a" : "#111"};${lined}
      transform:rotate(${r.rotate ?? 0}deg);filter:blur(${r.blur ?? 0}px);box-shadow:0 2px 6px #0003"><style>b,div{white-space:pre-wrap} b{display:block;font-size:20px} hr{border:0;border-top:1px dashed #555}</style>${body}</div></body></html>`);
  const box = await page.locator("#r").boundingBox(); // the receipt (rotated box included) plus a margin
  await page.screenshot({ path: join(out, `${r.id}.jpg`), type: "jpeg", quality: 80,
                          clip: { x: box.x - 20, y: box.y - 20, width: box.width + 40, height: box.height + 40 } });
}
await browser.close();
console.log(`${receipts.length} receipts written to ${out}`);
