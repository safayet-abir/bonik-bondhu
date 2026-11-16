// Plan Ultra F1 — Repayment Fit Finder in the browser (run `python -m app.cli reset-demo` first).
//   D1 Rahim Store      → finder shows fitting schedules → "Use this schedule" → Check → ready for lender review
//   D3 Rahim Rice Farm  → options after the harvest; farm examples in the wizard (F0)
//   D2 Karim Variety    → "No schedule we tried fits" with the closest miss — said plainly
// Usage: node e2e/ultra-fit.mjs <baseUrl> <shotsDir> [demoPassword | env DEMO_PASSWORD]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { launchOpts, rec } from "./rec.mjs";

const [base = "http://localhost:8000", shots = "e2e-shots-ultra-fit", demoPw = process.env.DEMO_PASSWORD] = process.argv.slice(2);
if (!demoPw) throw new Error("pass the DEMO password as 3rd argument or DEMO_PASSWORD");
mkdirSync(shots, { recursive: true });
const step = (msg) => console.log(`✓ ${msg}`);
const browser = await chromium.launch(launchOpts);
const size = { width: 360, height: 760 };
const ctx = await browser.newContext({ viewport: size, ...rec(size) });
const page = await ctx.newPage();
const shot = (name) => page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
const text = (s, timeout = 30_000) => page.getByText(s).first().waitFor({ timeout });
const en = () => page.getByRole("button", { name: "EN", exact: true }).first().click();
const get = async (path) => (await page.request.get(`${base}/api/v1${path}`)).json();

async function login(phone) {
  await ctx.clearCookies();
  await page.goto(`${base}/login`);
  await page.getByLabel(/Mobile number|মোবাইল নম্বর/).fill(phone);
  await page.getByLabel(/Password|পাসওয়ার্ড/).fill(demoPw);
  await page.locator("form").getByRole("button", { name: /^(Log in|লগইন করুন)$/ }).click();
  await page.waitForURL(/\/(profiles|p\/)/);
}
async function wizard(profileName, stepNo) {
  const pid = (await get("/profiles")).items.find((p) => p.display_name === profileName).id;
  const rid = (await get(`/profiles/${pid}/financing-requests`)).items[0].id;
  await page.goto(`${base}/p/${pid}/financing/${rid}/step/${stepNo}`);
  await en();
  return { pid, rid };
}

try {
  await login("01900000001");
  await wizard("Rahim Store", 5);
  await page.getByRole("button", { name: "Find schedules that fit" }).click();
  await text("Safest — most cash left");
  await text("schedules tried with the same check as your result");
  await shot("01-shop-options");
  await page.getByRole("button", { name: "Use this schedule" }).first().click();
  await page.waitForTimeout(800);
  await page.getByRole("button", { name: "Check", exact: true }).click();
  await page.waitForURL(/\/assessment\//, { timeout: 30_000 });
  await text("Ready for lender review");
  await shot("02-shop-ready");
  step("D1: finder → use the safest schedule → check → ready for lender review");

  // F2: World Bank inflation what-if on the result, economy card on Home
  await page.getByRole("button", { name: /^Risks/ }).click();
  await text("If prices keep rising at last year's inflation");
  await text("Based on World Bank data");
  await shot("02b-inflation-whatif");
  await page.getByRole("link", { name: "Home" }).click();
  await text("Bangladesh economy (World Bank)");
  await text("not live, and not about your business");
  await shot("02c-home-economy");
  step("F2: inflation what-if on the Risks tab; World Bank figures on Home with year and source");

  await wizard("Rahim Rice Farm", 1);
  await text("Example: buy urea, seed and diesel for the Boro season"); // F0: farm examples for a farm
  await wizard("Rahim Rice Farm", 5);
  await page.getByRole("button", { name: "Find schedules that fit" }).click();
  await text("is left after the repayment");
  await shot("03-farm-options");
  step("D3: farm examples in the wizard; schedules after the harvest with the surplus shown");

  await login("01900000002");
  await wizard("Karim Variety Store", 5);
  await page.getByRole("button", { name: "Find schedules that fit" }).click();
  await text("No schedule we tried fits your cash right now");
  await text("Closest:");
  await shot("04-none-fits");
  step("D2: nothing fits → said plainly with the closest miss");
  console.log("Plan Ultra F1 (Fit Finder) passed");
} catch (err) {
  await shot("zz-failure").catch(() => {});
  throw err;
} finally {
  await browser.close();
}
