// Plan Ultra F4 — Supply graph in the browser (run `python -m app.cli reset-demo` first).
//   D1 Rahim Store: graph from Suppliers → pick the Kaliakair area (65 %) → "Stops 7 days" → the golden D1
//   delay result (short by Tk 9,376.90) labelled what-if only; D3 farm: graph shows the rice crop, no what-if.
// Usage: node e2e/f4-graph.mjs <baseUrl> <shotsDir> [demoPassword | env DEMO_PASSWORD]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { launchOpts, rec } from "./rec.mjs";

const [base = "http://localhost:8000", shots = "e2e-shots-f4", demoPw = process.env.DEMO_PASSWORD] = process.argv.slice(2);
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

try {
  await page.goto(`${base}/login`);
  await page.getByLabel(/Mobile number|মোবাইল নম্বর/).fill("01900000001");
  await page.getByLabel(/Password|পাসওয়ার্ড/).fill(demoPw);
  await page.locator("form").getByRole("button", { name: /^(Log in|লগইন করুন)$/ }).click();
  await page.waitForURL(/\/(profiles|p\/)/);
  const profiles = (await get("/profiles")).items;
  const shop = profiles.find((p) => p.display_name === "Rahim Store").id;
  const farm = profiles.find((p) => p.display_name === "Rahim Rice Farm").id;
  const rid = (await get(`/profiles/${shop}/financing-requests`)).items[0].id;
  const a = await page.request.post(`${base}/api/v1/profiles/${shop}/financing-requests/${rid}/assessments`,
                                    { headers: { "X-BB-Client": "web" } });
  if (a.status() !== 201) throw new Error(`assessment ${a.status()}`);

  await page.goto(`${base}/p/${shop}/suppliers`);
  await en();
  await page.getByRole("link", { name: /Supply graph/ }).click();
  await page.waitForURL(/supply-graph$/);
  await text("Pick an area, a good or a news item in the list below or on the map.");
  step("graph opens from Suppliers; nothing picked yet");

  await page.getByRole("button", { name: /^Kaliakair, Gazipur/ }).click();
  await text("65% of your purchases come through here");
  await page.getByRole("button", { name: "Stops 7 days" }).click();
  await text(/short by Tk 9,376\.90/);
  await text("What-if only — does not change your result");
  await shot("01-shop-kaliakair-7d");
  step("Kaliakair 65 % → 7 days stopped → golden D1 shortfall Tk 9,376.90, what-if label shown");

  await page.getByRole("button", { name: /^lentils/ }).click();
  await text("90% of your purchases come through here");
  step("lentils from two suppliers → 90 %");

  await page.goto(`${base}/p/${farm}/supply-graph`);
  await en();
  await page.getByRole("button", { name: /^Rice/ }).click();
  await text("None of your purchases come through here");
  if (await page.getByRole("button", { name: "Stops 7 days" }).count()) throw new Error("farm must not offer the shop what-if");
  await shot("02-farm-graph");
  step("farm graph shows the rice crop and the DEMO flood; no shop what-if");
  console.log("Plan Ultra F4 (Supply graph) passed");
} finally {
  await browser.close();
}
