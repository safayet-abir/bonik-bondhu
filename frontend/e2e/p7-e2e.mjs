// P7-T06 end-to-end scripts (Testing §8) not covered by the phase walkthroughs:
//   E2E-1 Shop with a NEW account: register → profile → 2 suppliers → history → linked purchase →
//         summary + forecast → financing wizard (supplier quote, 6 weekly) → status + how calculated
//         → Risks shows the supplier-delay what-if → logout.
//         The 4 weeks of past entries (12 rows) are posted through the same API with the logged-in
//         browser session; one purchase is entered through the form.
//   E2E-4 Exceptions: 6 wrong passwords → locked; D4 check lists what is missing; FS-05 session
//         expires inside the wizard → login → back on the same wizard step.
//   (E2E-2 = p3 + p4 walkthroughs, E2E-3 = p5, duplicate warning = p2, AI-off photo = p6.)
// Usage: node e2e/p7-e2e.mjs <baseUrl> <shotsDir> [demoPassword | env DEMO_PASSWORD]   (reset-demo first)
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { launchOpts, rec } from "./rec.mjs";

const [base = "http://localhost:8000", shots = "e2e-shots-p7", demoPw = process.env.DEMO_PASSWORD] = process.argv.slice(2);
if (!demoPw) throw new Error("pass the DEMO password as 3rd argument or DEMO_PASSWORD");
mkdirSync(shots, { recursive: true });
const step = (msg) => console.log(`✓ ${msg}`);
const dhaka = (days = 0) => new Date(Date.now() + 6 * 3600e3 + days * 864e5).toISOString().slice(0, 10);
const browser = await chromium.launch(launchOpts);
const ctx = await browser.newContext({ viewport: { width: 360, height: 760 }, ...rec({ width: 360, height: 760 }) });
const page = await ctx.newPage();
const shot = (name) => page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
const text = (s) => page.getByText(s).first().waitFor();
const save = () => page.getByRole("button", { name: "Save", exact: true }).click();
const api = async (method, path, data) => {
  const r = await page.request.fetch(`${base}/api/v1${path}`, { method, data, headers: { "X-BB-Client": "web" } });
  if (!r.ok()) throw new Error(`${method} ${path} → ${r.status()} ${await r.text()}`);
  return r.json();
};

async function register(name, phone, pw) {
  await page.goto(base);
  await page.getByRole("button", { name: "EN" }).click();
  await page.getByRole("button", { name: "Create a new account" }).click();
  await page.getByLabel("Full name").fill(name);
  await page.getByLabel("Mobile number").fill(phone);
  await page.getByLabel("Email").fill(`e2e.${phone}@example.com`);
  await page.getByLabel("Password").fill(pw);
  await page.getByRole("button", { name: "Create account" }).click();
  await text("Account created");
}

