"""Edit decision list. Code patterns: references/editing.md §6; effects: references/effects-catalog.md.

Rules of thumb (details: references/editing.md):
  * median shot ≈ 2 s (1.2-3 s); hold graphics 2-3 s; cut ON words: add(at("L02", "word"), shot)
  * never a static still: every I() has zoom or pan
  * alternate video clip / photo / motion graphic; every number gets a counter or graphic
  * keep text out of the subtitle band (y 1250-1420) and the platform UI (y > 1650)
Replace every TODO_clip / TODO_img with real names from raw/ and raw/img/.
"""
import math
import numpy as np, cv2
from fx import *
from shots import *
from timeline import L, at, TOTAL

PACE = 1.15                                   # transition-length multiplier: 1.0 energetic, 1.2-1.3 calm (history/emotional)
SUB_STYLE = "pop"                             # pop | karaoke | box | bounce | typewriter  (references/effects-catalog.md)
HEADER = "TODO 系列名 · 本期主题"            # persistent top bar (≤ 16 chars)
HEADER_FROM = L["L03"]["start"]; HEADER_TO = L["L06"]["start"] - 0.2
CHAPTERS = []                                 # optional small badge under the header: [(t0, t1, "线索①", "short title"), ...]
BIG_SKIP = set()                              # {("L04", "3000")} when a graphic already shows that keyword
BIG_EXTRA = []                                # centre stamps, e.g. [dict(t=at("L02", "代价"), text="代价", color=RED, size=300, y=760, rot=-8, dur=1.0)]

def build():
    S = []
    def add(t, shot): shot.start = t; S.append(shot); return shot
    # HOOK — your most vivid footage/image; a label naming what the viewer is looking at
    add(0.0, V("TODO_clip", 12.0, z=(1.3, 1.15), name="hook", labels=[label("TODO 画面说明", 0.15, y=330, bg=WHITE)]))
    add(at("L01", "核心问题"), I("TODO_img", z=(1.0, 1.25), tin="punch"))
    add(at("L02", "TODO"), I("TODO_img", z=(1.3, 1.05), c=(0.5, 0.4), tin="whip"))
    # BEAT 1
    add(L["L03"]["start"] - 0.2, I("TODO_img", z=(1.1, 1.3), tin="flash"))
    add(at("L04", "证据"), g_counter("TODO_img", 3000, "TODO 单位", "TODO 上方说明", "TODO 下方说明", at("L04", "3000") - 0.3, 0.7))
    # PAYOFF + ENDING
    add(L["L05"]["start"] - 0.2, g_quote("TODO_img", "TODO 金句第一行", "TODO 第二行"))
    add(at("L06", "选哪个") - 0.4, g_cta("TODO_img", "你选哪个？", "A TODO", "B TODO"))
    add(L["L06"]["end"] + 0.15, g_end_title("TODO_img", "TODO 结尾金句", "TODO"))
    return S

def sfx_cues(shots):
    C = transition_sfx(shots)
    t = at("L04", "3000") - 0.3                                     # counter: ticks while counting, impact on landing
    C += [(t + i * 0.07, "tick", 0.35) for i in range(10)] + [(t + 0.7, "boom", 0.7)]
    C += [(L["L05"]["start"] - 0.2, "boom_s", 0.5), (at("L06", "选哪个"), "ding", 0.6)]
    return sorted(C)

MUSIC = [   # follow the emotional curve of YOUR structure; kits & styles: references/audio.md
    dict(t0=0.0, t1=L["L03"]["start"] - 0.3, kit="western", style="drone", chords=["Am"]),
    dict(t0=L["L03"]["start"] - 0.3, t1=L["L05"]["start"] - 0.2, kit="western", style="drive", melody="A"),
    dict(t0=L["L05"]["start"] - 0.2, t1=TOTAL - 2.3, kit="western", style="sparse", chords=["Am", "F", "C", "E"]),
    dict(t0=TOTAL - 2.3, t1=TOTAL, kit="western", style="end", chords=["Am"]),
]
MUSIC_HOLES = [(L["L05"]["start"] - 0.5, L["L05"]["start"] - 0.2)]   # a beat of silence right before the payoff
