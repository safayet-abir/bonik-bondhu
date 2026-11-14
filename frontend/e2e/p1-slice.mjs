// P1 Definition of Done, scripted (SUG-20: Playwright optional for E2E):
// register -> login -> create shop profile -> cash sale 8,500 + rent 1,500
// -> reload -> summary shows net operating cash 7,000; then lender routing.
//
// Usage: node e2e/p1-slice.mjs <baseUrl> <screenshotDir> [lenderPhone] [lenderPassword]
// Uses the installed Microsoft Edge (channel "msedge"), phone viewport 360 px.
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const [base = "http://localhost:8000", shots = "e2e-shots", lenderPhone, lenderPassword] = process.argv.slice(2);
mkdirSync(shots, { recursive: true });

const phone = `017${String(Math.floor(Math.random() * 1e8)).padStart(8, "0")}`;
const password = "bazar-2026!";
const step = (msg) => console.log(`✓ ${msg}`);

const browser = await chromium.launch({ channel: "msedge" });
const page = await browser.newPage({ viewport: { width: 360, height: 760 } });
const shot = (name) => page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });

try {
  // SCR-A01 welcome (Bangla first) + /health status
  await page.goto(base);
  await page.getByText("চালু আছে").waitFor();
  await shot("01-welcome-bn");
  step("welcome shows server status OK");

  // SCR-A02 register
  await page.getByRole("button", { name: "নতুন অ্যাকাউন্ট খুলুন" }).click();
  await page.getByLabel("পুরো নাম").fill("মোঃ রহিম উদ্দিন");
  await page.getByLabel("মোবাইল নম্বর").fill(phone);
  await page.getByLabel("ইমেইল").fill(`e2e.${phone}@example.com`);
  await page.getByLabel("পাসওয়ার্ড").fill("12345678");
  await page.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();
  await page.getByText("পাসওয়ার্ডে শুধু সংখ্যা রাখা যাবে না").waitFor();
  await shot("02-register-field-error");
  step("server validation error shown under the password field");
  await page.getByLabel("পাসওয়ার্ড").fill(password);
  await page.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();

  // SCR-A03 login (phone prefilled)
  await page.getByText("অ্যাকাউন্ট খোলা হয়েছে").waitFor();
  await page.getByLabel("পাসওয়ার্ড").fill(password);
  await page.getByRole("button", { name: "লগইন করুন" }).click();

  // 0 profiles -> SCR-O02 create
  await page.getByLabel("ব্যবসার নাম").fill("Rahim Store");
  await page.getByRole("button", { name: "দোকান" }).click();
  await shot("03-create-profile");
  await page.getByRole("button", { name: "সংরক্ষণ করুন" }).click();

  // SCR-O03 first-time home -> Path A
  await page.getByText("টাকার হিসাব রাখি").waitFor();
  await shot("04-home-first-time");
  await page.getByText("টাকার হিসাব রাখি").click();

  // SCR-O04 cash sale 8,500 (typed with Bangla digits)
  await page.getByLabel("টাকা (Tk)").fill("৮৫০০");
  await shot("05-add-sale");
  await page.getByRole("button", { name: "সংরক্ষণ করুন" }).click();
  await page.getByText("সংরক্ষণ হয়েছে").waitFor();
  step("cash sale saved");

  // rent 1,500 via quick add
  await page.getByRole("button", { name: "খরচ" }).click();
  await page.getByLabel("টাকা (Tk)").fill("1500");
  await page.getByLabel("কোন খরচ?").selectOption("rent");
  await page.getByRole("button", { name: "সংরক্ষণ করুন" }).click();
  await page.getByText("সংরক্ষণ হয়েছে").waitFor();
  await shot("06-home-returning");
  step("rent saved");

  // Reload the browser, open summary: totals come back from the server
  await page.reload();
  await page.getByRole("link", { name: "সারাংশ" }).click();
  const net = page.locator("div", { hasText: /^ব্যবসার নিট নগদ/ }).last();
  await net.waitFor();
  const netText = await net.innerText();
  if (!netText.includes("৭,০০০")) throw new Error(`net operating cash wrong: ${netText}`);
  await shot("07-summary-bn");
  step(`after reload, summary net operating cash = ${netText.replace(/\s+/g, " ")}`);

  // Language switch (instant, saved on account)
  await page.getByRole("button", { name: "EN" }).click();
  await page.getByText("Net operating cash").waitFor();
  await shot("08-summary-en");
  step("English switch works");

  // Logout -> login again: language preference persisted (FR-AUTH-08)
  await page.getByRole("link", { name: "More" }).click();
  await page.getByRole("button", { name: "Log out" }).click();
  await page.getByLabel("Mobile number").fill(phone);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.getByText("Cash in").first().waitFor();
  step("re-login lands on the single profile's home, still in English");
  await page.getByRole("link", { name: "More" }).click();
  await page.getByRole("button", { name: "Log out" }).click();

  if (lenderPhone && lenderPassword) {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.getByLabel("Mobile number").fill(lenderPhone);
    await page.getByLabel("Password").fill(lenderPassword);
    await page.getByRole("button", { name: "Log in" }).click();
    // The lender's own saved language (Bangla by default) is applied after login.
    await page.getByText("এখনও কোনো কেস নেই").waitFor();
    await shot("09-lender-cases");
    step("lender is routed to the case list, in their own saved language");
    await page.goto(`${base}/profiles`);
    await page.getByText("এখনও কোনো কেস নেই").waitFor();
    step("lender opening an owner route is sent back to the case list");
  }
  console.log("P1 slice E2E passed");
} catch (err) {
  await shot("zz-failure");
  console.error(err);
  process.exitCode = 1;
} finally {
  await browser.close();
}
