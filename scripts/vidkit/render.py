"""Render the video: shots + transitions + grade + film finish + header + big pops + karaoke subtitles.

usage:
  python render.py --project DIR                    full render -> build/video_noaudio.mp4
  python render.py --project DIR stills 1.0 5.2 ...  write build/stills/<t>.jpg (ALWAYS check stills before a full render)
  python render.py --project DIR sheet              1 frame/sec contact sheet of the current edit -> build/sheets/edit.jpg
env JOBS=N to set parallel processes (default: cpu count).

The project's edit.py must define:
  build() -> list[Shot] with .start set (absolute seconds, ascending). The end of each shot = next start.
  sfx_cues(shots) -> list[(time, sfx_name, gain)]   (start with transition_sfx(shots))
Optional in edit.py:
  HEADER = "好莱坞没告诉你的 · 牛仔真相"   persistent top title (shown from HEADER_FROM to HEADER_TO)
  HEADER_FROM, HEADER_TO = seconds
  CHAPTERS = [(t0, t1, "真相①", "short title"), ...]   small badge under the header
  BIG_EXTRA = [dict(t=, text=, color=, size=, y=, rot=, dur=)]   extra centre stamps (e.g. "错！")
  BIG_SKIP = {("L10", "3000")}   "big" highlights NOT to pop (because a graphic already shows them)
"""
import os, sys, math, subprocess, time, importlib
sys.path.insert(0, os.path.dirname(__file__))
import config
ARGV = config.parse_project_arg(sys.argv[1:])
import numpy as np, cv2
from multiprocessing import Pool
from fx import *
from timeline import LINES_T, L, TOTAL, spans, at
from shots import pop_in
FPS = config.FPS

E = importlib.import_module("edit")
SHOTS = E.build()
SHOTS.sort(key=lambda s: s.start)
for i, s in enumerate(SHOTS):
    s.end = SHOTS[i + 1].start if i + 1 < len(SHOTS) else TOTAL
    if s.end - s.start < 0.2: print(f"WARNING: shot {i} '{s.name}' at {s.start:.2f}s is only {s.end - s.start:.2f}s long")
    if s.end - s.start > 3.5: print(f"WARNING: shot {i} '{s.name}' at {s.start:.2f}s lasts {s.end - s.start:.2f}s — fine for an animated graphic, otherwise split it")
if SHOTS[0].start > 0: raise SystemExit("first shot must start at 0.0")

HEADER = getattr(E, "HEADER", "")
HEADER_FROM = getattr(E, "HEADER_FROM", 0.0); HEADER_TO = getattr(E, "HEADER_TO", TOTAL)
CHAPTERS = getattr(E, "CHAPTERS", [])
BIG_SKIP = getattr(E, "BIG_SKIP", set())
BIG_EXTRA = getattr(E, "BIG_EXTRA", [])

# ---------------------------------------------------------------- subtitles
PUNCT = set("，。！？：、；,.!?:;…")
SUB_Y = 1330
COL = {"y": YELLOW, "r": RED, "big": YELLOW}

def build_subs():
    phrases = []
    for line in LINES_T:
        text = line["text"]
        reveal = [None] * len(text)
        for a, b, w in spans(line):
            for i in range(a, min(b, len(text))): reveal[i] = w["t"]
        nxt = line["end"]
        for i in range(len(text) - 1, -1, -1):
            if reveal[i] is None: reveal[i] = nxt
            else: nxt = reveal[i]
        style = [None] * len(text)
        for kw, st in line["hl"]:
            j = text.find(kw)
            while j >= 0:
                for i in range(j, j + len(kw)): style[i] = st
                j = text.find(kw, j + 1)
        cur = []
        for i, ch in enumerate(text):
            if ch in PUNCT:
                if cur: phrases.append(dict(line=line["id"], chars=cur)); cur = []
            elif ch != " " or cur: cur.append((ch, reveal[i], style[i]))
        if cur: phrases.append(dict(line=line["id"], chars=cur))
    for i, p in enumerate(phrases):
        p["t0"] = p["chars"][0][1] - 0.06
        line = L[p["line"]]
        if i + 1 == len(phrases): p["t1"] = line["end"] + 0.3
        else:
            nxt = phrases[i + 1]["chars"][0][1] - 0.06
            p["t1"] = min(nxt, line["end"] + 0.35) if phrases[i + 1]["line"] != p["line"] else nxt
    return phrases

