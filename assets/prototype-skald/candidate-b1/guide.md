# Skald house style: Tutor's notebook (candidate B1)

Read this in full before every visual. You write the body (HTML and inline SVG) and at
most one `<style>` block, never JavaScript: the shell reveals steps and switches the
highlight from your markup.

## The feel

A Mimir visual is a dot-grid pad a tutor has written on with you: bright white paper,
blue-black ink for text and drawings, and the tutor's marks on top: a red pen that
circles and points, a yellow highlighter that swipes. At night: a slate page, pale ink,
the highlighter glowing. Text is Andika (a plain school face); the hand (Kalam) writes
only frame words, labels, step numbers and figure tags. Tidy first, hand-made second.

Avoid the stock looks: no cream or parchment paper, no big serif headline, no drop cap,
no terracotta accent, no hairline-and-lozenge rules, no giant pale numerals, no black
page with one neon pop, no gradients, emoji, shadows on cards, or centred layouts.

## Composing a page

`<main>` is the pad. Everything is left-aligned and reads down the page.

- `header.top`: `p.label` (provenance label, verbatim), `h1` (the title, or
  `h1.question` for a question), `p.intro`. A question may get
  `<span class="tag" aria-hidden="true">Q.</span>` before the `h1`, in the margin.
  Never invent a title or an intro.
- `div.steps` holds `section.step[data-step="N"]`: one note each, with `span.num` (circled
  by hand; red while newest) and `div.body` or one `p`. `.wide` spans the number margin.
- `p.answer`: the final answer line, boxed by hand. Put it in the last step.
- `div.spread`: notes on the left, the figure beside them on desktop, sticking while
  the reader steps. Children: `figure`, then `div.run` holding the `.step`s. On phone
  the figure sticks to the top; set `--sticky-fig` to its height there
  (`style="--sticky-fig: 18rem"`) so new steps scroll clear.
- Run-in names: start a step with `<span class="runin">Capsule.</span>` when the content
  begins with a name.

Figures are **drawn** into the pad (plain `figure`: plots, notation, sketches) or
**taped** in (`figure.taped`: a printout with two strips of tape, for depictions of real
things). Captions: `figcaption`, optionally led by `<span class="fig-tag">fig. 1</span>`.

Tables: plain `<table>` in `.table-wrap`, ruled like a hand-drawn value table; `th
scope="row"` for row heads, `\dfrac` in cells. Inline input symbols: `span.sym` (boxed).

Display maths is written from the left, as in notes. Under 900 px display maths, tables
and figures in a step use the number margin. Check 390 px: nothing overflows sideways.

Step reveals: put `data-step` on the step and on the figure parts it talks about (same
N). Reveal in the content's order. Text that is always shown has no `data-step`.

## Tokens

Use variables, never raw colours: `--paper`, `--sheet`, `--ink`, `--ink-soft`,
`--pencil` (frame words), `--rule`, `--pen` (red pen), `--hi`, `--hi-edge` (highlighter). Figures: `--fig-ink` (the one neutral ink for
notation), `--fig-soft` (axes, grids, leaders, ghosts), `--fig-paper` (knock-outs; it
follows the sheet inside `.taped`), `--fig-curve` (a second pen, royal blue, for plot
curves). Coloured pencils for depictions and sketches: `--pig-ochre|sage|violet|sky`
and `--wash-ochre|sage|violet|sky`; conventional colours `--arterial`, `--venous`. Type:
`--font-text` (Andika), `--font-hand` (Kalam), `--font-tex` (KaTeX). Space: `--sp-1` to
`--sp-8`. Red and yellow belong to the teaching marks: never use them for content.

SVG classes: `.ink` (neutral stroke, no fill), `.ink-fill` (arrowheads), `.soft`,
`.curve`, `.leader`, `.label` (handwritten label), `.small` (small text label), `.tex`
and `.tex-i` (KaTeX upright and italic, so a figure's symbols match the formulas:
`q`, `x`, `π`, digits), `.halo`, `.knock`. The hand labels names of parts (Capsule,
input); symbols, digits and state names stay in `.tex`/`.tex-i`, since a hand blurs `1`
and `l`. Set SVG font sizes in viewBox units, at least 11 px
on a 390 px phone (raise them under `max-width: 600px`). Every SVG gets `role="img"`,
`<title>`, `<desc>` and a viewBox cropped to the drawing.

