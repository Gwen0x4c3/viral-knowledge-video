# QA checklist + known failures

## Final checklist (open `build/sheets/final.jpg` and the stills, and run the commands)

**Format**
- [ ] 1080×1920, 30 fps, H.264 + AAC, duration 60–90 s (`finalize.py` prints it)
- [ ] loudness −14 LUFS ±1, no clipping

**Hook and ending**
- [ ] Frame at 0.3 s is already striking (motion, face or action) and has a label/subtitle; the first line is a hook, not a greeting
- [ ] The last ~2 s are a deliberate closing shot that fades out; the music resolves; nothing is cut off

**Visual rhythm**
- [ ] 35–50 shots for ~80 s; median ≈ 2 s; at most 2 fast bursts; holds on graphics (`render.py` warns about extremes)
- [ ] No 3 consecutive shots of the same type; the 1 frame/s sheet looks varied from start to end
- [ ] Every still moves; no frozen frame longer than intended
- [ ] Fancy transitions are rationed (see effects-catalog.md A)

**Text and layout**
- [ ] Subtitles readable, synced, never covered by graphics; nothing important under y=1650 or at x>960 in the button area
- [ ] No □ missing glyphs anywhere
- [ ] Labels ≤ 12 characters; keywords highlighted; big pops ≤ 1 per ~10 s and never duplicating an on-screen number
- [ ] Consistent palette and fonts (one style preset)

**Content**
- [ ] Every beat has concrete facts; numbers shown as graphics or counters
- [ ] Contested claims hedged; no invented numbers; facts list prepared for the report
- [ ] The hook's promise matches the body (e.g. "4个真相" means four truths)

**Audio**
- [ ] Whisper transcript matches the script; key words intelligible
- [ ] Music changes with the mood; silence before the big hit; no audible 8-bar loop for the whole video
- [ ] SFX on transitions, numbers and reveals, but not on top of key words

**Rights**
- [ ] Only PD/CC/user-provided/procedural media; nothing watermarked; no modern copyrighted clips

## Known failures and fixes

| Symptom | Cause | Fix |
|---|---|---|
| edge-tts `Cannot connect to host speech.platform.bing.com ... nodename nor servname` | aiohttp ignores HTTPS_PROXY in sandboxes | `tts.py` passes `proxy=$HTTPS_PROXY`; also allow the host |
| `SSL: CERTIFICATE_VERIFY_FAILED` with urllib | macOS Python without certs | use `requests` (already done in commons.py) |
| Images are 1.9 KB / won't open | HTTP 429/400 HTML page saved as .jpg | `commons.py` checks content-type; delete files < 5 KB and refetch slowly |
| Thumbnail requests fail (000 / 429) | `thumb.wikimedia.org` blocked or thumbnail wider than original | allow the host; originals for small images (built in) |
| `No such filter: 'drawtext'` | ffmpeg built without freetype | all text is drawn with PIL; contact sheets via `sheet.py` |
| A box □ instead of a character | font lacks the glyph (e.g. `→` in Rockwell) | use `F_HEAVY`/`F_SYMBOL`, or draw the shape (`draw_arrow`) |
| Freeze frame is white/blank | froze on a muzzle flash or smoke | freeze a few frames *before* the event |
| Map is a single colour blob | 4:5 map cropped to 9:16 and over-zoomed | `g_pins(..., box=(300, 1200))`, lower zoom, check stills |
| Numbers overlap ("×12 VS ×3000") | widths grow while counting | reserve space for the widest value; smaller font |
| Text collides with subtitles | graphic placed in y 1250–1420 | move graphics up; check stills |
| Subtitle and hook disagree ("三个真相" but 4) | script edited later | re-read the hook after finishing the body |
| A word inaudible in the transcript | SFX/music masks it | move the SFX off the word; lower its gain |
| Video feels rushed (急促) | median shot < 1.5 s, many fancy transitions, speech > +26% | longer holds, `PACE = 1.2`, fewer whips, slower rate |
| Video feels like a slideshow | < 30 shots, static or slow images, no graphics | add graphics/footage, cut on words, add motion |
| `rm`/`find` silently not deleting | shell wrapper/sandbox | verify with `ls -la`; delete files one by one |
| Chromium won't start (`MachPortRendezvous ... Permission denied`) | macOS sandbox | run the 3D render outside the sandbox or use 2D graphics |
| Playwright `Executable doesn't exist ... chromium_headless_shell-XXXX` | pinned browser build differs | renderer falls back to the installed Chrome/Chromium automatically |
| `PermissionError ~/.cache` | sandbox write restriction | caches go to `<project>/build/cache` |
| Render is slow | full 1080p frames in Python | `JOBS=<cores>`; iterate with stills and `sheet`, full render only at the end |
| Viewers can't explain the concept after watching | trivia-style script for a concept: undefined terms, missing subjects, no "why", no running example | explainer mode (script-writing.md §10) + subtitle-only comprehension test |
| `NameError: S` / custom graphic can't see absolute time | old closure pattern | write `fn(u, d, t)` and use `t` directly |
| Image renders all black (no error) | PDF converted with `sips`, or SVG without background | `pdftoppm`; run `sheet.py check` after every download/convert |
| Chinese in an Impact/Rockwell text renders as □ | latin font lacks CJK | handled automatically (fallback + warning); read the `[vidkit] font ...` warnings |
| Technical term misheard ("etcd" → "At") | TTS mispronounces English | `SAY` map + per-line re-TTS + Whisper check |
| Overlapping labels found late | each still opened separately | `render.py stills ...` writes one mosaic `build/sheets/stills.jpg`; review that |