try {
  // ------------------------------------------------------------- E2E-1
  const phone = "017" + String(Date.now()).slice(-8), pw = "e2e-shop-2026";
  await register("E2E Shop Owner", phone, pw);
  await page.getByLabel("Password").fill(pw);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.getByLabel("ব্যবসার নাম").fill("E2E-1 Shop");
  await page.getByRole("button", { name: "দোকান" }).click();
  await page.getByRole("button", { name: "সংরক্ষণ করুন" }).click();
  await page.getByText("টাকার হিসাব রাখি").waitFor();
  await page.getByRole("button", { name: "EN" }).click();
  const pid = page.url().match(/\/p\/([^/]+)\//)[1];
  step("registered, logged in, shop profile created");

  for (const [name, goods, district, upazila] of [["Supplier North (E2E)", "rice, oil", "Gazipur", "Kaliakair"],
                                                    ["Supplier South (E2E)", "lentils", "Dhaka", "Savar"]]) {
    await page.goto(`${base}/p/${pid}/suppliers`);
    await page.getByRole("button", { name: "EN" }).click(); // a reload restores the saved language
    await page.getByRole("button", { name: "Add supplier" }).click();
    await page.getByLabel("Supplier name").fill(name);
    await page.getByLabel("What do they supply?").fill(goods);
    await page.getByLabel("District").fill(district);
    await page.getByLabel("Upazila").fill(upazila);
    await save();
    await text(`${upazila}, ${district}`);
  }
  const sup = Object.fromEntries((await api("GET", `/profiles/${pid}/suppliers`)).items.map((s) => [s.display_name, s.id]));
  for (let k = 1; k <= 4; k++) {
    const d = dhaka(-7 * k + 2);
    await api("POST", `/profiles/${pid}/transactions`, { txn_type: "sale_cash", amount: "30000", value_date: d });
    await api("POST", `/profiles/${pid}/transactions`, { txn_type: "purchase_cash", amount: "12000", value_date: d, supplier_id: sup["Supplier North (E2E)"] });
    await api("POST", `/profiles/${pid}/transactions`, { txn_type: "operating_expense", amount: "2000", value_date: d, category: "rent" });
  }
  await page.getByRole("link", { name: "Entries" }).click();
  await page.getByRole("button", { name: "New entry" }).click();
  await page.getByRole("button", { name: "Stock purchase (cash)" }).click();
  await page.getByLabel("Amount (Tk)").fill("6000");
  await page.getByLabel("Date").fill(dhaka(-3));
  await page.getByLabel("Supplier", { exact: true }).selectOption({ label: "Supplier South (E2E)" });
  await save();
  await text("Saved");
  const s = await api("GET", `/profiles/${pid}/summary?from=${dhaka(-28)}&to=${dhaka(0)}`);
  if (s.sales_recorded !== "120000.00" || s.operating_cash_out !== "62000.00" || s.net_operating_cash !== "58000.00") {
    throw new Error(`summary wrong: ${JSON.stringify(s)}`);
  }
  step("2 suppliers, 4 weeks of records + 1 linked purchase via the form; summary 1,20,000 in / 62,000 out");

  await page.getByRole("link", { name: "More" }).click();
  await page.getByRole("link", { name: "Forecast (estimate)" }).click();
  // the page computes the forecast (POST) after a 404 on latest; a sleepy free host can take a while
  for (let i = 0; i < 60 && (await page.request.get(`${base}/api/v1/profiles/${pid}/forecasts/latest`)).status() === 404; i++) {
    await page.waitForTimeout(1000);
  }
  if ((await api("GET", `/profiles/${pid}/forecasts/latest`)).status !== "ok") throw new Error("forecast not ok");
  await shot("e2e1-01-forecast");
  step("forecast ok");

  await page.getByRole("link", { name: "Home" }).click();
  await page.getByRole("button", { name: "Check financing" }).click();
  await page.getByRole("button", { name: "New financing check" }).click();
  await page.getByLabel("District").fill("Dhaka");
  await page.getByLabel("Upazila").fill("Savar");
  await page.getByLabel("Business category").fill("Grocery");
  await page.getByLabel("Money you take for your family each month").fill("5000");
  await save();
  await page.getByLabel("How much do you want?").fill("30000");
  await page.getByLabel("What is it for?").fill("Rice and oil before Eid");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("Item", { exact: true }).fill("Rice sack");
  await page.getByLabel("Quantity").fill("10");
  await page.getByLabel("Unit", { exact: true }).fill("sack");
  await page.getByLabel("Price per unit (Tk)").fill("3000");
  await page.getByRole("button", { name: "Supplier quote" }).click();
  await page.getByRole("button", { name: "Add item" }).last().click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel(/Other necessary costs/).fill("0");
  await page.getByLabel("Extra safety money").fill("0");
  await page.getByLabel(/Your own cash you can safely/).fill("0");
  await page.getByLabel("Other financing already arranged").fill("0");
  await page.getByLabel(/Cash you have now/).fill("20000");
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "I have no current loans" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByLabel("Number of installments").fill("6");
  await page.getByLabel("First installment date").fill(dhaka(7));
  await page.getByLabel("Total interest + fees (Tk)").fill("600");
  await page.getByLabel("Minimum cash you must always keep").fill("2000");
  await page.getByRole("button", { name: "Check" }).click();
  await page.waitForURL(/assessment\//, { timeout: 30_000 });
  await text("Ready for lender review");
  await page.getByRole("button", { name: "How calculated" }).click();
  await text("funding_gap");
  await page.getByRole("button", { name: /^Risks/ }).click();
  await text("cannot deliver for 7 days");
  await shot("e2e1-02-risks");
  step("wizard → ready for a lender to review; how calculated; Risks shows the 7-day supplier delay");
  await page.getByRole("link", { name: "More" }).click();
  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL(/\/(login|)$/);
  step("E2E-1 passed (logged out)");

  // ------------------------------------------------------------- E2E-4
  const p2 = "018" + String(Date.now()).slice(-8);
  await register("E2E Lockout", p2, "right-pass-2026");
  for (let i = 0; i < 6; i++) {
    await page.getByLabel("Password").fill(`wrong-${i}-pass`);
    await page.getByRole("button", { name: "Log in" }).click();
    await page.waitForLoadState("networkidle");
  }
  await text("ACCOUNT_LOCKED");
  step("6 wrong passwords → account locked");

  await page.getByLabel("Mobile number").fill("01900000004");
  await page.getByLabel("Password").fill(demoPw);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(/\/(profiles|p\/)/);
  await page.goto(`${base}/profiles`);
  await page.getByText("Selina Tailoring", { exact: true }).click();
  await page.waitForURL(/\/p\/[^/]+\/home/);
  await page.getByRole("button", { name: "EN" }).click();
  const sid = page.url().match(/\/p\/([^/]+)\//)[1];
  const rid = (await api("GET", `/profiles/${sid}/financing-requests`)).items[0].id;
  // D4's terms are empty, so the wizard's Check button is (rightly) disabled; run the check via the API
  const aid = (await api("POST", `/profiles/${sid}/financing-requests/${rid}/assessments`, {})).id;
  await page.goto(`${base}/p/${sid}/assessment/${aid}`);
  await page.getByRole("button", { name: "EN" }).first().click();
  await text("Tell us about your current loans (or say you have none)");
  await text("Record at least 4 weeks of sales and costs");
  await shot("e2e4-01-d4-missing");
  step("D4: check lists the missing information");

  await page.goto(`${base}/p/${sid}/financing/${rid}/step/1`); // step 1: "Next" saves (PATCH) → 401
  await page.getByRole("button", { name: "EN" }).first().click();
  await ctx.clearCookies(); // the session ends while the owner is in the wizard
  await page.getByRole("button", { name: "Next" }).click();
  await page.waitForURL(/\/login$/);
  await page.getByLabel("Mobile number").fill("01900000004");
  await page.getByLabel("Password").fill(demoPw);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(new RegExp(`/financing/${rid}/step/1$`));
  step("FS-05: session expired in the wizard → login → back on the same step");
  console.log("P7 E2E-1 + E2E-4 passed");
} catch (err) {
  await shot("zz-failure").catch(() => {});
  throw err;
} finally {
  await browser.close();
}
