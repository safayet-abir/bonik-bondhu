# Review packs for people (P7-T01, P7-T02)

## 1. Bangla text review — `bn_review.csv` (818 rows)

Open in Excel / Google Sheets (UTF-8). One row per screen text: `key`, `english`, `bangla`.
Reviewer (native Bangla speaker, ideally someone who runs or knows a small shop or farm):

- Read the **bangla** column next to the english one. If it is wrong, unclear, too formal or too long
  for a phone screen, write the better text in **correction**; otherwise leave it empty.
- Keep `{{…}}` placeholders exactly as they are (e.g. `{{amount}}`, `{{date}}`) — the app fills them.
- Most important rows: keys starting with `asm.` (check result), `fin.` (financing), `scn.` (what-ifs),
  `share.` / `consent.` (sharing with lenders), `advisor.`, `photo.`, `ai.`, `err.` and `auth.`.
- Words that must never appear: "অনুমোদিত"/"approved", "যোগ্য"/"eligible", "ক্রেডিট স্কোর". Bonik
  Bondhu never lends and never approves — the lender decides.
- Send the file back; the developer copies corrections into `frontend/src/i18n/bn.json` (the CI checks
  that bn and en keep the same keys).

## 2. Accessibility — what was measured and what needs a person

Measured 15 Nov 2026 (WCAG 2.x contrast of the colour tokens; AA needs ≥ 4.5 for normal text):

| Token | on white | on page bg | on primary-soft |
|---|---|---|---|
| text | 16.0 | 14.9 | 13.8 |
| primary | 6.5 | 6.0 | 5.6 |
| muted | 6.0 | 5.6 | 5.1 |
| success | 5.3 | 5.0 | 4.6 |
| danger / info / demo | 6.4–6.6 | 6.0–6.1 | 5.5–5.7 |
| warning (was #B26A00) | 4.2 ✗ | 3.9 ✗ | 3.6 ✗ |
| **warning now #975A00** | 5.6 | 5.2 | 4.8 |

White text on primary buttons 6.5, on the DEMO badge 6.5. All browser walkthroughs run at 360 px width,
and every form field used in them is found by its visible label.

**Needs a person (about 30 minutes, on an Android phone):**

1. **TalkBack** (Settings → Accessibility → TalkBack): log in, add an entry, open Financing → result.
   Every button and field should be read out with a meaningful name; note any that say only "button".
2. **Large text**: set the phone font to the largest size and browser zoom to 200 %; check that no text
   is cut off and nothing needs sideways scrolling on Home, Add entry, the wizard and the result page.
3. **Keyboard** (laptop): use only Tab / Shift+Tab / Enter on the login page and Add entry; the focus
   ring must always be visible and the order must follow the screen.
4. **Bangla rendering**: on a low-cost Android phone, check that Bangla conjuncts and ৳ show correctly.

Write findings as: screen · what happened · expected. P0/P1 issues are fixed before the demo (KS-3).
