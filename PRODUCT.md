# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Shop owners** (grocery, variety, tailoring) in Bangladeshi towns and upazilas, on a low-cost Android phone, Bangla first.
  Job: record money in and out correctly, see whether a loan they want would fit their cash, and share a proof-backed
  case with a lender.
- **Crop farmers** (Boro/Aman rice, vegetables), same phone and language. Job: plan a season's costs and income and
  see whether repayment after harvest is possible.
- **Lender officers** (bank, MFI, NGO), desktop, Bangla or English. Job: read a consented case file, ask for more
  information, record their own decision.
- **Hackathon judges** (International AI Builders Congress 2026, FinSphere AI — "SME Capital Engine"), laptop or
  phone, English, deciding in minutes. The landing page must work for judges and owners equally (confirmed 17 Nov 2026).

## Product Purpose

Help small businesses and farmers reach working capital faster by turning their own records into a cash-flow
forecast, a repayment check against that cash, risk what-ifs, and a consent-based case a lender can trust.
Success: an owner goes from first entry to a lender-ready case, and a lender reads it without paperwork.
Challenge ask: faster capital access, lower defaults; cash-flow modeling + risk + integrations.

## Positioning

The repayment is tested against the borrower's own cash before a lender sees it: a schedule *found to fit*, risks
traced to a number, every number with "how was this calculated?", explained in Bangla, shared by the owner's
consent with a SHA-256 fingerprint. It never lends, approves or scores — the lender decides.

## Operating Context

- Owner flow: register → profile (shop or farm) → entries (manual or receipt photo) → summary/forecast →
  financing wizard (5 steps, Fit Finder) → result (status, risks, news, how calculated) → advisor → sharing.
- Lender flow: request access with the owner's share code → owner approves sections → case file → notes,
  information request, decision.
- Demo: DEMO accounts and data (D1 Rahim Store, D2 Karim Variety Store, D3 Rahim Rice Farm, D4 Selina Tailoring;
  DEMO Bank / DEMO MFI). Live at https://bonik-bondhu.onrender.com (free host; sleeps after 15 min).

## Capabilities and Constraints

- Stack in place: React 19 + Vite 8 + Tailwind 4 (tokens in `src/styles/tokens.css`), TypeScript, react-router 8,
  react-i18next (bn/en key parity enforced), lucide-react; FastAPI backend serves the SPA. No chart library; charts
  are hand-made SVG/CSS.
- Mobile first: 360 px phones, owner max width 480 px; lender portal desktop first.
- AI: Gemini/Groq read receipts, list purchase items, answer in the advisor; code calculates every money figure.
  Everything works with AI off.
- Browser E2E scripts select by visible English labels and roles (`frontend/e2e/*.mjs`); renamed labels must be
  updated there.
- Must not claim: approval, eligibility, credit score, probability of default, live prices, real-time news, bank
  partnership, Bangladesh Bank or CIB integration, reduced defaults.

## Brand Commitments

- Name: **বণিক বন্ধু / Bonik Bondhu** in both languages (confirmed).
- Tagline: **"Loans that move with your money"** (confirmed); a Bangla rendering to be written with the team.
- Honesty labels stay visible and are never hidden or softened by design: "DEMO", "Your proposal — not a lender
  offer", "What-if only — does not change your result", "Estimate", "Reported by one source — not confirmed",
  "Collected automatically — not checked by a person" (confirmed).
- No logo or photography exists; illustrations and a logo mark are to be made in-house as SVG (confirmed).

## Evidence on Hand

- Working product with tests (260 backend tests, browser walkthroughs) and golden numbers (`docs/05_Development`).
- Measured AI results: receipts E2 19/20 on 20 synthetic receipts; advisor E10 16/20 — synthetic/small N, never
  presented as accuracy on real users.
- World Bank 2025 figures for Bangladesh (inflation 8.8 %, lending rate 8.6 %, GDP growth 3.5 %).
- No real users, testimonials, partner banks, customer counts or outcome data exist. None may be invented.

## Product Principles

1. The lender decides. The product checks and explains; it never approves.
2. Every number is traceable — a formula, its inputs and a label for what is assumed.
3. The owner owns the data: consent per section, proof instead of paperwork.
4. Bangla first and phone first: plain words, large targets, works on a slow phone and with AI off.
5. Honest by default: what is real, what is DEMO and what is an assumption is always visible.

## Accessibility & Inclusion

WCAG 2.1 AA (axe 0 violations, 320 px reflow), touch targets ≥ 48 px, reduced-motion respected, Bangla digits and
South-Asian grouping in Bangla, low literacy in mind (icons with text, plain words).
