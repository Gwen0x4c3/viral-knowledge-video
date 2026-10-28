"""Audio: narration + procedural BGM (sectioned, ducked under the voice) + SFX cues -> build/mix.wav

usage: python mix.py --project DIR

The project's edit.py provides:
  MUSIC = [dict(t0=0.0, t1=5.4, kit="western", style="drone", ...), ...]   (see SECTION KEYS below)
  sfx_cues(shots) -> [(t, name, gain), ...]          names: see SFX_NAMES (print with --list-sfx)
  optional MUSIC_HOLES = [(t0, t1)]             music fades to silence inside (dramatic "错!" moments, big reveals)
  optional music_extra(m, ctx)                  custom hook: m = dict of stems (numpy), ctx has place(), SR, instruments

SECTION KEYS
  t0, t1   absolute seconds (use at()/L[...] from timeline so it follows the narration)
  kit      western | electronic | cinematic | lofi | suspense     (see references/style-presets.md)
  style    drive (full beat) | light (kick+hats, intros) | tense (staccato, heavy) | half (half-time, emotional)
           | sparse (bass + slow chords + pad) | drone (pad + heartbeat/ticks, hooks & suspense) | silence
  chords   list of chord names, one per bar (bar = 2 s at 120 bpm), e.g. ["Am","G","F","E"]
  melody   "A" | "B" | "SAD" | None     (melodies are written in A minor — keep chords A-minor friendly)
  lead_gain, gain  optional loudness tweaks
"""
import os, sys, subprocess, functools, importlib
sys.path.insert(0, os.path.dirname(__file__))
import config
ARGV = config.parse_project_arg(sys.argv[1:])
import numpy as np
from scipy.io import wavfile
from audio_lib import *
from timeline import LINES_T, L, TOTAL

N = int((TOTAL + 0.5) * SR)
BEAT = 0.5; BAR = 2.0

def place(buf, t, x, g=1.0):
    s = int(round(t * SR))
    if s >= len(buf) or s + len(x) <= 0: return
    if s < 0: x = x[-s:]; s = 0
    e = min(len(buf), s + len(x)); buf[s:e] += g * x[: e - s]

