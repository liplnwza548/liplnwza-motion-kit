# Prompt to paste to ChatGPT after it clones this repo

> Clone https://github.com/liplnwza548/liplnwza-motion-kit and read
> `layouts/aot/SPEC.md` FIRST, before you read anything else about style.
>
> The default style for new work is the AoT layout in that spec:
> top image frame, middle word chips, bottom mascot. 1080x1920, 30fps.
>
> Do NOT use `examples/benchmark15/` as a style reference. It is only a
> technical smoke test for the old paper engine. Its topic, its card
> layout and its chip position are legacy, not the target.
>
> Do NOT use the old paper layout in `renderer/kit.py` (`paper-v021`)
> for a new clip. Use `layouts/aot/compose.py` and the job format in
> `layouts/aot/example/job.json`.
>
> First step only: run the AoT example stills check in
> `layouts/aot/example/README.md` and report the three stills you
> checked (top frame / chips / mascot, any overlap?). Stop there and
> wait for approval before you render a full clip or change any
> approved file.
>
> Rules you must not break: images are AI-generated per beat with a
> manifest (accepted + SHA-256 only, no glob fallback); chips are split
> into words, max 3 per row; mascot is master-lock + rig only, never
> AI-generated; sales clips use real recorded voice only, never clone
> voice; OFF = 0.08 must not change; never overwrite an old file.
