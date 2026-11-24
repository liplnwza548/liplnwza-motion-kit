# `scene_spec.json` Schema Reference (`liplnwza-motion` v3.4)

## Top-Level Structure

```json
{
  "title": "Clip Title",
  "duration": 45.0,
  "audio": {
    "vo_path": "/path/to/voice.wav",
    "visemes_path": "/optional/path/to/visemes.json",
    "bgm_preset": "funk_brass",
    "bgm_path": "/optional/custom/bgm.mp3",
    "bgm_gain": 0.22
  },
  "beats": [ ... ],
  "word_rows": [ ... ]
}
```

- When `audio.vo_path` exists, clip duration is locked automatically to `ffprobe(vo_path)`.
- `audio.bgm_preset`: `"funk_brass"` (default, 118 BPM Cory Wong Funk + Brass), `"warm_groove"` (108 BPM Rhodes), or `"mystery_pulse"` (104 BPM deep bass tension).

## Beat Fields (`beats[]`)

| Field | Allowed Values |
| :--- | :--- |
| `id` | `"B01"`, `"B02"`, ... |
| `start`, `end` | Seconds (continuous, first beat starts at `0.0`) |
| `bg` | `"dark_navy_grid"`, `"yellow_lined"`, `"cream_graph"`, `"pale_blue_grid"`, `"pale_pink_grid"`, `"pale_green_grid"` |
| `ribbon` | Short Thai/English top banner text (2-5 words) |
| `ribbon_color` | `"red"`, `"blue"`, `"yellow"`, `"green"` |
| `pose` | 16 full-body Clean-Plate poses: `"wave"`, `"pointer"`, `"clipboard"`, `"confident"`, `"magnify"`, `"laptop_focus"`, `"laptop_smile"`, `"cheer"`, `"facepalm"`, `"thinking_chin"`, `"shocked"`, `"holding_card"`, `"thumbs_up_full"`, `"newspaper_hold"`, `"shrug"`, `"idea_finger"` |
| `sidekick` | 12 transparent WebP props/sidekicks: `"bot_curious"`, `"bot_cheer"`, `"bot_shock"`, `"badge_alert"`, `"badge_check"`, `"badge_question"`, `"pointer_stick"`, `"clipboard"`, `"magnifying_glass"`, `"laptop"`, `"newspaper"`, `"lightbulb"` |
| `camera` | `"push_in"`, `"pull_out"`, `"focus_tv"`, `"punch_in"` |
| `transition` | `"paper_slide"`, `"page_peel"`, `"whip_zoom"`, `"ink_flash"` |
| `widget` | Object with `"type"` from the 12 widgets below |

## 12 Built-In Animated Micro-Widgets (`widget.type`)

1. `rating_stars`: `{ "type": "rating_stars", "card_title": "...", "stars": 5, "filled": 4, "badge": "..." }`
2. `chat_bubbles`: `{ "type": "chat_bubbles", "header": "...", "messages": ["..."], "stamp": "..." }`
3. `calendar_flip`: `{ "type": "calendar_flip", "before_month": "...", "before_num": "30", "after_month": "...", "after_num": "40", "flip_at": 0.65, "caption": "..." }`
4. `checklist_ticks`: `{ "type": "checklist_ticks", "items": ["...", "...", "..."] }`
5. `cycle_diagram`: `{ "type": "cycle_diagram", "nodes": ["1. ...", "2. ...", "3. ...", "4. ..."] }`
6. `score_grid`: `{ "type": "score_grid", "title": "...", "cols": 5, "rows": 3, "hits": 12 }`
7. `waveform_notes`: `{ "type": "waveform_notes", "label": "..." }`
8. `terminal_code`: `{ "type": "terminal_code", "title": "...", "lines": ["$ ...", "> ..."] }`
9. `screenshot_frame`: `{ "type": "screenshot_frame", "kicker": "...", "headline": "...", "source": "...", "quote": "..." }`
10. `media_clip_frame`: `{ "type": "media_clip_frame", "channel_label": "LEMO: ISO-INFOGRAPHIC", "clip_path": "/tmp/lemo_clip.mp4", "credit": "..." }`
11. `vote_buttons`: `{ "type": "vote_buttons", "left": "...", "right": "...", "prompt": "..." }`
12. `cta_comment_box`: `{ "type": "cta_comment_box", "keyword": "...", "sublabel": "..." }`

## Progressive Word Chips (`word_rows[]`)

```json
{
  "start": 0.0,
  "end": 1.25,
  "words": [
    { "text": "รถบินได้", "start": 0.0, "role": "emphasis" },
    { "text": "ของ", "start": 0.64, "role": "connector" },
    { "text": "อีลอน มัสก์", "start": 0.82, "role": "tool" }
  ]
}
```

- `role` colors: `"emphasis"` (yellow), `"tool"` (blue), `"result"` (green), `"verb"` (red), `"connector"` (cream white).
