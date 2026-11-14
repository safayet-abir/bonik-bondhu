# UI / UX SPECIFICATION — Bonik Bondhu Hackathon MVP

**Document ID:** BB-DOC-04 · **Version:** 1.0 (12 Nov 2026)
**Depends on:** `PRD.md`, `APP_FLOW.md` · **Implements:** MP §9, S1 §2 (mobile-first, Bangla first), FR-I18N-*

> Visual values (colours, fonts, spacing) are **SUG-17 — Not Approved; Outside Current Sources**. The *principles* are sourced from MP §9.

---

## 1. Design principles `[SRC: MP §9]`

1. **Practical utility, not a showcase.** Plain white cards, one accent colour, no gradients, no decorative illustrations, no animation except a simple loading spinner.
2. **Mobile-first** (360 px baseline) for owners; **desktop-first** (≥ 1024 px) for lender portal `[SRC: S1 §2]`.
3. **One main action per screen.** Large primary button at the bottom (thumb zone).
4. **Text + icon, always.** Icons support labels, never replace them.
5. **Bangla first, English available.** Default language `bn` (ASM-06).
6. **Show the "why".** Every calculated number has a "How was this calculated? / কীভাবে হিসাব হলো?" link.
7. **Honest labels.** "Estimate", "Your proposal", "DEMO", "Reported by news, not confirmed".
8. **No more than one simple bar visual per screen**; no chart library (SUG-16).

---

## 2. Design tokens `[SUG-17]`

### 2.1 Colour

| Token | Hex | Use |
|---|---|---|
| `--bb-primary` | `#0B6B53` | Primary buttons, active nav, links |
| `--bb-primary-dark` | `#084C3B` | Pressed state, headers |
| `--bb-primary-soft` | `#E3F1EC` | Selected chip background |
| `--bb-bg` | `#F6F7F5` | App background |
| `--bb-surface` | `#FFFFFF` | Cards, sheets |
| `--bb-text` | `#1C2321` | Body text |
| `--bb-muted` | `#5B6661` | Secondary text, hints |
| `--bb-border` | `#DDE2DF` | Dividers, inputs |
| `--bb-success` | `#1E7B34` | Money in, "ready" status |
| `--bb-warning` | `#B26A00` | Flags, scenarios with shortfall |
| `--bb-danger` | `#B42318` | Errors, "not affordable" status |
| `--bb-info` | `#1F5FA8` | News cards, info banners |
| `--bb-demo` | `#6B4FA1` | DEMO badge only |

Status colours are never the only signal: each status also has an icon and text (accessibility).

### 2.2 Typography

| Token | Value |
|---|---|
| Font family | `"Noto Sans Bengali", "Noto Sans", system-ui, sans-serif` (both OFL fonts, self-hosted) |
| Base size | 16 px; line-height 1.6 (Bangla conjuncts need height) |
| Scale | 13 (caption) · 14 (small) · 16 (body) · 18 (card title) · 22 (screen title) · 28 (key amount) |
| Weights | 400 regular, 600 semibold only |
| Numbers | Tabular figures for amounts (`font-variant-numeric: tabular-nums`) |

### 2.3 Spacing, shape, touch

Spacing scale 4 · 8 · 12 · 16 · 24 · 32 px. Card radius 8 px; button radius 8 px; input height 48 px; minimum touch target 48 × 48 px; bottom nav height 64 px. Max content width (owner) 480 px centred on larger screens.

---

## 3. Icon system `[SUG-16: lucide-react]`

| Concept | Icon | Label (bn / en) |
|---|---|---|
| Shop profile | `Store` | দোকান / Shop |
| Farm profile | `Sprout` | খামার / Farm |
| Sale (cash) | `ArrowDownCircle` (green) | নগদ বিক্রি / Cash sale |
| Sale on baki | `NotebookPen` | বাকিতে বিক্রি / Sale on credit (baki) |
| Purchase | `ShoppingCart` | মাল কেনা / Stock purchase |
| Expense | `Receipt` | খরচ / Expense |
| Loan received | `Landmark` | ঋণ পেলাম / Loan received |
| Loan repayment | `CalendarCheck` | কিস্তি দিলাম / Paid installment |
| Household withdrawal | `Home` | সংসারের জন্য নিলাম / Taken for household |
| Photo entry | `Camera` | ছবি থেকে / From photo |
| Supplier | `Truck` | সরবরাহকারী / Supplier |
| Forecast | `TrendingUp` | আগামী দিনের হিসাব / Forecast |
| Financing | `HandCoins` | ঋণ যাচাই / Check financing |
| News | `Newspaper` | খবর / News |
| Advisor | `MessageCircle` | পরামর্শ / Advisor |
| Share | `Share2` | শেয়ার / Share |
| Warning | `AlertTriangle` | সতর্কতা / Warning |
| Info "how calculated" | `Info` | কীভাবে হিসাব হলো / How calculated |

---

## 4. Navigation structure

