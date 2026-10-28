# Editing: rhythm, shot grammar, layout, code patterns

## 1. Rhythm (the most important section)

Fast but not frantic: the viewer should always feel momentum and still have time to *read the picture*.

| Measure | Target | Why |
|---|---|---|
| Median shot length | **≈ 2.0 s** (normal range 1.2–3.0 s) | under ~1 s the eye can't parse an image, and the video feels 急促 (rushed) |
| Shots in an 80 s video | **35–50** | fewer feels like a slideshow; more feels frantic |
| Fast montage bursts | 3–5 shots of 0.5–0.9 s, **max 2 bursts per video** | only for listing things or a "boom-boom-boom" hook |
| Holds | 2.5–3.5 s for counters, maps, charts, chapter cards, emotional beats | graphics need time to animate and be read |
| Breathing room | after every big beat (reveal, "错！", big number), 1 calmer shot of ≥ 2 s | contrast is what makes the hits feel big |
| Static time | a frame must never be completely static for > 0.6 s | Ken Burns, counters, footage motion |

Rhythm comes from **variation**: short-short-long, never metronomic. Map pace to the emotional curve: hook brisk,
evidence medium, emotional beats slow (2.5–3.5 s shots, `fade`/`leak`/`dip`), finale brisk again.

Global calm knob: `PACE = 1.2` in edit.py lengthens every transition by 20%. Use 1.0 for energetic topics (sports,
tech) and 1.15–1.3 for history, culture and emotional stories.

Speech rate also affects perceived haste. Explanation lines at +18–24% feel energetic. Above +26% everything feels
rushed no matter how you cut.

## 2. Shot grammar: what to show while each phrase is spoken

For every phrase, ask *"what is the viewer imagining right now?"* and show exactly that.

- **Literal first**: a person's name → their portrait; a place → the place or a map pin; a number → a counter/graphic;
  an object → the object; an action → footage of that action.
- **Abstract phrases** ("黄金时代", "讽刺的是") → mood shots: golden-graded wide landscape, a slow push on a lone figure,
  a film-strip frame.
- **Lists** ("套索、马刺、皮护腿") → one card or shot per item, cut on each item word.
- **Contrasts** (A vs B, myth vs truth, then vs now) → `g_split`.
- **Causes chains** ("铁路通了，铁丝网圈了草原，暴雪…") → one shot per cause, cut on each.

Mix types: about 35% video (V), 35% stills (I), 30% graphics (G). Never 3 graphics or 3 stills in a row. Open and close
each section with the strongest visual.

## 3. Choosing transitions (`tin=`)

See `effects-catalog.md` for the full list. Default distribution for an 80 s video:
- 45% `cut` or `punch` (most cuts should be invisible; punch = small zoom-in for emphasis)
- 20% `whip` (topic moves on, energetic)
- 10% `slide` / `zoomblur` / `iris` (variety, at most 3–4 each)
- 5–8 `flash` (section starts, shocks, gunshots)
- 2–4 `glitch` (media, tech, "lies", film references)
- 2–4 `fade` / `leak` / `dip` (emotional beats, time skips, the ending)

Don't use the same fancy transition twice in a row. Fancy transitions draw attention to themselves, so ration them.

## 4. Layout (1080 × 1920)

```
y    0-130   status bar — nothing important
y  130-200   HEADER bar (series/topic title), centred, y=160
y  220-270   chapter badge (left), y=245
y  300-460   shot labels / map titles ("1700年代", "道奇城 · 1878")
y  460-1220  main visual focus area — faces, numbers, graphics live here (counters at y≈820)
y 1250-1420  SUBTITLES (SUB_Y=1330) — keep empty in every graphic
y 1500-1640  secondary labels / captions (names, sources)
y 1650-1920  platform UI (caption, buttons) — keep empty
x  > 960     like/comment buttons between y 900-1650 — no text there
```
For `cover()` crops of portraits, set the focus to `c=(0.5, 0.3)` so faces sit in the upper-middle. Films in 4:3/16:9
cropped to 9:16 lose ~60% of the width: pick moments with a central subject, or use `mode="frame"`.

