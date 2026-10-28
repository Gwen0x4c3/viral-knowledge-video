"""Wikimedia Commons search + download (public-domain / CC media for historical & educational topics).

usage:
  python commons.py search "cowboy filetype:video" [--n 15]       list file titles (videos)
  python commons.py search "Bass Reeves" --n 10                    list file titles (images & others)
  python commons.py vinfo "File:The Great Train Robbery (1903).webm"   size/duration + transcode URLs
  python commons.py get-video --project DIR NAME "File:....webm" [--height 480|720|1080]
  python commons.py get-images --project DIR list.txt              list.txt lines: name|File:Title.jpg
  python commons.py get-videos --project DIR list.txt              list.txt lines: name|File:Title.webm[|height]
Re-running any get-* command skips files that already exist, so after FAILs just run it again later.
COMMONS_PAUSE=5 (env) slows down between files if you keep getting HTTP 429.

Hard-won rules (each one cost a failed run):
  * Use the `requests` library (python urllib fails SSL verification on some macOS Pythons).
  * Send a descriptive User-Agent; Wikimedia rate-limits anonymous/default agents (HTTP 429).
  * Thumbnails come from thumb.wikimedia.org, originals from upload.wikimedia.org — in a sandbox, BOTH
    hosts (plus commons.wikimedia.org) must be allowed.
  * Asking for a thumbnail WIDER than the original returns 429/error -> use the original URL instead.
  * Error responses are small HTML pages saved with a .jpg name. Always check content-type == image/*.
  * Throttle (≥1 s between files) and back off on 429.
  * Long films: download the 480p transcode, not the multi-GB original.
"""
import sys, os, time, json, requests
sys.path.insert(0, os.path.dirname(__file__))
import config
ARGV = config.parse_project_arg(sys.argv[1:])
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "EduShortVideoBot/1.0 (educational short-video research; python-requests)"}

def api(**p):
    p["format"] = "json"
    for k in range(5):
        r = requests.get(API, params=p, headers=UA, timeout=30)
        if r.status_code == 200: return r.json()
        time.sleep(3 * (k + 1))
    raise SystemExit(f"Commons API failed: {r.status_code}")

def search(q, n=15):
    d = api(action="query", list="search", srnamespace=6, srlimit=n, srsearch=q)
    return [x["title"] for x in d["query"]["search"]]

def vinfo(title):
    d = api(action="query", titles=title, prop="videoinfo", viprop="url|size|derivatives|mediatype")
    p = list(d["query"]["pages"].values())[0]; vi = p.get("videoinfo", [{}])[0]
    ders = {x.get("height"): x["src"] for x in vi.get("derivatives", []) if "transcoded" in x["src"] and x["src"].endswith(".webm")}
    return dict(width=vi.get("width"), height=vi.get("height"), mb=round(vi.get("size", 0) / 1e6, 1), duration=vi.get("duration"),
                url=vi.get("url"), transcodes=ders)

PAUSE = float(os.environ.get("COMMONS_PAUSE", "2.5"))   # seconds between files; raise to 5-10 if you keep seeing 429

def download(url, out, want_prefix):
    """Download with Wikimedia-friendly behaviour: honour Retry-After, exponential backoff (up to ~4 min total),
    only accept the expected content-type, write to a .part file and rename on success (no half/HTML files)."""
    wait = 5
    for k in range(8):
        try:
            r = requests.get(url, headers=UA, timeout=180, stream=True)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and ct.startswith(want_prefix):
                with open(out + ".part", "wb") as fh:
                    for chunk in r.iter_content(1 << 20): fh.write(chunk)
                os.replace(out + ".part", out)
                return True
            ra = r.headers.get("retry-after")
            wait = max(wait, int(ra)) if (ra and ra.isdigit()) else wait
            print(f"   HTTP {r.status_code} {ct[:30]} -> retry in {wait}s")
        except requests.RequestException as e:
            print("   ", e)
        time.sleep(wait); wait = min(wait * 2, 60)
    return False

def get_video(name, title, height=480):
    info = vinfo(title)
    if info["height"] and info["height"] <= height and (info["mb"] or 0) < 150: url = info["url"]
    else:
        hs = sorted(h for h in info["transcodes"] if h and h <= height) or sorted(info["transcodes"])
        url = info["transcodes"][hs[-1]] if hs else info["url"]
    os.makedirs(config.raw(), exist_ok=True)
    out = config.raw(name + ".webm")
    if os.path.exists(out) and os.path.getsize(out) > 100_000: print("skip (exists)", name); return
    ok = download(url, out, "video")
    print(("OK  " if ok else "FAIL"), name, f"{info['duration'] and round(info['duration'])}s", url[:100])

def get_images(listfile):
    os.makedirs(config.raw("img"), exist_ok=True)
    for line in open(listfile).read().strip().splitlines():
        if not line.strip() or line.startswith("#"): continue
        name, title = [x.strip() for x in line.split("|", 1)]
        out = config.raw("img", name + ".jpg")
        if os.path.exists(out) and os.path.getsize(out) > 5000: continue
        d = api(action="query", titles=title, prop="imageinfo", iiprop="url|size|mime", iiurlwidth=1280)
        p = list(d["query"]["pages"].values())[0]
        if "imageinfo" not in p: print("MISSING", name, title); continue
        ii = p["imageinfo"][0]
        url = ii["url"] if (ii["width"] <= 1280 and not title.lower().endswith((".svg", ".tif", ".tiff"))) else ii.get("thumburl", ii["url"])
        ok = download(url, out, "image")
        print(("OK  " if ok else "FAIL"), name, f"{ii['width']}x{ii['height']}")
        time.sleep(PAUSE)

if __name__ == "__main__":
    cmd = ARGV[0]
    n = int(ARGV[ARGV.index("--n") + 1]) if "--n" in ARGV else 15
    if cmd == "search":
        for t in search(ARGV[1], n): print(t)
    elif cmd == "vinfo": print(json.dumps(vinfo(ARGV[1]), indent=1))
    elif cmd == "get-video":
        h = int(ARGV[ARGV.index("--height") + 1]) if "--height" in ARGV else 480
        get_video(ARGV[1], ARGV[2], h)
    elif cmd == "get-images": get_images(ARGV[1])
    elif cmd == "get-videos":
        for line in open(ARGV[1]).read().strip().splitlines():
            if not line.strip() or line.startswith("#"): continue
            parts = [x.strip() for x in line.split("|")]
            get_video(parts[0], parts[1], int(parts[2]) if len(parts) > 2 else 480); time.sleep(PAUSE)
    else: print(__doc__)