### 4.1 Owner — shop profile (bottom nav, 5 items)
`হোম Home` · `হিসাব Entries` · `ঋণ যাচাই Financing` · `পরামর্শ Advisor` · `আরও More`
- **More** → Money summary, Suppliers, Loans I owe (Debts), Forecast, Sharing, Settings, Switch profile, Logout.

### 4.2 Owner — farm profile (bottom nav, 5 items)
`মৌসুম Seasons` · `হিসাব Entries` · `ঋণ যাচাই Financing` · `পরামর্শ Advisor` · `আরও More`
- **More** → Loans I owe, Suppliers (optional), Sharing, Settings, Switch profile, Logout. **No forecast entry** (FR-SEA-08).

### 4.3 Header (all owner screens)
`[Store icon] Rahim Store ▾   [DEMO]   [বাং | EN]`
Tapping the profile name opens SCR-O01. DEMO badge shown when `is_demo=true`.

### 4.4 Lender (desktop left sidebar)
`Cases` · `Request access` · `Logout`. Top bar: organisation name + officer name + language switch. No owner navigation exists.

### 4.5 Responsive behaviour
| Width | Owner app | Lender portal |
|---|---|---|
| < 480 px | Full-width cards, bottom nav | "Use a larger screen for full case file" notice, still readable single column |
| 480–1023 px | Centred 480 px column | Single column, sidebar collapses to top tabs |
| ≥ 1024 px | Centred 480 px column | Sidebar + two-column case file |

---

## 5. Screen inventory

| ID | Screen | Role | Main endpoint(s) | PRD |
|---|---|---|---|---|
| SCR-A01 | Welcome + language | all | — | FR-I18N-02 |
| SCR-A02 | Register | owner | `POST /auth/register` | FR-AUTH-01/02 |
| SCR-A03 | Login | all | `POST /auth/login` | FR-AUTH-04/05 |
| SCR-O01 | Profile chooser | owner | `GET /profiles` | FR-PROF-01/04 |
| SCR-O02 | Create / edit profile | owner | `POST/PATCH /profiles…` | FR-PROF-02/06 |
| SCR-O03 | Shop home | owner | `GET …/summary` (today, month) | US-02 |
| SCR-O04 | Add / edit entry | owner | `POST …/transactions` | FR-LED-01..07 |
| SCR-O05 | Photo entry + draft review | owner | documents, extraction-drafts | FR-EXT-* |
| SCR-O06 | Entries list + detail/void | owner | `GET …/transactions`, void | FR-LED-06 |
| SCR-O07 | Money summary | owner | `GET …/summary` | FR-LED-08 |
| SCR-O08 | Suppliers + dependency | owner | suppliers, supplier-concentration | FR-SUP-* |
| SCR-O09 | Loans I owe (debts) | owner | debts, declare-none | FR-DEBT-* |
| SCR-O10 | Forecast | owner (shop) | forecasts | FR-FC-* |
| SCR-O11 | Financing wizard (5 steps) | owner | financing-requests, items, parse-purpose | FR-FIN-* |
| SCR-O12 | Assessment result (tabs: Result · Risks · News · How calculated) | owner | assessments, scenarios, news-signals | FR-ASM-*, FR-SCN-*, FR-NEWS-* |
| SCR-O14 | Sharing & lender requests | owner | consents | FR-CON-* |
| SCR-O15 | Advisor chat | owner | advisor/messages, help-topics | FR-ADV-* |
| SCR-O16 | Settings | owner | `PATCH /auth/me`, logout | FR-AUTH-08 |
| SCR-F01 | Farm home (seasons) | owner (farm) | `GET …/seasons` | FR-SEA-01 |
| SCR-F02 | Create / edit season | owner (farm) | `POST/PATCH …/seasons` | FR-SEA-01..03 |
| SCR-F03 | Season costs & sales | owner (farm) | cost-items, transactions | FR-SEA-04/05 |
| SCR-F04 | Record harvest | owner (farm) | `POST …/harvest` | FR-SEA-06 |
| SCR-F05 | Season summary | owner (farm) | `GET …/seasons/{sid}/summary` | FR-SEA-07 |
| SCR-L01 | Case list | lender | `GET /lender/cases` | FR-LEN-02 |
| SCR-L02 | Request access | lender | `POST /lender/access-requests` | FR-CON-01 |
| SCR-L03 | Case file + review panel | lender | `GET /lender/cases/{cid}`, events | FR-LEN-03..06 |

(SCR-O13 intentionally unused: risks and news are tabs inside SCR-O12.) No Buy/Sell screen exists (DEC-06).

---

## 6. Screen-by-screen wireframes (text)

### SCR-A01 Welcome
```
┌──────────────────────────────┐
│        বণিক বন্ধু             │
│     Bonik Bondhu             │
│ আপনার টাকার হিসাব, সহজভাবে      │
│                              │
│  ভাষা / Language             │
│  [ বাংলা ✓ ]  [ English ]     │
│                              │
│  [   নতুন অ্যাকাউন্ট খুলুন   ]   │
│  [        লগইন করুন        ]   │
└──────────────────────────────┘
```

