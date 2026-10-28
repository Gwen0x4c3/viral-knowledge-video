---
name: viral-knowledge-video
description: Produce a complete, fully edited viral-style vertical knowledge short video (Douyin / TikTok / Bilibili / Reels / Shorts, 9:16 1080x1920, 60-150 s) from just a topic — angle + script, fact discipline, expressive TTS voiceover with word timing, public-domain footage/photos, procedural BGM + sound effects, animated karaoke subtitles, transitions, motion graphics, optional real 3D animation (three.js), and QA. Use whenever the user asks for a 短视频 / 知识视频 / 科普视频 / 抖音视频 / B站视频 / TikTok / Shorts / Reels / explainer video / "make a video about X", wants voiceover + subtitles + BGM rendered into an mp4, or wants to batch-produce knowledge videos — even if they don't say "viral".
---

# Viral Knowledge Short Video

## 0. Prerequisites: check these before accepting the task

| Requirement | Why | If missing |
|---|---|---|
| **Vision (the model can read images)** | You must look at contact sheets to pick footage moments, read map coordinates, and inspect rendered stills for layout bugs. Without seeing, you will ship broken frames. | Don't attempt the full workflow. Tell the user that this skill needs an image-capable model. |
| **Code execution (shell + Python 3.9+)** | The whole video is rendered by scripts | not possible without it |
| **ffmpeg + ffprobe** on PATH | decoding footage, encoding, loudness | `brew install ffmpeg` / `apt install ffmpeg` |
| Python packages: `numpy scipy opencv-python-headless pillow edge-tts requests` (+ `openai-whisper` or `faster-whisper` for the audio check) | engine dependencies | `pip install ...` |
| A **bold CJK font** (macOS has one; Linux: `fonts-noto-cjk`) | subtitles and labels | `python3 $K/config.py` shows what was found |
| **Network**: `speech.platform.bing.com` (TTS), `commons.wikimedia.org`, `upload.wikimedia.org`, `thumb.wikimedia.org` (media); optional `cdn.jsdelivr.net` (three.js) | voice and assets | In a sandbox, declare these hosts. If blocked, tell the user which host; don't work around the sandbox. |
| ~2 GB free disk, 4+ CPU cores | footage and parallel rendering | fewer cores still work, just slower |
| Optional: a premium TTS key (Volcengine 豆包 / MiniMax / ElevenLabs / Azure) or a local CosyVoice3 setup | the voice is the biggest quality factor; edge-tts (default) is decent but slightly robotic | ask the user once; otherwise use edge-tts (`references/audio.md` §1) |
| Optional: Playwright + Chromium (three.js) and/or Blender + CC0 model libraries | real 3D animation | skip 3D and use 2D graphics (`references/real-animation.md`) |
| Time budget: 1–2 hours of agent work | many render/inspect loops | warn the user up front |

You can't *hear* audio. Verify it by measurement and transcription (Step 6), and say so in the final report.

## What you deliver

An **mp4 a creator could post today**: a hook in the first 3 s, a steady flow of relevant visuals (a new one about every
2 s), expressive narration, subtitles that pop word by word, music that changes with the mood, sound effects on every
key moment, and a satisfying ending. It's built locally with the bundled engine **vidkit** (Python + ffmpeg).

vidkit does all the plumbing: TTS timing, the shot timeline, 12 transitions, color grades, film finish, 5 subtitle styles,
graphic templates, procedural music, SFX, mixing and encoding. **Your job is the creative layer**, in two files
per project: `script_data.py` (what is said) and `edit.py` (what is seen and heard).

```
K=<absolute path of this skill>/scripts/vidkit      # every tool takes --project <project-dir>
```

## Quality bar (each rule exists because breaking it was a real failure)

1. **A story engine, not a list.** One central question (or a protagonist with stakes) is opened in the first 3 s and
   paid off at the end; beats escalate; facts are evidence or episodes, not a checklist. Accurate-but-listy videos
   ("N个真相") lose viewers at every chapter break, and Chinese viewers instantly recognize 营销号 formulas
   ("你以为…？错！", "最后一个最扎心", a bare "评论区聊聊"). Never reuse a previous video's structure or hook pattern.
   The hook is a vivid image plus the question, in ≤ 3 s, with no greetings or channel intro.
2. **Pace: lively but readable.** Median shot ≈ **2 s** (range 1.2–3 s), 35–50 shots for ~80 s. Hold graphics and
   emotional beats for 2.5–3.5 s. Use at most 2 short fast-cut bursts. Under ~1 s per image the viewer can't read
   the picture and the video feels 急促 (rushed); over 3.5 s of a still image feels like a slideshow.
   (Details: `references/editing.md` §1.)
