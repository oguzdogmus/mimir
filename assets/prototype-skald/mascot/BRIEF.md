# Mimir mascot brief (prototype, issue #87)

Mimir is a study tutor. Every visual page it builds carries a small mascot in the
bottom-right corner: a vector, cartoony, friendly head of Mímir. In Norse myth Mímir is the
wise one whose head was cut off and kept alive by Odin; it gives counsel and guards a
well of wisdom. Use that myth as the only source.

## The chosen design (m4)

Round 1 asked for an original design. The maintainer then chose **m4**, a
deliberately simple fan-art Mímir. m4 is now the reference, and any change must keep
to it:
- **What he has:** gold horns on the crown, round gold eyes, a long grey beard split
  into five braids with a gold ring at each end, bushy grey brows and a big friendly
  nose.
- **How he is drawn:** flat fills only, one thick dark outline, and an off-white
  sticker edge round the whole silhouette, horns and rings included.
- **What he never gets:** hairline detail (wrinkles, strands, scars), rope or cord,
  blush on the cheeks, or rune tattoos.

He is still a head with no body, cute and not grim: no neck stump and no blood.

## Feel

Cartoony, warm and friendly: a kind grandad tutor who enjoys a good question. Not
cute-baby, not mean, not a sticker-shop cliché. He must read at 56 px wide on a phone, so
shapes must be big and simple; detail that only shows at 200 px is fine as long as the
56 px read holds.

## Moods (one per step state; the shell sets them)

The shell sets `data-mood` on the wrapper `div.mimir-mascot` (also `#mimir-mascot` on real
pages):
- `curious`: before the first step. A question mark floats above his head.
- `explaining`: talking, one brow up, mouth open mid-sentence.
- `thinking`: eyes up to one side, mouth to one side, maybe a beard stroke.
- `surprised`: the "aha": eyes wide, brows high, small round mouth.
- `pleased`: content smile, eyes squinted happily.
- `proud`: the last step. A big satisfied grin. The question mark becomes an "!" or a
  small check or spark above his head.

Each mood must be clearly different at 56 px. Only the face (brows, eyes, mouth) and the
mark above the head change; the head, beard and colours stay put.

## File contract

Write exactly one file: `mascot/<name>.svg` (the name you were given). Rules:
- Plain SVG, `viewBox` with room above the head for the mark; square-ish or a little taller
  than wide. No width/height attributes. No `id` attributes anywhere (several copies of
  the file are inlined into one page), so no gradients, filters, masks or clipPaths that
  need ids. No scripts, no external references, no fonts (draw the "?" and "!" as paths).
- One `<style>` element inside the SVG. Every selector in it must start with
  `.mimir-mascot` so it cannot leak into the page. Use classes prefixed `mm-`.
- Colours (revised after round 1): the character keeps ONE fixed palette on every page and
  theme, like any cartoon character: warm light skin (never orange or terracotta), a white
  to light-grey beard and brows, a dark warm-grey line, gold for the horns, eyes and rings
  (pink only inside an open mouth, never on the cheeks). Define these
  once as custom properties on `.mimir-mascot` inside your `<style>` (`--mm-skin`,
  `--mm-beard`, `--mm-line` and so on); hex values are fine there and nowhere else. Do not
  derive them from the page tokens, and add no theme-specific rules. Give the whole
  silhouette a thick off-white sticker edge (a wider stroke drawn behind it) so he stands
  out on a dark page and stays tidy on a light one. Only the marks above his head (the
  "?", the thinking dots, the "!") use the page's `--mm-accent`, with a thin
  `--mm-line` outline so a pale accent still reads on a light page. `--mm-ink`,
  `--mm-paper` and `--mm-soft` stay available but you need not use them.
- Moods: draw each mood's face parts in a `<g class="mm-face mm-<mood>">` and hide the
  ones not in use, e.g.
  `.mimir-mascot:not([data-mood="thinking"]) .mm-thinking { opacity: 0; }`.
  Do the same for the "?" (`curious`) and the "!" or check (`proud`).
- Motion, scoped by the page's `<html data-motion="none|gentle|full">`:
  - none (also the default when no attribute): instant swap;
  - `[data-motion="gentle"] .mimir-mascot …`: a short crossfade of face parts (about
    200 ms);
  - `[data-motion="full"] .mimir-mascot …`: the crossfade plus a little life, e.g. a
    small bob of the "?", a blink loop, a nod on change. Keep it calm.
  - Wrap every animation in `@media (prefers-reduced-motion: no-preference)`.

## How to check your work

A local HTTP server should already be serving `assets/` on port 8790. Check with
`curl -s -o /dev/null -w '%{http_code}' http://localhost:8790/prototype-skald/mascot/sheet.html`;
if it is not 200, start it in the background with
`python3 -m http.server 8790 -d /home/oguz/mimir/assets`.

- Every mood on four palettes at 200, 104 and 56 px:
  `http://localhost:8790/prototype-skald/mascot/sheet.html?m=<name>`
- On a real page: `http://localhost:8790/prototype-skald/candidate-b2n1/math.html?mascot=<name>&theme=dark&step=3`
  (also try `candidate-b3/` and `theme=light`, phone width 390 and desktop 1280).

Screenshot with headless Firefox, always under a timeout and with a fresh profile:
`timeout 40 firefox --headless --profile "$(mktemp -d -p <your scratch dir>)" --screenshot <out.png> --window-size=1280,2400 '<url>'`
then look at the PNG with the Read tool. Iterate until it reads well at 56 px in every
mood on both light and dark palettes.

Do not edit any file except your own `mascot/<name>.svg`. Put scratch files under the
scratchpad directory you are given, not in the repo.
