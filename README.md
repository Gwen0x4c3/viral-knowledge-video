# viral-knowledge-video

给 AI Agent 用的 skill：给一个选题，产出一条能直接发的竖屏知识短视频，成品是一个 mp4。

它不是调个 API 返回视频链接的工具。整套后期流水线——选题角度、脚本、配音、字幕、素材、配乐、音效、剪辑、渲染、质检——都在这个仓库里，由 Agent 按照 `SKILL.md` 的流程在本机跑完。`scripts/vidkit/` 是配套的渲染引擎，纯 Python + ffmpeg，没有云服务依赖。

一条成片大概长这样：

- 9:16，1080×1920，60–150 秒（故事类 60–90，原理讲解类 90–150）
- 前 3 秒有钩子，中位镜头 2 秒左右，按台词的词切镜头
- 解说词逐句有事实依据（有争议的说法加「传说 / 据估计」，查不到出处的数字宁可不用）
- TTS 配音，默认 edge-tts，带词级时间戳，字幕逐字弹出
- 素材只从公有领域 / CC 渠道来（Wikimedia、Met 等），BGM 和音效是程序合成的
- 混音归一到 -14 LUFS，交付前过一张 QA 清单

脚本分两种模式：**故事 / 辟谣**（历史人物、冷知识）和**概念讲解**（算法、科学原理、系统机制）。讲解模式有个硬性门槛：只把字幕喂给一个没看过视频的模型，让它复述内容，复述不出来就回头改脚本。

## 先说不完美的地方

- 配音是 edge-tts，免费即时，但念长句偏平。文档里留了接豆包 / MiniMax / Azure 的口子（`references/audio.md` §1），有 key 明显更好
- BGM 是程序合成的功能伴奏，跟情绪走，但别指望编曲
- Agent 听不了音频。声音把关靠响度测量和 Whisper 转写回查，人耳那一关还得你自己过
- 流程的核心动作是「渲一帧、看一帧、改一帧」，所以**需要能读图的模型**，纯文本模型跑不了
- 一条视频 Agent 要跑一两个小时，中间若干轮渲染-检查循环，token 消耗不小

## 环境

- Python 3.9+；ffmpeg + ffprobe 在 PATH 里
- `pip install numpy scipy opencv-python-headless pillow edge-tts requests`，音频检查另装 `openai-whisper` 或 `faster-whisper`
- 一个粗体中文字体（macOS 自带；Linux 装 `fonts-noto-cjk`。`python3 scripts/vidkit/config.py` 会打印检测结果）
- 磁盘 2 GB、4 核以上；联网用到 `speech.platform.bing.com`（TTS）和 `*.wikimedia.org`（素材），沙箱里记得放行
- 可选：Playwright + Chromium 跑 three.js 3D 镜头，没有就退回 2D 图形

## 用法

把整个目录放进 agent 的 skills 目录（Claude Code 是 `~/.claude/skills/`，其他 agent 按各自的约定），然后正常说话：

> 帮我做个讲中世纪骑士的短视频

Agent 会自己建工程、走完八步流程，最后交给你 mp4 路径，外加一份「用了哪些事实、哪些说法是估计」的清单。

vidkit 也能脱离 skill 单独用，每个脚本都有 docstring：

```bash
K=path/to/viral-knowledge-video/scripts/vidkit
python3 $K/new_project.py my-video                        # 建工程（script_data.py + edit.py 模板）
python3 $K/tts.py --project my-video                      # 配音 + 词级时间戳
python3 $K/render.py --project my-video stills 12 33 55   # 渲指定帧出来检查
python3 $K/render.py --project my-video                   # 全量渲染
python3 $K/finalize.py --project my-video "out/标题.mp4"   # 混音封装，-14 LUFS
```

改内容就是改两个文件：`script_data.py`（说什么）和 `edit.py`（画面怎么切）。所有时间点用 `at("L12", "骑士")` 锚到台词的词上，重跑 TTS 后时间轴自动跟着变，不用手调秒数。

## 流程

选题定角度 → 写脚本（附事实表）→ TTS 测时长 → 按分镜找素材并逐帧目检 → 写剪辑 → 渲静帧逐张检查 → 混音 + Whisper 回查 → 全量渲染 → QA 清单 → 交付报告。每步有 gate，过不了就回头改。

写法细节在 `references/` 里：脚本结构和一个逐行标注的完整范例（script-writing.md）、素材渠道与下载坑（asset-sourcing.md）、剪辑语法与节奏（editing.md）、转场与图形模板清单（effects-catalog.md）、配音配乐与验音（audio.md）、八类题材的风格预设（style-presets.md）、上线前检查表（qa-checklist.md）。

## 目录

```
SKILL.md                  # 流程与质量标准，Agent 读这个
references/*.md           # 八份参考文档
scripts/vidkit/*.py       # vidkit 渲染引擎
scripts/anim/             # three.js 3D 镜头渲染（可选）
templates/project/        # 新工程模板
```

## 素材版权

硬性规定：只用公有领域、CC、用户自备或程序生成的素材，成品无水印、无 logo、无现代影视片段。`commons.py` 自带规范的 User-Agent 和 429 退避重试。历史类选题主要吃 Wikimedia Commons 和博物馆开放接口（Met 的 CC0 直链很好用，不限流）。
