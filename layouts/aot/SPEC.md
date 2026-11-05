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
| 3. Bottom mascot | Mascot scaled 1.2x (A-fixed, approved 2026-11-05), alpha-bbox centre x=540, alpha-bbox bottom anchored at y=1872 + bob (amplitude 7px). | The mascot top varies per pose and mouth shape, so the chips/mascot gap is a frame-QC check, not a static assert: at the A-fixed test frame (t=4.10s) the visible mascot was 600x597px, top y=1269 (14px below the chip strip's end at y=1255, 63px below the lowest actual chip pixel). See "Mascot" below for the CTA rule. |

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
  job gives sentence junctions, rows never mix sentences. Rows
  accumulate left to right (Progressive Word Pills, locked 2026-11-05)
  and the whole row clears at the last word's end + OFF.
- **Words come only from the MFA pipeline (locked 2026-11-05).**
  Approved script + real voice → MFA alignment → `renderer/mfa_to_cues.py`
  (PyThaiNLP newmm tokenisation + per-job merge map) → `words.json` +
  `<words-stem>.provenance.json` (voice/script SHA-256, MFA model, chip
  count). Never hand-write `words.json`, never write a per-project
  build script that invents phrases or guesses times from character
  length — that is exactly how the 2026-11-05 procrastination clip
  shipped 37 phrase chips with estimated times. `compose.py` enforces
  this at load: a chip may have at most 12 grapheme clusters, 16
  characters, 600px rendered width at 80px, and 1.2s duration; times
  must be monotonic; and a real job without its provenance sidecar
  fails. The only exemption is a job with `"fixture": true`, reserved
  for the checked-in layout example. If the load fails, re-run the
  MFA pipeline — never hand-edit a time to make it pass.
- **Word-role colours (locked 2026-11-05, optional):** a word in
  `words.json` may carry a `"role"` field, and the role alone decides
  its chip colour — the renderer never guesses a role from the text:
  `emphasis` (condition/emphasis) = yellow #FFD648, `tool` (tool name /
  command) = blue #2264D8, `result` (good result) = green #38B577,
  `verb` (key verb) = red #F44336, `connector` (connector word) =
  paper #FFFDF6 with dark ink. A word with no role, or an unknown role,
  falls back to the cycling palette. The job author owns the roles;
  a missing role is never an error.
- A chip springs in **0.13s: 0.6x -> ~1.08x -> 1.0x** (locked
  2026-11-05, replacing the old 0.14s back-out pop), rotated -2 or +2
  degrees alternating, with a dark shadow offset. It appears at
  `word.start + OFF` and the row clears at the last word's end + OFF.
- **Stagger (locked 2026-11-05):** sub-elements of a single widget
  appear **0.12s** apart, never all at once. Chips themselves are
  already staggered by their word timings, so the 0.12s stagger does
  not apply to chips.
- **Thai stacked marks (locked 2026-11-05).** Words like "ซื้อ" and
  "รื้อ" stack a sara and a tone mark above one base letter: 4
  codepoints but only 2 grapheme clusters. The compositor therefore
  never slices text by codepoint — typewriter and CTA typing advance
  one grapheme cluster per step — and never centres text by its bbox:
  chips, pills and centred labels are anchored by their baseline, so
  words with stacked marks sit on the same line as words without
  them. Thai shaping needs Pillow with RAQM; `compose.py` fails
  loudly before rendering when RAQM is missing. Never work around
  that by dropping the RAQM flag — install a Pillow with RAQM
  (`renderer/requirements.txt`) and re-run.
- A chip must never end with a bare negation word hanging in the middle
  of a phrase. The job author fixes the row split; the renderer does not
  guess.
- Text on screen comes only from the approved script. Never invent new
  on-screen wording.

## Beat banner and background (locked 2026-11-05, optional)

- A beat may carry `"banner"` (text, **at most 4 tokens** — more is a
  hard error, never silently truncated) and `"bg"` (a pastel hex colour,
  e.g. `"#DDEBFF"`). When present, the banner is drawn centred in the
  top frame's header bar (shrinking until it fits beside the three
  dots) and the background colour changes at exactly the same beat
  boundary; the dot grid is redrawn on the new colour. The banner never
  covers the image below the header.
- When a beat has no banner/bg, the old behaviour is kept exactly:
  cream #FFF6E8 background and a dots-only header bar.

## Poses per clause (locked 2026-11-05)

- The compositor already supports pose switches as `{"at", "pose"}`
  entries, so no new code was needed for this formula. The rule is on
  the job author: list pose switches **per clause, roughly every
  1.5–3.0s**, not only per beat. The example job demonstrates this
  (8 switches over 12.5s). Poses still come only from the rig's
  supported set; the compositor never invents a pose.

## Story widgets (locked 2026-11-05, optional per beat)

- A beat may carry a `"widgets"` list. Each widget has `"type"`,
  `"start"` and `"end"` (absolute times that must lie inside the beat,
  or the job fails loudly) plus its own fields below. **If a beat
  lists no widgets, nothing extra is drawn.** Panel widgets are drawn
  over the top panel for their window only; they never cover the chip
  strip or the mascot. All widget text comes from the job.
- **At most ONE panel widget per beat** (`container` / `typewriter` /
  `cta`). `highlight` is header-only and may co-exist with one panel
  widget. Two panel widgets in one beat put too many moving focal
  points on screen at once (procrastination demo B05+B07, 2026-11-05);
  the job fails loudly instead of rendering the clutter.
- `highlight` — a contrasting sweep across the header bar: a
  translucent red band sweeps left to right over 1.2s, then tints the
  bar and underlines it. (The first locked test used a yellow band on
  the yellow header and was nearly invisible; red on yellow is the
  fix, verified on a real frame.)