### SCR-A02 Register
```
নতুন অ্যাকাউন্ট / Create account
পুরো নাম / Full name        [ মোঃ রহিম উদ্দিন        ]
মোবাইল নম্বর / Mobile      [ 01712345678           ]
ইমেইল / Email               [ rahim.demo@example.com ]
পাসওয়ার্ড / Password        [ ••••••••    👁 ]
  ≥ ৮ অক্ষর, শুধু সংখ্যা নয় / ≥ 8 characters, not only digits
ⓘ আপনার নম্বর এখন যাচাই করা হয় না। নিজের নম্বর দিন।
  Your number is not verified yet. Use your own number.
[          অ্যাকাউন্ট খুলুন / Create account          ]
আগে থেকে অ্যাকাউন্ট আছে? লগইন
```
Validation inline on blur; server errors mapped to fields (409 → phone/email field).

### SCR-A03 Login
```
লগইন / Log in
মোবাইল নম্বর  [ 01712345678 ]
পাসওয়ার্ড     [ •••••••• ]
[        লগইন / Log in        ]
পাসওয়ার্ড ভুলে গেছেন? সাহায্যের জন্য টিমের সাথে যোগাযোগ করুন।
Forgot password? Contact the team for help.
```

### SCR-O01 Profile chooser
```
কোন ব্যবসা? / Which business?
┌ 🏪 Rahim Store            দোকান  › ┐
┌ 🌱 Rahim Rice Farm        খামার  › ┐
[ + আরেকটি ব্যবসা যোগ করুন / Add another business ]
```

### SCR-O02 Create profile (minimal)
```
ব্যবসার নাম / Business name   [ Rahim Store ]
ধরন / Type   ( ) 🏪 দোকান / Shop   ( ) 🌱 ফসলের খামার / Crop farm
— Optional now, needed for financing —
জেলা / District [ Dhaka ▾ ]   উপজেলা / Upazila [ Savar ▾ ]
ব্যবসার ধরন / Category [ Grocery ▾ ]
[ সংরক্ষণ / Save ]
```
District/upazila: dropdown lists from a static JSON file maintained by the team (GAP: list content must come from an official source; until then free text with suggestions).

### SCR-O03 Shop home
First-time variant:
```
স্বাগতম, রহিম! / Welcome
আপনি কী করতে চান? / What do you want to do?
┌──────────────────────────────┐
│ 📒 টাকার হিসাব রাখি           │
│    Record my money           │
│    বিক্রি, খরচ, কেনাকাটা লিখুন   │
└──────────────────────────────┘
┌──────────────────────────────┐
│ 🤝 ঋণের হিসাব যাচাই করি        │
│    Check financing           │
│    কত টাকা দরকার, কিস্তি পারবো কি? │
└──────────────────────────────┘
```
Returning variant:
```
আজ / Today            এই মাস / This month
নগদ এল  Tk 8,500       নগদ এল   Tk 1,44,300
নগদ গেল Tk 1,500       নগদ গেল  Tk 1,12,000
Quick add:
[⬇ নগদ বিক্রি] [📝 বাকি] [🛒 মাল কেনা] [🧾 খরচ] [📷 ছবি]
সাম্প্রতিক / Recent
• নগদ বিক্রি  Tk 8,500  আজ
• দোকান ভাড়া  Tk 1,500  আজ
```

### SCR-O04 Add entry
```
নতুন এন্ট্রি / New entry
কী হয়েছে? / What happened?
[⬇ নগদ বিক্রি] [📝 বাকিতে বিক্রি] [💵 বাকি আদায়]
[🛒 নগদে মাল কেনা] [📋 বাকিতে মাল কেনা] [💸 মালের বাকি শোধ]
[🧾 খরচ] [🏦 ঋণ পেলাম] [📅 কিস্তি (আসল)] [％ সুদ/ফি]
[🏠 সংসারে নিলাম] [➕ নিজের টাকা দিলাম]
টাকা / Amount (Tk)   [ 8500 ]   উদাহরণ: 8500
তারিখ / Date          [ আজ ▾ ]
সরবরাহকারী / Supplier [ — ▾ ]   (purchase types only)
কোন ঋণ? / Which loan? [ — ▾ ]  (loan types only)
মৌসুম / Season        [ Boro 2026–27 ▾ ] (farm only)
নোট / Note (optional) [ ঈদের আগে বিক্রি ]
[ সংরক্ষণ / Save ]
```
Helper text under selected type explains the accounting rule in one line, e.g. **Sale on credit:** "এটি নগদ নয়। টাকা পেলে 'বাকি আদায়' লিখুন। / Not cash yet. When paid, record 'Credit collected'." `[SRC: S1 F2]`