3. **Cuts land on words.** Every cut, label, pop and sound is timed with `at("Lxx", "word")`, never hand-typed seconds.
4. **Information density — of the right kind.** Story topics: every line carries a concrete fact. **Concept topics
   (algorithms, science, systems): every line moves *understanding* forward**: terms defined before use, one running
   example, a "why" for every mechanism, full sentences with subjects and 因为/所以. Telegraph-style fragments that
   sound punchy but explain nothing are the #1 script failure. Every number on screen gets a counter or graphic.
5. **Everything moves.** Ken Burns on every still, animated graphics, footage with motion. Nothing fully static for more than 0.6 s.
6. **Readable layout.** Subtitles at y≈1250–1420. Graphics avoid that band and everything below y=1650 (platform UI).
   1–3 highlighted keywords per line. No □ missing glyphs.
7. **Sound design.** Sounds on transitions (not every single one), numbers tick and land, reveals ding, stamps thud.
   Music sections follow the mood and drop out before the biggest hit. The voice is always on top.
8. **Ending:** a twist or callback, a comment prompt, then a ~2 s closing shot that fades out. Never end abruptly.
9. **Facts must be right.** Hedge contested claims ("传说", "据估计"). Never invent numbers or quotes.
10. **Legal media only**: public domain, CC, user-provided, or procedural. No modern film/TV clips, watermarks or logos.

## The procedure (follow in order; each step ends with a gate)

### Step 1 — Angle, structure, style → read `references/script-writing.md` and `references/style-presets.md`
- Turn the topic into an **angle**: a question or claim with tension ("刀枪不入的骑士，为什么会消失？", not "骑士文化介绍").
  Start from what this audience already knows (games, films, everyday life) and bridge from there.
- **Pick the MODE**: *story/myth-busting* (60–90 s, surprise) or *concept explainer* (90–150 s, understanding). See
  script-writing.md §1b and §10. Explainers start with 3 learning objectives: what the viewer can explain afterwards.
- **Pitch three, then choose** (script-writing.md §1c): 3 pitches with *different* structures (mystery / protagonist arc /
  timeline / comparison / POV / list / explainer steps), scored on engine, escalation, bridge, material fit, freshness and
  load. Write the scores in the brief.
- Fix **one style preset** (grade, fonts,
  graphics vocabulary, music kit, SFX palette, subtitle style).
- Write the brief: the chosen pitch (central question, beats, payoff, the line viewers will repeat), emotional curve,
  preset, and a fact table with sources.
- **Gate:** one question or protagonist runs through every beat, the best beat is last, each beat has a verifiable fact,
  the hook would stop *you* scrolling, and the result doesn't resemble the previous video's structure.

### Step 2 — Script → `script_data.py`
- `python3 $K/new_project.py <dir>` creates the project from the templates.
- Story mode: 18–24 lines, 8–30 characters each, ≈300–380 characters for 70–90 s. Explainer mode: 22–34 lines, up to ~40
  characters, ≈450–650 characters for 90–150 s, with ≥ 60% of the time on the core mechanism and one running example.
  Technical names go in `SAY` (pronunciation map) so the voice says them correctly while subtitles keep the spelling. Per-line `rate`/`pitch` give expressive delivery
  (explanations +18~24%, never above +26%; emotional beats slower and lower). 1–3 highlighted keywords per line.
- **Gate:** read it as a viewer. Every line adds a fact or tension, and the hook's promise matches the body.
  **Explainer mode, mandatory:** the subtitle-only comprehension test. From the line texts alone, write the 3-sentence
  explanation, or better, ask a fresh sub-agent to. If it doesn't match your objectives, fix the script before any visuals.
  **Story mode:** read the lines only and ask: can I state the central question after line 3? Does every beat move toward
  its answer? Is there at most ~1 new proper noun per 8 s?

### Step 3 — Voice → measure
```bash
python3 $K/tts.py --project P            # or: tts.py --project P L03 L07  (redo only some lines)
python3 $K/timeline.py --project P       # word timings + TOTAL
```
- **Gate:** TOTAL is 60–90 s (story) or 90–150 s (explainer). Too long: cut side facts, not explanations or pauses.
  Then check technical terms in a quick Whisper pass and fix them via `SAY`.

### Step 4 — Shot list, then assets → read `references/asset-sourcing.md`
- First write the shot list: for each phrase, what's on screen. Mark it V (video ~35%), I (image ~35%) or G (graphic ~30%),
  and decide which 2–4 "wow" beats deserve real 3D animation (`references/real-animation.md`).
- Then search and download (`commons.py search / get-videos list / get-images list`; re-run to resume after 429s), and run
  `sheet.py --project P check` to catch silently broken files (black PDF renders, error pages).
- **Look at every asset**: `sheet.py video SRC`, `sheet.py peek SRC@t`, `sheet.py images`, `sheet.py grid MAP`. Open
  the images and confirm each timecode and crop.
- **Gate:** every shot-list row has a confirmed asset/timecode or a graphic.

