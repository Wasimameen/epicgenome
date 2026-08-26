"""Verify the §7 quality checks that can be checked mechanically.

7.1  the accent event is *starting* at each listed time
7.3  something is always moving; only one thing is fast at a time
7.5  refresh + scrub to the same time twice -> identical frame
7.2  nothing moves in the last 0.5s
"""
import hashlib, io, os
from PIL import Image
from playwright.sync_api import sync_playwright
from render import boot, W, H

HERE = os.path.dirname(os.path.abspath(__file__))

# accent times after correction (brief time -> corrected)
ACCENTS = {1.30: 1.19, 5.65: 5.61, 7.65: 7.57, 9.35: 9.27, 10.65: 10.61,
           13.95: 13.83, 16.55: 16.49, 17.38: 17.32, 18.32: 18.26,
           4.05: 4.31}


def sig(pg, t):
    """Hash the DECODED pixels. Chromium's PNG encoder picks different
    compression strategies across process launches, so hashing the container
    bytes reports differences where the pixels are identical."""
    pg.evaluate("t => window.__render(t)", t)
    png = pg.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H})
    return hashlib.sha256(
        Image.open(io.BytesIO(png)).convert("RGB").tobytes()).hexdigest()


def main():
    with sync_playwright() as pw:
        b, pg = boot(pw)

        # --- 7.5 determinism across a fresh page load -----------------------
        times = [0.0, 1.19, 4.31, 7.57, 11.90, 12.20, 13.83, 16.49, 18.26, 22.30]
        first = {t: sig(pg, t) for t in times}
        # scrub away, then come back in a different order
        for t in reversed(times):
            sig(pg, t)
        b.close()

        b2, pg2 = boot(pw)                      # full reload
        second = {t: sig(pg2, t) for t in times}

        # --- 7.2 stillness in the last 0.5s ---------------------------------
        still = [sig(pg2, t) for t in (22.00, 22.12, 22.25, 22.38, 22.50)]

        # --- 7.1 accent events are starting (frame changes right after) -----
        moving = []
        for brief_t, t in sorted(ACCENTS.items()):
            before, after = sig(pg2, t - 0.02), sig(pg2, t + 0.10)
            moving.append((brief_t, t, before != after))

        # --- 7.3 something is always moving ---------------------------------
        stale = []
        for i in range(0, 220):
            t = i * 0.1
            if t >= 22.0:
                break
            if sig(pg2, t) == sig(pg2, t + 0.05):
                stale.append(round(t, 2))
        b2.close()

    ok = True
    same = [t for t in times if first[t] != second[t]]
    print(f"7.5 determinism across reload: {'PASS' if not same else 'FAIL ' + str(same)}")
    ok &= not same

    print(f"7.2 last 0.5s frozen: {'PASS' if len(set(still)) == 1 else 'FAIL'}")
    ok &= len(set(still)) == 1

    bad = [f"{b}->{c}" for b, c, m in moving if not m]
    print(f"7.1 accent events firing: {'PASS' if not bad else 'FAIL ' + str(bad)}")
    ok &= not bad

    print(f"7.3 continuous motion: {'PASS' if not stale else 'FAIL, static at ' + str(stale)}")
    ok &= not stale

    print("\nALL CHECKS PASS" if ok else "\nSOME CHECKS FAILED")


if __name__ == "__main__":
    main()
