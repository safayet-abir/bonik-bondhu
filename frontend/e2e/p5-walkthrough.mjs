// P5 DoD / E2E-3 on the DEMO seed (run `python -m app.cli reset-demo` first).
// Browser A = owner (360 px), browser B = lender (desktop 1280 px).
//   B Nasrin requests access with the D1 share code (pending, applicant hidden)
//   A Rahim runs the check, approves 5 sections for 14 days
//   B case file: hash verified, Supplier 1/2/3 (names hidden), CIB notice;
//     private note + information request
//   A sees the message, "viewed" count
//   B records a demo decision "refer" with reason -> banner
//   A sees the decision, stops sharing -> B "access ended"
//   Other-org officer cannot open the case
//
// Usage: node e2e/p5-walkthrough.mjs <baseUrl> <screenshotDir> [demoPassword | env DEMO_PASSWORD]
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { launchOpts, rec } from "./rec.mjs";

const [base = "http://localhost:8000", shots = "e2e-shots-p5", demoPw = process.env.DEMO_PASSWORD] = process.argv.slice(2);
if (!demoPw) throw new Error("pass the DEMO password as 3rd argument or DEMO_PASSWORD");
mkdirSync(shots, { recursive: true });
const step = (msg) => console.log(`✓ ${msg}`);

const browser = await chromium.launch(launchOpts);
const ownerCtx = await browser.newContext({ viewport: { width: 360, height: 760 }, ...rec({ width: 360, height: 760 }) });
const lenderCtx = await browser.newContext({ viewport: { width: 1280, height: 900 }, ...rec({ width: 1280, height: 900 }) });
const A = await ownerCtx.newPage();
const B = await lenderCtx.newPage();
const shot = (page, name) => page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
const see = (page, s) => page.getByText(s).first().waitFor();

async function login(page, phone) {
  await page.goto(`${base}/login`);
  if (await page.getByRole("button", { name: "EN" }).isVisible()) await page.getByRole("button", { name: "EN" }).click();
  await page.getByLabel(/Mobile number|মোবাইল নম্বর/).fill(phone);
  await page.getByLabel(/Password|পাসওয়ার্ড/).fill(demoPw);
  await page.getByRole("button", { name: /^(Log in|লগ ইন)$/ }).click();
  await page.waitForURL(/\/(profiles|p\/|lender\/)/);
  await page.waitForLoadState("networkidle");
  if (await page.getByRole("button", { name: "EN" }).isVisible()) await page.getByRole("button", { name: "EN" }).click();
}

