---
name: Bonik Bondhu (বণিক বন্ধু)
description: Loans that move with your money — every loan weighed on the owner's own brass balance before a lender sees it.
colors:
  wall: "#1e6f66"
  wall-deep: "#14504a"
  wall-mist: "#d6ece8"
  brass: "#e2b54f"
  brass-deep: "#8a6214"
  iron: "#14201d"
  enamel: "#f6f8f5"
  primary: "#1e6f66"
  primary-dark: "#14504a"
  primary-soft: "#e1eeeb"
  bg: "#eef3f1"
  surface: "#ffffff"
  text: "#14201d"
  muted: "#4f5e59"
  border: "#d3deda"
  success: "#1e7b34"
  warning: "#975a00"
  danger: "#c2362b"
  info: "#1f5fa8"
typography:
  display:
    fontFamily: "Anek Bangla Variable, Noto Sans Bengali, Noto Sans, sans-serif"
    fontSize: "3.75rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 92"
  headline:
    fontFamily: "Anek Bangla Variable, Noto Sans Bengali, Noto Sans, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.6
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 92"
  title:
    fontFamily: "Anek Bangla Variable, Noto Sans Bengali, Noto Sans, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.6
  amount:
    fontFamily: "Anek Bangla Variable, Noto Sans Bengali, Noto Sans, sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.25
    fontFeature: "'tnum' 1"
  body:
    fontFamily: "Noto Sans Bengali, Noto Sans, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  body-small:
    fontFamily: "Noto Sans Bengali, Noto Sans, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Noto Sans Bengali, Noto Sans, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  stamp: "2px"
  bb: "8px"
  pill: "9999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  touch: "48px"
components:
  button-brass:
    backgroundColor: "{colors.brass}"
    textColor: "{colors.iron}"
    typography: "{typography.title}"
    rounded: "{rounded.bb}"
    padding: "0 16px"
    height: "56px"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.bb}"
    padding: "0 16px"
    height: "48px"
  button-primary-active:
    backgroundColor: "{colors.primary-dark}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.bb}"
    padding: "0 16px"
    height: "48px"
  button-secondary-active:
    backgroundColor: "{colors.primary-soft}"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.surface}"
    rounded: "{rounded.bb}"
    padding: "0 16px"
    height: "48px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.bb}"
    padding: "16px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.bb}"
    padding: "0 12px"
    height: "48px"
  chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "48px"
  chip-selected:
    backgroundColor: "{colors.primary-soft}"
    textColor: "{colors.primary}"
  demo-stamp:
    backgroundColor: "{colors.enamel}"
    textColor: "{colors.iron}"
    typography: "{typography.label}"
    rounded: "{rounded.stamp}"
    padding: "0 6px"
  verdict-plate-fits:
    backgroundColor: "{colors.enamel}"
    textColor: "{colors.iron}"
    rounded: "{rounded.bb}"
    padding: "10px 16px"
  verdict-plate-short:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.surface}"
    rounded: "{rounded.bb}"
    padding: "10px 16px"
  owner-header:
    backgroundColor: "{colors.wall}"
    textColor: "{colors.surface}"
    padding: "8px 16px"
  bottom-nav:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
    height: "64px"
---

# Design System: Bonik Bondhu (বণিক বন্ধু)

## Overview

**Creative North Star: "Daripalla — the shop's brass balance"**

The system is a bazaar counter. A distemper-teal wall is the committed field; on it hangs a polished brass balance, cast-iron weights stamped in brass, and enamel-white plates for everything you read or press. Every loan is weighed on the owner's own scale before a lender sees it, so the scale is not decoration: on the landing it tips live as the loan amount moves, and on the assessment result it rests cash-side-down (fits), payment-side-down (short), or level (not enough information).

The world speaks in two registers. The public landing (Persuade) is the full teal wall with the balance at hero scale, brass for the one action, and stamped Anek Bangla headings. Inside the owner app and lender portal (Operate), the world retreats to precise details: a teal header strip, brass marks for the active nav tab and focus ring, the balance once on the result screen, cast-weight step numbers, and the iron-ink DEMO stamp. Everything else is plain enamel cards on a pale wall wash, built for a 360 px Android in Bangla.

Density is low and targets are large: 48 px minimum touch height everywhere, one main action per screen, icon plus words, never icon alone. State is carried by marks and words first and colour second.

**Key Characteristics:**
- Teal wall field, brass instrument, iron ink, enamel plates; red reserved for shortfalls and errors.
- One authored motion: the balance's damped-spring swing. One page-level motion: a 260 ms settle-in.
- Stamped Anek Bangla headings (92 % width) over Noto Sans Bengali reading text at 16 / 1.6.
- 8 px corners on every plate and button; pill only for filter chips.
- Soft, short drops under plates; no hard offset shadows.
- Bilingual by construction: Bangla digits in bn, tabular numerals for every amount.

