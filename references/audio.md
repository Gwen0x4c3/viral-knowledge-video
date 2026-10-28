# Audio: voice, music, sound effects, mixing, verification

## 1. Voice

### Engine options (best quality first)
| Engine | Quality (Chinese) | Cost / setup | Word timings |
|---|---|---|---|
| **Volcengine 豆包语音 (Doubao TTS 2.0 / 大模型语音合成)** | the voices used across Douyin; very natural, emotional, many narrator styles | API key (appid + token) from the user | returns timestamps |
| MiniMax Speech-02 / ElevenLabs v3 / Azure TTS (full SSML with `mstts:express-as` styles) | excellent | API key | yes (Azure word boundaries) / via alignment |
| **CosyVoice3 (Fun-CosyVoice3-0.5B, open source, local)** | more natural than edge-tts with a good reference voice (UTMOS 3.84 vs 3.30 in our test); emotion via text instructions | ~10 GB download, Python 3.10 + torch 2.3 venv; ~3× slower than realtime on Apple M3 CPU | forced alignment needed (FunASR `fa-zh` or Whisper word timestamps) |
| IndexTTS2 / F5-TTS / Spark-TTS (open source) | strong; IndexTTS2 has fine emotion control | GPU recommended | forced alignment |
| **edge-tts (default, bundled)** | decent, slightly robotic; only rate/pitch control | free, no key, instant | native word boundaries |

Rules: if the user can provide an API key for a premium engine, use it. Ask once at the start, because the voice is the
single biggest quality factor. Zero-shot cloning engines (CosyVoice, F5, IndexTTS) need a 5–15 s **reference clip**
whose energy matches the video: a calm reference gives a calm narrator. Only use a reference the user owns or that is
licensed for it (their own recording is best). Never clone a real person's voice without consent. Whatever engine you
use, `tts.py` must end with `build/tts/<id>.mp3` + `<id>.json` word timings `[{t, d, w}]` so the rest of vidkit works unchanged.

### Technical terms & English words
Use the `SAY` map in script_data.py (display spelling ≠ spoken form): letters spelled with spaces (`"etcd": "E T C D"`),
uppercase acronyms (`"K8s": "K8S"`), Chinese readings for symbols (`"C++": "C 加加"`, `"3/5": "五分之三"`). Verify with the
Whisper transcript and iterate per line (`tts.py --project P L18`).

### edge-tts voices (default engine)

| Voice | Character | Good for |
|---|---|---|
| `zh-CN-YunxiNeural` (default) | young male, lively, expressive | most knowledge/myth-busting videos |
| `zh-CN-YunjianNeural` | deeper male, powerful | war, sports, epic history |
| `zh-CN-YunyangNeural` | news-anchor male, formal | business, current-affairs style |
| `zh-CN-XiaoxiaoNeural` | warm female, versatile | culture, food, nature, lifestyle |
| `zh-CN-XiaoyiNeural` | lively young female | fun facts, animals, playful topics |
| `zh-CN-YunxiaNeural` | boyish | kids' science |
| English: `en-US-AndrewNeural`, `en-US-AvaNeural`, `en-US-BrianNeural` | — | English versions |
List all: `edge-tts --list-voices`. Set `VOICE` in script_data.py.

Expressiveness comes from **per-line rate/pitch** (see script-writing.md §6). Keep explanation lines at +18~24%
(above +26% everything sounds rushed), and use slower, lower lines for emotional beats. If a word is mispronounced, rephrase
it (synonym, or digits ↔ Chinese numerals) and re-run `tts.py` for just that line id.

## 2. Music: sections that follow the emotional arc

The engine synthesizes music from `MUSIC` sections. Each section has a **kit** (instrument palette) and a **style** (groove).
Plan it from the emotional curve:

| Story moment | style | Notes |
|---|---|---|
| Hook / question / suspense | `drone` | pad + heartbeat + accelerating ticks; builds tension under the first lines |
| Right before the big reversal | `MUSIC_HOLES` | 0.3–0.5 s of silence, then the hit (scratch → boom) |
| Facts, energy, lists | `drive` (+ `melody="A"` or `"B"`) | full groove; alternate melodies A/B between sections so it doesn't loop |
| Intros after a hit, low-key facts | `light` | kick + hats only, leaves room for voice |
| Conflict, danger, crime, war | `tense` | staccato, heavier |
| Deflation ("其实少得可怜") | `sparse` with 1 chord | instant mood drop |
| Sad / human / poor / loss | `half` + `melody="SAD"` | half-time, harmonica/e-piano/strings melody |
| End of an era / reflection | `sparse` | slow chords + pad |
| Final build | `light`/`drive` + `riser` in `music_extra` + snare roll | to the last reveal |
| Outro | `drive` → `style="end"` | resolving chord + boom, music tail ~2 s |

