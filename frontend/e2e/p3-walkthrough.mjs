// P3 Definition of Done walkthrough on the DEMO seed (run `python -m app.cli
// reset-demo` first) plus a brand-new owner going through the 5-step wizard.
//   D1 Rahim Store   → forecast golden values, assessment ready, how-calculated
//   D3 Rahim Farm    → assessment ready, loan-cover 19.78 on result + season summary
//   D2 Karim         → not affordable, first shortfall 2,746.97
//   D4 Selina        → more information needed (6 fix links)
//   new owner        → mini profile form, item, live gap, no loans, terms, check
//
// Usage: node e2e/p3-walkthrough.mjs <baseUrl> <screenshotDir> <demoPassword>
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [base = "http://localhost:8000", shots = "e2e-shots-p3", demoPw = process.env.DEMO_PASSWORD] = process.argv.slice(2);
if (!demoPw) throw new Error("pass the DEMO password as 3rd argument or DEMO_PASSWORD");
mkdirSync(shots, { recursive: true });
const step = (msg) => console.log(`✓ ${msg}`);

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
  await page.waitForLoadState("networkidle"); // saved language (Bangla) is applied after /auth/me
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
  const url = page.url().replace(/step\/2$/, "step/5");
  await page.goto(url);
  await page.getByRole("button", { name: "Check" }).click();
  await page.waitForURL(/\/assessment\//);
}

async function logout() {
  await page.goto(`${base}/profiles`);
  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL(/\/login/);
}

