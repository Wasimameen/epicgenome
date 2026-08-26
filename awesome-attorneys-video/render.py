"""Render reel.html to frames, then encode a 1080x1920 MP4 with the VO muxed at t=0.

Usage:
  python3 render.py probe        # just the §7 checkpoint frames, into frames/probe/
  python3 render.py              # full render + encode -> the-first-offer.mp4
"""
import os, subprocess, sys, shutil
from playwright.sync_api import sync_playwright
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
FF   = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS, DUR = 1080, 1920, 60, 22.5
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# §7.1 — the accent event must be *starting* at each of these (brief times, and
# the corrected times they moved to).
CHECKS = [0.60, 1.19, 2.40, 3.60, 4.31, 5.61, 6.40, 7.57, 8.40, 9.27,
          10.61, 11.40, 12.20, 12.70, 13.83, 14.60, 15.40, 16.30, 16.49,
          17.32, 18.32, 19.50, 22.30]


def boot(pw):
    b = pw.chromium.launch(executable_path=CHROME,
                           args=["--no-sandbox", "--disable-dev-shm-usage",
                                 "--force-color-profile=srgb",
                                 "--font-render-hinting=none",
                                 "--disable-lcd-text"])
    pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    pg.goto("file://" + os.path.join(HERE, "reel.html"), wait_until="load")
    pg.wait_for_function("window.__ready === true", timeout=60000)
    # strip everything that must not appear in the export
    pg.evaluate("""() => {
        document.querySelectorAll('[data-export-hide]').forEach(e => e.remove());
        const s = document.getElementById('stage');
        s.style.transform = 'none';
        s.style.margin = '0';
        document.body.style.cssText =
            'margin:0;padding:0;overflow:hidden;background:#000';
        document.documentElement.style.cssText = 'margin:0;padding:0;overflow:hidden';
    }""")
    pg.set_viewport_size({"width": W, "height": H})
    return b, pg


def shoot(pg, out, t):
    pg.evaluate("t => window.__render(t)", t)
    pg.screenshot(path=out, clip={"x": 0, "y": 0, "width": W, "height": H})


def probe():
    out = os.path.join(HERE, "frames", "probe")
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    with sync_playwright() as pw:
        b, pg = boot(pw)
        for t in CHECKS:
            shoot(pg, os.path.join(out, f"t{t:06.2f}.png".replace('.', '_', 1)), t)
        b.close()
    print(f"{len(CHECKS)} probe frames -> {out}")


def full():
    out = os.path.join(HERE, "frames", "seq")
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    n = int(round(DUR * FPS))
    with sync_playwright() as pw:
        b, pg = boot(pw)
        for i in range(n):
            shoot(pg, os.path.join(out, f"f{i:05d}.png"), i / FPS)
            if i % 150 == 0:
                print(f"  frame {i}/{n}  t={i/FPS:.2f}s", flush=True)
        b.close()
    print(f"{n} frames rendered")

    mp4 = os.path.join(HERE, "the-first-offer.mp4")
    subprocess.run([
        FF, "-y", "-loglevel", "error",
        "-framerate", str(FPS), "-i", os.path.join(out, "f%05d.png"),
        "-i", os.path.join(HERE, "assets", "voiceover.mp3"),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart",
        "-t", str(DUR),            # video runs 22.5s; audio (20.04s) ends early
        mp4,
    ], check=True)
    print("wrote", mp4, os.path.getsize(mp4), "bytes")


if __name__ == "__main__":
    (probe if len(sys.argv) > 1 and sys.argv[1] == "probe" else full)()
