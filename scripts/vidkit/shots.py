"""Shot builders + reusable motion-graphic templates.

A Shot is a function fn(u, d) -> RGB frame (H, W, 3), where u = seconds since the shot started and
d = shot duration. Custom graphics that need the ABSOLUTE time (to sync with at("Lxx", "word")) should take a third
argument: fn(u, d, t) — the renderer passes t automatically. (No need for the old `S = G(fn); return S` + S.start trick.) The renderer handles transitions, grading, grain, subtitles and the header.

Builders (use these in your project's edit.py):
  V(src, t0, ...)    video clip from raw/<src>.webm starting at t0 seconds of the source
  I(img, ...)        still image raw/img/<img>.jpg with Ken-Burns zoom/pan (never leave a still static)
  G(fn, ...)         custom graphic; fn(u, d) returns a frame

Templates (return Shots):
  g_chapter, g_counter, g_split, g_years, g_route, g_pins, g_filmstrip, g_cta, g_end_title, g_quote
Overlay helpers: label(), pop_in(), draw_arrow(), ring(), dot(), snow(), person_icon(), coin_sprite()

Coordinates: frame is 1080 x 1920. SAFE ZONES — keep important content out of:
  y < 130 (status bar), y 1250-1420 (subtitle band, SUB_Y=1330), y > 1650 (platform caption/UI),
  x > 960 between y 900-1650 (like/comment buttons on Douyin/TikTok).
"""
import math, functools
import numpy as np, cv2
from PIL import Image, ImageDraw
from fx import *
from timeline import L, at, TOTAL

class Shot:
    def __init__(self, fn, tone="none", tin="cut", film=False, labels=(), name="", fade_out=0.0, desat_in=0.0, header=True):
        # tone    : grade applied by renderer ("film" b/w sepia, "color", "gold", "night", "cold", "red", "none")
        # tin     : transition INTO this shot: cut | punch | whip | flash | glitch | fade | slide | iris | zoomblur | dip | leak | spin
        # film    : add scratches/flicker (old-footage look)
        # fade_out: darken to black over the last N seconds (emotional beats: "...就这样消失了")
        # desat_in: drain colour over the first N seconds ("其实少得可怜" deflation beats)
        # header  : show the persistent top title bar on this shot
        import inspect
        try: self.nargs = len(inspect.signature(fn).parameters)
        except (TypeError, ValueError): self.nargs = 2
        self.fn, self.tone, self.tin, self.film, self.labels, self.name = fn, tone, tin, film, list(labels), name
        self.fade_out, self.desat_in, self.header = fade_out, desat_in, header
        self.start = self.end = 0.0

FILM_TONES = ("film", "red", "gold", "cold", "night")

def V(src, t0, z=(1.0, 1.08), c=(0.5, 0.5), c2=None, speed=1.0, freeze=None, mode="fill", tone="film", fy=820, rot=(0, 0), ramp=None, **kw):
    """Video shot.
    z=(start_zoom, end_zoom) slow push; c/c2 = focus point (0-1 image coords) start/end for pans;
    speed: 0.5 slow-mo, 1.5 fast, 0 = freeze frame at t0; freeze=u -> hold frame after u seconds;
    mode: "fill" (crop to 9:16, immersive) or "frame" (fit width over blurred copy, keeps whole 4:3/16:9 frame).
    ramp=(s0, s1): speed ramp, playback speed goes linearly from s0 to s1 over the shot
    (e.g. (1.6, 0.35) = rush into a dramatic slow-motion moment; (0.4, 2.0) = slow then whoosh away)."""
    st = {}
    def fn(u, d):
        if "frames" not in st:
            need = d * (max(ramp) if ramp else max(speed, 0.01)) + 0.3
            st["frames"], st["fps"] = load_clip(src, t0, need)
            if len(st["frames"]) == 0: raise RuntimeError(f"no frames decoded from {src} @ {t0}s (beyond the end?)")
        fr, fps = st["frames"], st["fps"]
        uu = u if freeze is None else min(u, freeze)
        src_t = (ramp[0] * uu + (ramp[1] - ramp[0]) * uu * uu / (2 * d)) if ramp else uu * speed
        img = fr[min(len(fr) - 1, int(src_t * fps))]
        k = ease_io(u / d); zz = lerp(z[0], z[1], k)
        cc = c if c2 is None else (lerp(c[0], c2[0], k), lerp(c[1], c2[1], k))
        if mode == "fill": return cover(img, zz, *cc, rot=lerp(rot[0], rot[1], k))
        return framed(img, zz, *cc, y=fy)
    return Shot(fn, tone, film=tone in FILM_TONES, **kw)

