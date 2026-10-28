"""Render a real 3D animation with three.js in headless Chromium -> raw/<name>.mp4 (1080x1920, 30 fps).
Then use it in edit.py like any footage: V("<name>", 0.0, tone="none").

usage: python three_render.py --project DIR scenes/bars3d.js NAME [--duration 3.0] [--fps 30] [--params '{"values":[3,9,4]}']

Scene file contract (plain JS, no imports — THREE is a global):
    const DURATION = 3.0;                       // optional, seconds
    function setup(ctx) { ... }                 // ctx = {THREE, scene, camera, renderer, W, H, params, loadTex}
    function update(t, ctx) { ... }             // t = seconds; MUST be a pure function of t (deterministic frames)
Rendering is frame-by-frame (not real time), so heavy scenes are fine — they just take longer.
Text: put Chinese text on top later with vidkit labels/subtitles (3D text needs font files; avoid).
Images: any param whose key ends in "_img" names a file in raw/img/ (without .jpg); it is passed to the scene as a
data URL, e.g. --params '{"earth_img":"earth_map"}'  ->  ctx.loadTex(ctx.params.earth_img)

Requirements: `pip install playwright && python -m playwright install chromium` and, once, network access to
cdn.jsdelivr.net (three.js is downloaded to <project>/build/cache/, or $VIDKIT_CACHE). WebGL runs on SwiftShader (CPU) if no GPU.
"""
import sys, os, json, subprocess, time, pathlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vidkit"))
import config
ARGV = config.parse_project_arg(sys.argv[1:])
THREE_URL = "https://cdn.jsdelivr.net/npm/three@0.149.0/build/three.min.js"   # last version with a UMD build
CACHE = pathlib.Path(os.environ.get("VIDKIT_CACHE") or config.build("cache")); CACHE.mkdir(parents=True, exist_ok=True)
THREE = CACHE / "three-0.149.0.min.js"

def get_three():
    if THREE.exists() and THREE.stat().st_size > 500_000: return
    import requests
    r = requests.get(THREE_URL, timeout=60); r.raise_for_status()
    THREE.write_bytes(r.content)

HTML = """<!doctype html><html><body style="margin:0;background:#000"><canvas id="c" width="%(W)d" height="%(H)d"></canvas></body></html>"""
BOOT = """
window.__ctx = (() => {
  const W = %(W)d, H = %(H)d;
  THREE.ColorManagement.legacyMode = false;          // hex colours are sRGB -> correct, non-washed-out colours
  const loadTex = (url) => { const t = new THREE.TextureLoader().load(url); t.encoding = THREE.sRGBEncoding; t.anisotropy = 8; return t; };
  const renderer = new THREE.WebGLRenderer({canvas: document.getElementById('c'), antialias: true, preserveDrawingBuffer: true});
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, W / H, 0.1, 2000);
  const ctx = {THREE, scene, camera, renderer, W, H, params: %(params)s, loadTex};
  setup(ctx);
  return ctx;
})();
window.__render = (t) => { update(t, window.__ctx); window.__ctx.renderer.render(window.__ctx.scene, window.__ctx.camera); return true; };
"""

GL_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
def launch(p):
    """Playwright's pinned browser build often doesn't match what is installed. Try, in order: the pinned build,
    system Google Chrome, then any Chromium found in the Playwright cache."""
    import glob
    try: return p.chromium.launch(args=GL_ARGS)
    except Exception as e: err = e
    try: return p.chromium.launch(channel="chrome", args=GL_ARGS)
    except Exception: pass
    home = os.path.expanduser("~")
    pats = [home + "/Library/Caches/ms-playwright/chromium-*/chrome-mac*/*.app/Contents/MacOS/*",
            home + "/Library/Caches/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell",
            home + "/.cache/ms-playwright/chromium-*/chrome-linux*/chrome",
            home + "/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell"]
    for pat in pats:
        for exe in sorted(glob.glob(pat), reverse=True):
            try: return p.chromium.launch(executable_path=exe, args=GL_ARGS)
            except Exception: continue
    raise SystemExit(f"no usable Chromium. Run: python -m playwright install chromium\n{err}")

def main():
    scene_file, name = ARGV[0], ARGV[1]
    dur = float(ARGV[ARGV.index("--duration") + 1]) if "--duration" in ARGV else None
    fps = int(ARGV[ARGV.index("--fps") + 1]) if "--fps" in ARGV else 30
    params = json.loads(ARGV[ARGV.index("--params") + 1]) if "--params" in ARGV else {}
    import base64
    for k, v in list(params.items()):
        if k.endswith("_img"):
            pth = v if os.path.exists(v) else config.raw("img", v + ".jpg")
            params[k] = "data:image/jpeg;base64," + base64.b64encode(open(pth, "rb").read()).decode()
    params = json.dumps(params)
    src = open(scene_file if os.path.exists(scene_file) else os.path.join(os.path.dirname(__file__), scene_file)).read()
    get_three()
    from playwright.sync_api import sync_playwright
    W, H = config.W, config.H
    out = config.raw(name + ".mp4"); os.makedirs(config.raw(), exist_ok=True)
    with sync_playwright() as p:
        b = launch(p)
        page = b.new_page(viewport={"width": W, "height": H})
        page.set_content(HTML % dict(W=W, H=H))
        page.add_script_tag(path=str(THREE))
        page.add_script_tag(content=src)
        if dur is None: dur = page.evaluate("typeof DURATION !== 'undefined' ? DURATION : 3.0")
        page.add_script_tag(content=BOOT % dict(W=W, H=H, params=params))
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-c:v", "png", "-r", str(fps), "-i", "-",
                               "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        n = int(round(dur * fps)); t0 = time.time()
        for i in range(n):
            if i == 0: page.wait_for_timeout(300)        # let textures decode before the first frame
            page.evaluate(f"window.__render({i / fps})")
            ff.stdin.write(page.locator("#c").screenshot(type="png"))
        ff.stdin.close(); ff.wait(); b.close()
    print(f"-> {out}  ({n} frames, {time.time() - t0:.0f}s)")

if __name__ == "__main__":
    main()