## 5. Typography and color

- Subtitles: `F_HEAVY` white with a 10 px black stroke and shadow, keywords yellow/red at 1.24×.
- Labels: `label_box()` in yellow with black text (primary), white with black text (secondary), red with white text (alert).
  Max ~12 characters.
- Big numbers: `F_IMPACT` 220–300 px. Titles and quotes: `F_SONG` (serif), 110–170 px.
- Max 2 accent colors (yellow + red by default; per preset otherwise).
- Check every non-Chinese glyph: `→ ♪ ★ ✓ ①` may be missing from a font and render as □. Draw arrows with `draw_arrow()`,
  and use `F_SYMBOL` for ♪ ♫.

## 6. edit.py patterns

### Skeleton
```python
from fx import *; from shots import *; from timeline import L, at, TOTAL
PACE = 1.15; SUB_STYLE = "pop"
HEADER = "好莱坞没告诉你的 · 牛仔真相"; HEADER_FROM = L["L04"]["start"]; HEADER_TO = L["L23"]["start"] - 0.2
CHAPTERS = [(L["L05"]["start"], L["L08"]["start"] - 0.3, "真相①", "牛仔是墨西哥人发明的"), ...]
BIG_SKIP = {("L10", "3000")}     # graphic already shows it
BIG_EXTRA = [dict(t=at("L03", "错"), text="错！", color=RED, size=360, y=760, rot=-8, dur=1.05)]

def build():
    S = []
    def add(t, shot): shot.start = t; S.append(shot); return shot
    add(0.0, V("gtr_final", 2.62, z=(1.35, 1.2), c=(0.5, 0.42), labels=[label("电影里的牛仔", 0.12, y=330, bg=WHITE)]))
    add(at("L01", "是"), V("stagecoach", 177.6, z=(1.05, 1.25), tin="punch"))
    add(at("L02", "白人"), V("stagecoach", 106.0, z=(1.3, 1.5), c=(0.55, 0.35), tin="punch"))
    add(at("L03", "错") - 0.02, V("gtr", 762.6, speed=0.0, tone="red", tin="flash"))   # freeze + red on "错!"
    ...
    return S
```

### Sync a gunshot or other event inside footage to a word
Find the event's source time (e.g. the muzzle-flash frame via per-frame brightness), then start the clip so it lands on
the word: `t0 = event_src_t - (at("L22","观众") - at("L22","一枪"))`.

### Freeze frame
`V(src, t, speed=0.0, tone="red")`. Check the still: freezing on a flash or smoke frame gives a blank image, so pick
the frame *before* the event.

### Labels on shots
`labels=[label("巴斯·里夫斯 Bass Reeves", at("L10", "巴斯"), y=1540, size=48), label("美国联邦副警长", at("L10","巴斯")+0.25, y=1640, size=40, bg=WHITE)]`

### Custom graphic (icon array "1/4")
```python
def g_four():
    t_icons = [at("L08", "四") + 0.1 * i for i in range(4)]; t_hl = at("L08", "黑人")
    def fn(u, d):
        t = S.start + u
        f = darken(grade(cover(load_img("wyoming"), lerp(1.0, 1.1, u / d), 0.5, 0.45), "film"), 0.38)
        for i in range(4):
            k = pop_in(t, t_icons[i])
            hl = i == 3 and t >= t_hl - 0.45
            blit(f, person_icon(ORANGE if hl else (235, 225, 205), 210, hat=True), 165 + i * 250, 900, scale=k * (1.2 if hl else 1))
        if t >= t_hl - 0.45: blit(f, text_sprite("1/4", 230, ORANGE, 12, BLACK, F_IMPACT), W / 2, 500, scale=pop_in(t, t_hl - 0.45))
        return f
    S = G(fn, tin="punch", name="four"); return S
```
Rules for custom graphics: write `fn(u, d, t)`. The renderer passes `t` = absolute seconds, so compare it directly with
`at(...)` times (no `S.start` closure trick needed; the 2-argument form `fn(u, d)` still works for purely local animation).
Compute `at()` times *outside* `fn`, animate everything with `pop_in`/`ease_out`, keep the background moving (slow zoom),
and cache anything expensive (sprites, layers) outside `fn`. A custom `fn` must return an RGB uint8 array of shape (1920, 1080, 3).