PHRASES = build_subs()
SUB_Y = getattr(E, "SUB_Y", 1330)
SUB_SIZE = getattr(E, "SUB_SIZE", 84)          # keyword chars are 1.24x
SUB_STYLE = getattr(E, "SUB_STYLE", "pop")     # pop | karaoke | box | bounce | typewriter  (see references/effects-catalog.md)
SUB_COLOR = getattr(E, "SUB_COLOR", WHITE)
KARAOKE_COLOR = getattr(E, "KARAOKE_COLOR", YELLOW)

def char_sprite(ch, style, color=None):
    big = style is not None
    col = color or (SUB_COLOR if not big else COL[style])
    return text_sprite(ch, int(SUB_SIZE * (1.24 if big else 1)), col, 10, BLACK, F_HEAVY, True, 18)

def box_sprite(ch, style):
    """keyword glyph for the 'box' style: dark text, no stroke (box is drawn behind)."""
    return text_sprite(ch, int(SUB_SIZE * 1.12), BLACK if style != "r" else WHITE, 0, BLACK, F_HEAVY, False, 18)

def draw_subs(f, t):
    for p in PHRASES:
        if not (p["t0"] <= t < p["t1"]): continue
        chars = p["chars"]
        def size(st):
            if SUB_STYLE == "box": return SUB_SIZE * (1.12 if st else 1)
            return SUB_SIZE * (1.24 if st else 1)
        adv = [font(F_HEAVY, int(size(st))).getlength(ch) + (14 if (SUB_STYLE == "box" and st) else 4) for ch, tr, st in chars]
        total = sum(adv); sc = min(1.0, 1000 / total)
        x0 = W / 2 - total * sc / 2
        out_k = clamp((p["t1"] - t) / 0.08); in_k = clamp((t - p["t0"]) / 0.12)
        xs = []; x = x0
        for a in adv: xs.append(x + a * sc / 2); x += a * sc
        if SUB_STYLE == "box":    # rounded colour box behind each keyword run, whole phrase slides up
            yb = SUB_Y + 30 * (1 - ease_out(in_k))
            i = 0
            while i < len(chars):
                if chars[i][2]:
                    j = i
                    while j + 1 < len(chars) and chars[j + 1][2]: j += 1
                    if t >= chars[i][1] - 0.02:
                        k = clamp((t - chars[i][1]) / 0.15)
                        bw = int((xs[j] - xs[i]) + adv[j] * sc + 16); bh = int(SUB_SIZE * 1.35 * sc)
                        colr = (255, 214, 0, 255) if chars[i][2] != "r" else (255, 59, 48, 255)
                        blit(f, rounded_rect(bw, bh, 14, colr), (xs[i] + xs[j]) / 2, yb, scale=lerp(0.6, 1, back_out(k)), alpha=out_k)
                    i = j + 1
                else: i += 1
        for idx, ((ch, tr, st), cx) in enumerate(zip(chars, xs)):
            spoken = t >= tr - 0.02
            k = clamp((t - tr + 0.02) / 0.14)
            if SUB_STYLE == "pop":
                if not spoken: continue
                s_ = (lerp(0.4, 1, back_out(k)) if st is None else lerp(1.8, 1, ease_out(k))) * sc
                yoff = 0 if st is None else -4 * math.sin(clamp((t - tr) / 0.3) * math.pi)
                blit(f, char_sprite(ch, st), cx, SUB_Y + yoff, scale=s_, alpha=min(clamp(k * 2), out_k))
            elif SUB_STYLE == "karaoke":   # whole phrase visible; colour sweeps over spoken chars
                spr = char_sprite(ch, st, None if st else (KARAOKE_COLOR if spoken else SUB_COLOR))
                s_ = sc * (1 + (0.12 * math.sin(math.pi * k) if spoken and k < 1 else 0))
                blit(f, spr, cx, SUB_Y, scale=s_, alpha=min(in_k, out_k) * (1.0 if spoken else 0.85))
            elif SUB_STYLE == "box":
                yb = SUB_Y + 30 * (1 - ease_out(in_k))
                if st and spoken: blit(f, box_sprite(ch, st), cx, yb, scale=sc, alpha=out_k)
                else: blit(f, char_sprite(ch, None, SUB_COLOR if (st is None) else WHITE), cx, yb, scale=sc, alpha=min(in_k, out_k))
            elif SUB_STYLE == "bounce":
                if not spoken: continue
                yoff = -70 * (1 - elastic(clamp((t - tr) / 0.45)))
                blit(f, char_sprite(ch, st), cx, SUB_Y + yoff, scale=sc, alpha=min(clamp(k * 3), out_k))
            elif SUB_STYLE == "typewriter":
                if not spoken: continue
                blit(f, char_sprite(ch, st), cx, SUB_Y, scale=sc, alpha=out_k)
                last = idx + 1 == len(chars) or t < chars[idx + 1][1] - 0.02
                if last and int(t * 3) % 2 == 0:
                    cv2.rectangle(f, (int(cx + adv[idx] * sc / 2 + 6), int(SUB_Y - SUB_SIZE * 0.45)), (int(cx + adv[idx] * sc / 2 + 14), int(SUB_Y + SUB_SIZE * 0.45)), (255, 255, 255), -1)
    return f

