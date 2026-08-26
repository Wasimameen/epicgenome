"""Parse the fetched awesomeattorneys.com HTML for §2 brand data.

Chromium is blocked by this environment's egress policy (ERR_CONNECTION_RESET on
every navigation), so brand capture is done from the raw HTML + inline CSS that
curl retrieves successfully.
"""
import json, os, re, html as htmllib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "site.html")
OUT = os.path.join(HERE, "brand_capture.json")

doc = open(SRC, encoding="utf-8", errors="replace").read()
out = {"source": "https://awesomeattorneys.com/", "method": "curl + HTML/CSS parse"}

# ---- meta ---------------------------------------------------------------
def meta(pat):
    m = re.search(pat, doc, re.I)
    return htmllib.unescape(m.group(1)).strip() if m else None

out["themeColor"] = meta(r'<meta[^>]+name=["\']theme-color["\'][^>]+content=["\']([^"\']+)')
out["title"] = meta(r"<title[^>]*>(.*?)</title>")
out["description"] = meta(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)')
out["ogImage"] = meta(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)')
out["ogTitle"] = meta(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)')

# ---- inline <style> blocks ---------------------------------------------
styles = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", doc, re.S | re.I))
out["inlineCssBytes"] = len(styles)

# ---- CSS custom properties ---------------------------------------------
props = {}
for name, val in re.findall(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+)[;}]", styles):
    v = val.strip()
    if len(v) < 120:
        props.setdefault(name, v)
out["cssVars"] = props
out["colorVars"] = {k: v for k, v in props.items()
                    if re.search(r"#[0-9a-f]{3,8}\b|rgba?\(", v, re.I)}

# ---- colour census, excluding known social-share brand colours ----------
SOCIAL = {
    "#5865f2", "#3499cd", "#4680c2", "#e94c89", "#ea4434", "#e60122", "#f00075",
    "#ff5600", "#ff4500", "#f6405f", "#f45800", "#ef4155", "#e65678", "#e8d833",
    "#e21b24", "#d32422", "#6440a4", "#6c6c89", "#4280ff", "#3288d4", "#382110",
    "#826235", "#f0f0f0",
}
hexes = Counter(h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", doc))
out["allHexCounts"] = dict(hexes.most_common(40))
out["brandCandidates"] = {h: c for h, c in hexes.most_common(40) if h not in SOCIAL}

# ---- fonts --------------------------------------------------------------
fams = Counter()
for f in re.findall(r"font-family\s*:\s*([^;{}]+)", styles, re.I):
    fams[re.sub(r"\s+", " ", f).strip().strip('"\'')] += 1
out["fontFamilies"] = [{"value": k, "count": v} for k, v in fams.most_common(12)]
out["googleFonts"] = sorted(set(re.findall(
    r"fonts\.googleapis\.com/css2?\?([^\"'\s>]+)", doc)))
out["fontFaceNames"] = sorted(set(re.findall(
    r"@font-face\s*{[^}]*?font-family\s*:\s*[\"']?([^;\"'}]+)", styles, re.I)))

# ---- logo / wordmark ----------------------------------------------------
imgs = re.findall(r"<img[^>]+>", doc, re.I)
logos = []
for tag in imgs:
    src = re.search(r'src=["\']([^"\']+)', tag)
    if not src:
        continue
    u = src.group(1)
    if re.search(r"logo|wordmark|brand|mark", u, re.I) or \
       re.search(r'class=["\'][^"\']*logo', tag, re.I):
        alt = re.search(r'alt=["\']([^"\']*)', tag)
        logos.append({"src": u, "alt": alt.group(1) if alt else None})
out["logoCandidates"] = logos[:12]

# inline SVG logos
out["inlineSvgLogos"] = [s[:600] for s in re.findall(
    r"<svg[^>]*(?:logo|brand)[^>]*>.*?</svg>", doc, re.S | re.I)][:4]

# ---- CTA ----------------------------------------------------------------
ctas = []
for tag in re.findall(r"<a\b[^>]*>.*?</a>|<button\b[^>]*>.*?</button>", doc, re.S | re.I):
    text = re.sub(r"<[^>]+>", " ", tag)
    text = re.sub(r"\s+", " ", htmllib.unescape(text)).strip()
    if re.fullmatch(r"(get matched|get paid|find a lawyer|get started)", text, re.I):
        href = re.search(r'href=["\']([^"\']+)', tag)
        cls = re.search(r'class=["\']([^"\']+)', tag)
        style = re.search(r'style=["\']([^"\']+)', tag)
        ctas.append({"text": text,
                     "href": href.group(1) if href else None,
                     "class": cls.group(1) if cls else None,
                     "style": style.group(1) if style else None})
seen, uniq = set(), []
for c in ctas:
    k = (c["text"].lower(), c["class"])
    if k not in seen:
        seen.add(k); uniq.append(c)
out["ctas"] = uniq[:10]

# ---- copy ---------------------------------------------------------------
text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", doc, flags=re.S | re.I)
text = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", text)))
m = re.search(r"[^.]*not a law firm[^.]*\.", text, re.I)
out["disclaimer"] = m.group(0).strip() if m else None
m = re.search(r"[^.|]*independent attorney guide[^.|]*", text, re.I)
out["tagline"] = m.group(0).strip() if m else None
out["headings"] = [re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", h))).strip()
                   for h in re.findall(r"<h1[^>]*>(.*?)</h1>|<h2[^>]*>(.*?)</h2>",
                                       doc, re.S | re.I)[:0]]
out["headings"] = [re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", m0 or m1))).strip()
                   for m0, m1 in re.findall(r"<h1[^>]*>(.*?)</h1>|<h2[^>]*>(.*?)</h2>",
                                            doc, re.S | re.I)][:12]
out["socialHandles"] = sorted(set(re.findall(r"@[Aa]wesome[Aa]tty?s?\b", doc)))

json.dump(out, open(OUT, "w"), indent=2)

print(json.dumps({k: out[k] for k in (
    "themeColor", "title", "tagline", "disclaimer", "brandCandidates",
    "colorVars", "fontFamilies", "googleFonts", "fontFaceNames",
    "logoCandidates", "ctas", "headings", "socialHandles", "ogImage")}, indent=2)[:6000])