### SCR-O05 Photo entry + draft review
```
ছবি থেকে এন্ট্রি / Entry from photo
[ 📷 ছবি তুলুন ]  [ 🖼 গ্যালারি ]
☐ ছবিটি পড়ার জন্য AI সেবায় পাঠানো হবে (Google Gemini)।
   The photo will be sent to an AI service to read it.
--- after extraction ---
AI যা পড়েছে — যাচাই করুন / Check what AI read
ধরন   [ নগদে মাল কেনা ▾ ]   ⚠ নিশ্চিত নয় / unsure
টাকা   [ 12,450 ]           ✓
তারিখ  [ 10 Nov 2026 ]      ⚠
সরবরাহকারী [ Supplier A ]
[ ঠিক আছে, সংরক্ষণ করুন / Confirm & save ]  [ বাতিল / Discard ]
```
Fields with confidence < 0.8 are highlighted in warning colour and focused first (threshold is UI-only, SUG-17 family).

### SCR-O06 Entries list
Filter chips: All · In · Out · Loans · Voided. Each row: icon, label, amount (green in / dark out), date, evidence icon (📎 if document attached). Detail sheet has "ভুল হয়েছে? বাতিল করুন / Wrong? Void" with required reason.

### SCR-O07 Money summary
```
সময় / Period  [এই সপ্তাহ] [এই মাস ✓] [গত ৮ সপ্তাহ] [নিজে বাছাই]
বিক্রি (মোট লেখা) / Sales recorded      Tk 1,46,300
  ├ নগদ বিক্রি / Cash sales             Tk 1,44,300
  └ বাকিতে বিক্রি / Credit sales         Tk 2,000
ব্যবসায় নগদ এল / Operating cash in     Tk 1,45,800
ব্যবসায় নগদ গেল / Operating cash out   Tk 1,12,000
ব্যবসার নিট নগদ / Net operating cash     Tk 33,800
পাওনা বাকি / Receivables outstanding    Tk 500
দেনা বাকি / Payables outstanding        Tk 0
ঋণ পেলাম / Loans received (not income)  Tk 0
কিস্তি আসল / Principal repaid            Tk 0
সংসারে নিলাম / Household withdrawals    Tk 15,000
ⓘ ঋণের টাকা বিক্রি নয়; বাকি বিক্রি নগদ নয়। কীভাবে হিসাব হলো?
```
(Amounts above are layout examples, not golden values.)

### SCR-O08 Suppliers + dependency
```
সরবরাহকারী / Suppliers                  [+ যোগ করুন]
Supplier A   চাল, তেল   Savar    65.0% ███████████████
Supplier B   ডাল        Dhaka    25.0% ██████
Supplier C   মশলা       Ashulia  10.0% ██
⚠ একজন সরবরাহকারীর উপর বেশি নির্ভরতা (65%)।
  High dependency on one supplier (65%).
ভিত্তি: গত ৮ সপ্তাহের কেনাকাটা এন্ট্রি / Basis: purchase entries, last 8 weeks
```

### SCR-O09 Loans I owe
List cards: lender type icon + label ("MFI — DEMO NGO"), outstanding, installment × frequency, next due date, overdue badge. Buttons: `+ ঋণ যোগ করুন / Add loan`, `আমার এখন কোনো ঋণ নেই / I have no current loans`. Footer text: "অফিসিয়াল ক্রেডিট যাচাই (CIB) ঋণদাতা নিজে করবে। / Official credit checks (CIB) are done by the lender, outside Bonik Bondhu." `[SRC: S1 F9]`

### SCR-O10 Forecast (shop only)
```
আগামী দিনের হিসাব (অনুমান) / Forecast (estimate)
তৈরি: 1 Dec 2026, গত ৮ সপ্তাহের মধ্যে ৮ সপ্তাহের হিসাব আছে
                      কম (low)    সম্ভাব্য (expected)
৭ দিন / 7 days         Tk 25,000    Tk 32,313
৩০ দিন / 30 days       Tk 1,07,143  Tk 1,38,482
৬০ দিন / 60 days       ...          ...
৯০ দিন / 90 days       ...          ...
জানা কিস্তি / Known installments in 30 days: Tk 0
⚠ এটি অনুমান, নিশ্চিত আয় নয়। / This is an estimate, not guaranteed income.
[ পূর্বাভাস হালনাগাদ / Update forecast ]
```
Insufficient state: big icon, "আরও ২ সপ্তাহের হিসাব দিন / Record 2 more weeks", button to SCR-O04. (Numbers above are illustrative of layout; golden values are in Testing §4.)

