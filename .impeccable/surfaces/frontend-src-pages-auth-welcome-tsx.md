---
version: 1
slug: "frontend-src-pages-auth-welcome-tsx"
primary_target: "frontend/src/pages/auth/Welcome.tsx"
related_targets: ["frontend/src/pages/owner/OwnerLayout.tsx","frontend/src/pages/lender/LenderShell.tsx"]
---

# Surface brief — Welcome / landing (`/`) and the app's shared chrome

Scope: the public first screen `/` (Persuade) plus the owner app and lender portal chrome, which inherit the world
in Operate register (restraint: the world shows in precise details, not performance).
Audience: shop owners and farmers on a 360 px Android (Bangla), hackathon judges on a laptop (English), equally.
Action: try the demo or create an account / log in; language choice stays on the first screen.
Proof: the mechanism itself — a loan weighed against the owner's cash, with DEMO numbers labelled as DEMO.
Constraints: honesty labels visible; AA contrast; reduced-motion; E2E labels ("English", "Create a new account",
"Log in", nav names) unchanged; CSP self-only (fonts via @fontsource); no claims of approval, partners or outcomes.

## Direction contract

THESIS: Every loan is weighed on the owner's own scale before a lender ever sees it. Refuses the category default
(phone mockup beside a promise, gradient, trust-logo row).

OWN-WORLD: A bazaar counter. Distemper-teal wall as the committed field, polished brass for the scale and the one
action, cast-iron ink for type, enamel-white plates for anything you read or press, enamel red only for a
shortfall. Weights are stamped blocks with Bangla numerals; marks not colours carry state (tick fits, notch short,
folded tag where you stopped). Anek Bangla for stamped headings, Noto Sans Bengali for reading.

STORY: The visitor sees a loan and a week's cash on one scale, moves the amount, watches it tip, understands
"checked against my own money, the lender still decides", and taps Try the demo or Create an account.

FIRST VIEWPORT: Teal wall full-bleed. Top: logo mark + বণিক বন্ধু, language plates (বাংলা / English). Centre, 70 %
of the width on phone: the brass scale, left pan "weekly cash", right pan "installment", stamped weights; under
it a brass slider "loan amount" and a live verdict plate (fits ✓ / short by Tk …). Below: tagline in Anek, then
enamel plates Create a new account (primary) and Log in, then a small "DEMO numbers" stamp.

FORM: Daripalla — the shop's brass balance; position 6 of my ordered list; seed: 536653945ba4b85c.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