def I(img_name, z=(1.0, 1.15), c=(0.5, 0.5), c2=None, tone="film", mode="fill", fy=820, rot=(0, 0), ease=ease_io, **kw):
    """Still image with Ken-Burns. Always give it movement: z from 1.0->1.15 (push), 1.3->1.0 (pull),
    or a pan with c -> c2. For portraits use c=(0.5, 0.3) so faces stay in frame."""
    def fn(u, d):
        img = load_img(img_name); k = ease(u / d)
        zz = lerp(z[0], z[1], k); cc = c if c2 is None else (lerp(c[0], c2[0], k), lerp(c[1], c2[1], k))
        if mode == "fill": return cover(img, zz, *cc, rot=lerp(rot[0], rot[1], k))
        return framed(img, zz, *cc, y=fy, border=10)
    return Shot(fn, tone, film=tone in FILM_TONES, **kw)

def G(fn, tone="none", **kw):
    """Custom graphic. fn(u, d) or fn(u, d, t) -> RGB frame (H, W, 3). t = absolute seconds; compare it with at(...) times."""
    return Shot(fn, tone, **kw)

def label(text, t, x=W / 2, y=360, size=50, fg=BLACK, bg=YELLOW, dur=None, rot=0):
    """Pop-in caption box attached to a shot. t = absolute time (use at())."""
    return dict(text=text, t=t, x=x, y=y, size=size, fg=fg, bg=bg, dur=dur, rot=rot)

# ---------------------------------------------------------------- helpers
def cover_M(img, zoom, cx, cy, ow=W, oh=H):
    """Like cover() but also returns the 2x3 matrix so you can map image coords -> screen (mp())."""
    h, w = img.shape[:2]; s = max(ow / w, oh / h) * zoom
    vw, vh = ow / s, oh / s
    fx = clamp(cx * w, vw / 2, w - vw / 2); fy = clamp(cy * h, vh / 2, h - vh / 2)
    M = np.array([[s, 0, ow / 2 - fx * s], [0, s, oh / 2 - fy * s]], np.float32)
    return cv2.warpAffine(img, M, (ow, oh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT), M

def mp(M, x, y): return (M[0, 0] * x + M[0, 2], M[1, 1] * y + M[1, 2])
def pop_in(t, t0, dur=0.28): return back_out((t - t0) / dur) if t >= t0 else 0.0

def draw_arrow(frame, p0, p1, prog, color=(255, 80, 40), width=14):
    if prog <= 0: return
    x = lerp(p0[0], p1[0], prog); y = lerp(p0[1], p1[1], prog)
    cv2.line(frame, (int(p0[0]), int(p0[1])), (int(x), int(y)), color, width, cv2.LINE_AA)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (-1, 1):
        a = ang + math.pi + s * 0.5
        cv2.line(frame, (int(x), int(y)), (int(x + 40 * math.cos(a)), int(y + 40 * math.sin(a))), color, width, cv2.LINE_AA)

def ring(frame, x, y, r, color, th=8, alpha=1.0):
    ov = frame.copy(); cv2.circle(ov, (int(x), int(y)), int(max(1, r)), color, th, cv2.LINE_AA)
    cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, frame)

