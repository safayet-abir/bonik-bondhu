// F5 walkthrough on a disposable/local demo only. Credentials are injected by the
// trusted demo launcher, never embedded, printed, recorded or included in screenshots.
import assert from "node:assert/strict";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const base = process.argv[2] ?? "http://127.0.0.1:18080";
if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(base)) throw new Error("Use an isolated local demo only");
const out = process.argv[3];
if (out) mkdirSync(out, { recursive: true });
for (const key of ["DEMO_PASSWORD", "DEMO_OWNER_PHONE", "DEMO_LENDER_PHONE", "DEMO_SHARE_CODE"])
  if (!process.env[key]) throw new Error(`Missing injected ${key}`);
const browser = await chromium.launch({ channel: "msedge", headless: true });
const ownerContext = await browser.newContext({ viewport: { width: 360, height: 900 }, bypassCSP: !!process.env.AXE_PATH });
const lenderContext = await browser.newContext({ viewport: { width: 1440, height: 1000 }, bypassCSP: !!process.env.AXE_PATH });
const A = await ownerContext.newPage(), B = await lenderContext.newPage();
const call = async (page, path, body, method = "POST") => page.evaluate(async ({ path, body, method }) => {
  const r = await fetch(`/api/v1${path}`, { method, credentials: "include",
    headers: { "Content-Type": "application/json", "X-BB-Client": "web" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  return { status: r.status, body: await r.json() };
}, { path, body, method });

async function english(page) {
  await page.locator("main").waitFor();
  const en = page.getByRole("button", { name: "EN", exact: true });
  if (await en.isVisible()) await en.click();
}
async function login(page, phone) {
  await page.goto(`${base}/login`);
  await english(page);
  await page.locator('input[type="tel"]').fill(phone);
  await page.locator('input[type="password"]').fill(process.env.DEMO_PASSWORD);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page.waitForURL(/\/(profiles|p\/|lender\/)/);
}

async function accessibility(page, screen) {
  if (!process.env.AXE_PATH) return;
  for (const width of [360, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.waitForTimeout(700);
    await page.evaluate(() => document.fonts.ready);
    await page.addScriptTag({ path: process.env.AXE_PATH });
    const violations = await page.evaluate(async () => {
      const results = await window.axe.run(document, { runOnly: ["wcag2a", "wcag2aa", "wcag21aa"] });
      return results.violations.map((v) => ({ id: v.id, targets: v.nodes.map((n) => n.target) }));
    });
    assert.deepEqual(violations, [], `${screen} accessibility at ${width}px`);
    const overflow = await page.evaluate(() => [...document.querySelectorAll("body *")]
      .filter((el) => el.getBoundingClientRect().right > innerWidth + 1)
      .slice(0, 15).map((el) => ({ tag: el.tagName, class: typeof el.className === "string" ? el.className : "svg", width: Math.round(el.getBoundingClientRect().width) })));
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) console.log("Overflow diagnostic:", JSON.stringify(overflow));
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, "Page reflow");
  }
  console.log(`Accessibility PASS: ${screen}, 360 and 1440px`);
}

try {
  await login(A, process.env.DEMO_OWNER_PHONE);
  const profiles = await call(A, "/profiles", undefined, "GET");
  const profile = profiles.body.items.find((p) => p.display_name === "Rahim Store");
  assert.ok(profile);
  const pid = profile.id;
  await A.goto(`${base}/p/${pid}/sharing`);
  await english(A);
  await A.getByRole("button", { name: "Add or update your details", exact: true }).click();
  await A.getByLabel("Full legal name", { exact: true }).fill("Applicant (DEMO)");
  await A.getByLabel("Date of birth", { exact: true }).fill("1990-01-01");
  // Fictional NID stays hidden in the form and is never printed.
  const nid = "199" + String(Date.now()).slice(-10);
  await A.getByLabel("NID number", { exact: true }).fill(nid);
  await A.getByRole("button", { name: "Continue details", exact: true }).click();
  await A.getByLabel("Present address", { exact: true }).fill("Fictional demo address");
  await A.getByLabel("Nominee name", { exact: true }).fill("Nominee (DEMO)");
  await A.getByLabel("Relationship to nominee", { exact: true }).fill("Sibling");
  await A.getByRole("button", { name: "Continue details", exact: true }).click();
  await A.getByLabel("Years in business", { exact: true }).fill("5");
  await A.getByRole("button", { name: "Save details", exact: true }).click();
  await A.getByRole("status").filter({ hasText: "Details saved" }).waitFor();
  const ownDetails = await call(A, `/profiles/${pid}/applicant-details`, undefined, "GET");
  assert.equal(ownDetails.body.completeness.percent, 100);
  assert.ok(!JSON.stringify(ownDetails.body).includes(nid));
  await accessibility(A, "owner Sharing");
  await A.setViewportSize({ width: 360, height: 900 });
  if (out) await A.screenshot({ path: join(out, "01-owner-masked.png"), fullPage: true });

  await login(B, process.env.DEMO_LENDER_PHONE);
  await B.goto(`${base}/lender/request`);
  await english(B);
  await B.getByLabel("Owner's share code", { exact: true }).fill(process.env.DEMO_SHARE_CODE);
  await B.getByLabel("Applicant details", { exact: true }).check();
  await B.getByRole("button", { name: "Send request", exact: true }).click();
  await B.getByText("If the code is valid, the owner will see your request.", { exact: true }).waitFor();
  const requests = await call(A, `/profiles/${pid}/financing-requests`, undefined, "GET");
  const rid = requests.body.items[0].id;
  assert.equal((await call(A, `/profiles/${pid}/financing-requests/${rid}/assessments`, {})).status, 201);
  await A.reload(); await english(A);
  await A.getByRole("button", { name: "Allow", exact: true }).click();
  const applicantBox = A.getByLabel("Applicant details", { exact: true });
  assert.equal(await applicantBox.isChecked(), false, "Sensitive section must never be preselected");
  await applicantBox.check();
  if (out) await A.screenshot({ path: join(out, "02-explicit-consent.png"), fullPage: true });
  await A.getByRole("button", { name: "Approve", exact: true }).click();
  await applicantBox.waitFor({ state: "hidden" });
  const cases = await call(B, "/lender/cases?status=active", undefined, "GET");
  const active = cases.body.items.find((c) => c.applicant?.display_name === "Rahim Store");
  assert.ok(active);
  await B.goto(`${base}/lender/cases/${active.consent_id}`); await english(B);
  await B.getByRole("heading", { name: "Applicant details", exact: true }).waitFor();
  await B.getByText("Declared by the owner — not verified by Bonik Bondhu.", { exact: true }).waitFor();
  await B.getByText(nid, { exact: true }).waitFor();
  const caseData = await call(B, `/lender/cases/${active.consent_id}`, undefined, "GET");
  assert.equal(caseData.body.consent.hash_verified, true);
  await accessibility(B, "lender CaseFile");
  // Mask the screenshot in the browser DOM; the stored snapshot is not changed.
  await B.getByText(nid, { exact: true }).evaluate((el) => { el.textContent = "•••• •••• (DEMO)"; });
  await B.getByText("1990-01-01", { exact: true }).evaluateAll((els) => els.forEach((el) => { el.textContent = "(DEMO date hidden)"; }));
  if (out) await B.screenshot({ path: join(out, "03-lender-consented.png"), fullPage: true });
  assert.equal((await call(A, `/profiles/${pid}/consents/${active.consent_id}/revoke`, {})).status, 200);
  assert.equal((await call(B, `/lender/cases/${active.consent_id}`, undefined, "GET")).status, 403);
  console.log("F5 browser PASS: three-step form, masking, explicit opt-in, approved snapshot, revocation");
} finally {
  await browser.close();
}