### Step 5 — Edit → `edit.py`; read `references/editing.md` + `references/effects-catalog.md`
- `build()`: `add(at(line, word), V(...) | I(...) | g_template(...) | custom G(...))`. Custom graphics: `fn(u, d, t)`.
- Mechanisms are shown with `g_nodes` (animated system diagram driven by word-synced events), not with stock photos.
- Choose transitions deliberately (mostly cut/punch, some whip/slide, rare flash/glitch/iris/zoomblur/spin, and
  fade/leak/dip for emotion), plus `PACE` (1.0 energetic … 1.3 calm), `SUB_STYLE`, `HEADER`, `CHAPTERS`, `BIG_EXTRA`, `BIG_SKIP`.
- Optional 3D clips: `python3 <skill>/scripts/anim/three_render.py --project P scenes/bars3d.js bars ...` → use as `V("bars", 0)`.
- **Gate (stills):** `python3 $K/render.py --project P stills <10-15 times>` covering every graphic, freeze and section.
  Open the mosaic `build/sheets/stills.jpg` and check for text in the subtitle band, □ glyphs, blank frames, bad crops, overlapping numbers and an
  inconsistent style. Fix and re-check. Then `render.py --project P sheet` (1 frame/s): is it varied, and is the pace calm enough?

### Step 6 — Music + SFX → read `references/audio.md`
- `MUSIC` sections follow the emotional curve; `MUSIC_HOLES` before big hits; `music_extra()` for one-off touches.
- `sfx_cues(shots)` = `transition_sfx(shots)` + sounds for numbers, stamps, reveals and events. Keep SFX off key spoken words.
```bash
python3 $K/mix.py --project P && python3 $K/check_audio.py --project P --whisper
```
- **Gate:** no clipping, no unintended silent music, and the Whisper transcript matches the script on key words.

### Step 7 — Render and finalize
```bash
python3 $K/render.py --project P                     # parallel; JOBS=N to limit
python3 $K/finalize.py --project P "out/<标题>.mp4"   # mux, -14 LUFS, ~12 Mbps, QA sheet
```
- **Gate:** go through `references/qa-checklist.md` against `build/sheets/final.jpg`.

### Step 8 — Report
Give the path, duration, resolution and loudness, plus the title, angle, beat outline, techniques and style preset. State
honestly: how audio was verified (not by listening), that procedural music is functional rather than studio-grade, which
claims are estimates or contested and how they were phrased, and anything skipped (e.g. 3D blocked by the sandbox).
Offer concrete tweaks.

## Files

| Path | Content | Read at |
|---|---|---|
| `references/script-writing.md` | angles, hook formulas, structures, density, TTS-friendly writing, fact rules, annotated example script | Steps 1–2 |
| `references/style-presets.md` | 10 topic families → grade, palette, fonts, graphics, music kit, SFX, transitions | Step 1 |
| `references/asset-sourcing.md` | legal sources, search tactics, download pitfalls, how to inspect footage | Step 4 |
| `references/editing.md` | rhythm/pacing, shot grammar, transition mix, layout zones, typography, **code patterns** | Step 5 |
| `references/effects-catalog.md` | every transition, subtitle style, motion effect and graphic template, with when-to-use | Step 5 |
| `references/real-animation.md` | three.js (bundled renderer), Manim, Remotion, Blender, 2.5D parallax | Steps 4–5 |
| `references/audio.md` | voices, music sections and kits, SFX mapping, mixing, verification | Steps 3, 6 |
| `references/qa-checklist.md` | final checklist + table of known failures and fixes | Steps 5, 7 |
| `scripts/vidkit/` | engine; each file's docstring documents its CLI/API (`config, fx, shots, timeline, tts, render, mix, audio_lib, commons, sheet, check_audio, finalize, new_project`) | as needed |
| `scripts/anim/` | `three_render.py` + example scenes `bars3d.js`, `globe_arc.js` | Step 5 |
| `templates/project/` | starter `script_data.py` + `edit.py` with TODOs | Step 2 |

## Traps seen in real runs
- **Template collapse**: copying the last video's skeleton (hook pattern, "N个真相", chapter cards, ending) onto a new topic.
  Each topic gets the structure its material deserves.
- **Fact soup**: 15+ names and dates in 80 s that nobody can hold in their head. Fewer, more vivid facts, tied to the question.
- **Slideshow**: few, long, slowly zooming stills. **Frantic**: 65 shots in 89 s plus constant whooshes (viewers called it 急促).
  Aim between them: ~2 s median, varied lengths, rationed effects.
- Visuals that don't match the sentence being spoken. Show what is being said, *now*.
- Explaining a concept with trivia-style fragments ("心跳一断，随机闹钟开始倒数"): sounds punchy, teaches nothing.
- Downloading assets before the script and shot list exist.
- Hand-typed timings that break after re-running TTS. Use `at()`.
- Long on-screen text. Labels are ≤ 12 characters; the narration carries the information.
- Music as loud as the voice, or one loop for 90 s.
- Declaring success without opening the stills, the 1 frame/s sheet and the transcript.
