"""Objective audio QA (you usually cannot listen — so measure).

usage: python check_audio.py --project DIR [--whisper]
  * RMS per 3 s for music_only.wav and mix.wav (catches silent / missing sections and level jumps)
  * clipping count
  * --whisper: transcribes mix.wav (openai-whisper 'small' or faster-whisper) and prints it next to the script so you
    can spot words masked by music/SFX. If a keyword is mis-heard, move/soften the SFX on that word.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import config
ARGV = config.parse_project_arg(sys.argv[1:])
import numpy as np
from scipy.io import wavfile

def db(a): return 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-9)
for name in ("music_only.wav", "mix.wav"):
    sr, x = wavfile.read(config.build(name)); x = x.astype(float) / 32768
    if x.ndim > 1: x = x[:, 0]
    rows = [db(x[i * sr * 3:(i + 1) * sr * 3]) for i in range(int(len(x) / sr / 3))]
    print(f"{name:15s} rms/3s:", " ".join(f"{r:.0f}" for r in rows))
    quiet = [i * 3 for i, r in enumerate(rows) if r < -40]
    if name == "music_only.wav" and quiet: print("   NOTE: near-silent music at", quiet, "s (ok only if intended: MUSIC_HOLES / silence)")
    print(f"   peak {np.max(np.abs(x)):.3f}  clipped samples {int(np.sum(np.abs(x) > 0.999))}")
if "--whisper" in ARGV:
    from timeline import LINES_T
    try:
        import whisper
        r = whisper.load_model("small").transcribe(config.build("mix.wav"), language="zh", initial_prompt="以下是普通话的句子。")
        segs = [(s["start"], s["text"]) for s in r["segments"]]
    except Exception as e:
        from faster_whisper import WhisperModel
        segs = [(s.start, s.text) for s in WhisperModel("small").transcribe(config.build("mix.wav"), language="zh")[0]]
    print("\n--- heard ---")
    for t, txt in segs: print(f"{t:6.1f} {txt}")
    print("\n--- script ---")
    for ln in LINES_T: print(f"{ln['start']:6.1f} {ln['text']}")