def load_mp3(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

# ---------------------------------------------------------------- voice
def voice_track():
    v = np.zeros(N, np.float32)
    for ln in LINES_T:
        a = load_mp3(config.build("tts", f"{ln['id']}.mp3"))
        seg = a[int(ln["src0"] * SR): int(ln["src1"] * SR)].copy()
        fade = int(0.02 * SR); seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
        place(v, ln["start"], seg)
    v = hp(v, 70); v = v + 0.25 * bp(v, 2500, 6000)          # rumble cut + presence
    v = v / (np.max(np.abs(v)) + 1e-9)
    return (np.tanh(v * 1.6) / np.tanh(1.6) * 0.85).astype(np.float32)   # soft compression

# ---------------------------------------------------------------- harmony
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
def chord(name):
    """'Am' / 'C' / 'F#m' / 'Bb' -> (bass midi 40-51, [4 arpeggio midis around 52-69])"""
    minor = name.endswith("m") and not name.endswith("maj")
    root = NOTE[name[:-1] if minor else name]
    third = 3 if minor else 4
    b = 40 + (root - 4) % 12
    base = 52 + (root - 4) % 12
    return b, [base, base + third, base + 7, base + 12]

MELODIES = {
    "A": [(76, 0, 1.5), (81, 1.5, 0.5), (79, 2, 1), (76, 3, 1), (74, 4, 1.5), (76, 5.5, 0.5), (74, 6, 0.5), (71, 6.5, 1.5),
          (72, 8, 1), (69, 9, 1), (72, 10, 0.5), (74, 10.5, 0.5), (76, 11, 1), (76, 12, 2.5), (75, 14.5, 0.5), (76, 15, 1)],
    "B": [(81, 0, 1), (79, 1, 0.5), (76, 1.5, 1.5), (74, 3, 1), (79, 4, 1), (76, 5, 1), (74, 6, 2),
          (77, 8, 1.5), (76, 9.5, 0.5), (74, 10, 1), (72, 11, 1), (71, 12, 1), (68, 13, 1), (71, 14, 2)],
    "SAD": [(69, 0, 3), (72, 3, 1), (71, 4, 2), (67, 6, 2), (69, 8, 2.5), (64, 10.5, 1.5), (68, 12, 4)],
}

# ---------------------------------------------------------------- kits (instrument palettes)
@functools.lru_cache(maxsize=None)
def _note(kind, m, d):
    f = midi(m)
    return {"pluck": lambda: pluck(f, d, 1.0, 0.55), "pluck_soft": lambda: pluck(f, d, 1.0, 0.3, False),
            "bass": lambda: bass(f, d, 1.0), "sub": lambda: sub_bass(f, d, 1.0), "saw": lambda: saw_pluck(f, d, 1.0),
            "ep": lambda: epiano(f, d, 1.0)}[kind]()
@functools.lru_cache(maxsize=None)
def _drum(kind):
    return {"kick": lambda: kick(), "kick_soft": lambda: lp(kick(amp=0.7), 2000), "808": lambda: kick808(),
            "snare": lambda: snare(), "snare_soft": lambda: lp(snare(amp=0.4), 3000), "clap": lambda: clap(),
            "hat": lambda: hat(), "shaker": lambda: shaker(), "taiko": lambda: taiko(), "rim": lambda: hp(snare(0.06, 0.5), 1500)}[kind]()

KITS = {
    "western":    dict(chord="pluck", bass="bass", kick="kick", snare="snare", hat="hat", lead=whistle, sadlead=harmonica, swing=0.04),
    "electronic": dict(chord="saw", bass="sub", kick="808", snare="clap", hat="hat", lead=lambda f, d: saw_pluck(f, d, 0.5, 5000), sadlead=lambda f, d: epiano(f, d, 0.5), swing=0.0),
    "cinematic":  dict(chord="pluck_soft", bass="sub", kick="taiko", snare="snare", hat="shaker", lead=lambda f, d: strings([f], d, 0.5), sadlead=lambda f, d: strings([f], d, 0.5), swing=0.0, pad=True),
    "lofi":       dict(chord="ep", bass="bass", kick="kick_soft", snare="snare_soft", hat="shaker", lead=lambda f, d: epiano(f, d, 0.6), sadlead=lambda f, d: epiano(f, d, 0.6), swing=0.07),
    "suspense":   dict(chord="pluck_soft", bass="sub", kick="kick_soft", snare="rim", hat="hat", lead=lambda f, d: strings([f], d, 0.4), sadlead=lambda f, d: strings([f], d, 0.4), swing=0.0, pad=True),
}

def section(m, s):
    t0, t1 = s["t0"], s["t1"]; style = s.get("style", "drive"); kit = KITS[s.get("kit", "western")]
    chords = s.get("chords", ["Am", "G", "F", "E"]); g = s.get("gain", 1.0)
    if style == "silence" or t1 <= t0: return
    def ok(t): return t < t1 - 0.02
    nb = int(np.ceil((t1 - t0) / BAR))
    if style == "drone":
        b, arp = chord(chords[0])
        place(m["pad"], t0, pad([midi(b), midi(b + 7), midi(b + 12)], t1 - t0 + 0.3, 1.4, 500), 0.7 * g)
        for i, tb in enumerate(np.arange(t0 + 0.4, t1, 0.5)):
            place(m["drums"], tb, sfx_heartbeat(1.0) if i % 2 == 0 else _drum("hat"), (0.8 if i % 2 == 0 else 0.5) * g)
        n_tick = int((t1 - t0) * 0.5 / 0.125)
        for e in range(n_tick):  # accelerating ticks in the second half
            place(m["drums"], t0 + (t1 - t0) * 0.5 + e * 0.125, _drum("hat"), (0.3 + 0.4 * e / max(1, n_tick)) * g)
    for bi in range(nb if style != "drone" else 0):
        tb = t0 + bi * BAR
        bnote, arp = chord(chords[bi % len(chords)])
        sw = kit["swing"]
        if style in ("drive", "tense", "light"):
            kicks = [(0, 1.0), (1.0, 0.9), (1.75, 0.5)] if style != "light" else [(0, 0.8), (1.0, 0.7)]
            for off, a in kicks:
                if ok(tb + off): place(m["drums"], tb + off, _drum(kit["kick"]), a * g)
            if style != "light":
                for off in (0.5, 1.5):
                    if ok(tb + off): place(m["drums"], tb + off, _drum(kit["snare"]), (0.55 if style == "drive" else 0.7) * g)
            for e in range(8):
                off = e * 0.25 + (sw if e % 2 else 0)
                if ok(tb + off): place(m["drums"], tb + off, _drum(kit["hat"]), (0.9 if e % 2 == 0 else 0.6) * g)
            for off, n, dd in ((0, bnote, 0.45), (0.75, bnote + 7, 0.2), (1.0, bnote + 7, 0.45), (1.75, bnote + 12, 0.2)):
                if ok(tb + off): place(m["bass"], tb + off, _note(kit["bass"], n - 12 if n > 47 else n, dd), 0.8 * g)
            for e in range(8):
                off = e * 0.25
                if not ok(tb + off): continue
                if style == "tense":
                    if e in (0, 3, 6): place(m["gtr"], tb + off, _note(kit["chord"], arp[0] + 12, 0.25), 0.55 * g)
                else:
                    place(m["gtr"], tb + off, _note(kit["chord"], arp[[0, 2, 1, 3, 2, 1, 3, 2][e]], 0.6), 0.38 * g)
            if kit.get("pad") and style != "light":
                place(m["pad"], tb, strings([midi(n) for n in arp[:3]], min(BAR, t1 - tb) + 0.5, 1.0), 0.35 * g)
        elif style == "half":
            if ok(tb): place(m["drums"], tb, _drum(kit["kick"]), 0.6 * g)
            if ok(tb + 1.0): place(m["drums"], tb + 1.0, _drum(kit["snare"]), 0.25 * g)
            place(m["bass"], tb, _note(kit["bass"], bnote, 1.6), 0.6 * g)
            for e in range(4):
                if ok(tb + e * 0.5): place(m["gtr"], tb + e * 0.5, _note(kit["chord"], arp[e], 1.4), 0.4 * g)
        elif style == "sparse":
            place(m["bass"], tb, _note(kit["bass"], bnote, 1.9), 0.5 * g)
            if ok(tb): place(m["gtr"], tb, _note(kit["chord"], arp[0], 2.0), 0.35 * g)
            if ok(tb + 1.0): place(m["gtr"], tb + 1.0, _note(kit["chord"], arp[2], 1.5), 0.25 * g)
            place(m["pad"], tb, pad([midi(n) for n in arp[:3]], min(BAR, t1 - tb) + 0.6, 1.0, 700), 0.5 * g)
    mel = s.get("melody")
    if mel:
        inst = kit["sadlead"] if mel == "SAD" else kit["lead"]
        plen = 16 * BEAT
        for r in range(int(np.ceil((t1 - t0) / plen))):
            for n, b0, bl in MELODIES[mel]:
                ts = t0 + r * plen + b0 * BEAT
                if ts + 0.05 < t1: place(m["lead"], ts, inst(midi(n), min(bl * BEAT, t1 - ts) * 0.95), s.get("lead_gain", 0.75) * g)

def ending(m, t, kit="western", chord_name="Am"):
    """Resolving final chord + boom; call from music_extra or MUSIC via style='end'."""
    b, arp = chord(chord_name); k = KITS[kit]
    place(m["drums"], t, sfx_boom(2.0, 0.7), 0.6)
    for i, n in enumerate([b] + arp): place(m["gtr"], t + i * 0.004, _note(k["chord"], n, 2.6), 0.45)
    place(m["pad"], t, pad([midi(n) for n in arp[:3]], 2.4, 1.0, 900), 0.8)
    place(m["lead"], t, k["lead"](midi(arp[3] + 12), 1.8), 0.6)

def music_track(E):
    m = {k: np.zeros(N, np.float32) for k in ("drums", "bass", "gtr", "lead", "pad", "fx")}
    for s in getattr(E, "MUSIC", []):
        if s.get("style") == "end": ending(m, s["t0"], s.get("kit", "western"), s.get("chords", ["Am"])[0])
        else: section(m, s)
    if hasattr(E, "music_extra"):
        ctx = dict(place=place, SR=SR, midi=midi, chord=chord, whistle=whistle, harmonica=harmonica, bell=bell, pad=pad,
                   pluck=pluck, kick=kick, snare=snare, riser=sfx_riser, strings=strings, taiko=taiko, epiano=epiano)
        E.music_extra(m, ctx)
    mix = (m["drums"] * 0.55 + m["bass"] * 0.5 + reverb(m["gtr"], 1.2, 0.25) * 0.5 +
           reverb(m["lead"], 2.0, 0.45) * 0.33 + m["pad"] * 0.45 + m["fx"] * 0.3)
    for a, b in getattr(E, "MUSIC_HOLES", []):
        ia, ib = int(a * SR), int(b * SR); mix[ia:ib] *= np.linspace(1, 0, max(1, ib - ia)) ** 4
    return mix

# ---------------------------------------------------------------- sfx bank
def sfx_bank():
    def moo():
        t = t_arr(1.1); f = 140 + 30 * np.sin(np.pi * t / 1.1)
        return 0.6 * bp(signal.sawtooth(2 * np.pi * np.cumsum(f) / SR), 200, 1200) * np.sin(np.pi * np.clip(t / 1.1, 0, 1)) ** 0.7
    def gallop():
        out = np.zeros(int(1.6 * SR))
        for i in range(6):
            for off in (0, 0.07, 0.14): place(out, i * 0.27 + off, lp(noise(0.06), 900) * np.exp(-t_arr(0.06) * 60))
        return out
    def sad():
        out = np.zeros(int(1.4 * SR))
        for i, n in enumerate([62, 61, 60]): place(out, i * 0.32, harmonica(midi(n), 0.3 if i < 2 else 0.7, 1.0))
        return out
    def clicks(offs, lo=1500, hi=7000):
        out = np.zeros(int((max(offs) + 0.1) * SR))
        for o in offs: place(out, o, bp(noise(0.03), lo, hi) * np.exp(-t_arr(0.03) * 140))
        return out
    def train():
        t = t_arr(1.6); x = np.zeros(len(t))
        for i in range(8): place(x, i * 0.2, lp(noise(0.08), 1500) * np.exp(-t_arr(0.08) * 40))
        return 0.7 * x + 0.25 * (np.sin(2 * np.pi * 520 * t) + 0.6 * np.sin(2 * np.pi * 650 * t)) * np.minimum(1, t / 0.05) * np.exp(-t * 1.2)
    def stampede():
        out = np.zeros(int(1.8 * SR))
        for _ in range(40): place(out, rng.uniform(0, 1.6), lp(noise(0.08), 600) * np.exp(-t_arr(0.08) * 30), rng.uniform(0.4, 1))
        return out + 0.3 * lp(noise(1.8), 300)
    def typing():
        return clicks(list(np.cumsum(rng.uniform(0.05, 0.12, 12))), 2000, 8000)
    def notif():  # phone-style double blip
        out = np.zeros(int(0.5 * SR)); place(out, 0, sfx_pop(0.5, 1400)); place(out, 0.11, sfx_pop(0.5, 1900)); return out
    def heartbeat2(): return sfx_heartbeat(1.0)
    return {
        "whoosh": sfx_whoosh(0.4, True, 0.6), "whoosh_s": sfx_whoosh(0.3, True, 0.35), "whoosh_d": sfx_whoosh(0.5, False, 0.6),
        "pop_low": sfx_pop(0.5, 300), "pop": sfx_pop(0.5, 900), "boom": sfx_boom(), "boom_s": sfx_boom(1.0, 0.6),
        "impact": sfx_boom(1.2, 0.9), "taiko": taiko(1.2, 0.9), "glitch": sfx_glitch(0.5), "gunshot": sfx_gunshot(),
        "ricochet": sfx_ricochet(), "scratch": sfx_scratch(0.7), "stamp": sfx_stamp(), "ding": sfx_ding(), "notif": notif(),
        "riser": sfx_riser(2.0, 0.6), "riser_s": sfx_riser(0.6, 0.5), "whip": sfx_whip(), "shutter": sfx_shutter(),
        "tick": sfx_tick(0.5), "typing": typing(), "sad": sad(), "gun_cock": clicks([0, 0.12]), "kaching": sfx_kaching(),
        "coin": bell(2600, 0.3, 1.0) + bell(3400, 0.3, 0.5), "moo": moo(), "gallop": gallop(), "stampede": stampede(),
        "train": train(), "clank": bell(420, 0.8, 1.0) + 0.5 * np.pad(bell(1130, 0.5, 1.0), (0, int(0.3 * SR))),
        "wind": sfx_wind(5.5, 0.6), "projector": sfx_projector(1.6, 0.5), "heartbeat": heartbeat2(), "flash": np.zeros(10),
    }
SFX_NAMES = None

def main():
    E = importlib.import_module("edit")
    if "--list-sfx" in ARGV: print(sorted(sfx_bank())); return
    voice = voice_track(); music = music_track(E)
    B = sfx_bank(); sfx = np.zeros(N, np.float32)
    shots = sorted(E.build(), key=lambda s: s.start)
    for t, n, g in E.sfx_cues(shots):
        if n not in B: raise SystemExit(f"unknown sfx '{n}'. available: {sorted(B)}")
        place(sfx, t, B[n].astype(np.float32), g)
    env = np.convolve(lp(np.abs(voice), 8, 1), np.ones(2205) / 2205, "same")
    env = np.clip(env / (np.percentile(env[env > 1e-3], 90) + 1e-6), 0, 1)
    music = music / (np.max(np.abs(music)) + 1e-9)
    mus = music * getattr(E, "MUSIC_LEVEL", 0.30) * (1 - 0.5 * env)          # duck ~6 dB under speech
    fx = sfx * getattr(E, "SFX_LEVEL", 0.42) * (1 - 0.25 * env)
    left = voice + mus + fx; right = voice + np.roll(mus, int(0.012 * SR)) + fx   # tiny Haas widening on music
    st = np.stack([left, right], 1); st = st / (np.max(np.abs(st)) + 1e-9) * 0.95
    fade = int(0.8 * SR); st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    wavfile.write(config.build("mix.wav"), SR, (st * 32767).astype(np.int16))
    wavfile.write(config.build("music_only.wav"), SR, (music * 0.8 * 32767).astype(np.int16))
    wavfile.write(config.build("voice_only.wav"), SR, (voice * 32767).astype(np.int16))
    print("wrote", config.build("mix.wav"), f"{len(st) / SR:.2f}s")

if __name__ == "__main__":
    main()
