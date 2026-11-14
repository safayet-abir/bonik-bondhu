// P4 Definition of Done walkthrough on the DEMO seed (run `python -m app.cli
// reset-demo` first; `import-news ../data/news/curated_news.csv` is optional —
// real items only add extra cards).
//   D1 Rahim Store → supplier bars 65/25/10 + high dependency; Risks tab golden
//                    what-ifs; News: DEMO Kaliakair blockade via Supplier A,
//                    Dhamrai flood NOT shown; test the risk → computed, status unchanged
//   D3 Rahim Farm  → Risks tab crop what-ifs; News: Dhamrai flood → test → yield −20%
//
// Usage: node e2e/p4-walkthrough.mjs <baseUrl> <screenshotDir> [demoPassword | env DEMO_PASSWORD]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [base = "http://localhost:8000", shots = "e2e-shots-p4", demoPw = process.env.DEMO_PASSWORD] = process.argv.slice(2);
if (!demoPw) throw new Error("pass the DEMO password as 3rd argument or DEMO_PASSWORD");
mkdirSync(shots, { recursive: true });
const step = (msg) => console.log(`✓ ${msg}`);

const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ viewport: { width: 360, height: 760 } });
const shot = (name) => page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
const text = (s, exact = false) => page.getByText(s, { exact }).first().waitFor();
const tab = (name) => page.getByRole("button", { name }).click();

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
}

async function checkFirstRequest() {
  await page.getByRole("link", { name: "Financing" }).click();
  await page.getByRole("link", { name: /DEMO/ }).first().click();
  await page.waitForURL(/step\/2/);
  await page.goto(page.url().replace(/step\/2$/, "step/5"));
  await page.getByRole("button", { name: "Check" }).click();
  await page.waitForURL(/\/assessment\//);
}

try {
  await login("01900000001", demoPw);
  await openProfile("Rahim Store");

  // ------------------------------------------------------------ SCR-O08 dependency
  await page.goto(page.url().replace(/\/home$/, "/suppliers"));
  await page.getByRole("button", { name: "EN" }).click();
  await text("Who you buy from");
  await text("65% · Tk 4,88,800");
  await text("25% · Tk 1,88,000");
  await text("10% · Tk 75,200");
  await text("High dependency on one supplier (65%)");
  await text("Basis: 24 purchase entries in the last 8 weeks (total Tk 7,52,000)");
  await shot("01-d1-suppliers");
  step("D1 suppliers: 65/25/10 bars, high dependency, basis = 24 linked purchases");

  // ------------------------------------------------------------ SCR-O12 risks
  await page.goto(page.url().replace(/\/suppliers$/, "/home"));
  await checkFirstRequest();
  await text("Ready for lender review");
  await text("Most purchases come from one supplier");
  await tab("Risks");
  await text("What-if only — does not change your result");
  await text("If Supplier A (DEMO wholesaler) cannot deliver for 7 days");
  await text(/9,376\.9/);
  await text(/12,377\.35/);
  await text(/4,465\.12/);
  await text("We assumed 65% of your weekly net cash stops for 7 days", false);
  await shot("02-d1-risks");
  step("D1 risks: delay 7d short 9,376.90; delay 14d 12,377.35; price +15% 4,465.12; assumptions in words");

  // ------------------------------------------------------------ SCR-O12 news
  await tab(/^News/);
  await text("DEMO: Road blockade reported near a wholesale market in Kaliakair (fictional)");
  await text("Same area as your supplier Supplier A (DEMO wholesaler)");
  await text("Reported by one source — not confirmed");
  if (await page.getByText("ধামরাইয়ে নিচু জমিতে").count()) throw new Error("D1 must not show the Dhamrai flood");
  await shot("03-d1-news");
  const demoCard = page.getByRole("article", { name: /^DEMO: Road blockade reported near/ });
  await demoCard.getByRole("button", { name: "Test this risk" }).click();
  await demoCard.getByText("Tested — see the Risks tab").waitFor();
  await tab("Risks");
  await text("From a news item you chose to test");
  await tab("Result");
  await text("Ready for lender review");
  await text("A news signal comes from one source only");
  await shot("04-d1-after-test");
  step("D1 news: DEMO blockade via Supplier A (single source), Dhamrai flood absent; tested → status unchanged");

  // ------------------------------------------------------------ D3 farm
  await openProfile("Rahim Rice Farm");
  await checkFirstRequest();
  await text("Ready for lender review");
  await tab("Risks");
  await text("If the harvest price is 15% below your low price");
  await text("Tk 53,260");
  await text("Tk 49,480");
  await text("Tk 24.72");
  await text("Before harvest, cash may be short by Tk 1,275");
  await shot("05-d3-risks");
  step("D3 risks: price −15% → 53,260; yield −20% → 49,480 / loan-cover 24.72; inputs +15% pre-harvest short 1,275");
  await tab(/^News/);
  await text("Same area as your business");
  const flood = page.getByRole("article", { name: /ধামরাইয়ে নিচু জমিতে/ });
  await flood.getByText("Suggested what-if: If the harvest is 20% below your low output").waitFor();
  await flood.getByRole("button", { name: "Test this risk" }).click();
  await flood.getByText("Tested — see the Risks tab").waitFor();
  await shot("06-d3-news");
  step("D3 news: DEMO Dhamrai flood via upazila → yield −20% proposed → tested");

  // ------------------------------------------------------------ Bangla
  await page.getByRole("button", { name: "বাং" }).click();
  await tab("ঝুঁকি");
  await text("শুধু \"যদি এমন হয়\" হিসাব — আপনার ফলাফল বদলায় না");
  await shot("07-d3-risks-bn");
  step("Bangla risks tab renders");
} finally {
  await browser.close();
}
