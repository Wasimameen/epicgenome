# EPIGENOME.COM — Animated Landing Theme

A premium, highly-animated WordPress theme for the single-page **EPIGENOME.COM**
domain-sale landing page. Dark editorial-luxury styling (Fraunces + Inter Tight,
gold-on-near-black), an on-brand animated **DNA double-helix** hero, a sticky
header with a top contact bar, and motion throughout — all built on the original
markup and the working AJAX offer form.

## What's in this repo

```
epigenome-theme/        ← the installable WordPress theme
├── style.css           ← theme header (name, version, etc.)
├── functions.php       ← assets, "Offers" CPT, AJAX form handler
├── header.php          ← top contact bar + sticky animated nav
├── footer.php          ← floating "Make an offer" tab + back-to-top
├── index.php           ← the single-page content
└── assets/
    ├── style.css       ← all presentation + animation styling
    └── main.js         ← interactions (helix canvas, count-ups, etc.)
preview.html            ← self-contained preview (open directly in a browser)
```

## How to install

1. Download **`epigenome-theme.zip`**.
2. In WordPress: **Appearance → Themes → Add New → Upload Theme**.
3. Choose the zip, **Install**, then **Activate**.
4. Set this template as your front page if needed
   (**Settings → Reading → Your homepage displays**).

Offers submitted through the form are saved under **Offers** in the WP admin and
emailed to the owner address defined in `functions.php`
(`EPIGENOME_OWNER_EMAIL`).

## What's new vs. the original

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

All original copy, the Offers custom post type, and the AJAX form behaviour are
preserved unchanged.

## Customising

- **Contact details:** edit the top bar in `header.php` and the contact section
  in `index.php`; owner email in `functions.php`.
- **Colours / fonts:** the CSS custom properties at the top of
  `assets/style.css` (`--gold`, `--bg`, `--ink`, …).
- **Animation intensity:** helix/particle density and tilt strength live in
  `assets/main.js`; reduce or disable any effect there.
