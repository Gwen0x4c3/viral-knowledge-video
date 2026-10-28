"""Rendering primitives: image loading, cover/framed layouts, colour grades, film finish,
text sprites, alpha compositing, procedural backgrounds. Pure functions on RGB uint8 numpy arrays (H, W, 3)."""
import os, subprocess, functools
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import config
from config import W, H, FONTS

config.check_fonts()
F_HEAVY = FONTS["heavy"]; F_SONG = FONTS["serif"]; F_ROCK = FONTS["slab"]; F_IMPACT = FONTS["impact"]; F_SYMBOL = FONTS["symbol"]

YELLOW = (255, 214, 0); RED = (255, 59, 48); WHITE = (255, 255, 255); BLACK = (0, 0, 0)
PAPER = (236, 218, 178); INK = (60, 36, 20); ORANGE = (255, 140, 30)

# ---------------- easing ----------------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_in(x): x = clamp(x); return x ** 3
def ease_io(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def back_out(x, s=1.7):
    x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1
def elastic(x):
    x = clamp(x)
    if x in (0, 1): return x
    return 2 ** (-10 * x) * np.sin((x * 10 - 0.75) * (2 * np.pi / 3)) + 1
def lerp(a, b, t): return a + (b - a) * t

# ---------------- image loading ----------------
@functools.lru_cache(maxsize=64)
def load_img(name, maxdim=2400):
    p = config.raw("img", name + ".jpg")
    if not os.path.exists(p): p = config.raw("img", name)
    im = cv2.imread(p, cv2.IMREAD_COLOR)
    if im is None: raise FileNotFoundError(f"image not found or unreadable: raw/img/{name}.jpg")
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    h, w = im.shape[:2]
    s = min(1.0, maxdim / max(h, w))
    if s < 1: im = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return im

_clip_cache = {}
def load_clip(src, t0, dur, maxh=1080):
    """Decode a segment of a source video into a list of RGB frames + fps."""
    key = (src, round(t0, 3), round(dur, 3))
    if key in _clip_cache: return _clip_cache[key]
    path = next((config.raw(src + e) for e in (".webm", ".mp4", ".mov", ".mkv", "") if os.path.exists(config.raw(src + e))), None)
    if path is None: raise FileNotFoundError(f"video not found: raw/{src}.webm|.mp4")
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                            "stream=width,height,r_frame_rate", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
    w, h = int(probe[0]), int(probe[1]); n, d = probe[2].split("/"); fps = float(n) / float(d)
    if h > maxh: w, h = int(w * maxh / h) // 2 * 2, maxh
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", path, "-t", f"{dur + 0.2:.3f}",
           "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    frames = np.frombuffer(raw, np.uint8)
    nf = len(frames) // (w * h * 3)
    frames = frames[: nf * w * h * 3].reshape(nf, h, w, 3)
    if len(_clip_cache) > 6: _clip_cache.pop(next(iter(_clip_cache)))
    _clip_cache[key] = (frames, fps)
    return frames, fps

# ---------------- geometry ----------------
def cover(img, zoom=1.0, cx=0.5, cy=0.5, rot=0.0, ow=W, oh=H, shift=(0, 0)):
    """Fill an ow x oh canvas with img, zoomed around focus (cx, cy) in [0,1] image coords."""
    h, w = img.shape[:2]
    s = max(ow / w, oh / h) * zoom
    # keep focus point inside such that no border shows
    vw, vh = ow / s, oh / s
    fx = clamp(cx * w, vw / 2, w - vw / 2) if vw < w else w / 2
    fy = clamp(cy * h, vh / 2, h - vh / 2) if vh < h else h / 2
    M = cv2.getRotationMatrix2D((fx, fy), rot, s)
    M[0, 2] += ow / 2 - fx + shift[0]; M[1, 2] += oh / 2 - fy + shift[1]
    interp = cv2.INTER_AREA if s < 0.7 else cv2.INTER_LINEAR
    return cv2.warpAffine(img, M, (ow, oh), flags=interp, borderMode=cv2.BORDER_REFLECT)

def fit(img, ow, oh):
    h, w = img.shape[:2]; s = min(ow / w, oh / h)
    return cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)