BIGS = [(at(line["id"], kw), kw) for line in LINES_T for kw, st in line["hl"] if st == "big" and (line["id"], kw) not in BIG_SKIP]

def draw_bigs(f, t):
    for t0, kw in BIGS:
        u = t - t0
        if 0 <= u < 1.0:
            k = ease_out(u / 0.16); out = clamp((1.0 - u) / 0.2)
            sh = 8 * math.sin(u * 70) * math.exp(-u * 8)
            blit(f, text_sprite(kw, 210 if len(kw) <= 4 else 160, YELLOW, 14, BLACK, F_HEAVY), W / 2 + sh, 700,
                 scale=lerp(2.2, 1, k) * (1 + 0.03 * u), rot=-4, alpha=min(k * 1.5, out))
    for b in BIG_EXTRA:
        u = t - b["t"]; dur = b.get("dur", 1.0)
        if 0 <= u < dur:
            k = ease_out(u / 0.12); out = clamp((dur - u) / 0.15)
            blit(f, text_sprite(b["text"], b.get("size", 360), b.get("color", RED), 16, WHITE, F_HEAVY), W / 2, b.get("y", 760),
                 scale=lerp(3, 1, k), rot=b.get("rot", -8), alpha=min(1, k * 2) * out)
    return f

def draw_header(f, t, shot):
    if not HEADER or not shot.header or not (HEADER_FROM <= t <= HEADER_TO): return f
    blit(f, label_box(HEADER, 40, YELLOW, (20, 16, 12), padx=24, pady=10, r=30), W / 2, 160, alpha=0.92)
    for a, b, tag, title in CHAPTERS:
        if a + 0.9 <= t < b:
            k = ease_out((t - a - 0.9) / 0.3)
            blit(f, label_box(f"{tag} {title}", 34, BLACK, YELLOW, padx=18, pady=8), lerp(-300, 40, k), 245, anchor="l")
    return f

# ---------------------------------------------------------------- flashes / shakes driven by SFX cues
CUES = E.sfx_cues(SHOTS)
FLASHES = [(t, 0.55 * g) for t, n, g in CUES if n == "gunshot" or n == "flash"]
SHAKES = [(t, 22 * g) for t, n, g in CUES if n in ("gunshot", "boom", "stamp", "taiko", "impact")]

def shake_offset(t):
    dx = dy = 0.0
    for t0, a in SHAKES:
        u = t - t0
        if 0 <= u < 0.3:
            e = a * math.exp(-u * 14); dx += e * math.sin(u * 95); dy += e * math.cos(u * 77)
    return dx, dy

# ---------------------------------------------------------------- compositing
def shot_at(t):
    for i, s in enumerate(SHOTS):
        if s.start <= t < s.end: return i, s
    return len(SHOTS) - 1, SHOTS[-1]

