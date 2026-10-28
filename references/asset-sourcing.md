# Asset sourcing: legal media, search tactics, pitfalls

## 1. Where to get media

| Source | What | License | Access |
|---|---|---|---|
| **Wikimedia Commons** (`commons.py`) | historical photos, paintings, maps, PD films (1890s–1950s), NASA/US-gov media, CC footage | PD / CC (check the file page) | API, no key |
| Internet Archive (archive.org) | PD feature films, newsreels, Prelinger industrial films | mostly PD; check each item | `advancedsearch.php` API, no key |
| NASA image library (images.nasa.gov) | space photos & video | PD (US gov) | API, no key |
| Smithsonian Open Access, Met Museum, Rijksmuseum, Art Institute of Chicago | art, artifacts, photos | CC0 | APIs, mostly no key |
| Pexels / Pixabay | modern stock video & photos | free license | need an API key, often blocked in sandboxes |
| User-provided files | anything | the user's responsibility | ask if the topic is modern/branded |
| **Procedural** (vidkit graphics, three.js) | maps, charts, icons, props, 3D | yours | always available |

Not allowed: clips from modern movies/TV/YouTube videos, watermarked stock, screenshots of other creators' videos,
logos as main visuals, photos of private individuals. For modern topics (tech, brands, celebrities) where little PD media
exists, lean on graphics, CC Commons photos, and user-provided assets. Tell the user what you used.

## 2. Search tactics for Commons

`python3 $K/commons.py search "<query>" --n 15`
- Videos: add `filetype:video` → `"cowboy filetype:video"`, `"rodeo filetype:video"`, `"western film filetype:video"`.
- Old films are gold for history: search the film title + year (`"Great Train Robbery 1903"`, `"Stagecoach 1939 trailer"`).
- Specific people, places and objects in English: `"Bass Reeves"`, `"Dodge City 1878"`, `"Colt Single Action Army"`.
- Art: `"<artist> <subject> painting"` (`"Remington Stampede"`, `"Charles Marion Russell cowboy"`).
- Maps: `"<region> blank map svg"`, `"<historic entity> map 1800"`, `"<trail/route> map"`.
- Museum and library collections ("LCCN", "NARA", "Google Art Project") are usually high quality and PD.
- Try 2–3 phrasings per need. Collect 1.5× more candidates than you need, then choose by looking.

## 3. Quantities (80 s video, ~40 shots)

- Images: 20–30 (portraits of every named person, every place, every object, 3–5 atmosphere/landscape images).
- Video sources: 5–10. One long PD film can supply 5+ different moments.
- Maps: 1–3 (blank outline map for highlighting, plus a historic map for routes).
- Remember graphics replace about 30% of the visuals, so you don't need an asset for every phrase.

## 4. Downloading

```bash
python3 $K/commons.py vinfo "File:The Great Train Robbery (1903).webm"            # duration, size, transcodes
python3 $K/commons.py get-video --project P gtr "File:The Great Train Robbery (1903).webm" --height 480
python3 $K/commons.py get-images --project P images.txt                          # lines: name|File:Title.jpg
```
- Short clips (< 150 MB): the original is fine. Long films: use the 480p transcode (`--height 480`), because crops are low-res anyway.
- Name assets with short snake_case ids that you'll use in `edit.py` (`bass2`, `dodge1878`, `chisholm_map`).
- Run large downloads in the background and write the script/shot list meanwhile.

**Known pitfalls (all hit in real runs):**
- `urllib` SSL errors on macOS Python → `commons.py` uses `requests`.
- HTTP 429 → descriptive User-Agent, ≥ 1 s between files, retries with backoff (built in).
- Thumbnails are served from `thumb.wikimedia.org`; it must be reachable/allowed in addition to `upload.wikimedia.org`.
- A thumbnail wider than the original fails, so small images are fetched as originals (built in).
- Failed downloads saved as tiny HTML "images": `get-images` only saves `image/*` responses. If you download by other
  means, delete files under 5 KB and re-fetch.
- Your shell's `find`/`rm` may be wrapped or restricted: verify deletions with `ls -la`.

## 4b. Converting documents (papers, PDFs, SVGs)
- PDF page → image: `pdftoppm -r 150 -png -f 1 -l 1 paper.pdf raw/img/paper` (poppler) or PyMuPDF. **Don't use macOS `sips`
  for PDFs**: it can silently produce an all-black image.
- SVG: download the PNG rendering from Commons (`commons.py get-images` does this automatically).
- After any conversion or download run `sheet.py --project P check`. It flags black, white or flat images, error pages
  saved as .jpg, tiny images, and videos that don't decode. Silent bad assets are the most expensive bugs because each costs
  a render-and-look cycle.

## 4c. Rate limits (HTTP 429)
Downloads are the least predictable step. Download in one batch per type (`get-images list.txt`, `get-videos list.txt`),
in the background, while you write the script. The tools pause between files (`COMMONS_PAUSE`, default 2.5 s), honour
`Retry-After` and back off up to ~4 minutes. If files still FAIL, wait a few minutes and **re-run the same command**: existing
files are skipped. Don't hammer the server with parallel downloads.

## 4d. Modern tech / abstract topics
Expect 60–70% of visuals to be procedural: `g_nodes` diagrams, counters, splits, timelines, three.js clips. Commons has
little usable modern footage (videos of server rooms etc. are often vlogs with hosts' faces and channel logos). Good real
images: portraits of inventors (CC on Commons), paper title pages (PDF → PNG), product/hardware photos, data-centre photos
from companies' CC releases, screenshots of open-source project logos/sites only as small labels.

## 5. Look before you use (mandatory)

```bash
python3 $K/sheet.py --project P video gtr --every 8        # contact sheet with timestamps
python3 $K/sheet.py --project P peek gtr@655 stagecoach@178 # exact frames to confirm timecodes
python3 $K/sheet.py --project P images                      # all images labelled
python3 $K/sheet.py --project P grid chisholm_map           # coordinate grid for pins/routes
```
Open each sheet (you must be able to view images). Note in your shot list: `stagecoach@178 = Wayne firing rifle (good, central)`.
Contact-sheet tile positions are only approximate times, so confirm the final picks with `peek`.

Pick moments with: a clear central subject (it survives the 9:16 crop), motion (riders, crowds, smoke, trains),
expressive faces, and no burnt-in modern subtitles, logos or TV bugs. For modern footage, check for broadcaster
logos (e.g. a "21" channel bug) and avoid those seconds.
