"""Narration script.  ->  run tts.py after every change, then timeline.py to see the length.

LINES row: (id, text, rate, pitch, highlights)
  text       = exactly what is spoken AND shown as the subtitle. Chinese punctuation splits subtitle phrases.
               Write numbers as digits ("1886年", "3000") — the voice reads them correctly and subtitles look punchy.
               Avoid English words (the Chinese voice mangles them); use the Chinese name and show English in a label.
  rate       = "+0%".."+24%"    (explanations +18~24% — never above +26%, it sounds rushed; emotional beats slower)
  pitch      = "-6Hz".."+10Hz"  (questions/surprise higher; sad/serious lower)
  highlights = [(keyword, "y"|"r"|"big")]  1-3 per line. keyword must appear verbatim in text.
               "y" = yellow (names, places, things), "r" = red (shocking/negative words),
               "big" = also pops huge mid-screen — max ~1 per 10 s, only for THE punchline of a beat.
"""
VOICE = "zh-CN-YunxiNeural"     # energetic young male; see references/audio.md for alternatives
GAP = 0.16
PRE = {"L03": 0.6, "L05": 0.7}   # longer pauses before new sections / big reveals (0.5-0.9 s)
OUTRO = 2.3

LINES = [
    # Structure comes from your chosen pitch (references/script-writing.md §1c/§3) — these placeholders are neutral.
    # --- HOOK (0-3 s): a vivid image + the CENTRAL QUESTION that the whole video answers ---
    ("L01", "TODO 一个具体画面，加上核心问题？", "+14%", "+6Hz", [("核心问题", "y")]),
    ("L02", "TODO 为什么这个问题值得看：反差或代价。", "+18%", "+4Hz", [("代价", "r")]),
    # --- BEAT 1 (each beat moves toward the answer and raises the stakes) ---
    ("L03", "TODO 第一个线索或第一个转折。", "+18%", "+4Hz", [("线索", "y")]),
    ("L04", "TODO 证据：一个具体细节或数字，比如3000。", "+20%", "+0Hz", [("3000", "r")]),
    # ... more beats; best beat last; 18-24 lines (story) / 22-34 lines (explainer) ...
    # --- PAYOFF: answer the central question + the line viewers will repeat ---
    ("L05", "TODO 答案，和一句让人想转述的话。", "+12%", "+0Hz", [("答案", "y")]),
    # --- a SPECIFIC question for the comments (not a bare 评论区聊聊) ---
    ("L06", "TODO 如果是你，你会选哪个？", "+12%", "+4Hz", [("选哪个", "y")]),
]