### SCR-O11 Financing wizard (progress bar 1–5)
- **Step 1 — Amount & purpose:** amount (example "200000"), purpose text (example "ঈদের আগে চাল-ডাল-তেল কিনবো"), category chips (inventory / farm inputs / equipment / other), desired start date. If profile lacks district/upazila/category/household withdrawal → inline mini-form.
- **Step 2 — What will you buy?** Item rows: name, qty, unit, unit price, price source (chips: সরবরাহকারীর দর / আগের কেনা / বাজারদর / অনলাইন দাম / আমার অনুমান), price date. Button "🤖 লেখা থেকে তালিকা বানাও / Make list from my text" (AI, optional). AI rows show "AI suggestion — confirm".
- **Step 3 — Your money:** associated expenses (transport etc.), buffer + reason, cash safely available for this purchase, other financing already arranged, current cash in hand (optional). Live **funding gap** box with formula.
- **Step 4 — Loans you already have:** list from SCR-O09 + add, or "no current loans".
- **Step 5 — Your repayment proposal:** banner "এটি আপনার প্রস্তাব — ঋণদাতার অফার নয় / Your proposal — not a lender offer". Schedule type (সমান কিস্তি / এককালীন), number, frequency (weekly/monthly), first due date, total interest + fees (or "জানি না / don't know"), minimum cash reserve. Show computed installment table. Button `যাচাই করুন / Check`.

### SCR-O12 Assessment result
```
[ফলাফল] [ঝুঁকি] [খবর] [কীভাবে হিসাব]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ঋণদাতার পর্যালোচনার জন্য প্রস্তুত
   Ready for lender review
এটি ঋণ অনুমোদন নয়। সিদ্ধান্ত ঋণদাতা নেবেন।
This is not a loan approval. The lender decides.

আসলে কত দরকার / Funding gap        Tk 1,50,000
আপনি চেয়েছেন / You asked           Tk 2,00,000
পার্থক্য / Difference                Tk 50,000  [ব্যাখ্যা লিখুন]
কম আয়ের হিসাবে সব কিস্তির দিনে টাকা থাকে
In the low-income case, cash covers every due date.
সবচেয়ে কম ব্যালান্স / Lowest balance after a payment: Tk 21,626

সতর্কতা / Flags
⚠ চাওয়া টাকা প্রয়োজনের চেয়ে বেশি
⚠ এক সরবরাহকারীর উপর ৬৫% নির্ভরতা
[ ঋণদাতার সাথে শেয়ার / Share with a lender ]
```
Other status headers:
- `insufficient_information`: ℹ️ "আরও তথ্য দরকার / More information needed" + checklist of missing items, each a link.
- `not_affordable_base_case`: 🔴 "এই শর্তে কিস্তি দিতে কষ্ট হতে পারে / These terms may cause a cash shortfall" + "<date> তারিখে প্রায় Tk X কম পড়তে পারে" + suggestions (smaller amount, different terms to discuss with lender).

**Risks tab:** scenario cards: title, plain assumption, result (covered ✓ / shortfall on date ⚠ amount), label "What-if only — does not change your status".
**News tab:** cards: headline, source, date, location, match reason, "একটি সূত্র / Single source" or "একাধিক সূত্র / Corroborated", DEMO badge if fictional, buttons "এই ঝুঁকি পরীক্ষা করুন / Test this risk" (confirm) and "প্রাসঙ্গিক নয় / Not relevant" (dismiss).
**How calculated tab:** formulas (funding gap, capacity), every input with source tag (declared / document attached / computed), forecast method, assumptions list.

### SCR-O14 Sharing & lender requests
```
শেয়ার কোড / Your share code: 7KQ2M-9XA4P  [কপি] [নতুন কোড]
ঋণদাতাকে এই কোড দিলে তিনি অনুরোধ পাঠাতে পারবেন।
Give this code to a lender so they can send a request.

নতুন অনুরোধ / New requests
┌ DEMO Bank Ltd — Officer: Nasrin (DEMO)
│ চাইছেন: সারসংক্ষেপ, ঋণের প্রস্তাব, ঋণ, সরবরাহকারী ঝুঁকি
│ [অনুমতি দিন] [না]
Approve sheet:
  কোন তথ্য দেখাবেন? ☑ প্রোফাইল ☑ টাকার সারাংশ ☑ পূর্বাভাস
  ☑ ঋণের প্রস্তাব ও যাচাই ☑ বর্তমান ঋণ ☑ সরবরাহকারী ঝুঁকি ☑ খবর ☐ সব এন্ট্রির তালিকা
  কতদিন? (•) ১৪ দিন ( ) ৭ দিন ( ) ৩০ দিন
  ⚠ একবার দেখা তথ্য ফেরত নেওয়া যায় না।
  [ অনুমতি দিন / Approve ]
চলমান শেয়ার / Active shares
DEMO Bank Ltd — valid until 15 Dec — viewed 2× — [বন্ধ করুন / Revoke]
ঋণদাতার বার্তা / Lender messages: "Please upload supplier quotation"
```

### SCR-O15 Advisor
Chat bubbles; quick-question chips: "আগামী সপ্তাহে কত কিস্তি?", "আমার সবচেয়ে বড় খরচ কী?", "কেন ২ লাখ বেশি?", "সরবরাহকারী দেরি করলে কী হবে?". Footer: "পরামর্শদাতা শুধু আপনার হিসাব থেকে উত্তর দেয়; ঋণ অনুমোদন করে না।" Fallback mode shows the same chips mapped to deterministic answers.

