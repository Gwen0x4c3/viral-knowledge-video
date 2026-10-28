"""Procedural western BGM + sound effects (numpy). All functions return float32 mono/stereo at SR."""
import numpy as np
from scipy import signal

SR = 44100
rng = np.random.default_rng(7)

def t_arr(d): return np.arange(int(d * SR)) / SR
def env_ad(n, a=0.005, d=0.3):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)
    return e
def lp(x, f, o=2): b, a = signal.butter(o, min(f / (SR / 2), 0.99), "low"); return signal.lfilter(b, a, x)
def hp(x, f, o=2): b, a = signal.butter(o, min(f / (SR / 2), 0.99), "high"); return signal.lfilter(b, a, x)
def bp(x, f1, f2, o=2): b, a = signal.butter(o, [f1 / (SR / 2), min(f2 / (SR / 2), 0.99)], "band"); return signal.lfilter(b, a, x)
def noise(d): return rng.uniform(-1, 1, int(d * SR))
def midi(n): return 440 * 2 ** ((n - 69) / 12)

def reverb(x, decay=1.6, mix=0.25, seed=3):
    r = np.random.default_rng(seed)
    n = int(decay * SR)
    ir = r.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 6.9 / decay)
    ir = lp(ir, 6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = signal.fftconvolve(x, ir)[: len(x)]
    return x * (1 - mix) + wet * mix * 0.6

# ---------------- instruments ----------------
def kick(d=0.35, f0=150, f1=45, amp=1.0):
    t = t_arr(d); f = f1 + (f0 - f1) * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return amp * np.sin(ph) * np.exp(-t * 9) + 0.15 * amp * noise(d) * np.exp(-t * 120)

def snare(d=0.22, amp=0.6, bright=4000):
    t = t_arr(d)
    n = bp(noise(d), 1200, bright) * np.exp(-t * 22)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return amp * (n * 1.4 + 0.5 * tone)

def hat(d=0.06, amp=0.25, open_=False):
    dd = 0.25 if open_ else d
    t = t_arr(dd); return amp * hp(noise(dd), 7000) * np.exp(-t * (14 if open_ else 70))

def shaker(d=0.09, amp=0.18):
    t = t_arr(d); e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return amp * hp(noise(d), 5000) * e

def pluck(freq, d=1.2, amp=0.5, bright=0.5, twang=True):
    """Karplus-Strong guitar with a little pitch 'twang'."""
    n = int(d * SR); N = int(SR / freq)
    buf = rng.uniform(-1, 1, N); buf = lp(buf, 1500 + 6000 * bright)
    damp = 0.996
    blocks = []; cur = buf.copy()
    for _ in range(n // N + 1):
        blocks.append(cur)
        cur = damp * 0.5 * (cur + np.roll(cur, -1))
    out = np.concatenate(blocks)[:n]
    if twang:  # slight upward bend in first 60ms via resample warp
        t = np.arange(n) / SR; warp = t + 0.004 * (1 - np.exp(-t * 18))
        out = np.interp(warp * SR, np.arange(n), out, right=0)
    out = np.tanh(out * 1.8) / 1.8
    return amp * out * env_ad(n, 0.002, d * 0.6)

def bass(freq, d=0.4, amp=0.55):
    t = t_arr(d)
    x = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t) + 0.12 * np.sign(np.sin(2 * np.pi * freq * t))
    return amp * lp(x, 900) * env_ad(len(t), 0.004, d * 0.5)

def whistle(freq, d, amp=0.22, vib=5.5):
    t = t_arr(d)
    f = freq * (1 + 0.012 * np.sin(2 * np.pi * vib * t) * np.minimum(1, t / 0.25))
    f = f * (1 - 0.03 * np.exp(-t * 25))  # scoop up into the note
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.05 * lp(noise(d), 3000)
    e = np.minimum(1, t / 0.04) * np.minimum(1, (d - t) / 0.08).clip(0)
    return amp * x * e

def harmonica(freq, d, amp=0.16):
    t = t_arr(d)
    f = freq * (1 + 0.008 * np.sin(2 * np.pi * 5 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = signal.square(ph, 0.4) * 0.6 + np.sin(ph)
    x = lp(x, 2200) + 0.02 * noise(d)
    e = np.minimum(1, t / 0.06) * np.minimum(1, (d - t) / 0.12).clip(0)
    return amp * x * e

def pad(freqs, d, amp=0.1, cutoff=900):
    t = t_arr(d); x = 0
    for f in freqs:
        for det in (-0.25, 0.25):
            x = x + signal.sawtooth(2 * np.pi * (f + det) * t + rng.uniform(0, 6))
    x = lp(x / (2 * len(freqs)), cutoff)
    e = np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.8).clip(0)
    return amp * x * e

def bell(freq, d=1.5, amp=0.12):
    t = t_arr(d)
    x = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * k) for r, a, k in [(1, 1, 3), (2.76, 0.4, 6), (5.4, 0.2, 10)])
    return amp * x * np.minimum(1, t / 0.002)