## Colors

A narrow bazaar palette: one committed teal field, one metal accent, one ink, one enamel, plus four functional status colours held to WCAG AA.

### Primary
- **Distemper Teal Wall** (wall / primary): the committed field. Full-bleed on the landing, the owner header strip, the lender header's top rule, the panel behind the result balance; in-app it is also the primary button fill, link colour, active-tab text and input focus border. White on it measures about 6.0:1.
- **Shadowed Wall** (wall-deep / primary-dark): the landing's second band ("how it works") and the pressed state of primary buttons.
- **Wall Mist** (wall-mist): secondary text on the teal wall (readouts' labels, sub-tagline, DEMO note, wordmark sub-line). About 4.8:1 on the wall.
- **Pale Teal Plate** (primary-soft): selected chips, selected plate-tone language button, active lender nav item, secondary button pressed state, small info tags.

### Secondary
- **Polished Brass** (brass): the balance itself, the logo mark, the landing's Create-account button, the slider weight, stamps on the cast weights, the active-tab bar in the bottom nav, icons on the wall, text selection, and the focus ring when focus sits on the wall. About 3.1:1 against the wall, so it is used for graphics and large type there, never for small body text.
- **Deep Brass** (brass-deep): brass that must read on white. The default focus ring (3 px) and the balance's outlines and pan chains. About 5.2:1 on white.

### Tertiary
- **Enamel Red** (danger): the shortfall verdict plate on the landing, "short" results, field errors, error banners, destructive buttons, and the offline status dot. White on it is about 5.4:1.

### Neutral
- **Cast-Iron Ink** (iron / text): all body text, the weights, the slider rail, DEMO stamp ink and border, text on brass (about 8.7:1).
- **Enamel** (enamel): the fits-verdict plate, the selected wall-tone language button, the DEMO stamp ground, the lenders panel on the landing.
- **Wall Wash** (bg): the app background behind cards; the page ground under the owner and lender screens.
- **Plate White** (surface): cards, inputs, status banners, the bottom nav, the lender header.
- **Worn Iron** (muted): hints, secondary lines, inactive nav labels. About 6.8:1 on white.
- **Hairline** (border): card, input and chip edges, list dividers, the bottom nav's top rule.

### Status (functional)
- **Ledger Green** (success), **Deep Ochre** (warning, darkened to about 5.5:1 for AA), **Enamel Red** (danger), **Ink Blue** (info). Used as a banner's border, icon and title colour on a white plate, always with an icon and words.

### Named Rules
**The One Metal Rule.** Brass is the instrument and the one action on the wall. Inside the app, primary actions on white plates are teal, and brass appears only as marks (active tab, focus, logo, stamps), never as a second button colour.

**The Red Means Short Rule.** Enamel red marks a shortfall, an error, or a destructive act. It is never decoration, never a brand accent, and never the only signal: it always comes with a notch mark, an X icon, or words.

**The Mark Before Colour Rule.** State is a mark first: a tick for fits, a notched weight for short, the balance's tilt, an icon in every status banner. Colour reinforces; it never carries meaning alone.

## Typography

**Display Font:** Anek Bangla Variable (with Noto Sans Bengali, Noto Sans)
**Body Font:** Noto Sans Bengali (with Noto Sans, system-ui)

**Character:** Anek, narrowed to 92 % width with slight negative tracking, reads like lettering cast into a bazaar weight; Noto Sans Bengali carries every paragraph and form at a generous 1.6 line height so Bangla conjuncts never collide. Both are self-hosted (@fontsource), weights 400 and 600 only.

### Hierarchy
- **Display** (600, 1.9rem phone / 3rem tablet / 3.75rem desktop, tight leading): the landing tagline only.
- **Headline** (600, 22px, 1.6): screen titles (every h1/h2 is Anek, 92 % width, balanced wrapping), the wordmark, the live loan amount.
- **Title** (600, 18px): card titles, profile name in the header, landing readouts and step titles, the brass button label.
- **Amount** (600, 28px, tabular): the key money figure on a screen.
- **Body** (400, 16px, 1.6): all reading text and inputs; landing sub-copy capped at 52ch.
- **Body Small** (400, 14px): hints, banner detail, secondary lines.
- **Label** (400–600, 13px): nav labels, captions, the DEMO stamp, year tags.

### Named Rules
**The Stamped Heading Rule.** Headings, wordmark, amounts and weight stamps use Anek; anything read as a sentence uses Noto Sans Bengali. Never set a paragraph in Anek.

**The Tabular Money Rule.** Every amount uses tabular numerals, South-Asian grouping (1,50,000) and Bangla digits when the language is bn.

## Layout

Phone first. Owner screens sit in a centred single column, max 480 px, 16 px side gutter, 16 px vertical gap between blocks and 24 px top/bottom padding; a 64 px fixed bottom nav and a sticky teal header frame them. The landing is full-bleed teal: one column on phones (balance at 70 % width, max 480 px, then readouts, slider, verdict, DEMO note, tagline, two stacked actions), two equal columns from the large breakpoint (1024 px) with a 64 px column gap inside a 1152 px container (32 px gutters from 640 px). The lender portal is desktop first in the same 1152 px container. Everything reflows at 320 px; the owner header wraps the DEMO stamp and language switch to a second line at 200 % zoom rather than overflow.

Spacing rhythm is Tailwind's 4 px grid in practice: 8, 12, 16, 24, 40 px, with 48 px as the floor for anything tappable.

## Elevation & Depth

Depth is physical and quiet: enamel plates resting on a wall. Plates carry a short soft drop; objects that sit forward on the wall (the brass button, the verdict plate, the sticky header) carry a slightly longer, darker drop. The balance itself casts a flat ellipse onto a drawn counter edge. Nothing floats far, and nothing uses a hard offset.

### Shadow Vocabulary
- **Plate rest** (`box-shadow: 0 2px 8px -4px rgb(20 32 29 / 0.18)`): cards and status banners.
- **Header lip** (`box-shadow: 0 6px 14px -10px rgb(0 0 0 / 0.6)`): the sticky owner header over content.
- **Verdict plate** (`box-shadow: 0 6px 16px -8px rgb(0 0 0 / 0.45)`): the live fits/short plate on the wall.
- **Brass lift** (`box-shadow: 0 8px 18px -10px rgb(0 0 0 / 0.6)`): the brass action button on the wall.
- **Weight drop** (`box-shadow: 0 4px 10px -4px rgb(0 0 0 / 0.55)`): the brass slider thumb.

### Named Rules
**The Resting Plate Rule.** Shadows are soft, negative-spread and short; they say "this plate rests on the wall", never "this card floats". Inputs, chips and the bottom nav are flat with a hairline.

## Shapes

One corner: gently rounded plates (8 px) for buttons, cards, inputs, banners, the verdict plate and the wall panel behind the result balance. Filter chips and small info tags are full pills. The DEMO stamp is nearly square (2 px) with a 2 px iron border, like a rubber stamp. The balance's own geometry recurs as the brand's silhouette: cast weights with shoulders and a ring handle (used for the landing's step numbers), rounded-top slider weight (6/6/3/3 px), a 6 px iron rail.

## Components

### Buttons
Plain, heavy and unmistakable; label plus optional icon, never icon alone.
- **Shape:** gently rounded (8 px), 48 px minimum height, 16 px side padding, 600 weight.
- **Brass (landing only):** brass fill, iron text, 18px label, 56 px tall, brass-lift shadow; presses down 1 px.
- **Primary (in app):** teal fill, white text; pressed state shadowed wall. Disabled at 60 % opacity; busy disables and sets aria-busy.
- **Secondary:** white with a 1 px teal border and teal text; pressed pale teal.
- **Danger:** enamel red, white text, for destructive acts only.
- **Ghost on wall:** 2 px white/70 border, white text, faint white wash on hover (the landing's Log in).
- **Focus:** global 3 px deep-brass outline at 2 px offset; polished brass when on the wall.

### Chips
- **Style:** full pill, 48 px tall, white with hairline border.
- **State:** selected = pale teal fill, teal border and text, 600 weight; `aria-pressed` carries the state. Used for tabs on the result screen, period and filter choices.

### Cards / Containers
- **Corner Style:** 8 px.
- **Background:** plate white on the wall wash; enamel on the teal wall.
- **Shadow Strategy:** plate rest (see Elevation).
- **Border:** 1 px hairline.
- **Internal Padding:** 16 px (20 px for the landing's lenders panel).

### Inputs / Fields
- **Style:** 48 px tall, white, 1 px hairline, 8 px corners, 12 px side padding, 16 px text; visible label above, hint below (never placeholder-only).
- **Focus:** border turns teal plus a 2 px teal ring.
- **Error:** red border and a red message under the field, linked by aria-describedby.

### Navigation
- **Owner header:** sticky teal wall strip, max 480 px inner; profile name in Anek 18px with a brass profile icon and a wall-mist chevron; DEMO stamp; compact language plates.
- **Owner bottom nav:** fixed white bar, 64 px, five equal columns, icon over 13px label; active = teal 600 text with a 3 px brass bar at the top edge, inactive = worn iron.
- **Lender desk:** white header under a 4 px teal top rule, logo mark, organisation in Anek with the DEMO stamp, nav items as 8 px plates (active pale teal), language plates and a secondary Log out.
- **Language switch:** two 48 px bordered plates. Plate tone: selected pale teal / teal. Wall tone: selected enamel with iron text (and a tick on the large landing variant), unselected transparent with white/50 border.

### Status Banner
- White plate with a coloured 1 px border, a matching status icon, an iron title and muted detail; `role="status"`. Used for the assessment status (always paired with "this is not loan approval"), staleness warnings and page errors.

### DEMO Stamp
- Iron ink on enamel, 2 px iron border, 2 px corners, Anek 13px 600, uppercase in English. Sits directly beside any DEMO number, profile, organisation or news item; reads on the teal wall and on white plates alike.

### The Brass Balance (signature)
- Pure SVG (400 × 272 viewBox) with a three-stop brass gradient (light `#f6dc8e` → brass → `#a87a22`), deep-brass outlines, iron weights stamped with 5 / 2 / 1 in brass (Bangla digits in bn), a ring handle on the top weight, and a flat shadow on a drawn counter edge.
- Tilt = clamp(±14°, (right − left) / heavier × 30). Left pan is the cash, right pan what must be paid; the heavier side goes down, and the weight counts (3 vs 2 or 1, equal sets when level) rank exactly like the tilt.
- Motion: an under-damped spring (stiffness 60, damping 7, rAF) with one small overshoot, then rest; it swings in from a set start angle on mount and snaps straight to rest under reduced motion. This is the app's one authored motion.
- Uses: landing hero (live, driven by the brass slider), assessment result (on a teal wall panel, max 280 px), and the 32 px logo mark (beam, two pans, stand) on the landing and lender desk.

### Brass Slider
- 48 px hit area, 6 px iron rail, a brass weight thumb (34 × 30, rounded top) with an iron border and weight-drop shadow; `aria-valuetext` reads the amount in Taka.

### Verdict Plate
- Live (`aria-live="polite"`) 8 px plate under the slider: fits = enamel with an iron label and a teal tick; short = enamel red with white text and the notched-weight mark.

## Do's and Don'ts

### Do:
- **Do** keep the teal wall as the committed field for the landing, the owner header and the balance panel, and plate white on the wall wash for working screens.
- **Do** use brass for the balance, the logo, the one landing action, the active-tab bar, stamps and focus; use teal for in-app primary buttons on white.
- **Do** pair every state with a mark and words: tick, notched weight, status icon, the balance's tilt.
- **Do** set headings, amounts and stamps in Anek Bangla at 92 % width; set reading text in Noto Sans Bengali 16 / 1.6.
- **Do** keep every tappable target at 48 px or more and every text pair at WCAG AA (body on wall in white or wall mist, never brass).
- **Do** show the DEMO stamp right beside any DEMO number, and keep every honesty label visible.
- **Do** honour reduced motion: the balance snaps to rest and the settle-in collapses to 1 ms.

### Don't:
- **Don't** use enamel red for anything but a shortfall, an error or a destructive act.
- **Don't** use a bazaar tile colour as a page field or for text outside its own tile; no chart library; gradients only as the teal/iron fade that keeps text readable over a photo.
- **Don't** use long soft floating shadows; edges are the 2 px iron line with a hard 2–4 px drop (round 3).
- **Don't** set small text in polished brass on the teal wall (about 3.1:1); use white, wall mist, or deep brass on white.
- **Don't** animate anything beyond the balance's swing, the settle-in, the slow photo drift, the tip fade and short press transitions.

## Round 3 — "the whole bazaar" (17 Nov 2026, owner brief; supersedes conflicting rules above)

- **Logo:** `public/brand/logo-mark.svg` (teal tile, iron edge + hard shadow, brass balance: taka coins left, rice sheaf
  right, beam level). Wordmark in Anek Bangla + letter-spaced "BONIK BONDHU". Poster PNGs beside it.
- **Photos:** real Bangladesh bazaar/field photos (Wikimedia Commons, CC BY / BY-SA, credited on screen and in
  `public/photos/CREDITS.md`). Each app section has one (`SCENES` in `src/components/Frame.tsx`); no photos of children.
- **Frame:** phones keep the 480 px column; ≥1024 px left nav of colour tiles; ≥1280 px right scene panel (photo,
  caption, tips, promise). Guest screens get a photo split screen. Title bands carry the section photo behind a teal fade.
- **Bazaar tiles:** six soft-ground/strong-ink pairs (`--color-tile-*`, all ≥ 5.8:1) — chili, turmeric, leaf, sky,
  plum, teal — only inside icon tiles and the tip card. One tone per section.
- **Edges:** cards, lists, buttons and tiles use `bb-hard-sm` (2 px iron + 2 px hard drop); hero pieces `bb-hard` (4 px).
  Buttons sink into their shadow when pressed.
- **Don't** let a design element suggest approval, a score or a lender offer; the balance shows fit against the owner's own cash, nothing more.