**Kits** (pick by style preset):

| kit | Sound | Presets |
|---|---|---|
| `western` | twangy plucked guitar, boom-chicka bass, whistle lead, harmonica for sad | history/West/frontier |
| `electronic` | saw plucks, 808 kick, clap, sub bass | tech, space, business, sports |
| `cinematic` | soft plucks + string pads, taiko drums, string lead | ancient, war, epic nature, space |
| `lofi` | FM e-piano, soft kick/snare, shaker, swing | food, culture, animals, chill explainers |
| `suspense` | strings, rim clicks, sub bass, drone | true crime, mysteries |

Chords: any names (`"Am"`, `"F"`, `"C#m"`, `"Bb"`), one per 2 s bar. Melodies are written in A minor, so keep
progressions A-minor friendly: `Am G F E` (Andalusian/dramatic), `Am F C G` (epic/pop), `Am F C E` (sad),
`Am Am F E` (tense), `Am Em F G` (calm).

`music_extra(m, ctx)` adds one-off touches: a whistle motif in the hook, music-box bells, a tom roll before a stampede,
a riser into the finale. `ctx` provides `place`, `midi`, `whistle`, `harmonica`, `bell`, `pad`, `pluck`, `kick`, `snare`,
`riser`, `strings`, `taiko`, `epiano`.

Procedural music is functional, not studio-grade. If the user supplies licensed music files, mix them instead: load with
ffmpeg, then apply the same ducking (see `mix.py` main) and cut or fade them at section boundaries.

## 3. Sound effects

Available names: `python3 $K/mix.py --project P --list-sfx`.

| Event | SFX | Gain |
|---|---|---|
| whip / slide / punch transitions | auto via `transition_sfx` (whoosh / pop_low) | 0.4 |
| chapter card / flash | auto `boom_s` + `riser_s` 0.35 s before | 0.5 |
| "错！"/ reversal | `scratch` (0.3 s before) + `boom` + `stamp` | 0.8–1.0 |
| number counting | `tick` × 8–10 every 0.07 s, then `boom`/`impact` on landing | 0.3 / 0.7 |
| money | `kaching` + a few `coin` | 0.7 / 0.25 |
| label / icon / pin popping in | `pop` | 0.4–0.5 |
| reveal / correct / punchline | `ding` | 0.6 |
| stamp, sign, verdict | `stamp` | 0.7–0.9 |
| photo of a person appearing | `shutter` | 0.5 |
| gun / fight | `gunshot` (+ `ricochet`), auto flash + shake | 0.6–1.0 |
| sad deflation | `sad` (descending harmonica) | 0.6 |
| tech / glitch | `glitch`, `typing`, `notif` | 0.4–0.5 |
| epic hit | `taiko`, `impact` | 0.7–0.9 |
| weather / place ambience | `wind`, `train`, `gallop`, `stampede`, `moo`, `projector` | 0.4–0.6 |
| build-up | `riser` | 0.6 |

Rules: never put a loud SFX on a key spoken word (put it on the word's end, in a gap, or on the cut); use at most about one
sound per 0.7 s; ambiences stay quiet (≤ 0.6).

## 4. Mix

`mix.py` does: voice (high-pass, presence lift, soft compression, peak 0.85) + music (normalized, × `MUSIC_LEVEL`=0.30,
ducked about 6 dB under speech) + SFX (× `SFX_LEVEL`=0.42, lightly ducked) → stereo, 0.8 s fade-out. `finalize.py` then
normalizes to −14 LUFS (the standard for Douyin, TikTok and YouTube). Tweak `MUSIC_LEVEL` and `SFX_LEVEL` in edit.py if needed.

## 5. Verify (you probably can't listen, so measure)

```bash
python3 $K/check_audio.py --project P --whisper
```
- Music RMS per 3 s should be roughly constant (−17 to −22 dB) except intended holes and sparse sections. A −40 dB block means
  a missing section.
- 0 clipped samples.
- The Whisper transcript should match the script apart from homophones. A key phrase that comes out wrong (e.g. "拔枪决斗" → "爬枪出锅")
  means an SFX or the music is masking it: move the SFX off the word or lower it.
- Tell the user that audio was verified by measurement and transcription, not by listening.
