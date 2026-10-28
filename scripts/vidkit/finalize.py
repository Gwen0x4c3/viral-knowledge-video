"""Mux video + audio, normalise loudness to -14 LUFS, encode at an upload-friendly bitrate, make a QA sheet.

usage: python finalize.py --project DIR "out/标题.mp4"
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import config
ARGV = config.parse_project_arg(sys.argv[1:])
out = config.path(ARGV[0]) if not os.path.isabs(ARGV[0]) else ARGV[0]
os.makedirs(os.path.dirname(out), exist_ok=True); os.makedirs(config.build("sheets"), exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", config.build("video_noaudio.mp4"), "-i", config.build("mix.wav"),
                "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-c:v", "libx264", "-preset", "slow", "-b:v", "12M", "-maxrate", "16M",
                "-bufsize", "24M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                "-movflags", "+faststart", out], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-vf", "fps=1,scale=150:-1,tile=15x7", "-frames:v", "1",
                config.build("sheets", "final.jpg")], check=True)
probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=width,height", "-of", "compact", out], capture_output=True, text=True).stdout
lufs = [l for l in subprocess.run(["ffmpeg", "-nostats", "-i", out, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr.splitlines() if l.strip().startswith("I:")]
print(probe.strip()); print("loudness", lufs[-1].strip() if lufs else "?"); print("->", out); print("QA sheet ->", config.build("sheets", "final.jpg"))
