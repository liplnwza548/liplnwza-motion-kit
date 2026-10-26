# Job authoring notes

## Opening scene

The first scene must show a visible scene title or hero media. Keep
`show_title` enabled and provide a non-empty scene `title`, or provide valid
image/video media in that first scene. The validator rejects an opening scene
that hides its title and has no hero media.

## Mascot placement

New jobs keep the mascot at the lower left by default. To change sides between
scenes, set `allow_mascot_side_switch: true` at the job root and set the
`right` boolean only on scenes that should place the mascot on the right.
Legacy jobs without `render_policy_version` retain their explicit per-scene
`right` behavior for compatibility.

## Closing CTA

Write the final scene CTA as a two-way invitation, such as asking viewers to
comment a keyword or answer a short question. A one-way “follow/subscribe” line
alone is not enough. Promise a reply, link, or other benefit only when the job
can actually deliver it and the offer belongs to the approved script. This is
an authoring rule; the renderer does not validate CTA wording.

## Summary items

On new jobs, a `summary` scene may include up to four `items` below its `body`.
The items enter in order during the existing scene duration; rendering does
not extend the scene to finish their animations.