# ---------------- SFX ----------------
def sfx_whoosh(d=0.45, up=True, amp=0.5):
    t = t_arr(d); n = noise(d); out = np.zeros_like(n)
    seg = 256
    for i in range(0, len(n), seg):
        p = i / len(n); fc = 300 + (5000 if up else 3000) * (p if up else 1 - p)
        out[i:i + seg] = bp(n[max(0, i - 2048):i + seg], max(80, fc * 0.6), fc * 1.4)[-len(n[i:i + seg]):]
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    return amp * out * e * 2.5

def sfx_boom(d=1.4, amp=1.0):
    t = t_arr(d); f = 38 + 90 * np.exp(-t * 12)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    x += 0.5 * lp(noise(d), 400) * np.exp(-t * 8)
    x += 0.4 * noise(d) * np.exp(-t * 60)
    return amp * np.tanh(x * 1.5)

def sfx_gunshot(amp=1.0, d=1.6):
    t = t_arr(d)
    crack = noise(d) * np.exp(-t * 55)
    body = lp(noise(d), 900) * np.exp(-t * 12)
    thump = np.sin(2 * np.pi * (60 + 120 * np.exp(-t * 30)) * t) * np.exp(-t * 10)
    x = 0.9 * crack + 0.9 * body + 0.8 * thump
    return amp * np.tanh(reverb(x, 1.4, 0.45) * 2.2)

def sfx_ricochet(amp=0.35, d=0.7):
    t = t_arr(d); f = 3200 * np.exp(-t * 1.6) + 600
    f = f * (1 + 0.04 * np.sin(2 * np.pi * 38 * t))
    return amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4) * np.minimum(1, t / 0.01)

def sfx_ding(amp=0.35):
    return amp * (bell(1318.5, 1.0, 1) + 0.8 * np.pad(bell(1760, 0.91, 1), (int(0.09 * SR), SR))[: int(1.0 * SR)])

def sfx_pop(amp=0.3, f=900):
    t = t_arr(0.09); fr = f * (1 + 1.5 * np.exp(-t * 60))
    return amp * np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 40)

def sfx_tick(amp=0.25):
    t = t_arr(0.03); return amp * hp(noise(0.03), 2500) * np.exp(-t * 200)

def sfx_scratch(amp=0.5, d=0.45):
    t = t_arr(d); n = noise(d)
    pos = np.sin(2 * np.pi * 3.2 * t) ** 2
    out = np.zeros_like(n); seg = 256
    for i in range(0, len(n), seg):
        fc = 400 + 2600 * pos[i]
        out[i:i + seg] = bp(n[max(0, i - 2048):i + seg], fc * 0.7, fc * 1.3)[-len(n[i:i + seg]):]
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * pos) / SR)
    return amp * (out * 2 + 0.3 * tone) * np.minimum(1, (d - t) / 0.05).clip(0)

def sfx_stamp(amp=0.8):
    t = t_arr(0.5)
    x = np.sin(2 * np.pi * (70 + 80 * np.exp(-t * 40)) * t) * np.exp(-t * 14) + 0.6 * lp(noise(0.5), 2500) * np.exp(-t * 35)
    return amp * np.tanh(2 * x)

def sfx_kaching(amp=0.4):
    out = np.zeros(int(1.2 * SR))
    for i, o in enumerate([0, 0.05, 0.09]):
        c = hp(noise(0.03), 3000) * np.exp(-t_arr(0.03) * 150) * 0.6
        s = int(o * SR); out[s:s + len(c)] += c
    b = bell(2093, 1.0, 0.8) + bell(2637, 1.0, 0.5)
    s = int(0.14 * SR); out[s:s + len(b)] += b[: len(out) - s]
    return amp * out

def sfx_riser(d=3.0, amp=0.35):
    t = t_arr(d); p = t / d
    f = 180 * 2 ** (p * 3)
    x = 0.4 * signal.sawtooth(2 * np.pi * np.cumsum(f) / SR) + 0.6 * hp(noise(d), 800) * p
    return amp * (lp(x, 800) * (1 - p) + lp(x, 9000) * p) * p ** 1.6