### SCR-F01 Farm home
Season cards: crop icon, "Boro rice 2026–27 · 1.5 acres (150 decimal)", status chip (planned/growing/harvested), planned cost vs paid, expected harvest date. Button `+ নতুন মৌসুম / New season`.

### SCR-F02 Create season
```
ফসল / Crop [ ধান / Rice ▾ ]  জাত / Variety [ BRRI dhan28 (optional) ]
মৌসুম / Season [বোরো ✓] [আমন] [আউশ] [শীতের সবজি] [অন্য]
জমি / Land area [ 150 ] [ শতাংশ / decimal ▾ ]  = 1.5 একর
  (bigha → "আপনার এলাকায় ১ বিঘা = [ 33 ] শতাংশ")
বপন / Sowing date [ 10 Jan 2027 ]   ফসল তোলা / Harvest [ 05 May 2027 ]
সম্ভাব্য ফলন (কেজি) / Expected output (kg): কম 2700 · সম্ভাব্য 3300 · বেশি 3750
সম্ভাব্য দাম (টাকা/কেজি) / Expected price: কম 28 · সম্ভাব্য 32 · বেশি 35
ⓘ এগুলো আপনার অনুমান। / These are your estimates.
```

### SCR-F03 Season costs & sales
Two lists: **Plan** (item, qty, unit cost, total, "Paid ✓" button that opens SCR-O04 pre-filled with season) and **Actual** (ledger entries for this season). Totals: planned 65,000 · paid 4,500 · sales 0.

### SCR-F04 Record harvest
Actual harvest date, actual output (kg), note. Then prompt "বিক্রি লিখুন / Record sale".

### SCR-F05 Season summary
```
Boro rice 2026–27 (DEMO)
সম্ভাব্য আয় / Income range: কম 75,600 · সম্ভাব্য 1,05,600 · বেশি 1,31,250
পরিকল্পিত খরচ / Planned cost      Tk 65,000
খরচ দেওয়া হয়েছে / Paid so far     Tk 4,500
লাভ-ক্ষতি সমান দাম / Break-even   Tk 19.70 / kg
ঋণ শোধের দাম / Loan-cover price   Tk 19.78 / kg (কম ফলনে)
ⓘ এর কম দামে বিক্রি করলে কিস্তি দিতে টাকা কম পড়তে পারে। আগেই ঋণদাতার সাথে কথা বলুন।
```

### SCR-L01 Lender case list (desktop)
Table: Applicant (profile display name + type) · Requested amount · Assessment status · Consent valid until · Review status · Last viewed. Tabs: Pending owner approval · Active · Closed (expired/revoked/declined).

### SCR-L02 Request access
Fields: Share code, sections (checkboxes, same keys as owner approval), message to applicant (max 500 chars). After submit: neutral confirmation.

### SCR-L03 Case file
Left column (snapshot): Applicant & consent (sections, valid until, snapshot hash, version) · Financing request & funding gap · Assessment status, due-date checks, flags · Scenarios (labelled what-if) · Existing obligations (declared) + CIB placeholder · Money summary & record coverage · Evidence mix (% declared / % document attached) · Supplier dependency (Supplier 1/2/3, names hidden) · News signals with sources.
Right column (review panel): status selector, note box (lender-only), "Request information" box (owner sees), decision (proceed / decline / refer) + mandatory reason → banner "Demo decision recorded by <org>. Bonik Bondhu does not issue or disburse loans."

---

## 7. Form specifications

### 7.1 Field rules (shared)

| Field | Type | Rules | Example |
|---|---|---|---|
| full_name | text | 2–100 chars | মোঃ রহিম উদ্দিন |
| phone | tel | SUG-24 pattern; stored `+8801…` | 01712345678 |
| email | email | RFC-like, ≤ 254, lower-cased | rahim.demo@example.com |
| password | password | SUG-25 | — |
| amount | numeric (inputmode=decimal) | > 0, ≤ 2 decimals; accept Bangla digits ০-৯ and commas | 8500 |
| date | date | not > today+1 for entries; season dates logical (sowing < harvest) | 2026-12-01 |
| percentage | numeric | 0–100, ≤ 1 decimal | 65 |
| area | numeric | > 0, ≤ 100000 | 150 |
| text note | text | ≤ 300 chars | ঈদের বিক্রি |

### 7.2 Entry form per type