### Explaining a mechanism: `g_nodes` (algorithms, networks, protocols, chains of events)
Keep ONE diagram on screen across several lines and drive it with events tied to words, so the picture changes exactly
as the narrator explains each step. Split it into 2–4 shots (one per step, each 3–8 s), cutting away to footage or photos
in between, but keep node positions identical so the viewer stays oriented.
```python
N = ["A", "B", "C", "D", "E"]
ev = [dict(t=0, do="state", node="A", label="领导", color=YELLOW, crown=True)] + \
     [dict(t=0, do="state", node=n, label="跟随者", color=(70, 110, 170)) for n in "BCDE"] + [
     dict(t=at("L08", "心跳"), do="msg", src="A", dst="all", text="心跳", dur=0.6),
     dict(t=at("L09", "宕机"), do="crash", node="A"),
     dict(t=at("L09", "倒计时"), do="timer", node="C", dur=0.9), dict(t=at("L09", "倒计时"), do="timer", node="E", dur=1.4),
     dict(t=at("L10", "竞选"), do="state", node="C", label="候选人", color=ORANGE), dict(t=at("L10", "竞选"), do="badge", node="C", text="任期 2"),
     dict(t=at("L10", "拉票"), do="msg", src="C", dst=["B", "D", "E"], text="投我一票", color=ORANGE),
     dict(t=at("L11", "过半"), do="state", node="C", label="新领导", color=YELLOW, crown=True),
     dict(t=at("L11", "过半"), do="caption", text="3票 = 5台里过半", dur=2.5)]
add(at("L08", "领导"), g_nodes(N, ev, title="第一步：选领导"))
```
Event types: state, msg, crash, recover, timer, log, commit, caption, badge (docstring of `g_nodes` in shots.py).

### Map with a moving camera and pins
1. `sheet.py grid mapname` → read the original pixel coordinates of each place.
2. `g_pins("usmap", [("道奇城", 570, 414), ...], at("L12","五"), z=(1.3, 2.6), focus=(0.47, 0.47), title="堪萨斯")`
3. For maps whose aspect is far from 9:16, pass `box=(300, 1200)` so the map sits in a band over paper instead of being cropped.
4. Route: `g_route("chisholm_map", [(830,1500), (822,1277), ...], "", 1000, "英里", sub="≈ 1600公里")`.

### Recoloring a blank map (highlight a region)
Load a blank outline map, then `cv2.floodFill` at a pixel inside the state/country to get its mask, and blend an accent color
into the mask with a pulsing alpha. That's how the cowboy video highlighted Texas and Kansas.

### Hand-made props
WANTED posters, wooden signs, case files, receipts and phone screens: draw them with PIL on a `paper_bg`/`wood_bg` crop
(rounded rectangles, borders, `F_SONG`/`F_ROCK` text), turn them into an RGBA array once, then `blit()` them with drop-in
(`y = lerp(-400, y_final, ease_out(k/0.25))`) and a damped swing (`rot = 9*sin(k*11)*exp(-k*3.5)`).

## 7. Stills review: what to look for

Render stills at: 0.3 s, mid-hook, each chapter card, every graphic (mid-animation and at its end), every freeze frame,
the final 3 s. For each one check:
- Text inside the subtitle band or under y=1650? Move it.
- Any □ glyph? Change the font or character.
- Is the main subject visible after the crop (faces not cut off at the forehead, not just an empty sky)?
- Numbers overlapping each other ("×12 VS ×3000" collisions)? Shrink or space them out.
- Blank, white or near-black frame? Bad freeze time or an over-zoomed map.
- Does it look like it belongs to the same video as the other stills (same palette and fonts)?
Then `render.py sheet` (1 frame/s overview): look for long stretches of similar-looking frames, which means you need more variety.
