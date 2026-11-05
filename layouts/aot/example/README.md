# AoT layout example — placeholder only, do not publish

This folder proves the AoT layout runs. It is not a clip.

- Voice, words and visemes are borrowed from `examples/benchmark15/`
  **only as a technical fixture**, so the layout can be checked without
  any real clip's voice. The benchmark's topic and its paper layout are
  not part of this example. That is why this job carries
  `"fixture": true` — it exempts the example from the provenance
  sidecar that real jobs must ship. Never copy that flag into a real
  job.
- Images are synthetic placeholders (plain shapes, no text, no story).
  They exist only so the top frame, the chips strip and the mascot can
  be checked for overlap and position.
- For a real clip, replace all three things: the voice (approved clone
  voice for social clips, real recorded voice for sales clips), the
  words/visemes for that voice, and every placeholder image with an
  AI-generated image listed in the manifest with its SHA-256.

Run a quick layout check (3 stills, no full video):

```bash
python layouts/aot/compose.py --job layouts/aot/example/job.json --stills /tmp/aot-check
```

Check the stills by eye: top frame at the top, chips in the middle,
mascot at the bottom, no overlap, chips popping word by word.

Run the full example video:

```bash
python layouts/aot/compose.py --job layouts/aot/example/job.json --out /tmp/aot-example.mp4
```

Never overwrite an old finished file. Every new render is a new file.
