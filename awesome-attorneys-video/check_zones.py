"""§7.4 — no live text inside the top 14% / bottom 20%, and no text under 30px.

Sweeps the timeline and measures every *visible* text element's real bounding
box. Cutout artwork is exempt (only live text is constrained), so SVG-internal
labels inside the phone/cheque mockups are not measured.
"""
import os
from playwright.sync_api import sync_playwright
from render import boot, H

TOP, BOTTOM, MIN_PX = H * 0.14, H * 0.80, 30.0

JS = r"""(t) => {
  window.__render(t);
  const out = [];
  const sel = '.word, .lbl, #cta1, #cta2, #url, #btn, #disclaimer, #mark';
  for (const el of document.querySelectorAll(sel)) {
    // an element is live only if it and every ancestor are actually visible
    let op = 1, n = el;
    while (n && n !== document.body) {
      op *= parseFloat(getComputedStyle(n).opacity || '1');
      if (getComputedStyle(n).display === 'none') { op = 0; break; }
      n = n.parentElement;
    }
    if (op < 0.05) continue;
    const txt = (el.innerText || '').trim();
    if (!txt) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    out.push({ id: el.id || el.className, txt: txt.slice(0, 28),
               top: r.top, bottom: r.bottom,
               fs: parseFloat(getComputedStyle(el).fontSize) });
  }
  return out;
}"""


def main():
    zone, small = [], []
    with sync_playwright() as pw:
        b, pg = boot(pw)
        for i in range(0, 226):
            t = round(i * 0.1, 2)
            for e in pg.evaluate(JS, t):
                if e["top"] < TOP or e["bottom"] > BOTTOM:
                    zone.append((t, e["txt"], round(e["top"]), round(e["bottom"])))
                if e["fs"] < MIN_PX:
                    small.append((t, e["txt"], e["fs"]))
        b.close()

    def show(name, rows):
        if not rows:
            print(f"{name}: PASS")
            return True
        print(f"{name}: FAIL ({len(rows)} samples)")
        seen = set()
        for r in rows:
            if r[1] in seen:
                continue
            seen.add(r[1]); print("   ", r)
        return False

    ok  = show(f"7.4 text clear of top {TOP:.0f}px / bottom {BOTTOM:.0f}px", zone)
    ok &= show(f"7.4 all text >= {MIN_PX:.0f}px", small)
    print("\nZONE CHECKS PASS" if ok else "\nZONE CHECKS FAILED")


if __name__ == "__main__":
    main()
