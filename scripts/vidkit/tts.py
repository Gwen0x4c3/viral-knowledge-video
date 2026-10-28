"""Generate narration with edge-tts (free Microsoft neural voices) + word-boundary timings.

usage: python tts.py --project DIR [L01 L05 ...]     (no ids = all lines)
Writes build/tts/<id>.mp3 and build/tts/<id>.json  [{t, d, w}, ...] (seconds).

Voice: script_data.VOICE (default zh-CN-YunxiNeural). One call per line so every line can
have its own rate/pitch (that is how the delivery gets "expressive").
Network: edge-tts talks to speech.platform.bing.com over websockets. aiohttp ignores
HTTPS_PROXY, so we pass the proxy explicitly — without this it fails with a DNS error in sandboxes.
"""
import asyncio, json, os, sys, importlib, time
sys.path.insert(0, os.path.dirname(__file__))
import config
argv = config.parse_project_arg(sys.argv[1:])
import edge_tts

sd = importlib.import_module("script_data")
VOICE = getattr(sd, "VOICE", "zh-CN-YunxiNeural")
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
OUT = config.build("tts"); os.makedirs(OUT, exist_ok=True)

def validate():
    ids = set()
    for row in sd.LINES:
        assert len(row) == 5, f"LINES row must be (id, text, rate, pitch, highlights): {row}"
        lid, text, rate, pitch, hl = row
        assert lid not in ids, f"duplicate id {lid}"; ids.add(lid)
        assert rate.endswith("%") and rate[0] in "+-", f"{lid}: rate like '+20%' got {rate}"
        assert pitch.endswith("Hz") and pitch[0] in "+-", f"{lid}: pitch like '+4Hz' got {pitch}"
        for kw, st in hl:
            assert kw in text, f"{lid}: highlight '{kw}' not in text"
            assert st in ("y", "r", "big"), f"{lid}: style must be y/r/big"

async def one(lid, text, rate, pitch):
    for attempt in range(4):
        try:
            c = edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch, proxy=PROXY, boundary="WordBoundary")
            words, audio = [], bytearray()
            async for ch in c.stream():
                if ch["type"] == "audio": audio += ch["data"]
                elif ch["type"] == "WordBoundary":
                    words.append(dict(t=ch["offset"] / 1e7, d=ch["duration"] / 1e7, w=ch["text"]))
            if not words: raise RuntimeError("no word boundaries returned")
            open(f"{OUT}/{lid}.mp3", "wb").write(audio)
            json.dump(words, open(f"{OUT}/{lid}.json", "w"), ensure_ascii=False)
            return words
        except Exception as e:
            print(f"  {lid} attempt {attempt + 1} failed: {e}"); time.sleep(2 + attempt * 3)
    raise SystemExit(f"TTS failed for {lid}")

async def main():
    validate()
    total = 0
    from textmap import say_text
    SAY = getattr(sd, "SAY", {})
    for lid, text, rate, pitch, _ in sd.LINES:
        if argv and lid not in argv: continue
        spoken = say_text(text, SAY)[0]
        w = await one(lid, spoken, rate, pitch)
        span = w[-1]["t"] + w[-1]["d"] - w[0]["t"]; total += span
        print(f"{lid} {span:5.2f}s {len(text):3d} chars  {text}")
    if not argv: print(f"speech total {total:.1f}s (add ~0.2s per line + outro for video length)")

asyncio.run(main())