def sfx_wind(d=4.0, amp=0.3):
    t = t_arr(d); n = noise(d)
    m = 0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * t + 1) * np.sin(2 * np.pi * 0.13 * t)
    x = bp(n, 250, 900) * m + 0.4 * bp(n, 900, 2200) * m ** 2
    e = np.minimum(1, t / 0.8) * np.minimum(1, (d - t) / 0.8).clip(0)
    return amp * x * e * 2.2

def sfx_whip(amp=0.5):
    d = 0.35; t = t_arr(d)
    sw = sfx_whoosh(0.2, True, 0.3)
    crack = hp(noise(0.05), 2000) * np.exp(-t_arr(0.05) * 90)
    out = np.zeros(int(d * SR)); out[: len(sw)] += sw; s = int(0.19 * SR); out[s:s + len(crack)] += crack * 1.2
    return amp * out

def sfx_shutter(amp=0.4):
    out = np.zeros(int(0.2 * SR))
    for o in (0, 0.07):
        c = bp(noise(0.03), 1500, 6000) * np.exp(-t_arr(0.03) * 120); s = int(o * SR); out[s:s + len(c)] += c
    return amp * out

def sfx_heartbeat(amp=0.6):
    out = np.zeros(int(0.7 * SR))
    for o, a in ((0, 1), (0.22, 0.7)):
        k = kick(0.25, 90, 40, a); s = int(o * SR); out[s:s + len(k)] += k
    return amp * lp(out, 300)

def sfx_projector(d=3.0, amp=0.18):
    t = t_arr(d)
    clicks = (np.sin(2 * np.pi * 24 * t) > 0.92).astype(float)
    x = hp(clicks, 1500) * 0.6 + 0.2 * bp(noise(d), 300, 3000)
    e = np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.4).clip(0)
    return amp * x * e

def sfx_glitch(amp=0.35, d=0.25):
    t = t_arr(d); x = signal.square(2 * np.pi * 110 * t) * (rng.uniform(size=len(t)) > 0.5)
    x = x + 0.5 * noise(d)
    return amp * lp(x, 4000) * np.minimum(1, (d - t) / 0.03).clip(0)

# ---------------- extra instruments for non-western kits ----------------
def saw_pluck(freq, d=0.4, amp=0.5, cutoff=3500):
    """Electronic pluck: detuned saw through a closing low-pass."""
    t = t_arr(d)
    x = signal.sawtooth(2 * np.pi * freq * t) + signal.sawtooth(2 * np.pi * freq * 1.006 * t + 1.3)
    e = np.exp(-t * 7)
    x = lp(x, 400) * (1 - e) + lp(x, cutoff) * e
    return amp * 0.5 * x * env_ad(len(t), 0.003, d * 0.5)

def sub_bass(freq, d=0.5, amp=0.6):
    t = t_arr(d); x = np.tanh(1.5 * np.sin(2 * np.pi * freq * t))
    return amp * x * env_ad(len(t), 0.005, d * 0.7)

def kick808(d=0.6, amp=1.0):
    t = t_arr(d); f = 42 + 110 * np.exp(-t * 22)
    return amp * np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5))

def clap(amp=0.6):
    d = 0.3; t = t_arr(d); n = bp(noise(d), 900, 5000)
    e = sum(np.exp(-np.maximum(0, t - o) * 90) * (t >= o) for o in (0, 0.012, 0.024)) + 0.5 * np.exp(-t * 18)
    return amp * n * e * 0.8

def epiano(freq, d=1.2, amp=0.4):
    """Soft FM electric piano (lo-fi / warm explainer)."""
    t = t_arr(d)
    mod = 1.2 * np.exp(-t * 3) * np.sin(2 * np.pi * freq * t)
    x = np.sin(2 * np.pi * freq * t + mod) + 0.2 * np.sin(4 * np.pi * freq * t)
    return amp * x * env_ad(len(t), 0.004, d * 0.6)

def taiko(d=1.0, amp=1.0):
    """Big cinematic low drum."""
    t = t_arr(d); f = 55 + 60 * np.exp(-t * 18)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) + 0.35 * lp(noise(d), 500) * np.exp(-t * 14)
    return amp * np.tanh(1.6 * reverb(x, 1.2, 0.3))

def strings(freqs, d, amp=0.12):
    """Slow-attack string ensemble pad (cinematic)."""
    t = t_arr(d); x = 0
    for f in freqs:
        for det in (-0.35, 0, 0.35):
            vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t + det * 9)
            x = x + signal.sawtooth(2 * np.pi * np.cumsum(np.full(len(t), f + det) * vib) / SR)
    x = lp(x / (3 * len(freqs)), 2200)
    e = np.minimum(1, t / 0.9) * np.minimum(1, (d - t) / 0.9).clip(0)
    return amp * x * e