def base_frame(s, t):
    u = t - s.start; d = s.end - s.start
    img = s.fn(u, d, t) if s.nargs >= 3 else s.fn(u, d)
    if img is None or img.shape != (H, W, 3): raise RuntimeError(f"shot '{s.name}' returned {None if img is None else img.shape}, expected {(H, W, 3)} uint8")
    if s.tone != "none": img = grade(img, s.tone)
    if s.desat_in:
        g = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB); k = clamp(u / s.desat_in)
        img = cv2.addWeighted(img, 1 - k, g, k, 0)
    if s.fade_out:
        img = darken(img, 1 - 0.85 * clamp((u - (d - s.fade_out)) / s.fade_out))
    for lb in s.labels:
        if t >= lb["t"] and (lb["dur"] is None or t < lb["t"] + lb["dur"]):
            blit(img, label_box(lb["text"], lb["size"], lb["fg"], lb["bg"]), lb["x"], lb["y"], scale=pop_in(t, lb["t"]), rot=lb["rot"])
    return img

# ---------------------------------------------------------------- transitions
# name: (duration_s, needs_previous_frame). Durations scale with PACE (edit.PACE, default 1.0; 1.2 = calmer).
PACE = getattr(E, "PACE", 1.0)
TRANS = {"cut": (0, False), "punch": (0.32, False), "whip": (0.28, True), "flash": (0.25, False), "glitch": (0.22, False),
         "fade": (0.45, True), "slide": (0.35, True), "iris": (0.40, True), "zoomblur": (0.30, True), "dip": (0.50, True),
         "leak": (0.50, True), "spin": (0.35, True)}
def apply_transition(kind, u, img, prev, fi):
    dur = TRANS[kind][0] * PACE
    if kind == "cut" or u >= dur: return img
    k = u / dur; e = ease_out(k); io = ease_io(k)
    if kind == "punch":   return zoom_frame(img, lerp(1.14, 1.0, e))
    if kind == "flash":   return img           # white overlay added after finishing
    if kind == "glitch":
        r = np.random.default_rng(fi); img = rgb_split(img, 26 * (1 - k))
        for _ in range(6):
            y = int(r.uniform(0, H - 80)); h = int(r.uniform(20, 120)); img[y:y + h] = np.roll(img[y:y + h], int(r.uniform(-120, 120)), axis=1)
        return img
    if prev is None: return img
    if kind == "whip":   # outgoing slides left & blurs, incoming arrives from the right
        if k < 0.5: return motion_blur(zoom_frame(prev, 1.0, (-W * 0.35 * (k / 0.5), 0)), 80 * (k / 0.5))
        kk = (k - 0.5) / 0.5; return motion_blur(zoom_frame(img, 1.0, (W * 0.35 * (1 - ease_out(kk)), 0)), 80 * (1 - kk))
    if kind == "fade":   return cv2.addWeighted(prev, 1 - io, img, io, 0)
    if kind == "slide":  # push: new shot pushes old one up
        out = np.empty_like(img); off = int(H * io)
        out[:H - off] = prev[off:]; out[H - off:] = img[:off]; return out
    if kind == "iris":   # circle reveal from centre
        m = (RADIUS < io * 1250).astype(np.float32)[:, :, None]
        return (img * m + prev * (1 - m)).astype(np.uint8)
    if kind == "zoomblur":
        if k < 0.5: return radial_blur(zoom_frame(prev, 1 + 0.5 * k), 0.25 * k / 0.5)
        return radial_blur(zoom_frame(img, 1.25 - 0.5 * (k - 0.5)), 0.25 * (1 - (k - 0.5) / 0.5))
    if kind == "dip":    # dip to black — chapter breaks, time skips, endings
        return darken(prev, 1 - k * 2) if k < 0.5 else darken(img, (k - 0.5) * 2)
    if kind == "leak":   # crossfade under a warm light leak — nostalgic / emotional
        return light_leak(cv2.addWeighted(prev, 1 - io, img, io, 0), k, fi // 100)
    if kind == "spin":
        M = cv2.getRotationMatrix2D((W / 2, H / 2), (1 - e) * 25 if k >= 0.5 else -k * 50, lerp(1.3, 1.0, e) if k >= 0.5 else 1 + k * 0.6)
        src = img if k >= 0.5 else prev
        return motion_blur(cv2.warpAffine(src, M, (W, H), borderMode=cv2.BORDER_REFLECT), 30 * (1 - abs(k - 0.5) * 2))
    return img

def frame_at(fi):
    t = fi / FPS
    i, s = shot_at(t); u = t - s.start
    img = base_frame(s, t)
    kind = s.tin if s.tin in TRANS else "cut"
    if u < TRANS[kind][0] * PACE and kind != "cut":
        prev = base_frame(SHOTS[i - 1], s.start - 1 / FPS) if (TRANS[kind][1] and i > 0) else None
        img = apply_transition(kind, u, img, prev, fi)
    dx, dy = shake_offset(t)
    if abs(dx) + abs(dy) > 0.5: img = zoom_frame(img, 1.04, (dx, dy))
    img = finish(img, fi, vignette=0.9 if s.tone != "none" else 0.5, grain=8 if s.film else 4, scratches=s.film)
    fd = TRANS["flash"][0] * PACE
    if s.tin == "flash" and u < fd:
        img = cv2.addWeighted(img, 1, np.full_like(img, 255), 0.85 * (1 - u / fd), 0)
    for t0, a in FLASHES:
        if 0 <= t - t0 < 0.1: img = cv2.addWeighted(img, 1, np.full_like(img, 255), a * (1 - (t - t0) / 0.1), 0)
    img = draw_header(img, t, s)
    img = draw_bigs(img, t)
    img = draw_subs(img, t)
    return img

def render_chunk(args):
    a, b, out = args
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for fi in range(a, b): p.stdin.write(np.ascontiguousarray(frame_at(fi)).tobytes())
    p.stdin.close(); p.wait()
    return out

def save_jpg(path, img): cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])

