# Skald house style: Risograph zine (candidate B2) (Slate, graphite and pink)

> **Palette variant.** Nordic pale slate paper and graphite ink (candidate A's neutrals, no ember). Graphite prints all content; the fluorescent pink stays the pen and the frame. Where this guide says blue or pink, read the token values in `tokens.css`.

Read this in full before every visual. You write the body (HTML and inline SVG) and at
most one `<style>` block, never JavaScript: the shell reveals steps and switches the
highlight from your markup.

## The feel

A Mimir visual is a page from a small-press zine, printed on a risograph in two spot
inks on uncoated grey stock. The storyteller made it by hand and explains with a pen.

- **Blue drum** (`--ink`) prints the content: all text, notation, curves, axes.
- **Pink drum** (`--pink`) is the pen and the frame: the teaching mark, step stickers,
  the provenance tab, halftone screens, the squiggle. Pink is never text.
- Overlaps overprint to violet (`--over`). The pink drum sits a little off register on
  decoration only; text and notation are always in register.

Loud in the frame, quiet in the reading. Dark theme: the same zine on black stock.

**Avoid** (reads as stock or AI-made): cream paper, serif display headlines,
terracotta accents, drop caps, ornamental rules, giant pale numerals, broadsheet
columns, black pages with one neon accent, purple gradients, emoji, centred
everything, rounded cards with shadows.

## Composing a page

`<main>` is the sheet: a left-aligned reading column (`--measure`) inside a wider page.

- `.masthead`: the opening. Inside: `p.tab` (the provenance label, verbatim; it
  becomes a crooked pink sticker), `h1` (the title, condensed and heavy; for a
  question with no title, set the question as `h1.question`, sized down in page CSS),
  then `p.lede` (the intro). Never invent a title or an intro.
- `hr`: the section break, a pink pen squiggle. One after the masthead.
- `.step[data-step="N"]`: a numbered block. Children: `.num` (the number, a blue
  sticker; the latest turns pink), the text (`.body` or `p`), optionally `.verdict`
  (the answer line, a pink slab) or `.aside`.
- Inside a step, figures, tables, display maths and `.wide` blocks may run wider than
  the reading column (to `--wide`).
- `.spread`: a figure beside a run of steps, for step-throughs of one diagram.
  Children: `figure` (sticks while the reader steps) and `.run` (the `.step`s). Set
  `--sticky-fig` to the figure's phone height (e.g. `18rem`) so steps scroll clear.
- Run-in heads: start a step with `<span class="runin">Capsule.</span>` when the
  content begins with a name.

Under 900 px everything is one column; a spread's figure sticks to the top. Check
390 px: nothing may overflow sideways.

Put `data-step` on the step and on the figure parts it talks about (same N), in the
content's order. Always-shown text has no `data-step`.

Tables: plain `<table>` in `.table-wrap`, `th scope="row"` for row heads, `\dfrac` in
cells.

Figures are printed plates: `figure.plate`. `figcaption` is set in the hand face.
Inline input symbols: `span.sym`. Frame words you add (an axis name, "input") may use
`.hand`.

## Tokens

Use variables, never raw colours. Frame: `--stock`, `--ink`, `--ink-soft`,
`--ink-faint`, `--rule`, `--pink`, `--over`, `--tint-ink`, `--tint-pink`, `--blend`
(multiply on light, screen on dark), `--mis-x`/`--mis-y` (the off-register offset).
Figures: `--fig-ink` (the one neutral ink for notation), `--fig-soft` (axes, grids,
leaders), `--fig-paper`, `--fig-plate`, `--fig-curve`. Depictions and sketches use the
two drums and their overprint at three densities: `--dep-a|b|ov`, `-mid`, `-tint`;
conventional colours `--arterial`, `--venous`. Screens: `--dots-pink`, `--dots-ink`
(backgrounds with a size, e.g. `0 0 / 6px 6px`). Type:
`--font-display` (Bricolage Grotesque, condensed via `font-stretch`), `--font-text`
(Instrument Sans), `--font-hand` (Shantell Sans), `--font-tex`. Space: `--sp-1` to
`--sp-8`.

SVG classes: `.ink` (neutral stroke, no fill), `.ink-fill` (arrowheads), `.soft`,
`.curve`, `.leader`, `.label` (hand-face label), `.small`, `.tex` and `.tex-i` (KaTeX
upright and italic, so a figure's symbols match the formulas in the text), `.halo`.
Set SVG font sizes in viewBox units, at least 11 px on a 390 px phone (raise them in a
`max-width: 600px` query). Every SVG gets `role="img"`, `<title>`, `<desc>` and a
viewBox cropped to the drawing.

## The teaching highlight: the pink pen

A pen mark in the pink drum drawn around the target, as a teacher marks up a printout.
It never recolours the target, so it is safe where colour is notation.

- HTML: put `data-highlight="N"` on the target (a `span` around an inline formula, a
  table cell, a tape cell). The tokens draw a hand loop around it.
- SVG: draw the mark as its own element next to the target, with the highlight on the
  mark: `<path class="mark-loop" data-highlight="N" pathLength="1" d="...">` for a loop
  around a thing (state, point, the contour just outside a new layer), or
  `<path class="mark-swipe" ...>` for a broad translucent stroke under a line (an edge,
  a flagellum, part of a curve; put it before the line so it lies beneath). Loops are
  slightly irregular: a bit more than one turn, a little wobble, a small tilt.
- Loops cross only shafts, never an arrowhead or a letter. Do not loop a label whose
  size changes on phone; swipe its target instead.
- One mark per step, on what the step is about; a target marked at several steps needs
  one mark element per step. Leave it out when it does not help.

## Motion

The shell sets `data-motion` on `<html>`; the tokens do the rest.

- **none**: nothing moves. Every step still appears, in order.
- **gentle**: the newest step fades up; its SVG parts and the pen mark fade in.
- **full**: as gentle, plus strokes with `pathLength="1"` in the newest step draw in
  like a pen, `.wash` fills ink in, the newest sticker slides into register, and the
  pen mark is drawn round its target. Put `pathLength="1"` on outlines, curves, edges
  and leaders, not on text, dots, arrowheads or strokes with their own dash pattern.

## Print

Printing gives a one-ink handout for free: white paper, black text and notation, every
step shown, no controls, pen marks or screens. Depictions keep their colours. Never
carry meaning by pink alone.

## Notation: what the house style may not touch

**The meaning test.** Would someone who knows this field read a different meaning if
this property changed? Then it is notation and the house style does not touch it. When
unsure, it is notation. Notation comes from the course source first (the professor's
slides, the fingerprint's notation section), then the field's standard textbook
convention.

Name the figure's kind before you draw. When unsure, the stricter kind applies. The
frame (page, title, captions, step controls) is always full house style.

1. **Depiction of a real thing** (heart, bacterium, cell). Fixed: shape, proportions,
   positions, conventional colours. You may style: label typeface, leader lines, layer
   colours from the two drums, reveal motion. Exaggeration (such as layer thickness)
   is said in a caption.
2. **Formal notation** (ERD, UML, DFA, Mealy/Moore, circuits, flowcharts). Fixed: every
   symbol, shape, arrow and label form. You may style: typeface, one neutral ink
   (`--fig-ink`), line weight, reveal motion. No fills, halftones, misregistration or
   decoration the notation lacks.
3. **Plot of data or a function.** Fixed: exact curve geometry, axes, scale, units. You
   may style: axis and grid style, typeface, curve colour, reveal motion. No halftone
   under a curve (it reads as an area).
4. **Mimir's own sketch** (analogy, concept map). Nothing fixed; everything styleable,
   including screens and overprints.

**Plots are computed.** Compute the points with code from the formula or the data and
draw the path from them (60 or more samples per period), never by eye. Ticks and labels
sit at the exact values.

**Labels.** Labels never cross a stroke and never leave the viewBox. Put edge labels
beside the edge, self-loop labels beyond the apex, tick labels on the side the curve
leaves free.

**Content.** You never add, solve, simplify, reorder or correct content; you compose the
given content. Labels are verbatim. Words you add are frame only (an axis name, "input").

### Field notes

- Anatomy: arterial red and venous blue (`--arterial`, `--venous`); the standard
  anterior view.
- Databases: one ERD notation per course, the course's own.
- Signals: plots label the time axis with its units.
- Automata: state names in maths italic (`.tex-i`), accepting states as double circles,
  the start arrow from nowhere.
- Microbiology: keep the cell's length-to-width ratio and the envelope order from the
  inside out; say "not to scale" when layers are thickened.
