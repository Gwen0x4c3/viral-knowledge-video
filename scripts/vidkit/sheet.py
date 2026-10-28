"""Look at footage before using it (never pick timecodes blind).

usage:
  python sheet.py --project DIR video SRC [--every 8] [--cols 10]   contact sheet of raw/SRC.webm, every N s, timestamps burned in
  python sheet.py --project DIR peek SRC@12.5 SRC2@40 ...           exact frames at given source times
  python sheet.py --project DIR images                              all raw/img/*.jpg in one labelled grid
  python sheet.py --project DIR grid IMG                            image with pixel-coordinate grid (for map pins / routes)
  python sheet.py --project DIR check                               validate ALL assets: catches silently broken files
                                                                    (error pages saved as .jpg, black/white/flat images from bad
                                                                    PDF conversions, tiny images, videos that decode no frames)
Outputs go to build/sheets/. Open them with your image viewer / Read tool.
Note: ffmpeg's drawtext filter is often missing; labels are drawn with PIL instead.
"""
import sys, os, glob, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import config
ARGV = config.parse_project_arg(sys.argv[1:])
from PIL import Image, ImageDraw

def grab(src, t, w=240, h=180):
    p = next((config.raw(src + e) for e in (".webm", ".mp4", ".mov", ".mkv") if os.path.exists(config.raw(src + e))), None)
    if not p: raise SystemExit(f"no raw/{src}.*")
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", p, "-frames:v", "1", "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombytes("RGB", (w, h), b) if len(b) == w * h * 3 else Image.new("RGB", (w, h))

def duration(src):
    p = next(config.raw(src + e) for e in (".webm", ".mp4", ".mov", ".mkv") if os.path.exists(config.raw(src + e)))
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)

def tile(ims, labels, cols, out):
    w, h = ims[0].size; rows = (len(ims) + cols - 1) // cols
    M = Image.new("RGB", (cols * w, rows * h))
    for i, (im, lb) in enumerate(zip(ims, labels)):
        d = ImageDraw.Draw(im); d.rectangle((0, 0, 8 * len(lb) + 8, 16), fill=(0, 0, 0)); d.text((4, 2), lb, fill=(255, 255, 0))
        M.paste(im, ((i % cols) * w, (i // cols) * h))
    os.makedirs(config.build("sheets"), exist_ok=True); M.save(config.build("sheets", out), quality=85); print("->", config.build("sheets", out))

if __name__ == "__main__":
    cmd = ARGV[0]
    if cmd == "video":
        src = ARGV[1]; every = float(ARGV[ARGV.index("--every") + 1]) if "--every" in ARGV else None
        cols = int(ARGV[ARGV.index("--cols") + 1]) if "--cols" in ARGV else 10
        dur = duration(src); every = every or max(1.0, dur / 100)
        ts = [round(x, 1) for x in [i * every for i in range(int(dur / every))]][:150]
        tile([grab(src, t) for t in ts], [f"{t:.0f}s" for t in ts], cols, f"{src}.jpg")
    elif cmd == "peek":
        pairs = [a.split("@") for a in ARGV[1:]]
        tile([grab(s, float(t)) for s, t in pairs], [f"{s}@{t}" for s, t in pairs], 6, "peek.jpg")
    elif cmd == "images":
        fs = sorted(glob.glob(config.raw("img", "*.jpg")))
        ims = []
        for f in fs:
            im = Image.open(f).convert("RGB"); im.thumbnail((240, 240)); c = Image.new("RGB", (240, 240)); c.paste(im, ((240 - im.width) // 2, (240 - im.height) // 2)); ims.append(c)
        tile(ims, [os.path.basename(f)[:-4] for f in fs], 8, "images.jpg")
    elif cmd == "grid":
        p = config.raw("img", ARGV[1] + ".jpg"); im = Image.open(p).convert("RGB"); w, h = im.size; d = ImageDraw.Draw(im)
        st = max(w, h) // 10
        for x in range(0, w, st): d.line([(x, 0), (x, h)], fill=(255, 0, 0), width=max(1, w // 600)); d.text((x + 3, 3), str(x), fill=(255, 0, 0))
        for y in range(0, h, st): d.line([(0, y), (w, y)], fill=(0, 0, 255), width=max(1, w // 600)); d.text((3, y + 3), str(y), fill=(0, 0, 255))
        im.thumbnail((1000, 1000)); os.makedirs(config.build("sheets"), exist_ok=True)
        out = config.build("sheets", f"grid_{ARGV[1]}.jpg"); im.save(out); print("->", out, f"(original {w}x{h}; labels are ORIGINAL pixel coords)")
    elif cmd == "check":
        import numpy as np
        bad = 0
        for f in sorted(glob.glob(config.raw("img", "*"))):
            nm = os.path.basename(f)
            try:
                im = Image.open(f).convert("L"); w, h = im.size; a = np.asarray(im.resize((64, 64)), np.float32)
            except Exception as e:
                print(f"BAD   img/{nm}: not an image ({os.path.getsize(f)} bytes) — probably an HTML error page; re-download"); bad += 1; continue
            prob = []
            if a.mean() < 12: prob.append("almost black (bad PDF/SVG conversion?)")
            if a.mean() > 245: prob.append("almost white")
            if a.std() < 4: prob.append("flat / no detail")
            if max(w, h) < 400: prob.append(f"tiny {w}x{h} (will look blurry; use only small, framed)")
            if prob: print(f"WARN  img/{nm}: " + "; ".join(prob)); bad += 1
        for f in sorted(glob.glob(config.raw("*.*"))):
            if not f.lower().endswith((".webm", ".mp4", ".mov", ".mkv")): continue
            src = os.path.basename(f).rsplit(".", 1)[0]
            try:
                d = duration(src); im = grab(src, min(1.0, d / 2))
                if np.asarray(im).mean() < 3: print(f"WARN  {os.path.basename(f)}: first frame black (check with peek)")
                print(f"ok    {os.path.basename(f)}  {d:.1f}s")
            except Exception as e:
                print(f"BAD   {os.path.basename(f)}: cannot decode ({e})"); bad += 1
        print(f"{bad} problem(s)" if bad else "all assets look valid")
    else: print(__doc__)
