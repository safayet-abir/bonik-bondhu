// P6 walkthrough with AI OFF (LLM_PROVIDER=none, AI-09 / NFR-03): every AI
// feature falls back and the owner can still finish the job. Run
// `python -m app.cli reset-demo` first.
//   D1 Rahim Store → nav has Advisor · receipt photo + "Read with AI" → manual
//                    form with the photo attached → saved · Advisor: AI off
//                    banner, quick answers from records, help topics, Bangla ·
//                    wizard "Make the list with AI" → friendly fallback
//   D3 Rahim Farm  → Advisor forecast chip says farms have no weekly forecast
//
// Usage: node e2e/p6-walkthrough.mjs <baseUrl> <screenshotDir> [demoPassword | env DEMO_PASSWORD]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [base = "http://localhost:8000", shots = "e2e-shots-p6", demoPw = process.env.DEMO_PASSWORD] = process.argv.slice(2);
if (!demoPw) throw new Error("pass the DEMO password as 3rd argument or DEMO_PASSWORD");
mkdirSync(shots, { recursive: true });
const step = (msg) => console.log(`✓ ${msg}`);
// 2×2 white PNG (a real image the server can decode and re-encode)
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEklEQVR4nGP4//8/AxJgYGBgAAB4CQX7Ex0VVQAAAABJRU5ErkJggg==", "base64");

const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ viewport: { width: 360, height: 760 } });
const shot = (name) => page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
const text = (s, exact = false) => page.getByText(s, { exact }).first().waitFor();

async function login(phone, password) {
  await page.goto(`${base}/login`);
  if (await page.getByRole("button", { name: "EN" }).isVisible()) await page.getByRole("button", { name: "EN" }).click();
  await page.getByLabel(/Mobile number|মোবাইল নম্বর/).fill(phone);
  await page.getByLabel(/Password|পাসওয়ার্ড/).fill(password);
  await page.getByRole("button", { name: /^(Log in|লগ ইন)$/ }).click();
  await page.waitForURL(/\/(profiles|p\/)/);
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "EN" }).click();
}

async function openProfile(name) {
  await page.goto(`${base}/profiles`);
  await page.getByText(name, { exact: true }).click();
  await page.waitForURL(/\/p\/[^/]+\/home/);
  await page.getByRole("button", { name: "EN" }).click();
  return page.url().match(/\/p\/([^/]+)\//)[1];
}

try {
  await login("01900000001", demoPw);
  const pid = await openProfile("Rahim Store");
  const health = await (await page.request.get(`${base}/api/v1/health`)).json();
  if (health.llm !== "disabled") throw new Error("run this walkthrough with LLM_PROVIDER=none");
  await page.getByRole("link", { name: "Advisor" }).waitFor();
  if (await page.getByRole("link", { name: "Add", exact: true }).count()) throw new Error("nav still has Add");
  step("nav: Home · Entries · Financing · Advisor · More");

  // Receipt photo with AI off -> manual form, photo attached (FR-EXT-04)
  await page.getByRole("link", { name: "Entries" }).click();
  await page.getByRole("button", { name: "Entry from a receipt photo" }).click();
  await page.locator("input[type=file]").setInputFiles({ name: "receipt.png", mimeType: "image/png", buffer: PNG });
  await page.getByRole("img", { name: "Receipt photo" }).waitFor();
  const readAi = page.getByRole("button", { name: "Read with AI" });
  if (await readAi.isEnabled()) throw new Error("AI read must need the consent tick");
  await page.getByRole("checkbox").check();
  await readAi.click();
  await page.waitForURL(/entries\/new/);
  await text("AI is not available right now");
  await text("Please type the entry yourself. The photo stays attached.");
  await page.getByRole("img", { name: "Receipt photo" }).waitFor();
  await page.getByRole("button", { name: "Stock purchase (cash)" }).click();
  await page.getByLabel("Amount (Tk)").fill("1234");
  await shot("01-photo-manual-fallback");
  await page.getByRole("button", { name: "Save" }).click();
  await text("Saved", true);
  const list = await (await page.request.get(`${base}/api/v1/profiles/${pid}/transactions?limit=1`)).json();
  if (list.items[0].evidence_state !== "document_attached" || list.items[0].amount !== "1234.00") {
    throw new Error("photo was not attached to the saved entry");
  }
  step("photo kept as evidence; AI off falls back to the manual form");

  // Advisor with AI off: help menu with answers from the records
  await page.getByRole("link", { name: "Advisor" }).click();
  await text("AI chat is off. The buttons below still answer from your records.");
  await page.getByRole("button", { name: "Installments in the next 7 days" }).click();
  await text("Known installments in the next 7 days");
  await text("Fixed answer from your records", true);
  await page.getByRole("button", { name: "Supplier dependency" }).click();
  await text("of your purchases go to Supplier 1");
  if (await page.getByText("Supplier A (DEMO wholesaler)").count()) throw new Error("supplier name shown in advisor");
  await page.getByText("What is the funding gap?").click();
  await text("That is the gap.");
  await shot("02-advisor-ai-off");
  await page.getByRole("button", { name: "বাং" }).click();
  await page.getByRole("heading", { name: "সাহায্য" }).waitFor();
  await text("আগামী ৭ দিনের কিস্তি");
  await shot("03-advisor-bangla");
  await page.getByRole("button", { name: "EN" }).click();
  step("advisor help menu (EN + বাংলা), Supplier 1 label only");

  // Wizard: AI list falls back politely, manual items still work
  const reqs = await (await page.request.get(`${base}/api/v1/profiles/${pid}/financing-requests`)).json();
  await page.goto(`${base}/p/${pid}/financing/${reqs.items[0].id}/step/2`);
  await page.getByRole("button", { name: "EN" }).click(); // a reload restores the saved language
  await page.getByRole("button", { name: "Make the list with AI" }).click();
  await text("AI is not available right now");
  await page.getByRole("button", { name: "Add item" }).first().waitFor();
  await shot("04-wizard-ai-off");
  step("wizard: AI list unavailable → manual items still there");

  // Farm: no forecast
  await openProfile("Rahim Rice Farm");
  await page.getByRole("link", { name: "Advisor" }).click();
  await page.getByRole("button", { name: "Estimate for coming weeks" }).click();
  await text("Farm profiles have no weekly forecast");
  step("farm advisor: no weekly forecast");
  console.log("P6 walkthrough (AI off) passed");
} catch (err) {
  await shot("zz-failure").catch(() => {});
  throw err;
} finally {
  await browser.close();
}
