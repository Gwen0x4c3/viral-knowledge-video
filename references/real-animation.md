# Real animation (beyond zoom & pan)

Ken Burns on photos is "fake motion". For some beats, real animation is far more engaging: a 3D bar chart rising,
a globe with a flight arc, an exploded view of an engine, a molecule rotating, a math proof, a growing network graph.
The workflow is always the same:

**render a short clip (2–5 s, 1080×1920, 30 fps) → save it as `raw/<name>.mp4` → use it like footage:
`V("<name>", 0.0, tone="none", z=(1.0, 1.0))`.** Subtitles, labels, header and sound are added by vidkit on top.

Keep Chinese text out of the 3D render and add it with vidkit labels instead (3D text needs font files and looks blurry).

## Which tool?

| Need | Tool | Notes |
|---|---|---|
| Data-viz in 3D (bars, globes with arcs, particles, abstract shapes), fast | **three.js** via bundled `scripts/anim/three_render.py` | tested: ~0.1–0.3 s/frame on CPU; deterministic; can load glTF models too |
| **Polished scenes with ready-made models** (buildings, people, animals, vehicles), real lighting, shadows, depth of field, motion blur | **Blender (headless `blender -b -P script.py`) + CC0 asset libraries** | best quality-to-automation ratio; free; Eevee ≈ seconds/frame, Cycles = photoreal but slow |
| Math, geometry, equations, physics diagrams | **Manim** | vector-crisp; needs LaTeX for formulas |
| UI / phone-screen / typographic motion in React | **Remotion** | node + Chromium |
| Film-grade photoreal environments & digital humans | Unreal Engine 5 (Quixel Megascans, MetaHuman, Movie Render Queue) | highest fidelity, but heavy and GUI-centric — hard for an agent to drive; only if the user already uses UE |
| Nothing available | vidkit 2D graphics | always works |

### Ready-made 3D asset libraries (check each asset's license; prefer CC0)
| Library | Content | License | Access |
|---|---|---|---|
| **Quaternius** (quaternius.com, also on poly.pizza) | stylized low-poly **animated** characters (incl. cowboys, knights, zombies), **animals** (horse, cow, deer, wolf…), vehicles, buildings, nature packs | CC0 | zip/glTF downloads |
| **Kenney** (kenney.nl) | city/road/car kits, furniture, space, castles, characters — clean low-poly | CC0 | direct zip downloads |
| **Poly Haven** (polyhaven.com) | photoreal **HDRIs** (lighting!), PBR textures, ~500 models (furniture, props, plants, barrels…) | CC0 | JSON API: `api.polyhaven.com/assets?t=models`, `/files/<id>` |
| **Poly Pizza** | aggregator of thousands of CC0/CC-BY low-poly models | CC0 / CC-BY | site + API (key) |
| **Sketchfab** | huge library incl. realistic animals, historic buildings, scanned artifacts, vehicles | many CC-BY / CC0 downloadable | API token required |
| **Mixamo** (Adobe) | rigged humans + thousands of mocap animations (walk, run, fight, dance…) to retarget onto characters | free with Adobe login | manual download |
| **NASA 3D Resources** | spacecraft, rovers, planets, asteroids | public domain | glTF/OBJ downloads |
| **Smithsonian 3D** | scanned fossils, artifacts, aircraft | CC0 (most) | download per item |
| **BlenderKit** | big in-Blender library (free tier) | varies | Blender add-on, login |
| **Khronos glTF Sample Assets** | test models (helmet, fox with animations…) | various permissive | GitHub |
| AI text/image-to-3D (Hunyuan3D-2, TRELLIS, Tripo, Meshy) | a custom object when no library has it | check terms | local GPU or API |

**Recommended stack for 精致 3D beats:** Blender + Poly Haven HDRI (lighting) + Quaternius/Kenney models (stylized,
consistent) or Sketchfab/Smithsonian/NASA (realistic) + Mixamo motions for people. Render 2–4 s clips at 1080×1920 with
Eevee, a slow camera move, depth of field and motion blur, then use them as footage in vidkit. Keep one art style per video
(all low-poly OR all realistic). three.js stays the quick option for charts, globes and abstract data scenes.

