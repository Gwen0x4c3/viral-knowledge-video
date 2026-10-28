# Effects catalog: transitions, subtitle styles, motion effects, graphic templates

Everything here is implemented in `vidkit` and was tested by rendering. Each entry says *when* to use it, because the
effect alone means nothing. Defaults are tuned for a calm-but-lively pace (`PACE = 1.0`; raise to 1.2 for calmer).

## A. Transitions (`tin=` on the incoming shot)

| tin | Duration | Look | Use for | Avoid |
|---|---|---|---|---|
| `cut` | 0 | hard cut | most cuts inside a section; cutting on a word is already dynamic | — |
| `punch` | 0.32 s | incoming shot zooms 1.14→1.0 | emphasis on a new subject (a face, an object being named) | 3+ in a row |
| `whip` | 0.28 s | old shot whips left with motion blur, new arrives from the right | topic moves on, energetic beats | emotional moments |
| `slide` | 0.35 s | new shot pushes the old one up (feed-scroll feel) | next item in a list, "接下来" moments | more than 3–4 per video |
| `zoomblur` | 0.30 s | radial zoom blur through the cut | diving deeper ("放大看", "细节"), entering a map/place | slow sections |
| `iris` | 0.40 s | circle reveal from the centre | revealing an answer or a hidden person | serious/tragic topics |
| `spin` | 0.35 s | rotate + scale + blur | playful topics, "反转" moments | history/tragedy (feels cheap) |
| `flash` | 0.25 s | white flash fading out (+ soft boom sfx) | section/chapter starts, shocks, gunshots, the "错！" hit | > 8 per video |
| `glitch` | 0.22 s | RGB split + slice displacement | media/film/tech/"lie" beats, fake-news, digital topics | nature/emotional |
| `fade` | 0.45 s | crossfade | emotional beats, night scenes, time passing | energetic sections |
| `leak` | 0.50 s | crossfade under a warm light leak | nostalgia, "黄金时代", memories, endings | tech topics |
| `dip` | 0.50 s | dip to black | chapter breaks, time skips, before the final reveal | too often (feels slow) |

Sound: `transition_sfx(shots)` adds the matching whoosh/pop/boom automatically and leaves every third whip/punch silent
so the soundtrack stays clean. fade/leak/dip/cut get no sound by design.

## B. Subtitle styles (`SUB_STYLE` in edit.py)

All styles share: phrase splitting on punctuation, karaoke timing from TTS word boundaries, keyword colors from
`script_data` highlights (`y` yellow, `r` red), auto-shrink for long phrases, `SUB_Y` (default 1330), `SUB_SIZE` (84).

| SUB_STYLE | Behavior | Best for |
|---|---|---|
| `pop` (default) | each char pops in (scale 0.4→1, back-ease) as spoken; keywords slam in from 1.8× | most knowledge videos, energetic |
| `karaoke` | whole phrase visible, colour sweeps over spoken chars (`KARAOKE_COLOR`) | calm/story narration, music-heavy |
| `box` | phrase slides up; keywords get a solid yellow/red rounded box with dark text | business/tech/news, high-contrast footage |
| `bounce` | chars drop in from above with an elastic bounce | playful topics, kids, food, animals |
| `typewriter` | chars appear instantly + blinking cursor | mystery, true crime, documents, hacking |

Extra subtitle knobs: `SUB_COLOR` (base color), `KARAOKE_COLOR`. Big centre pops come from `big` highlights (1 per
~10 s) and `BIG_EXTRA` stamps (e.g. "错！"). Skip a pop with `BIG_SKIP` when a graphic already shows the word.

## C. Shot-level motion effects

| Effect | How | Use for |
|---|---|---|
| Ken Burns push / pull | `I(img, z=(1.0, 1.2))` / `z=(1.3, 1.0)` | every still: push = attention, pull = reveal/context |
| Pan | `c=(0.3, 0.5), c2=(0.7, 0.5)` | wide paintings, panoramas, group photos, following a route |
| Tilt reveal | `c=(0.5, 0.8), c2=(0.5, 0.25)` | reveal a tall subject from feet to face |
| Rotation drift | `rot=(0, 3)` | dreamy/unstable moods (subtle!) |
| Freeze frame | `V(src, t, speed=0.0)` | "错！", "wait…", punchline holds |
| Slow motion | `V(..., speed=0.5)` | dramatic moments, action detail |
| Speed ramp | `V(..., ramp=(1.6, 0.35))` fast→slow; `(0.4, 2.0)` slow→fast | rush into a key moment / whoosh away from it |
| Colour drain | `desat_in=0.25` | deflation beats ("其实少得可怜") |
| Fade to black | `fade_out=1.0` | "就这样消失了", endings of sections |
| Red alarm grade | `tone="red"` | "wrong", danger, crisis |
| Night grade | `tone="night"` + moon/glow graphic | night scenes |
| Film look | `tone="film"` (auto scratches, flicker, grain) | archival material |
| Camera shake | automatic on `gunshot`, `boom`, `stamp`, `taiko`, `impact` sfx cues | impacts |
| White flash | automatic on `gunshot` / `flash` sfx cues | shots, lightning, camera flashes |
| Split screen | `g_split(top, bot, ...)` | comparisons, "prototype?", then vs now |
| Particles | `snow(f, u)`, `falling(f, coin_sprite(), t, t0)` | weather, money, notes (♪ via `F_SYMBOL`) |
| Light leak | `light_leak(img, k)` in a custom G | warm nostalgic flares |
| Zoom blur | `radial_blur(img, 0.2)` in a custom G | speed, impact, "zoom into" |

## D. Graphic templates (`shots.py`)

| Template | What it shows | Hold |
|---|---|---|
| `g_chapter(n, title, img, red=False, word="真相")` | chapter stinger: darkened image, diagonal band, big number, title box | 1.1–1.8 s |
| `g_counter(img, target, suffix, cap1, cap2, t_go, dur_count)` | number counts up to target in sync with speech, then shakes | 1.8–2.6 s |
| `g_split(top, bot, lt, lb, badge)` | top/bottom comparison with centre badge (VS, 原型?, 对比) | 2–4 s |
| `g_years(y0, y1, big, sub)` | timeline bar fills from y0 to y1 + huge headline ("20年") | 1.8–2.5 s |
| `g_route(map, pts, ..., total, unit)` | route draws across a map with the camera following + distance counter | 2–3 s |
| `g_pins(map, pins, t_first, title=, box=)` | map zooms in, pins pop one by one with names | 2–3 s |
| `g_filmstrip(img)` | image inside moving film sprockets | 1.2–2 s |
| `g_quote(img, line1, line2, video=)` | big serif statement over a darkened image/video | 2–3 s |
| `g_cta(img, question, a, b)` | comment-bait speech bubble with two options | 1.3–2 s |
| `g_nodes(nodes, events, title=)` | **animated system diagram**: nodes with roles/colours, messages flying, crashes, countdown rings, log boxes, commits, captions — driven by word-synced events | 3–8 s per step |
| `g_end_title(img, line1, line2, video=)` | final quote that fades to black | 2–2.5 s |

Custom graphics (posters, signs, icon arrays, money rain, VS stats, night scenes, maps with highlighted regions) are
built from the `fx` primitives. Patterns are in `editing.md` §6.

## E. Real 3D / vector animation

For things zoom-and-pan can't fake (3D charts, globes with flight arcs, rotating objects, mechanical processes,
math animations), render a real animated clip and drop it in as footage. See `real-animation.md`.
