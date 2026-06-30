# Counsel — WordPress Theme

**Counsel** is a classic (PHP) WordPress theme for an independent legal-directory
and legal-marketing publication — *"Forbes meets Zillow meets LinkedIn for the
legal industry."* It is built to look credible, calm, and editorial: a serious
publication, not a lead-gen listing site or a flashy law-firm template. **Trust
is the product**, so disclosure (the Sponsored label and the legal disclaimers)
is treated as a first-class design element.

- **Type:** Classic PHP theme (not a block theme).
- **No required plugins.** Everything works on a clean WordPress install.
- **Version:** 1.0.0 · **License:** GPL-2.0-or-later · **Text Domain:** `counsel`

---

## 1. What's in the box

| Area | Highlights |
| --- | --- |
| **Firm Profiles** | `firm` custom post type with URLs at `/attorneys/…`, native meta boxes for all firm fields, a 10-section editorial profile layout. |
| **Taxonomies** | `practice_area` and `city` (both hierarchical), seeded with starter terms on activation. |
| **Directory** | `/attorneys/` archive with a search form, filter rail (practice area, city, firm size), and responsive firm cards. |
| **Editorial** | Ask Counsel advice columns, Best Of roundups (with mandatory methodology box), evergreen Guides. |
| **Disclosure** | Centralized legal strings, a reusable Sponsored badge, and disclaimers wired into every relevant template. |
| **Design** | Editorial-prestige aesthetic — Fraunces + Inter, oxblood/brass on warm paper, hairline rules, generous whitespace, fully responsive and accessible. |

---

## 2. Install

**Option A — Zip upload (recommended)**
1. Zip the `counsel/` folder so the archive contains `counsel/style.css` at its top level.
2. In WordPress: **Appearance → Themes → Add New → Upload Theme**.
3. Choose the zip, **Install**, then **Activate**.

**Option B — Copy**
1. Copy the entire `counsel/` folder into `wp-content/themes/`.
2. **Appearance → Themes → Activate "Counsel."**

On activation the theme automatically:
- Registers the `firm` post type and the `practice_area` / `city` taxonomies.
- Seeds the ten practice areas (Personal Injury, Car Accidents, Criminal Defense
  & DUI, Family & Divorce, Bankruptcy, Immigration, Employment, Estate Planning,
  Business & Contracts, Real Estate) and the flagship city (**Phoenix, AZ**).
- Flushes rewrite rules so `/attorneys/…` URLs work immediately.

> If firm URLs ever 404 after moving the site, go to **Settings → Permalinks**
> and click **Save** once to flush the rules again.

---

## 3. Set the static front page

The home layout lives in `front-page.php` and renders automatically. To also
give it editor-managed intro copy:

1. Create a Page (e.g. "Home").
2. **Settings → Reading → Your homepage displays → A static page → Homepage =
   Home.** (Optionally set "Posts page" to a "Blog/News" page.)
3. Anything you type into the Home page's editor appears between the hero and the
   "three lanes" section. Leave it empty to skip that band.

---

## 4. Create your first Firm Profile

1. **Firm Profiles → Add New.**
2. **Title** = the firm name. **Featured image** = the profile/hero photo.
3. Fill in the **Firm Details** meta box:
   - `Best for` — the one-liner shown on cards and at the top of the profile.
   - `Year founded`, `Firm size`, `Languages`, `Consultation`, `Fee structure`,
     `Phone`, `Website` — these build the **At a glance** fact box and the
     contact card.
   - `Notable results` — one per line; the *"Past results do not guarantee future
     outcomes"* disclaimer is appended automatically.
   - `Sources` — one per line; URLs become links.
   - **This firm is a sponsor** — check to show the **Sponsored** label on the
     firm's card and profile. *Disclosure is required — never hide it.*
4. Assign **Practice Areas** and a **City** (right-hand panels).
5. Write the editorial body (Origins, Size/reach/team, What clients say,
   Community & presence, FAQs, etc.) using `H2` headings — they're styled within
   the reading measure. The fact box, results, sources, and disclaimers render
   around your content.
