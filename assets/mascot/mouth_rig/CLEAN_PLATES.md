# Clean-plate assets

These images supply skin only inside the pose-specific mask in `profiles.json`. The full generated image is never placed in the film. Every pose's eyes, hair, hands, clothing, sticker outline and transparent silhouette continue to come from `original/<pose>.png`; the compositor asserts that pixels outside the repair mask match exactly.

| Pose | Base image | Clean-plate origin | Pose-specific protection |
|---|---|---|---|
| `explain` | `original/explain.png` | Built-in image-generation edit of the same original pose on 2026-10-20; removed only smile and filled with matching skin | Preserve both hands and all facial details |
| `point_right` | `original/point_right.png` | Built-in image-generation edit of the same original pose on 2026-10-20 | Preserve pointing arm, fingers and other hand |
| `thinking` | `original/thinking.png` | Built-in image-generation edit of the same original pose on 2026-10-20; removed only the frown | Keep hand/fingers on the chin unchanged; use a short mouth range above the fingers |
| `magnify` | `original/magnify.png` | Built-in image-generation edit of the same original pose on 2026-10-20 | Keep magnifying glass/handle unchanged; restore dark neutral rim pixels in front of the moving mouth |
| `point_left` | `original/point_left.png` | Reused the clean plate from the owner-reviewed MouthFix Demo03 | Preserve the accepted point-left placement and appearance |
| `thumbs_up` | `original/thumbs_up.png` | Built-in image-generation edit of the same original pose on 2026-10-20 | Preserve the wink and thumbs-up hand |

Common edit instruction: remove the existing mouth, lips, teeth, tongue, corners and mouth-only creases; fill only the small mouth area with continuous skin; leave no replacement expression; preserve character identity, all other features, framing and transparent sticker background. For `thinking`, remove the frown. For `magnify`, keep the lens and rim. For `thumbs_up`, preserve the wink.

All six generated clean plates are shipped so rendering is offline and deterministic. Do not replace the source mascot with the generated full-frame plate.