- `container` — fields `"items"` (list of short texts), `"box"`
  (box label), `"target"` (target-window label). Items pop in
  staggered 0.12s, shrink into the box, then the box slides into the
  target window and a green tick pops. Drawn with pills, boxes and
  text only — no source footage or artwork. **Labels sit 12px above
  their box, never on its border** (the old centred labels had their
  lower half clipped by the box edge — procrastination B05,
  2026-11-05). The items row must fit the panel width (984px) or the
  job fails loudly.
- `typewriter` — field `"text"`. A command box **at the panel
  bottom, sized to its content** (height = lines only, never a fixed
  260px slab over the image centre — procrastination B07, 2026-11-05)
  types the text one grapheme cluster per step, then shows a green
  tick badge on the box's bottom-right corner. **The full text must
  wrap to at most 3 lines at 48px, with the last line short enough
  to leave room for the tick badge** — otherwise the job fails loudly
  instead of truncating the text silently.
- `cta` — fields `"profile"` (name text only, never a photo),
  `"keyword"`, optional `"pill"` (pill text, defaults to the keyword)
  and optional `"below_mascot": true`. A profile card in the panel
  pops in, the follow button flips to "ติดตามแล้ว" after one stagger,
  and the keyword types into the comment box. If `below_mascot` is
  set, a pill is also drawn in the strip below the mascot, and the
  mascot anchor rule in "Mascot" (1835 during the pill) applies —
  that rule is now implemented in `compose.py` itself, not just in
  this spec: while a below-mascot CTA pill is on screen, the
  mascot's bottom anchor is 1835 instead of 1872.

## Sound: event-driven SFX and BGM bed (locked 2026-11-05, optional)

- A job may carry `"sfx": [{"at", "file", "gain"}]` and/or
  `"bgm": {"file", "gain"}`. Files are resolved relative to the job
  folder and must exist, or the job fails. The compositor mixes them
  with the voice (SFX delayed to their `at` time, BGM looped under
  the voice at its gain) and nothing else changes. **No audio file is
  bundled in this repo, and no synthesised tone is ever presented as
  a real SFX** — a synthetic tone may only be used in `/tmp` to test
  the mixing code, and such a test proves the code, not SFX quality.
- If a job gives no sfx/bgm, the output is the voice alone, exactly
  as before.
- **Only the principle is locked:** SFX tied to visual events, BGM
  kept low under the voice. The SFX timestamps and the ~79.5 BPM /
  F-major figures measured from the rea-video file set are
  low-confidence measurements and are **not** locked constants.
  Real SFX/BGM must be files with clear rights.

## Backward compatibility

- Every new field above is optional. A job without them renders
  exactly as before — **except** the chip spring, which Philip
  locked as the new 0.6x -> 1.08x -> 1.0x in 0.13s for all jobs.
  The old-job render test in the commit that introduced these fields
  verified that nothing else changed for a field-free job.

## Mascot

- **LipInwZa mascot only, from the master lock + rig, never AI-generated.**
  The compositor uses `PoseMouthRig` from `assets/mascot/mouth_rig/`:
  clean-plate mouths interpolated continuously, never a hard sprite swap.
- Poses cycle with the story (thinking, magnify, point_right, explain,
  point_left, thumbs_up). The job lists its pose switches; the compositor
  does not invent them.
- Gentle bob and sway only. The mascot must settle before a cut, and the
  motion must never run right up to a cut with no rest.
- **Size and placement (A-fixed, approved 2026-11-05):** the rig frame
  is scaled uniformly **1.2x** (LANCZOS) and placed by its alpha bbox:
  centre **x=540**, alpha-bbox bottom anchored at **y=1872 + bob**
  (bob amplitude 7px). Measured on the A-fixed test clip at t=4.10s
  (pose explain): visible mascot **600x597px**, versus **501x496px**
  for the pre-A-fixed locked version at the same frame — a 1.198x /
  1.204x enlargement, within 3% of the 1.2x target. The old fixed-canvas
  placement (top y1282) is superseded and must not be reintroduced.
- **CTA rule (projects only — no CTA widget in the generic
  compositor):** if a project adds a CTA pill **below** the mascot
  (pill height 56px at y=1852, as in the A-fixed test clip), then for
  exactly the period the pill is on screen the mascot's alpha-bbox
  bottom anchor must be raised to **1835** (from 1872), so the gap to
  the pill stays **>= 10px** (measured worst case: 11px at bob +7).
  The resulting 37px upward jump when the pill appears is accepted
  per Philip's 2026-11-05 decision — it is not a bug to smooth away
  in this layout. Since the 6-formula lock, the generic `compose.py`
  implements this shift itself for any `cta` widget with
  `"below_mascot": true` (see "Story widgets"); projects using an
  older project compositor must still implement the 1835 anchor
  themselves.

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
2. Build the words with the MFA pipeline only — never a per-project
   build script, never hand-written phrases, never times guessed from
   character length:
   ```bash
   # 1. MFA-align the approved script against voice.wav (thai_mfa)
   # 2. Convert the alignment into chips + provenance:
   python3 renderer/mfa_to_cues.py --mfa-out mfa_out.json --script script.txt \
       --voice voice.wav \
       --out-words words.json --out-provenance words.provenance.json
   ```
   The merge map (`--merge-map`, `{"newmm_merges": [{"parts": [...],
   "chip": "..."}]}`) is the only place a multi-token chip is ever
   defined, and the chip concatenation must equal the script exactly
   or the run fails. Then write the job folder (see `example/`):
   `job.json` with beats, images manifest, words, visemes, and pose
   switches. All paths are relative to the job folder.
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
