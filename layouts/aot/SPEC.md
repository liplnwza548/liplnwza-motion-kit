# AoT layout — the default layout for new work (locked 2026-11-02, confirmed 2026-11-03)

> **Read this first. This layout is the default for new work in this repo.**
> The paper layout in `renderer/kit.py` (`paper-v021`) and the 15-second
> benchmark in `examples/benchmark15/` are a legacy technical smoke test only.
> They prove the old engine runs. They are NOT a style reference for new
> clips. Do not copy their topic, their card layout, or their chip position
> into a new clip.

## Where this layout came from

This layout is the layout Philip approved in the Attack on Titan v2 test
(2026-10-28, 1080x1920, 30fps, 46.13s) and then locked as the channel's main
layout on 2026-11-02, confirmed again on 2026-11-03 as the main line
(Motion Kit) versus the Genhaha supplementary line. The same layout was
reused, with the same zones, for the Kurt Cobain full clip and for the
yawning example in its AoT version. The compositor in this folder
(`compose.py`) is a generic port of that proven compositor: no topic,
no voice, no image and no beat from any earlier clip is hardcoded in it.

## The three zones (1080x1920, 30fps, all coordinates in pixels)

| Zone | Position | Rule |
| --- | --- | --- |
| 1. Top image frame | x 48..1032, y 48..928. Header bar 96px high, colour #FFE9A8, with three dots (red, yellow, green). Image area below the header: 984x784, centre-crop cover. | One image per beat. Hard cut exactly on the beat boundary (`cut_frame = ceil(boundary x 30)`, first beat starts at frame 0). **No zoom, no pan, no overlay, no gold-dust particles on the image.** The image itself must already tell the story. |
| 2. Middle word chips | Strip y 915..1255 (height 340). Chip centre is roughly y 1080 in the strip. | See "Chips" below. Chips live here, in the middle, not at the bottom of the screen. |
| 3. Bottom mascot | Mascot top y 1282 (before bob), centred horizontally. Bob amplitude 7px. | The gap between the chips strip (ends y 1255) and the mascot top, minus bob, must stay >= 20px. That gap is asserted in code, not eyeballed. |

Background below the top frame: cream #FFF6E8 with a faint dot grid.
Note on the 13px container overlap: the chips strip container starts
at y 915 while the top frame ends at y 928, but the strip is
transparent at its top and chip pixels themselves start around
y 1010 (chip centre ~1080, height 140), so no chip pixel ever covers
the top frame. The mascot gap below is the hard rule (see the table).

## Images

- **AI-generated images are the main illustration for every project**
  (locked 2026-11-02). Generate a new image per beat, in the style of that
  project, with no text baked into the image.
- For a story/recap project, the approved reference is cinematic fan-art
  style: strong light and shadow, no direct copy of a character's costume
  or logo, no text.
- Every image used must be listed in the job's image manifest with its
  exact filename, its status (`accepted` only), and its SHA-256. A missing
  beat, a non-accepted image, or a SHA mismatch is a hard failure.
  Never fall back to a glob search that could silently pick a rejected
  or stale file.
- Minimum image size: 1024x768. Images are centre-crop covered to 984x784,
  never stretched.
- Beats change every 2-3 seconds in a story clip. The beat sheet, not the
  renderer, decides where each image starts and ends.

## Chips (subtitles)

- Style: Motion Kit paper chips, every project. Font Prompt-Bold only.
  Palette, cycling in order: yellow #FFD648, blue #2264D8, red #F44336,
  green #38B577. Ink #181B26, paper #FFFDF6.
- **Split into words / short phrases before rendering.** A whole long
  sentence as one chip is the old mistake this layout fixes. Rule used by
  the compositor: at most 3 words per row, and at most 1.2 seconds from
  the first word's start to the last word's end in the same row. If the
  job gives sentence junctions, rows never mix sentences.
- A chip pops in 0.14s with a back-out overshoot, rotated -2 or +2
  degrees alternating, with a dark shadow offset. It appears at
  `word.start + OFF` and the row clears at the last word's end + OFF.
- A chip must never end with a bare negation word hanging in the middle
  of a phrase. The job author fixes the row split; the renderer does not
  guess.
- Text on screen comes only from the approved script. Never invent new
  on-screen wording.

## Mascot

- **LipInwZa mascot only, from the master lock + rig, never AI-generated.**
  The compositor uses `PoseMouthRig` from `assets/mascot/mouth_rig/`:
  clean-plate mouths interpolated continuously, never a hard sprite swap.
- Poses cycle with the story (thinking, magnify, point_right, explain,
  point_left, thumbs_up). The job lists its pose switches; the compositor
  does not invent them.
- Gentle bob and sway only. The mascot must settle before a cut, and the
  motion must never run right up to a cut with no rest.

## Voice and loudness

- Voice is the anchor: clip length, beat cuts and chip timing all follow
  the real voice file, never a hardcoded duration.
- Social/content clips use Philip's clone voice (formula v2, locked
  separately and never published in this repo: no reference audio, no
  cloning details, no voice model files belong here).
- **Sales clips use Philip's real recorded voice only. Never clone
  voice for a sales clip.** This is the one exception to the clone-voice
  rule and it overrides everything else.
- Target loudness for a finished clip: -16 LUFS, true peak at most
  -1.0 dBTP. Check the finished MP4 itself, not just the WAV.
- **P2 guard — OFF = 0.08:** chip and pose timing in this layout uses
  `OFF = 0.08` seconds. Do not change it without Philip's own sync-test
  decision. It is not a tuning knob.

## What is NOT this layout

- Not the paper layout: no title card in the middle, no media panel in
  the middle, no aside card, no chips at the very bottom (y 1570+), no
  progress bar at the bottom.
- Not the benchmark: the benchmark's topic (flying car), its red-car
  illustration and its 4-scene card structure are a technical fixture.
  Reusing them as a style makes a new clip look old, which is exactly
  the failure this folder exists to prevent.
- Not a Genhaha style: Genhaha styles keep their own picture, character
  and subtitle rules. Do not force this layout, the mascot or these
  chips onto a Genhaha clip unless Philip orders a LipInwZa-channel clip
  specifically.

## How to make a new clip with this layout

1. Philip approves the script and the voice first. No rendering before
   that approval.
2. Write a job folder (see `example/`): `job.json` with beats, images
   manifest, words, visemes, and pose switches. All paths are relative
   to the job folder.
3. Run `python layouts/aot/compose.py --job <job.json> --out <video.mp4>`.
   For a quick layout check, render stills first:
   `python layouts/aot/compose.py --job <job.json> --stills <dir>`.
4. Check the finished MP4 itself: frame at each cut (before / at /
   after), chips against the real voice, mascot mouth against the real
   voice, loudness from the MP4. Report what was checked from the real
   file, not from a plan.
5. Never overwrite an old finished file. Every new render is a new file.

## Files in this folder

- `compose.py` — generic AoT compositor (PIL frames + ffmpeg, no AI video).
- `example/` — a topic-neutral job template with synthetic placeholder
  images, so the layout can be checked without any earlier clip's voice
  or images. Replace every placeholder with approved material for a
  real clip; do not publish the example itself.
- `PROMPT-FOR-CHATGPT.md` — the short prompt to paste to ChatGPT after
  it clones this repo, so it starts from this spec instead of the
  benchmark.