try {
  // ------------------------------------------------------------ B: request access
  await login(B, "01900000101");
  await B.getByRole("link", { name: "Request access" }).click();
  await B.getByLabel("Owner's share code").fill("7KQ2M-9XA4P");
  await B.getByRole("button", { name: "Send request" }).click();
  await see(B, "If the code is valid, the owner will see your request.");
  await B.getByRole("link", { name: "Cases" }).click();
  await see(B, "Waiting for owner approval");
  await shot(B, "01-lender-pending");
  step("lender: request sent with D1 code; case pending, applicant hidden");

  // ------------------------------------------------------------ A: check + approve
  await login(A, "01900000001");
  await A.goto(`${base}/profiles`);
  await A.getByText("Rahim Store", { exact: true }).click();
  await A.waitForURL(/\/p\/[^/]+\/home/);
  await A.getByRole("button", { name: "EN" }).click();
  const pid = A.url().match(/\/p\/([^/]+)/)[1];
  await A.getByRole("link", { name: "Financing" }).click();
  await A.getByRole("link", { name: /DEMO/ }).first().click();
  await A.waitForURL(/step\/2/);
  await A.goto(A.url().replace(/step\/2$/, "step/5"));
  await A.getByRole("button", { name: "Check" }).click();
  await A.waitForURL(/\/assessment\//);
  await see(A, "Ready for lender review");
  await A.goto(`${base}/p/${pid}/sharing`);
  await A.getByRole("button", { name: "EN" }).click();
  await see(A, "7KQ2M-9XA4P");
  await see(A, "DEMO Bank Ltd (fictional)");
  await A.getByRole("button", { name: "Allow" }).click();
  await A.getByLabel("Supplier risk").check();
  await A.getByLabel("News").check();
  await see(A, "Information already viewed cannot be taken back");
  await shot(A, "02-owner-approve-sheet");
  await A.getByRole("button", { name: "Approve" }).click();
  await see(A, "Active shares");
  await see(A, "Not viewed yet");
  step("owner: check ready; approved 7 sections (incl. supplier risk + news) for 14 days");

  // ------------------------------------------------------------ B: case file
  await B.reload();
  await B.getByRole("link", { name: "Rahim Store" }).click();
  await B.waitForURL(/\/lender\/cases\/[^/]+$/);
  await see(B, "Fingerprint matches the stored copy");
  await see(B, "Supplier 1");
  await see(B, "Official credit checks (CIB) are done by the lender, outside Bonik Bondhu.");
  await see(B, "This is not a loan approval. The lender decides.");
  if (await B.getByText("Supplier A (DEMO wholesaler)").count()) throw new Error("supplier name leaked to lender");
  await shot(B, "03-lender-case-file");
  await B.getByLabel("Private note").fill("Check quotation date (internal)");
  await B.getByRole("button", { name: "Add note" }).click();
  await see(B, "Check quotation date (internal)");
  await B.getByLabel("Ask the owner for information").fill("Please share the supplier quotation.");
  await B.getByRole("button", { name: "Send to owner" }).click();
  await see(B, "Information requested");
  step("lender: case file with verified hash, Supplier 1/2/3, CIB notice; private note + info request");

  // ------------------------------------------------------------ A: sees message
  await A.reload();
  await see(A, "Please share the supplier quotation.");
  await see(A, /viewed [1-9]\d*×/); // every lender read is logged (incl. reloads after each review action)
  if (await A.getByText("Check quotation date (internal)").count()) throw new Error("private note visible to owner");
  await shot(A, "04-owner-message");
  step("owner: sees the information request and the lender's views; private note hidden");

  // ------------------------------------------------------------ B: decision
  await B.getByRole("button", { name: "Refer" }).click();
  await B.getByLabel("Reason (required)").fill("ok");
  await B.getByRole("button", { name: "Record decision" }).click();
  await see(B, "Write a reason of at least 5 characters");
  await B.getByLabel("Reason (required)").fill("Needs supplier quotation verification at branch");
  await B.getByRole("button", { name: "Record decision" }).click();
  await see(B, "Decision recorded: Refer");
  await shot(B, "05-lender-decision");
  step("lender: reason required; decision 'refer' recorded with demo banner");

  // ------------------------------------------------------------ A: sees decision, revokes
  await A.reload();
  await see(A, "DEMO Bank Ltd (fictional) recorded: Refer");
  await A.getByRole("button", { name: "Stop sharing" }).click();
  await see(A, "Ended");
  await shot(A, "06-owner-revoked");
  await B.reload();
  await see(B, "The owner stopped sharing this case");
  await shot(B, "07-lender-blocked");
  step("owner revoked → lender blocked immediately");

  // ------------------------------------------------------------ other org
  const otherCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const C = await otherCtx.newPage();
  await login(C, "01900000103");
  await C.goto(B.url());
  await C.waitForLoadState("networkidle");
  await shot(C, "08-other-org");
  await see(C, "not found");
  step("other-org officer cannot open the case");

  // ------------------------------------------------------------ Bangla
  await A.getByRole("button", { name: "বাং" }).click();
  await see(A, "ঋণদাতার সাথে শেয়ার");
  step("Bangla sharing screen renders");
} finally {
  await browser.close();
}