**Blender headless pattern:**
```bash
blender -b -P make_scene.py -- --out raw/scene.mp4      # make_scene.py: import glTF (bpy.ops.import_scene.gltf),
                                                        # set world HDRI, add camera + keyframes, set 1080x1920 30fps,
                                                        # render.engine='BLENDER_EEVEE_NEXT', render.filepath, bpy.ops.render.render(animation=True)
```

## three.js with the bundled renderer

```bash
python3 <skill>/scripts/anim/three_render.py --project P scenes/bars3d.js bars --params '{"values":[2,5,3,9]}'
python3 <skill>/scripts/anim/three_render.py --project P scenes/globe_arc.js arc --params '{"from":[23,-102],"to":[31,-99]}'
python3 <skill>/scripts/anim/three_render.py --project P my_scene.js my_clip --duration 4
```
Bundled scenes: `scenes/bars3d.js` (bars rise one by one, hero bar glows in the accent colour, camera cranes up;
params `values`, `accent`, `base`, `bg`) and `scenes/globe_arc.js` (Earth with atmosphere glow and stars, an arc flies between
two lat/lon points while the globe spins into place; pass `"earth_img":"earth_map"` = NASA `File:Land ocean ice 2048.jpg`
from Commons for real continents). Any param ending in `_img` is loaded from raw/img/ and passed as a data URL
(`ctx.loadTex(ctx.params.x_img)`). Colour management (sRGB) and ACES tone mapping are set up by the renderer.

**Scene contract** (plain JS, `THREE` is a global, no imports):
```js
const DURATION = 3.0;
function setup(ctx) {            // ctx = {THREE, scene, camera, renderer, W, H, params}
  ctx.scene.background = new ctx.THREE.Color("#0b0d14");
  // build meshes, lights...
}
function update(t, ctx) {        // MUST depend only on t (frames are rendered out of real time)
  // animate with easing functions of t; move ctx.camera; never use Date.now() or accumulate state
}
```
Style tips: dark background matching the preset; 1 key light + 1 colored rim light; one accent color (the preset's);
slow camera orbit/dolly (never static); ease-out-back for things appearing; finish the motion ~0.5 s before the end
so the cut lands on a settled frame.

**Requirements & pitfalls**
- `pip install playwright && python -m playwright install chromium`. If Playwright's pinned browser build is missing,
  the renderer falls back to system Chrome or any Chromium in the Playwright cache.
- three.js r149 (the last version with a UMD build) is downloaded once from `cdn.jsdelivr.net` into
  `<project>/build/cache/` (set `VIDKIT_CACHE` to change this). In a sandbox, that host must be allowed.
- Tested renders: `bars3d.js` 3.5 s in ~11 s, `globe_arc.js` with a NASA earth texture 3.5 s in ~29 s (M3 Pro, SwiftShader).
- Sandboxed macOS sessions can block Chromium entirely (`bootstrap_check_in ... Permission denied` / `MachPortRendezvous`).
  That's the sandbox, not your code: tell the user and fall back to vidkit 2D graphics, or ask them to run the
  render command outside the sandbox.
- Rendering uses SwiftShader (CPU WebGL): ~0.1–0.4 s per frame. 3 s at 30 fps ≈ 10–40 s. Keep geometry modest.

## Manim quick recipe (if installed)
```python
from manim import *
config.pixel_width, config.pixel_height, config.frame_rate = 1080, 1920, 30
config.frame_width = 9; config.frame_height = 16
class Scene1(Scene):
    def construct(self):
        self.camera.background_color = "#0b0d14"
        bars = VGroup(*[Rectangle(width=1.2, height=h, fill_opacity=1, color=c) for h, c in [(2, GRAY), (5, GRAY), (8, YELLOW)]]).arrange(RIGHT, aligned_edge=DOWN)
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.3), run_time=2)
        self.wait(0.5)
```
`manim -qh --format mp4 -o name scene.py Scene1`, then copy the mp4 to `raw/name.mp4`.

## 2.5D parallax (no extra tools)
For a photo with a clear foreground subject, fake depth by moving two layers at different speeds: the background via
`cover()` with a slow zoom, and the subject cut out with a rough mask (`cv2.grabCut` with a rectangle around the subject)
as an RGBA sprite `blit()`ed with a faster drift. It's subtle but much livelier than a flat zoom. Use it on 1–3 hero images.