def dot(frame, x, y, r, color):
    cv2.circle(frame, (int(x), int(y)), int(r + 5), (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, (int(x), int(y)), int(max(1, r)), color, -1, cv2.LINE_AA)

@functools.lru_cache(maxsize=16)
def person_icon(color, size=200, hat=False):
    """Flat person silhouette for 'X out of N' statistics. hat=True gives a cowboy hat."""
    s = size; im = Image.new("RGBA", (s, int(s * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = color + (255,)
    if hat:
        d.ellipse((s * 0.05, s * 0.30, s * 0.95, s * 0.44), fill=c)
        d.rounded_rectangle((s * 0.27, s * 0.06, s * 0.73, s * 0.38), 18, fill=c)
    d.ellipse((s * 0.32, s * 0.36 if not hat else s * 0.42, s * 0.68, s * 0.72 if not hat else s * 0.78), fill=c)
    d.polygon([(s * 0.12, s * 1.5), (s * 0.2, s * 0.92), (s * 0.5, s * 0.82), (s * 0.8, s * 0.92), (s * 0.88, s * 1.5)], fill=c)
    return np.array(im)

@functools.lru_cache(maxsize=4)
def coin_sprite(size=100):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((2, 2, size - 2, size - 2), fill=(250, 200, 40, 255), outline=(150, 100, 0, 255), width=6)
    d.text((size / 2, size / 2), "$", font=font(F_IMPACT, int(size * 0.6)), fill=(150, 100, 0, 255), anchor="mm")
    return np.array(im)

SNOW = np.random.default_rng(12).uniform(0, 1, (260, 4))
def snow(f, u, heavy=1.0):
    ov = np.zeros_like(f)
    for x, y, s, ph in SNOW[: int(260 * heavy)]:
        yy = (y * H + (200 + 500 * s) * u) % H; xx = (x * W + 80 * math.sin(u * 2 + ph * 6) - 260 * u * s) % W
        cv2.circle(ov, (int(xx), int(yy)), int(2 + 6 * s), (255, 255, 255), -1, cv2.LINE_AA)
    return cv2.add(f, cv2.GaussianBlur(ov, (0, 0), 1.2))

def falling(f, sprite, t, t0, n=18, seed=4, speed=(700, 1100)):
    """Rain sprites (coins, notes, leaves...) from the top starting at t0."""
    r = np.random.default_rng(seed)
    for _ in range(n):
        x, dl, rot, sp = r.uniform(80, 1000), r.uniform(0, 0.8), r.uniform(-40, 40), r.uniform(*speed)
        tt = t - t0 - dl
        if tt < 0: continue
        y = -100 + sp * tt
        if y < H + 100: blit(f, sprite, x, y, rot=rot * tt * 4)

# ---------------------------------------------------------------- templates
def g_chapter(n, title, img, tone="film", accent=YELLOW, red=False, word="真相"):
    """Chapter stinger ~1.0-1.3s: darkened image, diagonal band, '真相 01', title box.
    Put it 0.25s before the line that announces the chapter. word: 真相/第/PART/原因..."""
    def fn(u, d):
        f = darken(grade(cover(load_img(img), lerp(1.25, 1.35, u / d), 0.5, 0.4), tone), 0.42)
        k = ease_out(u / 0.25)
        band = np.zeros_like(f); pts = np.array([[0, 700], [W, 560], [W, 1080], [0, 1220]], np.int32)
        pts[:, 0] = (pts[:, 0] - W * (1 - k)).astype(np.int32)
        cv2.fillPoly(band, [pts], (200, 30, 30) if red else (20, 20, 20))
        f = cv2.addWeighted(f, 1, band, 0.75, 0)
        blit(f, text_sprite(word, 170, WHITE, 0, BLACK, F_SONG), lerp(-300, 330, ease_out(u / 0.3)), 780)
        blit(f, text_sprite(f"{n:02d}" if isinstance(n, int) else str(n), 340, WHITE if red else accent, 12, BLACK, F_IMPACT),
             760, 800, scale=lerp(2.5, 1, ease_out((u - 0.08) / 0.2)), alpha=clamp((u - 0.08) / 0.08))
        blit(f, label_box(title, 72, WHITE if red else BLACK, RED if red else accent), W / 2, 1060, scale=pop_in(u, 0.3))
        return f
    return G(fn, tin="flash", name=f"chapter{n}", header=False)

def g_counter(img, target, suffix, cap1, cap2, t_go, dur_count=0.8, tone="film", plus=False, color=YELLOW, cz=(0.5, 0.4), fmt="{:,}"):
    """Animated number counting 0 -> target starting at absolute time t_go (sync with the spoken number)."""
    def fn(u, d):
        t = S.start + u
        f = darken(grade(cover(load_img(img), lerp(1.05, 1.2, u / d), *cz), tone), 0.45)
        k = ease_out((t - t_go) / dur_count); n = target * k
        shake = (6 * math.sin(t * 90) * math.exp(-(t - t_go - dur_count) * 8)) if t > t_go + dur_count else 0
        txt = (fmt.format(int(round(n))) if isinstance(target, int) else f"{n:.1f}") + ("+" if plus and k >= 1 else "")
        bump = 1 + 0.12 * max(0, 1 - abs(t - t_go - dur_count) / 0.15)
        blit(f, text_sprite(txt, 300 if len(txt) <= 5 else 220, color, 14, BLACK, F_IMPACT), W / 2 + shake, 820, scale=bump)
        if suffix: blit(f, text_sprite(suffix, 110, WHITE, 10), W / 2, 1020, alpha=clamp((t - t_go) / 0.2))
        blit(f, label_box(cap1, 50, BLACK, WHITE), W / 2, 540, scale=pop_in(u, 0.0))
        if cap2: blit(f, text_sprite(cap2, 52, YELLOW, 8), W / 2, 1150, alpha=clamp((t - t_go - dur_count) / 0.2))
        return f
    S = G(fn, tin="punch", name="counter"); return S

def g_split(top, bot, lt, lb, badge, tones=("film", "film"), tz=(0.5, 0.3), bz=(0.5, 0.35), t_badge=None, top_frame=None, bot_frame=None):
    """Top/bottom split screen with a centre badge (VS, 原型?, 对比...).
    top/bot: image names; lt/lb: (text, fg, bg) labels; top_frame/bot_frame: optional fn()->RGB to use video frames."""
    def fn(u, d):
        t = S.start + u
        f = np.zeros((H, W, 3), np.uint8)
        k1 = ease_out(u / 0.25); k2 = ease_out((u - 0.12) / 0.25)
        ta = top_frame() if top_frame else load_img(top); tb = bot_frame() if bot_frame else load_img(bot)
        a = grade(cover(ta, lerp(1.05, 1.15, u / d), *tz, ow=W, oh=955), tones[0])
        b = grade(cover(tb, lerp(1.15, 1.05, u / d), *bz, ow=W, oh=955), tones[1])
        blit_rgb(f, a, int(-W * (1 - k1)), 0); blit_rgb(f, b, int(W * (1 - k2)), 965)
        f[955:965] = (255, 255, 255)
        blit(f, label_box(lt[0], 46, *lt[1:]), 40, 860, anchor="l", alpha=k1)
        blit(f, label_box(lb[0], 46, *lb[1:]), 40, 1830 - 200, anchor="l", alpha=k2)
        kb = pop_in(t, t_badge if t_badge is not None else S.start + 0.35)
        if kb > 0:
            cv2.circle(f, (W // 2, 960), int(120 * kb), (220, 35, 35), -1, cv2.LINE_AA)
            cv2.circle(f, (W // 2, 960), int(120 * kb), (255, 255, 255), 8, cv2.LINE_AA)
            blit(f, text_sprite(badge, 76 if len(badge) > 2 else 96, WHITE, 0, BLACK, F_HEAVY, shadow=False), W / 2, 955, scale=kb)
        return f
    S = G(fn, name="split"); return S

def g_years(y0, y1, big, sub="", bg_seed=9):
    """Timeline bar filling from year y0 to y1 with a huge headline (e.g. '20年'). Good for durations/eras."""
    paper = paper_bg(bg_seed)
    def fn(u, d):
        f = paper.copy(); k = ease_io((u - 0.1) / 0.8)
        x0, x1, y = 120, 960, 900
        cv2.line(f, (x0, y), (x1, y), (90, 60, 30), 14, cv2.LINE_AA)
        xe = int(lerp(x0, x1, k)); cv2.line(f, (x0, y), (xe, y), (210, 50, 30), 22, cv2.LINE_AA)
        for i, (yr, x) in enumerate([(y0, x0), (y1, x1)]):
            dot(f, x, y, 24, (90, 60, 30) if (i == 1 and k < 1) else (210, 50, 30))
            blit(f, text_sprite(str(yr), 92, INK, 0, BLACK, F_IMPACT, shadow=False), x, y + 110)
        blit(f, text_sprite(str(int(lerp(y0, y1, k))), 80, (210, 50, 30), 0, BLACK, F_IMPACT, shadow=False), xe, y - 90)
        blit(f, text_sprite(big, 300, RED, 14, WHITE, F_HEAVY), W / 2, 560, scale=pop_in(u, 0.55), rot=-4)
        if sub: blit(f, text_sprite(sub, 56, INK, 0, BLACK, F_HEAVY, shadow=False), W / 2, 1150, alpha=clamp((u - 0.4) / 0.3))
        return f
    return G(fn, tin="whip", name="years")

def g_route(img, pts, unit_label, total, unit="英里", sub="", caption="", icon=None, zoom=1.25, tone="color"):
    """Camera follows a red route being drawn over a map image. pts = [(x, y), ...] in the map image's pixels
    (find them with peek_grid.py). total = number shown at the end (e.g. 1000 -> '1000+ 英里')."""
    im = load_img(img, 4000); h, w = im.shape[:2]
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; tot = sum(seg)
    def point(p):
        dd = p * tot
        for i, s in enumerate(seg):
            if dd <= s: a = dd / s; return (lerp(pts[i][0], pts[i + 1][0], a), lerp(pts[i][1], pts[i + 1][1], a)), i
            dd -= s
        return pts[-1], len(seg) - 1
    def fn(u, d):
        p = ease_io(u / d); (hx, hy), i = point(p)
        f, M = cover_M(im, zoom, hx / w, hy / h); f = grade(f, tone)
        poly = np.array([mp(M, *pts[j]) for j in range(i + 1)] + [mp(M, hx, hy)], np.int32)
        cv2.polylines(f, [poly], False, (0, 0, 0), 26, cv2.LINE_AA); cv2.polylines(f, [poly], False, (230, 40, 30), 16, cv2.LINE_AA)
        sx, sy = mp(M, hx, hy)
        if icon is not None: blit(f, icon, sx, sy - 20)
        else: dot(f, sx, sy, 16, RED)
        n = int(total * p)
        blit(f, label_box(f"{n}{'+' if p > 0.98 else ''} {unit}", 72, WHITE, (200, 40, 30)), W / 2, 330)
        if sub: blit(f, text_sprite(sub, 50, WHITE, 8), W / 2, 450, alpha=clamp((p - 0.6) / 0.3))
        if caption: blit(f, label_box(caption, 40, BLACK, YELLOW), W / 2, 1560)
        return f
    return G(fn, tin="whip", name="route")

def g_pins(img, pins, t_first, step=0.11, z=(1.3, 2.4), focus=(0.5, 0.5), title="", tone="color", box=None):
    """Map/photo with pins popping in one by one. pins = [(name, x, y), ...] in image pixels.
    box=(y0, y1): render the map inside a horizontal band over paper instead of full-bleed (use for maps
    whose aspect ratio is far from 9:16 so they don't get cropped to a meaningless blob)."""
    im = load_img(img, 4000); paper = paper_bg(2)
    def fn(u, d):
        t = S.start + u; zz = lerp(z[0], z[1], ease_out(u / 0.6))
        if box:
            m, M = cover_M(im, zz, *focus, ow=W, oh=box[1] - box[0]); f = paper.copy(); f[box[0]:box[1]] = grade(m, tone)
            M = M.copy(); M[1, 2] += box[0]
        else:
            f, M = cover_M(im, zz, *focus); f = grade(f, tone)
        if title: blit(f, label_box(title, 58, BLACK, YELLOW), W / 2, 380, scale=pop_in(u, 0.05))
        for i, (nm, x, y) in enumerate(pins):
            k = pop_in(t, t_first + i * step)
            if k <= 0: continue
            px, py = mp(M, x, y); dot(f, px, py, 16 * k, RED)
            if nm: blit(f, text_sprite(nm, 40, WHITE, 6), px, py - 50 if i % 2 == 0 else py + 50, scale=k)
        return f
    S = G(fn, tin="whip", name="pins"); return S

def g_filmstrip(img, tone="color", z=(1.0, 1.15), c=(0.5, 0.4)):
    """Image inside moving film-strip edges — use for 'movies / cinema / media' beats."""
    def fn(u, d):
        f = grade(cover(load_img(img), lerp(*z, u / d), *c), tone)
        cv2.rectangle(f, (0, 0), (110, H), (10, 10, 10), -1); cv2.rectangle(f, (W - 110, 0), (W, H), (10, 10, 10), -1)
        off = int(u * 600) % 120
        for y in range(-120, H + 120, 120):
            for x in (30, W - 80): cv2.rectangle(f, (x, y + off), (x + 50, y + off + 70), (230, 230, 220), -1)
        return f
    return G(fn, tin="glitch", name="film")

def g_quote(img, line1, line2="", tone="gold", t_in=0.0, video=None):
    """Big serif statement over a darkened image/video (endings, thesis lines). video=(src, t0, speed)."""
    st = {}
    def fn(u, d):
        if video:
            if "fr" not in st: st["fr"], st["fps"] = load_clip(video[0], video[1], d * video[2] + 0.5)
            base = st["fr"][min(len(st["fr"]) - 1, int(u * video[2] * st["fps"]))]
        else: base = load_img(img)
        f = darken(grade(cover(base, lerp(1.15, 1.25, u / d), 0.5, 0.5), tone), 0.6)
        blit(f, text_sprite(line1, 120, (255, 236, 200), 0, BLACK, F_SONG), W / 2, 820, alpha=clamp((u - t_in) / 0.4))
        if line2: blit(f, text_sprite(line2, 120, YELLOW, 0, BLACK, F_SONG), W / 2, 980, alpha=clamp((u - t_in - 0.35) / 0.4))
        return f
    return G(fn, name="quote", film=True, header=False)

def g_end_title(img, line1, line2="", tone="gold", video=None):
    """Final shot: quote that fades to black during the last 0.6s (the video must not end abruptly)."""
    q = g_quote(img, line1, line2, tone, video=video)
    inner = q.fn
    def fn(u, d): return darken(inner(u, d), 1 - clamp((u - (d - 0.6)) / 0.6))
    q.fn = fn; q.name = "final"; return q

def g_cta(img, question, opt_a, opt_b):
    """Comment-bait card: speech bubble with question + two options."""
    def fn(u, d):
        f = cv2.GaussianBlur(darken(grade(cover(load_img(img), lerp(1.1, 1.2, u / d), 0.5, 0.5), "color"), 0.35), (0, 0), 6)
        k = pop_in(u, 0.0)
        blit(f, rounded_rect(860, 320, 60, (255, 255, 255, 245)), W / 2, 760, scale=k)
        blit(f, text_sprite(question, 72, INK, 0, BLACK, F_HEAVY, shadow=False), W / 2, 680, scale=k)
        blit(f, label_box(opt_a, 60, BLACK, YELLOW), W / 2 - 200, 830, scale=pop_in(u, 0.15))
        blit(f, label_box(opt_b, 60, WHITE, RED), W / 2 + 200, 830, scale=pop_in(u, 0.25))
        return f
    return G(fn, tin="punch", name="cta", header=False)


# ---------------------------------------------------------------- sound helpers
TIN_SFX = {"whip": ("whoosh", 0.4, -0.12), "punch": ("pop_low", 0.4, 0.0), "flash": ("boom_s", 0.5, 0.0), "glitch": ("glitch", 0.45, 0.0),
           "slide": ("whoosh_s", 0.4, -0.05), "zoomblur": ("whoosh", 0.4, -0.1), "spin": ("whoosh", 0.45, -0.1), "iris": ("pop", 0.3, 0.0)}
def transition_sfx(shots, skip_every=3):
    """A sound for most transitions (whoosh for whips, low pop for punch-ins, soft boom for flashes...).
    Every `skip_every`-th whip/punch is left silent so the soundtrack doesn't turn into a constant whoosh-fest
    (flash/glitch/spin always sound — they are rare and meant to be felt). fade/dip/leak/cut are silent.
    Start your sfx_cues() with:  C = transition_sfx(shots)"""
    out, n = [], 0
    for s in shots:
        if s.tin not in TIN_SFX: continue
        if s.tin in ("whip", "punch", "slide"):
            n += 1
            if skip_every and n % skip_every == 0: continue
        nm, g, off = TIN_SFX[s.tin]; out.append((s.start + off, nm, g))
    return out

# ---------------------------------------------------------------- animated system diagram
def g_nodes(nodes, events, title="", bg="dark", center=(540, 880), radius=290, node_r=84, positions=None, tone="none"):
    """Animated node/message diagram for explaining algorithms, networks, protocols, organisations, food chains...
    The picture at time t is a pure function of the events with ev["t"] <= t, so it is always in sync with the voice.

    nodes:  ["A", "B", "C", "D", "E"]  (short names drawn inside the circles; positions on a circle unless `positions`
            = {"A": (x, y), ...} is given — keep node centres between y≈520 and y≈1110: title sits at y=300,
            captions at y=405, node labels + log boxes extend ~130 px below each node, subtitles start at y≈1250)
    events: list of dicts, each with "t" (absolute seconds — use at("Lxx", "word")) and "do":
      {"do": "state",  "node": "A", "label": "领导", "color": YELLOW, "crown": True}   role text under the node + fill colour
      {"do": "msg",    "src": "A", "dst": "all" | "B" | ["B","C"], "text": "心跳", "color": (90,200,255), "dur": 0.6}
      {"do": "crash",  "node": "A"}            grey out + red cross        {"do": "recover", "node": "A"}
      {"do": "timer",  "node": "C", "dur": 1.2, "color": RED}             countdown ring that drains over dur
      {"do": "log",    "node": "A" | "all" | ["A","B"], "entry": "x=5", "color": WHITE}   append a log/ledger box
      {"do": "commit", "node": "all", "upto": 1}   colour the first `upto` log boxes green (committed)
      {"do": "caption","text": "过半 = 5台里至少3台", "dur": 2.0}         caption box at the top
      {"do": "badge",  "node": "C", "text": "任期 2", "color": RED}      small tag above the node
    bg: "dark" (tech) | "paper" (history/culture) | an RGB image array
    """
    if positions is None:
        positions = {n: (center[0] + radius * math.sin(2 * math.pi * i / len(nodes)), center[1] - radius * math.cos(2 * math.pi * i / len(nodes)))
                     for i, n in enumerate(nodes)}
    evs = sorted(events, key=lambda e: e["t"])
    if isinstance(bg, np.ndarray): base = bg
    elif bg == "paper": base = paper_bg(4)
    else:
        base = np.zeros((H, W, 3), np.uint8); base[:] = (10, 13, 22)
        for y in range(0, H, 60): base[y:y + 1] = (18, 24, 38)
        for x in range(0, W, 60): base[:, x:x + 1] = (18, 24, 38)
    fg = WHITE if bg != "paper" else INK
    def targets(d):
        if d == "all": return None
        return [d] if isinstance(d, str) else list(d)
    def fn(u, d, t):
        f = base.copy()
        st = {n: dict(color=(70, 80, 100) if bg != "paper" else (200, 185, 150), label="", crown=False, dead=False, log=[], commit=0, badge=None) for n in nodes}
        cap = None
        for e in evs:
            if e["t"] > t: break
            k = e["do"]
            if k == "state": st[e["node"]].update(color=e.get("color", st[e["node"]]["color"]), label=e.get("label", st[e["node"]]["label"]), crown=e.get("crown", False))
            elif k == "crash": st[e["node"]]["dead"] = True
            elif k == "recover": st[e["node"]]["dead"] = False
            elif k == "log":
                for n in (targets(e["node"]) or nodes):
                    if not st[n]["dead"]: st[n]["log"].append((e["entry"], e.get("color", WHITE), e["t"]))
            elif k == "commit":
                for n in (targets(e["node"]) or nodes): st[n]["commit"] = e["upto"]
            elif k == "caption" and t < e["t"] + e.get("dur", 2.0): cap = e
            elif k == "badge": st[e["node"]]["badge"] = (e["text"], e.get("color", RED), e["t"])
        # mesh edges
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                cv2.line(f, tuple(map(int, positions[a])), tuple(map(int, positions[b])), (40, 50, 70) if bg != "paper" else (170, 150, 120), 3, cv2.LINE_AA)
        # messages in flight
        for e in evs:
            if e["do"] != "msg" or e["t"] > t: continue
            dur = e.get("dur", 0.6); p = (t - e["t"]) / dur
            if p > 1: continue
            dsts = targets(e["dst"]) or [n for n in nodes if n != e["src"]]
            for dname in dsts:
                (x0, y0), (x1, y1) = positions[e["src"]], positions[dname]
                q = ease_io(p); x, y = lerp(x0, x1, q), lerp(y0, y1, q)
                col = e.get("color", (90, 200, 255))
                cv2.circle(f, (int(x), int(y)), 16, col, -1, cv2.LINE_AA)
                if e.get("text") and dname == dsts[0]:
                    blit(f, label_box(e["text"], 30, BLACK, col, padx=12, pady=6), x, y - 44)
        # nodes
        for n in nodes:
            x, y = positions[n]; s = st[n]
            col = (60, 60, 66) if s["dead"] else s["color"]
            if s["crown"] and not s["dead"]:
                glow = np.zeros_like(f); cv2.circle(glow, (int(x), int(y)), node_r + 40, col, -1); f = cv2.addWeighted(f, 1, cv2.GaussianBlur(glow, (0, 0), 25), 0.6, 0)
            cv2.circle(f, (int(x), int(y)), node_r, col, -1, cv2.LINE_AA)
            cv2.circle(f, (int(x), int(y)), node_r, (255, 255, 255), 5, cv2.LINE_AA)
            blit(f, text_sprite(n, 76, WHITE if sum(col) < 450 else BLACK, 0, BLACK, F_IMPACT, shadow=False), x, y)
            if s["crown"] and not s["dead"]: blit(f, text_sprite("★", 60, YELLOW, 4, BLACK, F_SYMBOL, shadow=False), x, y - node_r - 30)
            if s["label"]: blit(f, text_sprite(s["label"], 36, fg, 6 if bg != "paper" else 0, BLACK, F_HEAVY, shadow=False), x, y + node_r + 34)
            if s["dead"]:
                for sgn in (-1, 1): cv2.line(f, (int(x - 60), int(y - 60 * sgn)), (int(x + 60), int(y + 60 * sgn)), (230, 40, 40), 14, cv2.LINE_AA)
            for i, (entry, ecol, et) in enumerate(s["log"][-5:]):
                bx = x - 2 * 38 + i * 38; by = y + node_r + 82
                k = clamp((t - et) / 0.2)
                c = (60, 200, 110) if i < s["commit"] else ecol
                cv2.rectangle(f, (int(bx - 16), int(by - 16 * k)), (int(bx + 16), int(by + 16 * k)), c, -1)
            if s["badge"]:
                txt, bc, bt = s["badge"]; blit(f, label_box(txt, 28, WHITE, bc, padx=10, pady=5), x + node_r * 0.8, y - node_r * 0.9, scale=pop_in(t, bt))
        for e in evs:   # countdown rings
            if e["do"] == "timer" and e["t"] <= t < e["t"] + e.get("dur", 1.0):
                x, y = positions[e["node"]]; p = 1 - (t - e["t"]) / e.get("dur", 1.0)
                cv2.ellipse(f, (int(x), int(y)), (node_r + 18, node_r + 18), -90, 0, 360 * p, e.get("color", RED), 10, cv2.LINE_AA)
        if title: blit(f, label_box(title, 52, BLACK, YELLOW), W / 2, 300)
        if cap: blit(f, label_box(cap["text"], 44, WHITE, (200, 40, 40) if bg != "paper" else INK), W / 2, 405, scale=pop_in(t, cap["t"]))
        return f
    return G(fn, tone=tone, name="nodes")