if __name__ == "__main__":
    nframes = int(round(TOTAL * FPS))
    if ARGV and ARGV[0] == "stills":
        os.makedirs(config.build("stills"), exist_ok=True)
        ts = list(map(float, ARGV[1:])); frames = []
        for t in ts:
            fr = frame_at(int(t * FPS)); save_jpg(config.build("stills", f"{t:06.2f}.jpg"), fr); frames.append(fr)
        # one mosaic of all requested stills (review this single image instead of opening each file)
        cols = min(6, len(frames)); rows = (len(frames) + cols - 1) // cols; tw, th = 270, 480
        sheet = np.zeros((rows * th, cols * tw, 3), np.uint8)
        for k, (t, fr) in enumerate(zip(ts, frames)):
            th_ = cv2.resize(fr, (tw, th), interpolation=cv2.INTER_AREA)
            cv2.rectangle(th_, (0, 0), (92, 26), (0, 0, 0), -1); cv2.putText(th_, f"{t:.2f}s", (4, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            sheet[(k // cols) * th:(k // cols + 1) * th, (k % cols) * tw:(k % cols + 1) * tw] = th_
        os.makedirs(config.build("sheets"), exist_ok=True); save_jpg(config.build("sheets", "stills.jpg"), sheet)
        print("stills ->", config.build("stills"), "| mosaic ->", config.build("sheets", "stills.jpg")); sys.exit()
    if ARGV and ARGV[0] == "sheet":
        os.makedirs(config.build("sheets"), exist_ok=True)
        thumbs = [cv2.resize(frame_at(int(t * FPS)), (144, 256), interpolation=cv2.INTER_AREA) for t in np.arange(0.5, TOTAL, 1.0)]
        cols = 15; rows = (len(thumbs) + cols - 1) // cols
        sheet = np.zeros((rows * 256, cols * 144, 3), np.uint8)
        for k, th in enumerate(thumbs): sheet[(k // cols) * 256:(k // cols + 1) * 256, (k % cols) * 144:(k % cols + 1) * 144] = th
        save_jpg(config.build("sheets", "edit.jpg"), sheet); print("sheet ->", config.build("sheets", "edit.jpg")); sys.exit()
    n = int(os.environ.get("JOBS", os.cpu_count() or 4))
    edges = np.linspace(0, nframes, n + 1).astype(int)
    jobs = [(int(edges[i]), int(edges[i + 1]), config.build(f"chunk_{i:02d}.mp4")) for i in range(n)]
    t0 = time.time()
    with Pool(n) as pool: paths = pool.map(render_chunk, jobs)
    with open(config.build("chunks.txt"), "w") as fh:
        for pth in paths: fh.write(f"file '{pth}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", config.build("chunks.txt"), "-c", "copy",
                    config.build("video_noaudio.mp4")], check=True)
    for pth in paths: os.remove(pth)
    print(f"rendered {nframes} frames ({TOTAL:.1f}s) in {time.time() - t0:.0f}s -> {config.build('video_noaudio.mp4')}")
