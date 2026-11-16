// P6 walkthrough with AI ON (real Gemini/Groq from backend/.env; P6-T07 "manual with AI on").
// Run `python -m app.cli reset-demo` first and again afterwards (it adds an entry and AI items to D1).
//   D1 Rahim Store → receipt photo → AI draft → owner checks → saved as photo_assisted
//                  → wizard "Make the list with AI" → items without prices → owner prices one → counts
//                  → Advisor answers from the real profile tools (Supplier 1 label, en + bn)
//
// Usage: node e2e/p6-ai-on.mjs <baseUrl> <screenshotDir> <receipt.jpg> [demoPassword | env DEMO_PASSWORD]
// The receipt must show TOTAL Tk 3,450 — use r01 from `node e2e/make-receipts.mjs <outDir>`.
import { mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { launchOpts, rec } from "./rec.mjs";

const [base = "http://localhost:8000", shots = "e2e-shots-p6-ai", receipt, demoPw = process.env.DEMO_PASSWORD] = process.argv.slice(2);
if (!receipt || !demoPw) throw new Error("usage: p6-ai-on.mjs <base> <shots> <receipt.jpg> [demoPassword]");
mkdirSync(shots, { recursive: true });
const step = (msg) => console.log(`✓ ${msg}`);
const AI_WAIT = { timeout: 90_000 }; // free-tier LLM calls can take a while

const browser = await chromium.launch(launchOpts);
const page = await browser.newPage({ viewport: { width: 360, height: 760 }, ...rec({ width: 360, height: 760 }) });
const shot = (name) => page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
const text = (s, opts = {}) => page.getByText(s, { exact: false }).first().waitFor(opts);
const get = async (path) => (await page.request.get(`${base}/api/v1${path}`)).json();
const en = () => page.getByRole("button", { name: "EN", exact: true }).click();

try {
  await page.goto(`${base}/login`);
  if (await page.getByRole("button", { name: "EN", exact: true }).isVisible()) await en();
  await page.getByLabel(/Mobile number|মোবাইল নম্বর/).fill("01900000001");
  await page.getByLabel(/Password|পাসওয়ার্ড/).fill(demoPw);
  await page.getByRole("button", { name: /^(Log in|লগ ইন)$/ }).click();
  await page.waitForURL(/\/(profiles|p\/)/);
  await page.goto(`${base}/profiles`);
  await page.getByText("Rahim Store", { exact: true }).click();
  await page.waitForURL(/\/p\/[^/]+\/home/);
  await en();
  const pid = page.url().match(/\/p\/([^/]+)\//)[1];
  if ((await get("/health")).llm !== "configured") throw new Error("AI must be configured (LLM_PROVIDER + key)");

  // 1. Receipt → AI draft → owner confirms (FR-EXT-02/03)
  await page.getByRole("link", { name: "Entries" }).click();
  await page.getByRole("button", { name: "Entry from a receipt photo" }).click();
  await page.locator("input[type=file]").setInputFiles({ name: "receipt.jpg", mimeType: "image/jpeg", buffer: readFileSync(receipt) });
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Read with AI" }).click();
  await page.waitForURL(/entries\/new/, AI_WAIT);
  if (!page.url().includes("draft=")) {
    await shot("zz-no-draft");
    throw new Error(`AI did not return a draft: ${new URL(page.url()).searchParams.get("notice")}`);
  }
  await text("Check and correct what AI read");
  const amount = await page.getByLabel("Amount (Tk)").inputValue();
  if (await page.getByText("Choose what happened — AI could not tell").count()) {
    await page.getByRole("button", { name: "Stock purchase (cash)" }).click();
  }
  const pressed = await page.locator("fieldset button[aria-pressed=true]").first().textContent();
  await shot("01-ai-draft");
  step(`AI draft: type="${pressed}", amount=${amount}, date=${new URL(page.url()).searchParams.get("date")}`);
  if (amount !== "3450.00") throw new Error(`AI read the amount as ${amount}, expected 3450.00`);
  await page.getByRole("button", { name: "Save" }).click();
  await text("Saved");
  // the list is ordered by value date, and the receipt's date is older than the seed's latest entries
  const tx = (await get(`/profiles/${pid}/transactions?limit=200`)).items.find((t) => t.entry_method === "photo_assisted");
  if (!tx || tx.evidence_state !== "document_attached" || tx.amount !== "3450.00") {
    throw new Error(`saved entry is not a confirmed photo draft: ${JSON.stringify(tx)}`);
  }
  step("owner confirmed → photo_assisted + document_attached, Tk 3450.00");

  // 2. Purpose → AI items (no prices) → owner prices one → it counts (FR-FIN-03)
  const req = (await get(`/profiles/${pid}/financing-requests`)).items[0];
  const before = Number(req.preview.items_total);
  await page.goto(`${base}/p/${pid}/financing/${req.id}/step/2`);
  await en();
  await page.getByRole("button", { name: "Make the list with AI" }).click();
  await text("AI made a list — add a price to each item and confirm it", AI_WAIT);
  let detail = await get(`/profiles/${pid}/financing-requests/${req.id}`);
  const ai = detail.items.filter((i) => i.ai_proposed && !i.confirmed);
  if (!ai.length || ai.some((i) => i.unit_price !== null)) throw new Error("AI items missing or carry a price");
  if (Number(detail.preview.items_total) !== before) throw new Error("unconfirmed AI items changed the total");
  step(`AI list: ${ai.map((i) => `${i.item_name} ${i.quantity} ${i.unit}`).join(", ")} — no prices, not counted`);
  const row = page.locator("li", { has: page.getByText("AI suggestion — add a price and confirm") }).first();
  await row.getByLabel("Price per unit (Tk)").fill("2500");
  await shot("02-ai-items");
  await row.getByRole("button", { name: "Confirm this item" }).click();
  // poll: a slow host may still be saving; the first row on screen need not be ai[0] of the API list
  let confirmed;
  for (let i = 0; i < 30 && !confirmed; i++) {
    if (i) await page.waitForTimeout(1000);
    detail = await get(`/profiles/${pid}/financing-requests/${req.id}`);
    confirmed = detail.items.find((it) => it.ai_proposed && it.confirmed);
  }
  if (!confirmed?.confirmed || Number(detail.preview.items_total) !== before + Number(confirmed.line_total)) {
    throw new Error("confirmed AI item did not count");
  }
  step(`owner priced "${confirmed.item_name}" → counted, items total ${before} → ${detail.preview.items_total}`);

  // 3. Advisor with the real profile tools
  await page.getByRole("link", { name: "Advisor" }).click();
  if (await page.getByText("AI chat is off").count()) throw new Error("advisor says AI is off");
  for (const q of ["Which supplier do I depend on most?", "এই মাসে আমার বিক্রি কত?"]) {
    const n = await page.locator("ol > li").count();
    await page.getByLabel(/Your question|আপনার প্রশ্ন/).fill(q);
    await page.getByRole("button", { name: /^(Ask|জিজ্ঞেস করুন)$/ }).click();
    await page.locator("ol > li").nth(n + 1).waitFor(AI_WAIT);
    await page.getByText(/Looking at your records|আপনার হিসাব দেখছি/).waitFor({ state: "detached", ...AI_WAIT });
    console.log(`  Q: ${q}\n  A: ${(await page.locator("ol > li").last().innerText()).replace(/\n/g, " | ")}`);
  }
  const chat = await page.locator("ol").innerText();
  if (/Supplier A|DEMO wholesaler/.test(chat)) throw new Error("supplier name reached the advisor reply");
  if (/approved|eligible|credit score|probability of default/i.test(chat)) throw new Error("forbidden words in reply");
  await shot("03-advisor-ai-on");
  step("advisor replied from the profile's tools; labels only, no forbidden words");
  console.log("P6 walkthrough (AI on) passed");
} catch (err) {
  await shot("zz-failure").catch(() => {});
  throw err;
} finally {
  await browser.close();
}