6. **Optional:** add a custom field `firm_roundup_url` to link the profile's
   *"How they compare"* section up to the matching Best Of roundup.

### How the Sponsored toggle works
The single checkbox `firm_is_sponsored` drives everything: it adds the badge to
the card (`template-parts/card-firm.php`), the badge near the profile title
(`single-firm.php`), and a `is-sponsored-firm` body class. Sponsored firms are
also visually flagged with a brass top-rule on their card.

---

## 5. Build the menus

**Appearance → Menus.** Two locations are registered:

- **Primary (Header)** — suggested: Find a Lawyer (`/attorneys/`), How It Works,
  About, Ask Counsel (`/advice/`), Guides (`/guides/`), **For Attorneys**.
  Give the "For Attorneys" menu item the CSS class `menu-item--attorneys` (enable
  *Screen Options → CSS Classes*) to get its distinguished advertiser styling.
- **Footer** — About, How It Works, For Attorneys, Contact, and legal pages.

If you don't build menus yet, the header and footer fall back to sensible default
links so nothing looks empty.

---

## 6. Recommended pages & how they map to templates

| Page | Template to assign (Page Attributes → Template) |
| --- | --- |
| Home | *(static front page; uses `front-page.php` automatically)* |
| How It Works | **How It Works** |
| For Attorneys | **For Attorneys** |
| Contact | **Contact** |
| About / legal pages | *(default — `page.php`)* |
| A "Best [area] lawyers in [city]" roundup | **Best Of Roundup** |

**Ask Counsel** and **Guides** are standard posts. Create two categories,
`advice` (for Ask Counsel) and `guides`, and the theme will:
- style advice posts with the composite-question treatment and append the
  composite editor's note + "not legal advice" disclaimer (`single.php`);
- give `/advice/` and `/guides/` category pages a card-grid landing
  (`category.php`).

### Authoring an Ask Counsel column
Use core blocks in this order: a **Quote** block for the composite question →
short answer paragraph → **ordered list** ("What to do now") → "What good looks
like" / "What to look for next time" sections → a short FAQ. The standing
disclaimers are added automatically.

### Best Of roundups
The **Best Of Roundup** template renders a magazine headline, a **mandatory
methodology box** near the top, your curated list (author it in the editor; link
each entry to a firm profile), a "how to choose" closing section, and the roundup
disclaimer. Optional custom fields: `counsel_subtitle`, `counsel_methodology`.
**These pages must never be sold or used as pay-to-rank** — this is stated in the
template's code comments.

---

## 7. Customizer (non-developer settings)

**Appearance → Customize → Counsel Settings:**
- General contact email · Attorney-inquiry email · Contact phone
- Social links (LinkedIn, X, Facebook, Instagram)
- Footer disclaimer text (leave blank for the default) + a toggle to show/hide it

The **For Attorneys** "check availability" form emails the *attorney-inquiry
email*; the **Contact** page routes consumers to the general email and attorneys
to the For Attorneys page.

---

## 8. Custom fields & ACF

Firm fields are stored as plain post meta (no leading underscore) so they're
editable via the native **Firm Details** meta box *and* visible to ACF or the
Custom Fields panel. If your team prefers ACF, map fields to the same keys
(`firm_founded`, `firm_size`, `firm_languages`, `firm_consultation`, `firm_fees`,
`firm_phone`, `firm_website`, `firm_best_for`, `firm_is_sponsored`,
`firm_results`, `firm_sources`). To hide the native boxes when ACF owns the
fields, define `COUNSEL_DISABLE_NATIVE_META` as `true` (e.g. in `wp-config.php`).

---

## 9. Design notes & decisions

- **Brand tokens** are implemented exactly as specified as CSS custom properties
  in `:root` (top of `assets/css/main.css`) and mirrored to the block editor
  palette and `editor-style.css`.
