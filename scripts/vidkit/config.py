"""Project paths, video constants and font discovery.

Every vidkit tool works on ONE project directory, chosen by (in order):
  1. --project DIR on the command line (tools call set_project())
  2. the VIDKIT_PROJECT environment variable
  3. the current working directory

Project layout (create with new_project.py):
  script_data.py   narration lines + header/chapter config      (you write this)
  edit.py          shots, sfx cues, music sections               (you write this)
  raw/             downloaded footage (*.webm/*.mp4) and raw/img/*.jpg
  build/           intermediate files (tts/, stills/, sheets/, chunks, mix.wav)
  out/             final mp4
"""
import os, sys, glob

W, H, FPS = 1080, 1920, 30
PROJECT = os.path.abspath(os.environ.get("VIDKIT_PROJECT", os.getcwd()))

def set_project(p):
    global PROJECT
    PROJECT = os.path.abspath(p)
    os.environ["VIDKIT_PROJECT"] = PROJECT
    if PROJECT not in sys.path: sys.path.insert(0, PROJECT)

def parse_project_arg(argv):
    """Strip `--project DIR` from argv (in place) and activate it."""
    if "--project" in argv:
        i = argv.index("--project"); set_project(argv[i + 1]); del argv[i:i + 2]
    else:
        set_project(PROJECT)
    return argv

def path(*p): return os.path.join(PROJECT, *p)
def raw(*p): return os.path.join(PROJECT, "raw", *p)
def build(*p):
    d = os.path.join(PROJECT, "build"); os.makedirs(d, exist_ok=True); return os.path.join(d, *p)

# ---------------------------------------------------------------- fonts
# (path, ttc index). The first existing candidate wins. Add your own if none exist.
_CANDIDATES = {
    "heavy": [  # bold sans for subtitles / labels — must contain CJK glyphs
        ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/*/AssetData/Lantinghei.ttc", 2),   # macOS 兰亭黑 Heavy
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 1),                                        # macOS W6
        ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/*/AssetData/PingFang.ttc", 0),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", 2),
        ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 2),
        ("/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc", 2),
        ("C:/Windows/Fonts/msyhbd.ttc", 0),
    ],
    "serif": [  # elegant CJK serif for titles / chapter cards / endings
        ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),                                     # 宋体 Black
        ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc", 2),
        ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", 2),
        ("C:/Windows/Fonts/simsun.ttc", 0),
    ],
    "impact": [  # condensed latin/digits for big numbers
        ("/System/Library/Fonts/Supplemental/Impact.ttf", 0),
        ("/usr/share/fonts/truetype/msttcorefonts/Impact.ttf", 0),
        ("C:/Windows/Fonts/impact.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
    ],
    "slab": [  # western/vintage latin (WANTED posters etc.)
        ("/System/Library/Fonts/Supplemental/Rockwell.ttc", 1),
        ("/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc", 1),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 0),
    ],
    "symbol": [  # ♪ ♫ ★ ✓ etc.
        ("/Library/Fonts/Arial Unicode.ttf", 0),
        ("/System/Library/Fonts/Apple Symbols.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
    ],
}

def _find(kind):
    for pat, idx in _CANDIDATES[kind]:
        hits = sorted(glob.glob(pat))
        if hits: return (hits[0], idx)
    return None

FONTS = {k: _find(k) for k in _CANDIDATES}
for _k in ("impact", "slab", "symbol", "serif"):
    if FONTS[_k] is None: FONTS[_k] = FONTS["heavy"]

def check_fonts():
    if FONTS["heavy"] is None:
        raise SystemExit("vidkit: no bold CJK font found. Install Noto Sans CJK (e.g. `apt install fonts-noto-cjk`) "
                         "or add a path to _CANDIDATES['heavy'] in vidkit/config.py")
    return FONTS

if __name__ == "__main__":
    for k, v in FONTS.items(): print(f"{k:7s} {v}")