def blur_bg(img, dark=0.45):
    small = cover(img, 1.0, ow=W // 8, oh=H // 8)
    small = cv2.GaussianBlur(small, (0, 0), 6)
    big = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
    return (big.astype(np.float32) * dark).astype(np.uint8)

def framed(img, zoom=1.0, cx=0.5, cy=0.5, y=820, fw=1080, fh=None, bg=None, border=0):
    """Blurred-background layout with the image fit to width in the middle band."""
    h, w = img.shape[:2]
    fh = fh or int(fw * h / w)
    canvas = blur_bg(img) if bg is None else bg.copy()
    inner = cover(img, zoom, cx, cy, ow=fw, oh=fh)
    y0 = int(y - fh / 2); x0 = (W - fw) // 2
    if border:
        cv2.rectangle(canvas, (x0 - border, y0 - border), (x0 + fw + border - 1, y0 + fh + border - 1), (245, 235, 210), -1)
    ys, ye = max(0, y0), min(H, y0 + fh)
    canvas[ys:ye, x0:x0 + fw] = inner[ys - y0: ye - y0]
    return canvas

# ---------------- grading ----------------
def _lut(curve): return np.clip(np.array([curve(i / 255.0) for i in range(256)]) * 255, 0, 255).astype(np.uint8)
def _sc(x, k=1.15): return clamp(0.5 + (x - 0.5) * k, 0, 1)
LUTS = {
    "film":  [_lut(lambda x: _sc(x, 1.2) ** 0.95 * 1.04), _lut(lambda x: _sc(x, 1.2) * 0.97), _lut(lambda x: _sc(x, 1.2) ** 1.1 * 0.82)],
    "color": [_lut(lambda x: _sc(x, 1.12) ** 0.95 * 1.05), _lut(lambda x: _sc(x, 1.1)), _lut(lambda x: _sc(x, 1.1) ** 1.05 * 0.9)],
    "gold":  [_lut(lambda x: _sc(x, 1.15) ** 0.85 * 1.08), _lut(lambda x: _sc(x, 1.1) ** 0.95 * 0.92), _lut(lambda x: _sc(x, 1.1) ** 1.3 * 0.6)],
    "night": [_lut(lambda x: _sc(x, 1.1) ** 1.4 * 0.45), _lut(lambda x: _sc(x, 1.1) ** 1.2 * 0.62), _lut(lambda x: _sc(x, 1.1) ** 0.95 * 0.95)],
    "cold":  [_lut(lambda x: _sc(x, 1.05) * 0.82 + 0.06), _lut(lambda x: _sc(x, 1.05) * 0.9 + 0.06), _lut(lambda x: _sc(x, 1.05) * 0.98 + 0.08)],
    "red":   [_lut(lambda x: _sc(x, 1.3) * 1.1), _lut(lambda x: _sc(x, 1.3) * 0.35), _lut(lambda x: _sc(x, 1.3) * 0.3)],
    "none": None,
}
def grade(img, tone="film", desat=0.0):
    if tone == "film" or desat > 0:
        g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        g3 = np.repeat(g[:, :, None], 3, 2)
        if tone == "film": img = g3
        else: img = cv2.addWeighted(img, 1 - desat, g3, desat, 0)
    L = LUTS.get(tone)
    if L is None: return img
    out = np.empty_like(img)
    for c in range(3): out[:, :, c] = cv2.LUT(img[:, :, c], L[c])
    return out

_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.6)) ** 2)
VIGNETTE = np.clip(1.15 - 0.55 * _r ** 2.2, 0.25, 1.0).astype(np.float32)[:, :, None]
_grng = np.random.default_rng(1)
GRAIN = [cv2.resize(_grng.normal(0, 1, (H // 3, W // 3)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR) for _ in range(6)]

def finish(img, fi, vignette=1.0, grain=7.0, scratches=False):
    f = img.astype(np.float32)
    if vignette: f *= (1 - vignette) + vignette * VIGNETTE
    if grain: f += GRAIN[fi % 6][:, :, None] * grain
    if scratches:
        r = np.random.default_rng(fi)
        for _ in range(r.integers(0, 3)):
            x = int(r.uniform(0, W)); f[:, x:x + 2] += r.uniform(30, 70)
        if r.uniform() < 0.25:
            x, y = int(r.uniform(0, W)), int(r.uniform(0, H)); cv2.circle(f, (x, y), int(r.uniform(2, 6)), (0, 0, 0), -1)
        f *= r.uniform(0.95, 1.03)  # flicker
    return np.clip(f, 0, 255).astype(np.uint8)

# ---------------- text ----------------
@functools.lru_cache(maxsize=4096)
def font(spec, size): return ImageFont.truetype(spec[0], size, index=spec[1])

@functools.lru_cache(maxsize=16)
def _cmap(fspec):
    """Set of codepoints the font can draw (empty set = unknown -> assume it covers everything)."""
    try:
        from fontTools.ttLib import TTFont
        tt = TTFont(fspec[0], fontNumber=fspec[1], lazy=True) if fspec[0].lower().endswith(".ttc") else TTFont(fspec[0], lazy=True)
        return frozenset(tt.getBestCmap().keys())
    except Exception:
        return frozenset()

_WARNED = set()
def covers(fspec, text):
    cm = _cmap(fspec)
    return not cm or all(ord(ch) in cm or ch.isspace() for ch in text)

def safe_font(fspec, text):
    """Return a font that can draw every character of `text`. Latin display fonts (Impact, Rockwell) have no
    Chinese glyphs and silently draw □ — this falls back to the CJK heavy font (then the symbol font) and warns once."""
    if covers(fspec, text): return fspec
    for alt in (F_HEAVY, F_SYMBOL):
        if covers(alt, text):
            if (fspec, text) not in _WARNED:
                _WARNED.add((fspec, text)); print(f"[vidkit] font {os.path.basename(fspec[0])} lacks glyphs in '{text}' -> using {os.path.basename(alt[0])}")
            return alt
    missing = "".join(ch for ch in text if not ch.isspace() and ord(ch) not in _cmap(F_HEAVY))
    if ("missing", text) not in _WARNED:
        _WARNED.add(("missing", text)); print(f"[vidkit] WARNING no font can draw {missing!r} in '{text}' — it will render as □. Rephrase or draw it.")
    return fspec

@functools.lru_cache(maxsize=2048)
def text_sprite(text, size, fill=WHITE, stroke=10, stroke_fill=BLACK, fspec=F_HEAVY, shadow=True, pad=None, spacing=0):
    fspec = safe_font(fspec, text)
    f = font(fspec, size)
    pad = pad if pad is not None else stroke + 20
    # measure
    if spacing:
        widths = [f.getbbox(ch, stroke_width=stroke)[2] - f.getbbox(ch, stroke_width=stroke)[0] for ch in text]
        tw = sum(widths) + spacing * (len(text) - 1)
    else:
        bb = f.getbbox(text, stroke_width=stroke); tw = bb[2] - bb[0]
    asc, desc = f.getmetrics()
    th = asc + desc + 2 * stroke
    im = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def draw_at(dx, dy, col, sf):
        if spacing:
            x = pad + dx
            for ch, cw in zip(text, widths):
                d.text((x - f.getbbox(ch, stroke_width=stroke)[0], pad + stroke + dy), ch, font=f, fill=col, stroke_width=stroke, stroke_fill=sf)
                x += cw + spacing
        else:
            d.text((pad - bb[0] + dx, pad + stroke + dy), text, font=f, fill=col, stroke_width=stroke, stroke_fill=sf)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
        d0 = d; d = ds; draw_at(6, 8, (0, 0, 0, 170), (0, 0, 0, 170)); d = d0
        sh = sh.filter(ImageFilter.GaussianBlur(6)); im = Image.alpha_composite(im, sh)
        d = ImageDraw.Draw(im)
    draw_at(0, 0, fill, stroke_fill)
    return np.array(im)

def rgba_from_pil(im): return np.array(im.convert("RGBA"))

def blit(frame, spr, cx, cy, scale=1.0, rot=0.0, alpha=1.0, anchor="c"):
    """Alpha-composite an RGBA sprite onto frame (in place) centred at (cx, cy)."""
    if alpha <= 0.01 or scale <= 0.01: return frame
    h, w = spr.shape[:2]
    if abs(scale - 1) > 1e-3 or abs(rot) > 1e-3:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)
        cos, sin = abs(M[0, 0]), abs(M[0, 1])
        nw, nh = int(h * sin + w * cos) + 2, int(h * cos + w * sin) + 2
        M[0, 2] += nw / 2 - w / 2; M[1, 2] += nh / 2 - h / 2
        spr = cv2.warpAffine(spr, M, (nw, nh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        h, w = nh, nw
    if anchor == "l": x0 = int(cx); y0 = int(cy - h / 2)
    else: x0 = int(cx - w / 2); y0 = int(cy - h / 2)
    fx0, fy0 = max(0, x0), max(0, y0); fx1, fy1 = min(frame.shape[1], x0 + w), min(frame.shape[0], y0 + h)
    if fx1 <= fx0 or fy1 <= fy0: return frame
    s = spr[fy0 - y0: fy1 - y0, fx0 - x0: fx1 - x0]
    a = s[:, :, 3:4].astype(np.float32) * (alpha / 255.0)
    roi = frame[fy0:fy1, fx0:fx1].astype(np.float32)
    frame[fy0:fy1, fx0:fx1] = (roi * (1 - a) + s[:, :, :3].astype(np.float32) * a).astype(np.uint8)
    return frame

def blit_rgb(frame, img, x0, y0, alpha=1.0):
    h, w = img.shape[:2]
    fx0, fy0 = max(0, x0), max(0, y0); fx1, fy1 = min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0: return
    s = img[fy0 - y0: fy1 - y0, fx0 - x0: fx1 - x0]
    if alpha >= 0.999: frame[fy0:fy1, fx0:fx1] = s
    else: frame[fy0:fy1, fx0:fx1] = cv2.addWeighted(frame[fy0:fy1, fx0:fx1], 1 - alpha, s, alpha, 0)

def rounded_rect(w, h, r, fill, outline=None, width=0):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill, outline=outline, width=width)
    return np.array(im)

def label_box(text, size=46, fg=BLACK, bg=YELLOW, padx=26, pady=14, fspec=F_HEAVY, r=12):
    fspec = safe_font(fspec, text); f = font(fspec, size); bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], size
    im = Image.new("RGBA", (tw + 2 * padx, th + 2 * pady + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), r, fill=bg)
    d.text((padx - bb[0], pady - bb[1] + 4), text, font=f, fill=fg)
    return np.array(im)

# ---------------- frame effects ----------------
def rgb_split(img, amt):
    if amt < 1: return img
    out = img.copy(); a = int(amt)
    out[:, a:, 0] = img[:, :-a, 0]; out[:, :-a, 2] = img[:, a:, 2]
    return out

def motion_blur(img, amt, horizontal=True):
    k = int(amt) | 1
    if k < 3: return img
    return cv2.blur(img, (k, 1) if horizontal else (1, k))

def zoom_frame(img, z, shift=(0, 0)):
    if abs(z - 1) < 1e-3 and shift == (0, 0): return img
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z); M[0, 2] += shift[0]; M[1, 2] += shift[1]
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def darken(img, k): return (img.astype(np.float32) * k).astype(np.uint8)

def paper_bg(seed=0, tone=(196, 160, 110)):
    r = np.random.default_rng(seed)
    n = cv2.resize(r.normal(0, 1, (H // 24, W // 24)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    n2 = cv2.resize(r.normal(0, 1, (H // 4, W // 4)).astype(np.float32), (W, H))
    base = np.array(tone, np.float32)[None, None, :] * (1 + 0.08 * n[:, :, None] + 0.04 * n2[:, :, None])
    base *= VIGNETTE ** 1.3
    return np.clip(base, 0, 255).astype(np.uint8)

def wood_bg(seed=0):
    r = np.random.default_rng(seed)
    x = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    n = cv2.resize(r.normal(0, 1, (H // 60, W // 4)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    grain = np.sin(x * 120 + n * 2.5 + y * 3) * 0.5 + 0.5
    planks = ((x * 5) % 1 < 0.012).astype(np.float32)
    v = 0.55 + 0.2 * grain - 0.35 * planks
    col = np.array([120, 74, 40], np.float32)[None, None, :] * v[:, :, None]
    col *= VIGNETTE
    return np.clip(col, 0, 255).astype(np.uint8)

# ---------------- transition / overlay effects (also usable inside custom graphics) ----------------
import math
_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)
_RAD = np.sqrt((_XX - W / 2) ** 2 + (_YY - H / 2) ** 2)
RADIUS = _RAD

def radial_blur(img, amt):
    """Zoom blur: average of progressively scaled copies."""
    if amt < 0.005: return img
    acc = img.astype(np.float32)
    for k in range(1, 6): acc += zoom_frame(img, 1 + amt * k / 5).astype(np.float32)
    return (acc / 6).astype(np.uint8)

def light_leak(img, k, seed=0):
    """Warm film burn sweeping across the frame; k in 0..1..0."""
    r = np.random.default_rng(seed)
    cx = lerp(-200, W + 200, k); cy = H * r.uniform(0.2, 0.8)
    g = np.exp(-(((_XX - cx) / 520) ** 2 + ((_YY - cy) / 900) ** 2))[:, :, None]
    col = np.array([255, 150, 60], np.float32)[None, None, :]
    a = math.sin(math.pi * clamp(k)) * 0.9
    return np.clip(img.astype(np.float32) + g * col * a, 0, 255).astype(np.uint8)

