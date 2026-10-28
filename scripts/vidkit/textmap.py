"""Pronunciation map helper shared by tts.py and timeline.py."""

def say_text(text, say):
    """Apply the SAY pronunciation map. Returns (spoken_text, cmap) where cmap[i] = index in the DISPLAY text of
    spoken char i, so word timings of the spoken text can be mapped back onto the subtitle characters."""
    keys = sorted(say, key=len, reverse=True)
    out, cmap, i = [], [], 0
    while i < len(text):
        k = next((k for k in keys if text.startswith(k, i)), None)
        if k:
            rep = say[k]
            for j, ch in enumerate(rep):
                out.append(ch); cmap.append(i + min(len(k) - 1, int(j * len(k) / max(1, len(rep)))))
            i += len(k)
        else:
            out.append(text[i]); cmap.append(i); i += 1
    return "".join(out), cmap