- **Fonts:** Fraunces (display/headings) + Inter (body/UI), loaded from Google
  Fonts with `display=swap` and `preconnect` hints. *To switch to the
  Georgia/Calibri "article side" of the brand system, change `--font-serif` /
  `--font-sans` in `:root` — nothing else needs to change.*
- **Type scale** is a fluid 1.25 modular scale (`clamp()`), ~18px base body,
  line-height 1.7, long-form capped at `--measure` (68ch).
- **Accessibility:** semantic HTML5 landmarks, a skip-to-content link, visible
  `:focus-visible` states, keyboard-navigable menus (with submenu toggles),
  `prefers-reduced-motion` support, and screen-reader text utilities.
- **Performance:** vanilla JS only (no jQuery added), assets cache-busted with
  `filemtime()`, images lazy-loaded, fonts non-render-blocking.
- **SEO:** one `H1` per page, clean `title-tag`, breadcrumbs on firm profiles and
  archives. Built-in Organization/`LegalService` microdata is **off by default**
  to avoid clashing with an SEO plugin; opt in with
  `add_filter( 'counsel_enable_microdata', '__return_true' );`.
- **Editorial ordering:** the directory shows 12 firms per page and respects the
  search form's query args (`practice_area`, `city`, `firm_size`).

---

## 10. File map

```
counsel/
├── style.css                       Theme header (CSS lives in assets/css/main.css)
├── functions.php                   Setup, enqueue, menus, image sizes, query filter, inquiry form, activation seeding
├── index.php                       Fallback loop
├── header.php · footer.php         Header (skip link, nav, wordmark) + footer (columns, disclaimers)
├── front-page.php                  Home (hero search, three lanes, trust row, practice grid, CTA)
├── page.php · single.php           Default page + single (advice/guides) templates
├── single-firm.php                 Firm profile — 10-section editorial layout
├── archive.php · archive-firm.php  Generic archive + the directory
├── taxonomy-practice_area.php      Firms by practice area
├── taxonomy-city.php               Firms by city
├── category.php                    Ask Counsel / Guides landings
├── search.php · 404.php            Search results + friendly not-found
├── searchform.php                  Practice-area + city search form
├── comments.php · sidebar.php      Minimal comments (off on firms) + optional sidebar
├── inc/
│   ├── post-types.php              register 'firm'
│   ├── taxonomies.php              register + seed 'practice_area' and 'city'
│   ├── meta-boxes.php              native firm meta boxes + register_post_meta
│   ├── template-tags.php           counsel_sponsored_badge(), counsel_fact_box(), breadcrumbs, etc.
│   ├── customizer.php              "Counsel Settings"
│   └── disclaimers.php             central legal strings
├── template-parts/
│   ├── hero-search.php · section-three-lanes.php
│   ├── card-firm.php · directory-filters.php
│   ├── methodology-box.php · disclaimer-block.php · content-none.php
├── assets/
│   ├── css/main.css · css/editor-style.css
│   ├── js/main.js
│   └── img/wordmark.svg · img/favicon.svg
└── page-templates/
    ├── template-for-attorneys.php
    ├── template-how-it-works.php
    ├── template-contact.php
    └── template-best-of.php
```

---

## 11. Things deliberately left as starting points / stubs

- **Legal strings are starting points, not legal sign-off.** Before launch, the
  disclaimers and any sponsored labeling still need a compliance review.
- **The attorney-inquiry form** is intentionally minimal: it validates, applies a
  honeypot, and emails the inquiry address via `wp_mail()`. It does not persist
  submissions to the database — add a forms plugin if you need a record/CRM.
- **Microdata / schema** is filter-gated and off by default; pair the site with
  an SEO plugin for full JSON-LD.
- **The wordmark** is a simple placeholder SVG (`COUNSEL` set in a serif,
  oxblood) with a text fallback. Replace it with final brand artwork or upload a
  **Custom Logo** under **Appearance → Customize → Site Identity**.

---

## 12. Adding content

The theme provides structure and styling; your separate *Counsel — Website
Content* document provides the words. After activating, paste that copy into the
matching pages/posts described in §5–§6.