| Type | Required | Optional | Shown helper (en) |
|---|---|---|---|
| sale_cash | amount, date | note, season | Money received now |
| sale_credit | amount, date | customer note | Not cash yet (baki) |
| receivable_collection | amount, date | note | Baki money you received |
| purchase_cash | amount, date | supplier, season, season cost item | Stock/inputs paid now |
| purchase_credit | amount, date | supplier | Bought now, pay later |
| payable_payment | amount, date | supplier | Paying supplier's due |
| operating_expense | amount, date, category (rent, salary, utility, transport, other / farm categories) | note, season | Running cost |
| loan_received | amount, date | debt link | Not income |
| loan_principal_repayment | amount, date | debt link | Reduces loan; not an expense |
| loan_interest_fee_payment | amount, date | debt link | Cost of borrowing |
| owner_withdrawal | amount, date | note | Taken for household/personal |
| owner_contribution | amount, date | note | Your own money put in; not income |

### 7.3 Microcopy table (bn / en)

| Key | বাংলা | English |
|---|---|---|
| app.tagline | আপনার টাকার হিসাব, সহজভাবে | Your money, simply recorded |
| auth.register | অ্যাকাউন্ট খুলুন | Create account |
| auth.login | লগইন করুন | Log in |
| auth.logout | লগআউট | Log out |
| auth.err.invalid | ফোন নম্বর বা পাসওয়ার্ড ভুল | Phone number or password is wrong |
| auth.err.locked | অনেকবার ভুল হয়েছে। ১৫ মিনিট পর চেষ্টা করুন। | Too many attempts. Try again in 15 minutes. |
| auth.err.phone_taken | এই নম্বরে আগেই অ্যাকাউন্ট আছে | An account already uses this number |
| auth.err.email_taken | এই ইমেইলে আগেই অ্যাকাউন্ট আছে | An account already uses this email |
| auth.session_expired | সময় শেষ। আবার লগইন করুন। | Session ended. Please log in again. |
| auth.unverified_note | আপনার নম্বর এখন যাচাই করা হয় না। নিজের নম্বর দিন। | Your number is not verified yet. Use your own number. |
| auth.forgot | পাসওয়ার্ড ভুলে গেলে টিমের সাথে যোগাযোগ করুন | Forgot your password? Contact the team |
| home.path_a | টাকার হিসাব রাখি | Record my money |
| home.path_b | ঋণের হিসাব যাচাই করি | Check financing |
| entry.saved | সংরক্ষণ হয়েছে | Saved |
| entry.duplicate | মনে হচ্ছে এটা আগেই লেখা হয়েছে। আবার রাখবেন? | This looks like an entry you already saved. Save again? |
| entry.void_reason | কেন বাতিল করছেন? | Why are you voiding this? |
| entry.err.amount | টাকার পরিমাণ লিখুন (০-এর বেশি) | Enter an amount above zero |
| entry.err.future_date | ভবিষ্যতের তারিখ দেওয়া যাবে না | Date cannot be in the future |
| rule.credit_sale | এটি নগদ নয়। টাকা পেলে "বাকি আদায়" লিখুন। | Not cash yet. When paid, record "Credit collected". |
| rule.loan_received | ঋণের টাকা বিক্রি বা আয় নয়। | A loan is not sales or income. |
| rule.principal | আসল শোধ খরচ নয়, ঋণ কমায়। | Principal repayment is not an expense; it reduces the loan. |
| photo.ai_consent | ছবিটি পড়ার জন্য AI সেবায় পাঠানো হবে | The photo will be sent to an AI service to read it |
| photo.check | AI যা পড়েছে — যাচাই করে ঠিক করুন | Check and correct what AI read |
| photo.failed | ছবি থেকে পড়া যায়নি। নিজে লিখুন। | Could not read the photo. Please type it. |
| summary.empty | এখনও কোনো হিসাব নেই। প্রথম এন্ট্রি দিন। | No entries yet. Add your first entry. |
| forecast.estimate | এটি অনুমান, নিশ্চিত আয় নয়। | This is an estimate, not guaranteed income. |
| forecast.insufficient | পূর্বাভাসের জন্য কমপক্ষে {required} সপ্তাহের হিসাব দরকার। এখন আছে {have} সপ্তাহ। | A forecast needs at least {required} weeks of records. You have {have}. |
| supplier.high_dep | একজন সরবরাহকারীর উপর বেশি নির্ভরতা ({pct}%) | High dependency on one supplier ({pct}%) |
| supplier.sparse | কম সরবরাহকারী লেখা আছে — এর মানে ঝুঁকি কম নয় | Few suppliers recorded — this does not mean low risk |
| debt.none | আমার এখন কোনো ঋণ নেই | I have no current loans |
| debt.cib | অফিসিয়াল ক্রেডিট যাচাই (CIB) ঋণদাতা নিজে করবে | Official credit checks (CIB) are done by the lender |
| fin.proposal_banner | এটি আপনার প্রস্তাব — ঋণদাতার অফার নয় | This is your proposal — not a lender offer |
| fin.gap | আসলে কত টাকা দরকার | How much new money is really needed |
| fin.over_request | আপনি প্রয়োজনের চেয়ে Tk {diff} বেশি চেয়েছেন। কেন, লিখবেন? | You asked Tk {diff} more than the estimated need. Can you explain why? |
| asm.ready | ঋণদাতার পর্যালোচনার জন্য প্রস্তুত | Ready for lender review |
| asm.not_approval | এটি ঋণ অনুমোদন নয়। সিদ্ধান্ত ঋণদাতা নেবেন। | This is not a loan approval. The lender decides. |
| asm.insufficient | আরও তথ্য দরকার | More information needed |
| asm.not_affordable | এই শর্তে কিস্তি দিতে কষ্ট হতে পারে | These terms may cause a cash shortfall |
| asm.shortfall_on | {date} তারিখে প্রায় Tk {amount} কম পড়তে পারে | About Tk {amount} may be short on {date} |
| asm.stale | তথ্য বদলেছে। আবার যাচাই করুন। | Your information changed. Check again. |
| scn.whatif | শুধু "যদি এমন হয়" হিসাব — আপনার ফলাফল বদলায় না | What-if only — does not change your result |
| scn.delay | যদি {supplier} {days} দিন মাল দিতে না পারে | If {supplier} cannot deliver for {days} days |
| scn.price_rise | যদি মালের দাম {pct}% বাড়ে | If stock prices rise by {pct}% |
| news.single | একটি সূত্রের খবর — নিশ্চিত নয় | Reported by one source — not confirmed |
| news.corroborated | একাধিক সূত্রে খবর | Reported by several sources |
| news.demo | ডেমো খবর (কাল্পনিক) | Demo event (fictional) |
| news.test | এই ঝুঁকি পরীক্ষা করুন | Test this risk |
| news.dismiss | প্রাসঙ্গিক নয় | Not relevant |
| share.code_help | ঋণদাতাকে এই কোড দিলে তিনি অনুরোধ পাঠাতে পারবেন | Give this code to a lender so they can send a request |
| share.warning | একবার দেখা তথ্য ফেরত নেওয়া যায় না | Information already viewed cannot be taken back |
| share.revoked | শেয়ার বন্ধ করা হয়েছে | Sharing stopped |
| adv.disclaimer | পরামর্শদাতা শুধু আপনার হিসাব থেকে উত্তর দেয়; ঋণ অনুমোদন করে না | The advisor answers only from your records; it does not approve loans |
| adv.limit | আজকের প্রশ্নের সীমা শেষ | You have reached today's question limit |
| adv.missing | এই প্রশ্নের উত্তরে {item} দরকার। {screen}-এ যোগ করুন। | To answer this I need {item}. Add it in {screen}. |
| err.network | সংযোগ সমস্যা। আবার চেষ্টা করুন। | Connection problem. Please try again. |
| err.generic | কিছু ভুল হয়েছে। আবার চেষ্টা করুন। | Something went wrong. Please try again. |
| demo.badge | ডেমো | DEMO |
| season.bigha_factor | আপনার এলাকায় ১ বিঘা = কত শতাংশ? | In your area, 1 bigha = how many decimals? |
| season.loan_cover | এর কম দামে বিক্রি করলে কিস্তির টাকা কম পড়তে পারে | Selling below this price may leave too little for repayment |
| lender.decision_banner | ঋণদাতার ডেমো সিদ্ধান্ত রেকর্ড হয়েছে। বণিক বন্ধু ঋণ দেয় না। | Demo decision recorded by the lender. Bonik Bondhu does not issue loans. |

