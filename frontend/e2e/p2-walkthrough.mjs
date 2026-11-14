// P2 Definition of Done walkthrough (shop + farm), scripted:
// shop: supplier → stock purchase linked to supplier → credit sale → duplicate
//       warning + confirm → void → entries filter → debts + CIB note
// farm: season in bigha (factor required) → planned costs → "Paid ✓" prefilled
//       entry → summary (break-even) → harvest; farm never shows Forecast.
//
// Usage: node e2e/p2-walkthrough.mjs <baseUrl> <screenshotDir>
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [base = "http://localhost:8000", shots = "e2e-shots-p2"] = process.argv.slice(2);
mkdirSync(shots, { recursive: true });

const phone = `018${String(Math.floor(Math.random() * 1e8)).padStart(8, "0")}`;
const password = "bazar-2026!";
const step = (msg) => console.log(`✓ ${msg}`);

const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ viewport: { width: 360, height: 760 } });
const shot = (name) => page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
const save = () => page.getByRole("button", { name: "Save", exact: true }).click();

try {
  // English UI for stable selectors (Bangla is covered by the P1 script)
  await page.goto(base);
  await page.getByRole("button", { name: "EN" }).click();
  await page.getByRole("button", { name: "Create a new account" }).click();
  await page.getByLabel("Full name").fill("E2E Owner P2");
  await page.getByLabel("Mobile number").fill(phone);
  await page.getByLabel("Email").fill(`e2e.${phone}@example.com`);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.getByText("Account created").waitFor();
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  // The account's own saved language (Bangla by default) applies after login.
  await page.getByLabel("ব্যবসার নাম").fill("P2 Shop");
  await page.getByRole("button", { name: "দোকান" }).click();
  await page.getByRole("button", { name: "সংরক্ষণ করুন" }).click();
  await page.getByText("টাকার হিসাব রাখি").waitFor();
  await page.getByRole("button", { name: "EN" }).click();
  await page.getByText("Record my money").waitFor();
  step("shop profile created; switched to English");

  // Supplier
  await page.getByRole("link", { name: "More" }).click();
  await page.getByRole("link", { name: "Suppliers" }).click();
  await page.getByRole("button", { name: "Add supplier" }).click();
  await page.getByLabel("Supplier name").fill("Supplier A (DEMO)");
  await page.getByLabel("What do they supply?").fill("rice, oil");
  await page.getByLabel("District").fill("Gazipur");
  await page.getByLabel("Upazila").fill("Kaliakair");
  await save();
  await page.getByText("Kaliakair, Gazipur").waitFor();
  await shot("01-suppliers");
  step("supplier saved");

  // Stock purchase linked to supplier
  await page.getByRole("link", { name: "Add" }).click();
  await page.getByRole("button", { name: "Stock purchase (cash)" }).click();
  await page.getByText("Stock bought for resale, paid now.").waitFor();
  await page.getByLabel("Amount (Tk)").fill("65000");
  await page.getByLabel("Supplier", { exact: true }).selectOption({ label: "Supplier A (DEMO)" });
  await shot("02-add-purchase");
  await save();
  await page.getByText("Saved", { exact: true }).waitFor();
  step("purchase linked to supplier saved");

  // Credit sale + duplicate warning + confirm
  for (let i = 0; i < 2; i++) {
    await page.getByRole("link", { name: "Add" }).click();
    await page.getByRole("button", { name: "Sale on credit (baki)" }).click();
    await page.getByText("Not cash yet.").waitFor();
    await page.getByLabel("Amount (Tk)").fill("2000");
    await save();
    if (i === 0) await page.getByText("Saved", { exact: true }).waitFor();
  }
  await page.getByText("This looks like an entry you already saved").waitFor();
  await shot("03-duplicate-warning");
  await page.getByRole("button", { name: "Yes, this is a separate entry" }).click();
  await page.getByText("Saved", { exact: true }).waitFor();
  step("duplicate warning shown, confirmed as separate entry");

  // Entries list → void one credit sale
  await page.getByRole("link", { name: "Entries" }).click();
  await page.getByRole("link", { name: /Sale on credit/ }).first().click();
  await page.getByRole("button", { name: "Wrong? Void this entry" }).click();
  await page.getByLabel("Why are you voiding this?").fill("Entered twice");
  await page.getByRole("button", { name: "Void entry" }).click();
  await page.getByText("Reason: Entered twice").waitFor();
  await shot("04-voided");
  await page.getByRole("link", { name: "Go back" }).click();
  await page.getByRole("button", { name: "Voided" }).click();
  await page.getByText("Voided", { exact: true }).last().waitFor();
  await shot("05-entries-voided-filter");
  step("entry voided and listed under the Voided filter");

  // Summary: sales 2,000 (voided one excluded), purchase linked
  await page.getByRole("link", { name: "More" }).click();
  await page.getByRole("link", { name: "Money summary" }).click();
  const credit = page.locator("div", { hasText: /^Credit sales/ }).last();
  await credit.waitFor();
  if (!(await credit.innerText()).includes("2,000")) throw new Error(`credit sales wrong: ${await credit.innerText()}`);
  step("summary excludes the voided entry (credit sales Tk 2,000)");

  // Debts
  await page.getByRole("link", { name: "Go back" }).click();
  await page.getByRole("link", { name: "Loans I owe" }).click();
  await page.getByText("Official credit checks (CIB)").waitFor();
  await page.getByRole("button", { name: "Add loan" }).click();
  await page.getByLabel("Name or note").fill("DEMO NGO weekly loan");
  await page.getByLabel("Original loan amount (Tk)").fill("100000");
  await page.getByLabel("Still to repay (Tk)").fill("60000");
  await page.getByLabel("Installment (Tk)").fill("2500");
  const due = new Date(Date.now() + 3 * 864e5).toISOString().slice(0, 10);
  await page.getByLabel("Next installment date").fill(due);
  await save();
  await page.getByText("MFI — DEMO NGO weekly loan").waitFor();
  await page.getByText("Next installments").waitFor();
  await shot("06-debts");
  step("debt saved with next installments and CIB notice");

  // Farm profile
  await page.goto(`${base}/profiles`);
  await page.getByRole("button", { name: "Add another business" }).click();
  await page.getByLabel("Business name").fill("P2 Rice Farm");
  await page.getByRole("button", { name: "Crop farm" }).click();
  await save();
  await page.getByRole("button", { name: "New season" }).waitFor();
  if (await page.getByText("Forecast").count()) throw new Error("farm shows forecast");
  step("farm home shows seasons; no forecast");

  await page.getByRole("button", { name: "New season" }).click();
  await page.getByLabel("Crop", { exact: true }).fill("Rice");
  await page.getByLabel("Land area").fill("2");
  await page.getByLabel("Unit", { exact: true }).selectOption("bigha");
  // A season already growing: sown ~100 days ago, harvest due soon (so harvest can be recorded today)
  const day = (n) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);
  await page.getByLabel("Sowing date").fill(day(-100));
  await page.getByLabel("Harvest date").fill(day(10));
  await save();
  await page.getByText("Enter how many decimals 1 bigha is in your area").waitFor();
  await shot("07-bigha-factor-required");
  step("bigha without factor refused (BIGHA_FACTOR_REQUIRED)");
  await page.getByLabel("In your area, 1 bigha = how many decimals?").fill("33");
  await page.getByText("= 0.66 acres").waitFor();
  const lows = page.getByLabel("Low");
  const likely = page.getByLabel("Likely");
  const highs = page.getByLabel("High");
  await lows.nth(0).fill("2700"); await likely.nth(0).fill("3300"); await highs.nth(0).fill("3750");
  await lows.nth(1).fill("28"); await likely.nth(1).fill("32"); await highs.nth(1).fill("35");
  await save();
  await page.getByText("0.66 acres (2 bigha)").waitFor();
  step("season saved: 2 bigha @33 = 0.66 acres");

  // Planned costs
  for (const [cat, cost] of [["seed", "4500"], ["fertilizer", "18000"], ["labour", "42500"]]) {
    await page.getByRole("button", { name: "Add planned cost" }).click();
    await page.getByLabel("Cost type").selectOption(cat);
    await page.getByLabel("Cost per unit (Tk)").fill(cost);
    await save();
    await page.getByRole("button", { name: "Add planned cost" }).waitFor();
  }
  await shot("08-season-plan");
  step("planned costs total 65,000");

  // "Paid ✓" → prefilled entry
  await page.getByRole("button", { name: "Paid ✓" }).first().click();
  await page.getByText("Paying for: Seed").waitFor();
  const amt = await page.getByLabel("Amount (Tk)").inputValue();
  if (amt !== "4500") throw new Error(`prefill amount wrong: ${amt}`);
  await shot("09-paid-prefilled");
  await save();
  await page.getByText("Paid: Tk 4,500").or(page.getByText("Paid", { exact: true })).first().waitFor();
  step("Paid ✓ opened a prefilled entry linked to the season cost item");

  await page.getByRole("button", { name: "Season summary" }).click();
  await page.getByText("Tk 19.70 / kg").waitFor();
  await page.getByText("Tk 75,600").waitFor();
  await shot("10-season-summary");
  step("season summary: income low 75,600, break-even 19.70/kg");

  await page.getByRole("link", { name: "Go back" }).click();
  await page.getByRole("button", { name: "Record harvest" }).click();
  await page.getByLabel("Actual output (kg)").fill("3100");
  await save();
  await page.getByText("Harvest saved").waitFor();
  await shot("11-harvest");
  step("harvest recorded");

  // Bangla check of a P2 screen
  await page.getByRole("button", { name: "বাং" }).click();
  await page.getByText("ফসল তোলার তথ্য সংরক্ষণ হয়েছে").waitFor();
  await page.getByRole("button", { name: "পরে" }).click();
  await page.getByText("পরিকল্পনা", { exact: true }).waitFor();
  await shot("12-season-bn");
  step("Bangla season screen renders");

  console.log("P2 walkthrough E2E passed");
} catch (err) {
  await shot("zz-failure");
  console.error(err);
  process.exitCode = 1;
} finally {
  await browser.close();
}
