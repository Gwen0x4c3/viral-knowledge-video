"""Master timeline: places every narration line on the clock using TTS word boundaries.

Reads the project's script_data.py:
  LINES  = [(id, text, rate, pitch, [(keyword, style), ...]), ...]   style: "y" yellow | "r" red | "big" centre pop
  GAP    = 0.14          default pause before each line (s)
  PRE    = {"L05": 0.55}  extra pause before specific lines (section breaks, dramatic beats)
  OUTRO  = 2.3           seconds after the last line (ending visual + music tail)
  SAY    = {"etcd": "E T C D", "K8s": "K8S"}   optional pronunciation map: what the voice says instead of the
                         displayed spelling (subtitles keep the original text; timings are mapped back)
Exposes LINES_T (list of dicts with start/end/words in absolute seconds), L (dict by id), TOTAL.
"""
import json, os, sys, importlib
import config
if __name__ == "__main__": config.parse_project_arg(sys.argv[1:])

from textmap import say_text

def _load():
    config.set_project(config.PROJECT)
    sd = importlib.import_module("script_data")
    gap = getattr(sd, "GAP", 0.14); pre = getattr(sd, "PRE", {}); outro = getattr(sd, "OUTRO", 2.3); say = getattr(sd, "SAY", {})
    head, tail = 0.04, 0.10
    out, t = [], 0.0
    for lid, text, rate, pitch, hl in sd.LINES:
        p = config.build("tts", f"{lid}.json")
        if not os.path.exists(p): raise SystemExit(f"timeline: missing {p} — run tts.py first")
        words = json.load(open(p))
        if not words: raise SystemExit(f"timeline: {lid} has no word boundaries — re-run tts.py {lid}")
        s0 = max(0.0, words[0]["t"] - head)
        s1 = words[-1]["t"] + words[-1]["d"] + tail
        t += pre.get(lid, gap)
        ws = [dict(w=w["w"], t=t + w["t"] - s0, e=t + w["t"] + w["d"] - s0) for w in words]
        spoken, cmap = say_text(text, say)
        out.append(dict(id=lid, text=text, spoken=spoken, cmap=cmap, hl=hl, start=t, end=t + (s1 - s0), src0=s0, src1=s1, words=ws))
        t += s1 - s0
    return out, t + outro, sd

LINES_T, TOTAL, SCRIPT = _load()
L = {x["id"]: x for x in LINES_T}

def spans(line):
    """Map each TTS word to its (start_char, end_char) in the DISPLAY text (handles SAY substitutions)."""
    sp, cmap, pos, out = line["spoken"], line["cmap"], 0, []
    for w in line["words"]:
        i = sp.find(w["w"], pos)
        if i < 0: i = pos
        j = min(len(sp), i + max(1, len(w["w"])))
        if i < len(cmap): out.append((cmap[i], cmap[j - 1] + 1, w))
        pos = j
    return out

def at(lid, sub, end=False):
    """Absolute time (s) when the word containing `sub` starts (or ends) in line `lid`.
    Use this for EVERY cut / label / sfx so visuals stay locked to the narration."""
    line = L[lid]; i = line["text"].find(sub)
    if i < 0: raise KeyError(f"at(): '{sub}' not found in {lid}: {line['text']}")
    for a, b, w in spans(line):
        if b > i: return w["e"] if end else w["t"]
    return line["words"][-1]["t"]

if __name__ == "__main__":
    for x in LINES_T:
        print(x["id"], f"{x['start']:6.2f}-{x['end']:6.2f}", " ".join(f"{w['w']}@{w['t']:.2f}" for w in x["words"]))
    print(f"TOTAL {TOTAL:.2f}s")