try {
  // ------------------------------------------------------------ D1 forecast + assessment
  await login("01900000001", demoPw);
  await openProfile("Rahim Store");
  await page.getByRole("button", { name: "Forecast (estimate)" }).click();
  await text("8 of the last 8 weeks have records");
  await text("Tk 1,07,142.86");
  await text("Tk 1,38,482.14");
  await text("Tk 4,15,446.43");
  await text("This is an estimate, not guaranteed income.");
  await shot("01-d1-forecast");
  step("D1 forecast: 30d low 1,07,142.86 / likely 1,38,482.14; 90d likely 4,15,446.43; estimate label");

  await checkFirstRequest();
  await text("Ready for lender review");
  await text("This is not a loan approval. The lender decides.");
  await text("Tk 1,50,000");
  await text("Tk 21,626.22");
  await text("You asked for more than the estimated need");
  await shot("02-d1-result");
  await page.getByRole("button", { name: "Show every payment date" }).click();
  await shot("03-d1-dates");
  await page.getByRole("button", { name: "How calculated" }).click();
  await text("max(0, 150000.00 + 10000.00 + 20000.00 − 30000.00 − 0.00) = 150000.00");
  await text("Input fingerprint", false);
  await shot("04-d1-how");
  step("D1 ready_for_lender_review: gap 1,50,000; lowest balance 21,626.22; how-calculated shows the formula with numbers");

  // ------------------------------------------------------------ D3 farm
  await openProfile("Rahim Rice Farm");
  await checkFirstRequest();
  await text("Ready for lender review");
  await text("Tk 64,600");
  await text("Tk 19.78 / kg");
  await text("Tk 19.70 / kg");
  await shot("05-d3-result");
  await page.getByRole("link", { name: "Seasons" }).click();
  await page.locator('main a[href*="/seasons/"]').first().click();
  await page.getByRole("button", { name: "Season summary" }).click();
  await text("Loan-cover price");
  await text("Tk 19.78 / kg");
  await shot("06-d3-season-summary");
  step("D3 farm ready: available at due 64,600; loan-cover 19.78 on result and season summary");
  await logout();

  // ------------------------------------------------------------ D2 not affordable
  await login("01900000002", demoPw);
  await checkFirstRequest();
  await text("These terms may cause a cash shortfall");
  await text(/About Tk 2,746\.97 may be short on/);
  await text("All prices are your own estimates", false);
  await shot("07-d2-result");
  step("D2 not_affordable_base_case: about 2,746.97 short at the first due date");
  await logout();

  // ------------------------------------------------------------ D4 insufficient
  await login("01900000004", demoPw);
  await page.getByRole("link", { name: "Financing" }).click();
  await page.getByRole("link", { name: /DEMO/ }).first().click();
  await page.goto(page.url().replace(/step\/2$/, "step/5"));
  await page.getByRole("button", { name: "Check" }).click();
  await page.waitForURL(/\/assessment\//);
  await text("More information needed");
  for (const s of ["Tell us about your current loans", "Write how much you take for your family", "Add what you will buy",
                   "Fill in your money details", "Complete your repayment proposal", "Record at least 4 weeks"]) {
    await text(s);
  }
  await shot("08-d4-result");
  await page.getByText("Add what you will buy").click();
  await page.waitForURL(/step\/2$/);
  step("D4 insufficient_information: 6 fix-it links; a link opens the right wizard step");
  await logout();

  // ------------------------------------------------------------ new owner, full wizard
  const phone = `018${String(Math.floor(Math.random() * 1e8)).padStart(8, "0")}`;
  const pw = "bazar-2026!";
  await page.goto(base);
  await page.getByRole("button", { name: "EN" }).click();
  await page.getByRole("button", { name: "Create a new account" }).click();
  await page.getByLabel("Full name").fill("E2E Owner P3");
  await page.getByLabel("Mobile number").fill(phone);
  await page.getByLabel("Email").fill(`e2e.${phone}@example.com`);
  await page.getByLabel("Password").fill(pw);
  await page.getByRole("button", { name: "Create account" }).click();
  await text("Account created");
  await page.getByLabel("Password").fill(pw);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.getByLabel("ব্যবসার নাম").fill("P3 Shop");
  await page.getByRole("button", { name: "দোকান" }).click();
  await page.getByRole("button", { name: "সংরক্ষণ করুন" }).click();
  await page.getByRole("button", { name: "EN" }).click();
  await page.getByRole("button", { name: "Check financing" }).click();
  await text("A few details are needed before checking financing");
  await page.getByLabel("District").fill("Dhaka");
  await page.getByLabel("Upazila").fill("Savar");
  await page.getByLabel("Business category").fill("Grocery");
  await page.getByLabel("Money you take for your family each month").fill("5000");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await text("Family money each month: Tk 5,000");
  await page.getByLabel("How much do you want?").fill("৫০,০০০");
  await page.getByLabel("What is it for?").fill("ঈদের আগে মাল কিনবো");
  await shot("09-wizard-1");
  await page.getByRole("button", { name: "Next" }).click();
  await page.waitForURL(/step\/2$/);
  step("wizard step 1: profile mini-form saved, request created (Bangla digits accepted)");

  await page.getByLabel("Item", { exact: true }).fill("Rice sack");
  await page.getByLabel("Quantity").fill("10");
  await page.getByLabel("Unit", { exact: true }).fill("sack");
  await page.getByLabel("Price per unit (Tk)").fill("3200");
  await page.getByRole("button", { name: "Add item" }).last().click();
  await text("Tk 32,000");
  await shot("10-wizard-2");
  await page.getByRole("button", { name: "Next" }).click();
  await page.waitForURL(/step\/3$/);

  await page.getByLabel(/Other necessary costs/).fill("1000");
  await page.getByLabel("Extra safety money").fill("2000");
  await page.getByLabel(/Your own cash you can safely/).fill("5000");
  await page.getByLabel("Other financing already arranged").fill("0");
  await page.getByLabel(/Cash you have now/).fill("12000");
  await text("Tk 30,000"); // 32,000 + 1,000 + 2,000 − 5,000 − 0 (live autosave preview)
  await text(/You asked Tk 20,000 more than the estimated need/);
  await page.getByLabel(/You asked Tk 20,000 more/).fill("Second shipment for the festival week");
  await shot("11-wizard-3-gap");
  await page.getByRole("button", { name: "Next" }).click();
  await page.waitForURL(/step\/4$/);
  step("wizard step 3: live funding gap 30,000 and over-request explanation");

  await page.getByRole("button", { name: "I have no current loans" }).click();
  await text("You said you have no current loans");
  await page.getByRole("button", { name: "Next" }).click();
  await page.waitForURL(/step\/5$/);

  await text("This is your proposal — not a lender offer");
  await page.getByLabel("Number of installments").fill("4");
  const due = new Date(Date.now() + 8 * 86400000).toISOString().slice(0, 10);
  await page.getByLabel("First installment date").fill(due);
  await page.getByLabel("Total interest + fees (Tk)").fill("2000");
  await page.getByLabel("Minimum cash you must always keep").fill("3000");
  await text("Tk 13,000"); // 52,000 / 4
  await shot("12-wizard-5");
  await page.getByRole("button", { name: "Check" }).click();
  await page.waitForURL(/\/assessment\//);
  await text("More information needed");
  await text("Record at least 4 weeks of sales and costs");
  await text("You asked for more than the estimated need and explained why");
  await shot("13-new-owner-result");
  step("wizard step 5 → check: 4 × 13,000 shown; honest result = more information needed (no history yet)");

  // Bangla rendering of the result
  await page.getByRole("button", { name: "বাং" }).click();
  await text("আরও তথ্য দরকার");
  await text("এটি ঋণ অনুমোদন নয়। সিদ্ধান্ত ঋণদাতা নেবেন।");
  await shot("14-result-bn");
  step("Bangla result screen renders");

  console.log("P3 walkthrough E2E passed");
} catch (err) {
  await shot("zz-failure");
  console.error(err);
  process.exitCode = 1;
} finally {
  await browser.close();
}
