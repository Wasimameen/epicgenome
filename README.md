# Domain Landing Themes — Animated WordPress Landers

Premium, highly-animated single-page **WordPress themes for domain-sale landing
pages**. A minimal, spacious, modern-dark style (Space Grotesk + Inter Tight, gold
accents on near-black), an on-brand animated **DNA double-helix** hero, a sticky
header with a top contact bar, and restrained motion throughout — all built on the
original markup and a working AJAX offer form.

Each domain gets its own self-contained theme so it can be installed independently.
All themes share the same design and copy; only the **domain name, contact email,
and price** differ.

## Domains in this repo

| Domain | Theme folder | Installable zip | Standalone preview | Buy-now |
|---|---|---|---|---|
| **EPIGENOME.COM** | `epigenome-theme/` | `epigenome-theme.zip` | `preview.html` | $14,888 / $1,241·mo |
| **EPIGENETIC.COM** | `epigenetic-theme/` | `epigenetic-theme.zip` | `epigenetic-preview.html` | $14,888 / $1,241·mo |

## What's in each theme

```
<domain>-theme/         ← the installable WordPress theme
├── style.css           ← theme header (name, version, etc.)
├── functions.php       ← assets, "Offers" CPT, AJAX form handler
├── header.php          ← top contact bar + sticky animated nav
├── footer.php          ← floating "Make an offer" tab + back-to-top
├── index.php           ← the single-page content
└── assets/
    ├── style.css       ← all presentation + animation styling
    └── main.js         ← interactions (helix canvas, count-ups, etc.)
<domain>-preview.html   ← self-contained preview (open directly in a browser)
```

## How to install (per domain)

1. Download the matching `…-theme.zip` (e.g. `epigenetic-theme.zip`).
2. In WordPress: **Appearance → Themes → Add New → Upload Theme**.
3. Choose the zip, **Install**, then **Activate**.
4. Set this template as your front page if needed
   (**Settings → Reading → Your homepage displays**).

Offers submitted through the form are saved under **Offers** in the WP admin and
emailed to the owner address defined in that theme's `functions.php`
(e.g. `EPIGENETIC_OWNER_EMAIL`).

## Adding a new domain

Each theme is a faithful clone with the domain content swapped. To spin up a new
one, copy an existing theme folder and replace every occurrence of the old domain
word (all casings — `EPIGENOME`, `Epigenome`, `epigenome`) with the new one, then
update the contact email and price. The function prefixes, the `Offers` custom
post type slug, the AJAX action/nonce, and the JS wordmark all use that same
prefix, so a clean find-and-replace keeps everything wired correctly.

## Features

**Top contact bar (left & right).** Email + phone sit top-left; a live
"Available now · owner-direct" status with a pulsing dot and a reply-time note
sit top-right. The bar collapses and the nav frosts into a glass bar on scroll.

**Animated, professional motion**
- Animated **DNA double-helix + drifting molecular particles** on a canvas in the hero.
- **Scroll-progress bar**, soft **cursor glow**, and an animated scroll cue.
- **Count-up** animations on the headline prices and the market-size stat.
- **Staggered, directional scroll reveals** for every section.
- **3D tilt + cursor-follow glow** on the pricing and "workaround" cards.
- **Magnetic** call-to-action buttons with a light shine sweep.
- A subtle genomics-term **marquee**, animated nav underlines, and an
  active-section indicator.
- Slide-in **mobile menu**, smooth anchored scrolling, and a back-to-top button.

**Polish & accessibility.** `wp_body_open()`, a skip link, semantic `<main>`,
and full **`prefers-reduced-motion`** support (heavy effects disable cleanly).

## Customising

- **Contact details:** edit the top bar in `header.php` and the contact section
  in `index.php`; owner email in `functions.php`.
- **Colours / fonts:** the CSS custom properties at the top of
  `assets/style.css` (`--gold`, `--bg`, `--ink`, …).
- **Animation intensity:** helix/particle density and tilt strength live in
  `assets/main.js`; reduce or disable any effect there.