The full key set lives in `frontend/src/i18n/bn.json` and `en.json`; CI fails if keys differ (FR-I18N-01).

---

## 8. Empty, loading and error states

| State | Pattern |
|---|---|
| Empty | Icon + one-line explanation + one primary action (never a blank card) |
| Loading | Skeleton rows for lists; spinner with "হিসাব হচ্ছে… / Calculating…" for assessment; buttons disabled while submitting (prevents double submit) |
| Field error | Red text under field, field border red, focus moved to first error |
| Page error | Inline banner with retry; no stack traces; error code shown small for support |
| AI unavailable | Neutral info banner, manual path shown immediately |
| Offline | Top banner "ইন্টারনেট নেই / No internet"; forms keep typed values |

---

## 9. Accessibility and low-literacy considerations

- Contrast ≥ 4.5:1 for text (tokens chosen accordingly; verify with a checker).
- All inputs have visible labels (not placeholder-only); examples shown as helper text.
- Buttons use verbs ("সংরক্ষণ করুন", "যাচাই করুন").
- Amounts displayed with Tk prefix and South Asian grouping (1,50,000) in both languages `[DERIVED: MP §9 familiarity]`.
- Status = icon + colour + words.
- Screen reader: `aria-label` in current language for icon buttons; `lang` attribute switches `bn`/`en`.
- Maximum 5 fields visible per wizard step on mobile.
- Avoid jargon; glossary popovers for: funding gap (প্রয়োজনীয় টাকার ঘাটতি), reserve (হাতে রাখা ন্যূনতম টাকা), baki (বাকি), installment (কিস্তি).
