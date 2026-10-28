# Style presets: pick by topic

A preset keeps every decision coherent: color grade, typography, backgrounds, graphic vocabulary, music kit, SFX
palette and transition mix. Choose the closest preset and adapt it, but **don't mix two presets**, because the
result looks random. Write your choice in the brief.

Engine knobs referenced below:
- `tone=`: `film` (B/W sepia + scratches), `color` (warm contrast), `gold` (nostalgic amber), `night` (blue),
  `cold` (icy desaturated), `red` (alarm/"wrong"), `none` (graphics).
- Backgrounds: `paper_bg()`, `wood_bg()`, a darkened/blurred photo (`darken(grade(cover(...)))`), or a solid/gradient you draw.
- Fonts: `F_HEAVY` (bold sans, subtitles/labels), `F_SONG` (serif titles), `F_IMPACT` (numbers), `F_ROCK` (slab/vintage latin).
- Music `kit=`: `western`, `electronic`, `cinematic`, `lofi`, `suspense` (see audio.md).

| # | Topic family | Grade / palette | Type & backgrounds | Signature graphics | Music kit & progression | SFX palette | Transitions |
|---|---|---|---|---|---|---|---|
| 1 | **History & old West, frontier, pirates, old trades** | `film` for archival footage and photos, `color`/`gold` for paintings; yellow #FFD600 + red #FF3B30 accents | Songti titles, slab latin, paper & wood backgrounds | WANTED posters, old maps with routes, wooden signs, stamps, year timelines | `western`: Am G F E (Andalusian); drone hook → drive → sad harmonica | gunshot, ricochet, whip, gallop, stamp, scratch, train | punch/whip/flash; fade only for sad |
| 2 | **Ancient civilizations, empires, archaeology** | `gold`, `color`; bronze/sand palette + red | Songti titles, paper background, big serif numbers | maps with pins, empire extent, timelines, split "then vs now" | `cinematic`: Am F C G; drone → drive with taiko → strings sparse | taiko, impact, whoosh, stamp, riser | whip/flash/punch |
| 3 | **War & military history** | `film` / `cold`; desaturated + red | Heavy sans, dark backgrounds | front-line maps with arrows, casualty counters, unit icons | `cinematic` or `suspense`: Am Am F E; tense → half | impact, boom, gunshot (sparingly), heartbeat, riser | punch/flash/glitch |
| 4 | **Space & physics** | `color` on NASA imagery, `night` for space; deep blue + cyan + white | Heavy sans, starfield/black background (draw dots) | scale comparisons (`g_split`), counters with units, orbit/route lines | `electronic` drive or `cinematic` sparse; Am F C G | riser, impact, glitch, ding, whoosh | glitch/whip/punch |
| 5 | **Tech, AI, internet, gadgets** | `color` + `none` graphics; black/near-black with neon cyan #00E5FF + magenta | Heavy sans, Impact numbers, grid/black backgrounds | spec cards, VS splits, bar growth, code/typing labels | `electronic`: Am F C G / Am G F E; drive with clap | glitch, typing, notif, pop, riser, ding | glitch/whip/punch |
| 6 | **Business, money, brands, economics** | `color`; black + gold #FFC400 + green #34C759 for money | Heavy sans, Impact numbers, dark gradient | counters ($, %, ¥), coin rain (`falling(coin_sprite)`), growth timelines, versus | `electronic` drive or `lofi`; tense for crashes | kaching, coin, tick, impact, ding | punch/whip |
| 7 | **Nature, animals, biology** | `color` (natural, slightly warm); green + yellow accents | Heavy sans, paper background | size comparisons, counters, life-cycle timelines, range maps with pins | `lofi` (curious) or `cinematic` (epic predators) | pop, ding, whoosh, heartbeat for tension | whip/punch/fade |
| 8 | **Food, travel, culture, customs** | `color`/`gold` warm, saturated | Heavy sans + Songti, paper/wood | origin maps, ingredient cards, "then vs now" splits | `lofi`: Am Em F G / Am F C E; light → drive | pop, ding, kaching, shutter | whip/punch |
| 9 | **True crime, mysteries, unsolved** | `cold`/`night`/`film`; black + blood red | Heavy sans, dark textured backgrounds | case-file labels, red-string maps (`draw_arrow`), stamps "未解", timelines | `suspense`: drone → tense → sparse; holes before reveals | heartbeat, tick, stamp, impact, whoosh_d, typing | glitch/flash/fade |
| 10 | **Sports, records, competitions** | `color` high contrast; team colors + yellow | Impact numbers huge, Heavy sans | record counters, versus splits, timelines, stats bars | `electronic` drive with clap, or `cinematic` taiko | impact, whoosh, riser, ding | punch/whip/flash, speed ramps |

## How to apply a preset in code

```python
# grade per shot
I("pyramid", tone="gold")                      # ancient
V("nasa_launch", 30.0, tone="color")           # space
# backgrounds for custom graphics
bg = paper_bg(3)                               # history/culture
bg = np.zeros((H, W, 3), np.uint8); bg[:] = (8, 10, 18)     # tech/space dark
# accent colours for label boxes
label("ChatGPT 2022", t, bg=(0, 229, 255))     # tech cyan
label_box("¥ 3.2万亿", 64, BLACK, (255, 196, 0))  # money gold
# music
MUSIC = [dict(t0=0, t1=..., kit="electronic", style="drone", chords=["Am"]), ...]
```

## Consistency rules (any preset)

- At most **2 accent colors** + white/black. Yellow for "look here" (keywords, labels) and red for "danger/wrong/emphasis" is the default pair.
- **One title font** (serif or heavy) for chapter cards and quotes; subtitles are always `F_HEAVY`.
- The header bar, chapter badges, label boxes and subtitles keep the same positions throughout.
- Graphics use the same background family throughout (all paper, or all dark).
- Archival footage keeps its look (`film`). Don't colorize randomly. Modern color footage next to archival is fine when the
  script contrasts then vs now.

## When there's little footage (abstract topics: math, psychology, economics)

Lean on graphics (50–60% of shots): counters, comparison splits, timelines, icon arrays (`person_icon` × N with one
highlighted, like the "1/4" shot), bars growing, maps with pins, quotes. Use photos of people and places mentioned
(portraits, buildings, objects) for the rest. Motion is mandatory either way.