## The teaching highlight: highlighter and red pen

The highlight is the tutor's mark on the page. It never recolours the target, so it is
safe where colour is notation, and it sits around notation, never on it.

- HTML: put `data-highlight="N"` on the target (a `span` around an inline formula, a
  table cell, a tape cell). The tokens swipe the highlighter behind it. Add class
  `loop` to the target for a red pen loop instead (for a whole line or block).
- SVG: draw the mark as its own element, with the highlight on the mark:
  `<path class="mark-loop" data-highlight="N" pathLength="1" d="...">` for a red loop
  around a thing (a state, a point, a label, the contour just outside a new layer);
  `<path class="mark-swipe" ...>` for a highlighter stroke under a line (an edge, part
  of a curve; put it before the line so it lies beneath); `<g class="mark-arrow" ...>`
  holding a shaft and an open head, each with `pathLength="1"`, for a red arrow pointing
  at a thing. Draw loops a bit more than one turn, slightly wobbly and tilted.
- `data-highlight` takes one step number: a target marked at several steps needs one
  mark per step. One mark per step, on what the step is about; none if it does not help.

## Motion

The shell sets `data-motion` on `<html>`; the tokens do the rest. You only mark what may
move.

- **none**: nothing moves. Every step still appears, in order.
- **gentle**: the newest note and the marks fade in softly.
- **full**: the newest note is written across from the left; strokes with
  `pathLength="1"` in it draw like a pen; `.wash` shapes ink their fill after the
  outline; the highlighter swipes, the red pen draws its loop, the number is circled. Put `pathLength="1"` on outlines, curves, edges and leaders, not on
  text, dots or arrowheads. A stroke with its own dash pattern must not carry it.

## Print

Printing gives a clean handout for free: white paper, black ink, no grid, every step,
no controls or marks, figures above the notes. Never carry meaning by red or yellow alone.

## Notation: what the house style may not touch

**The meaning test.** Would someone who knows this field read a different meaning if this
property changed? Then it is notation and the house style does not touch it. When unsure,
it is notation. Notation comes from the course source first (the professor's slides, the
fingerprint's notation section), then the field's standard textbook convention.

Name the figure's kind before you draw. When unsure, the stricter kind applies. The
frame (page, title, captions, step controls) is always full house style.

1. **Depiction of a real thing** (heart, bacterium, cell). Fixed: shape, proportions,
   positions, conventional colours. You may style: label typeface, leader lines, reveal
   motion. Exaggeration (such as layer thickness) is said in a caption.
2. **Formal notation** (ERD, UML, DFA, Mealy/Moore, circuits, flowcharts). Fixed: every
   symbol, shape, arrow and label form. You may style: typeface, one neutral ink colour
   (`--fig-ink`), line weight, reveal motion. No fills, rounded corners or decoration
   the notation lacks.
3. **Plot of data or a function.** Fixed: exact curve geometry, axes, scale, units. You
   may style: axis and grid style, typeface, curve colour, reveal motion.
4. **Mimir's own sketch** (analogy, concept map). Nothing fixed; everything styleable.

**Plots are computed.** Compute the points with code from the formula or the data and
draw the path from them (60 or more samples per period), never by eye. Ticks and labels
sit at the exact values.

**Labels.** Labels never cross a stroke and never leave the viewBox. Put edge labels
beside the edge, self-loop labels beyond the apex, tick labels on the side the curve
leaves free.

**Content.** You never add, solve, simplify, reorder or correct content; you compose the
given content. Labels are verbatim. Words you add are frame only ("input", "Q.",
"fig. 1", an axis name); the hand never writes new explanations.

### Field notes

- Anatomy: arterial red and venous blue (`--arterial`, `--venous`); the standard anterior
  view.
- Databases: one ERD notation per course, the course's own.
- Signals: plots label the time axis with its units.
- Automata: state names in maths italic (`.tex-i`), accepting states as double circles,
  the start arrow from nowhere.
- Microbiology: keep the cell's length-to-width ratio and the envelope order from the
  inside out; say "not to scale" when layers are thickened.
