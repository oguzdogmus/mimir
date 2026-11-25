# Skald house style: Saga editorial (candidate B)

Read this in full before every visual. You write the body (HTML and inline SVG) and at
most one `<style>` block, never JavaScript: the shell reveals steps and switches the
highlight from your markup.

## The feel

A Mimir visual is a page from a well-set textbook or a long-form magazine feature. Warm
paper, brown-black ink, one strong accent ink (madder red) and a second, quieter one
(indigo). Big, light Fraunces headlines; calm Inter body text. In dark theme the page is
ink-dark and the text is lamplight. Be confident and spare: big type, generous margins,
few rules. Never use boxes, shadows, gradients or icons for decoration.

## Composing a page

`<main>` is a folio grid with three columns: **margin** (step numerals), **text** (the
reading column), **notes** (marginalia). Every direct child of `<main>` sits in the text
column unless you give it a class:

- `.masthead`: the opening. Inside: `p.kicker` (the provenance label, verbatim), `h1`
  (the title; for a question with no title, use `h1.question` style in page CSS and set
  the question itself as the headline), then `p.lede.dropcap` (the intro, with a madder
  drop cap). Never invent a title or an intro.
- `hr`: the section break (double hairline with a lozenge). One after the masthead.
- `.step[data-step="N"]`: one step. Children: `.num` (the numeral, set large in the
  margin), `.body` (the text), and optionally `.aside` (a side note) or `.verdict` (the
  answer line) in the notes column. The latest step's numeral turns madder.
- `.wide` on a child of `main` or `.step`: breaks out across text and notes columns.
- `.spread`: a figure beside a run of steps, for step-throughs of one diagram. Children:
  `figure` (left, sticks while the reader steps) and `.run` (right, holding `.step`s,
  each with `.num` and its text). Set `--sticky-fig` on the spread to the figure's
  height on phone (e.g. `style="--sticky-fig: 18rem"`) so revealed steps scroll clear.
- Run-in headings: start a step with `<span class="runin">Capsule.</span>` when the
  content begins with a name.

On phone (under 900 px) everything collapses to one column: numerals hang in a slim
gutter, notes and verdicts fall inline below the body, display maths and figures in a
step reclaim the gutter, and a spread's figure sticks to the top. Check 390 px: nothing
may overflow sideways.

Step reveals: put `data-step` on the step and on the figure parts it talks about (same
N). Reveal in the content's order. Text that is always shown has no `data-step`.

Tables: plain `<table>`, booktabs style comes free (heavy top and bottom rule, hairlines
between rows, no vertical rules). Wrap in `.table-wrap`. Use `th scope="row"` for row
heads. Use `\dfrac` for fractions in cells so they read at full size.

Captions: `figcaption` (small, madder rule on the left), inside the `figure`. Inline
symbols such as input strings: `span.sym`.

## Tokens

Use variables, never raw colours: `--paper`, `--paper-deep` (plates), `--ink`,
`--ink-soft`, `--ink-faint`, `--rule`, `--madder`, `--indigo`. Figures:
`--fig-ink` (the one neutral ink for notation), `--fig-soft` (axes, grids, leaders,
ghosts), `--fig-paper` (knock-outs), `--fig-curve` (default curve colour). Pigments and
washes for depictions and sketches: `--pig-ochre|sage|violet|sky` and
`--wash-ochre|sage|violet|sky`; conventional colours `--arterial`, `--venous`. Type:
`--font-display` (Fraunces), `--font-text` (Inter), `--font-tex` (KaTeX's fonts). Space:
`--sp-1` to `--sp-8`.

SVG classes: `.ink` (neutral stroke, no fill), `.ink-fill` (arrowheads), `.soft`,
`.curve`, `.leader`, `.label` (Fraunces label), `.small` (Inter small label), `.tex` and
`.tex-i` (KaTeX upright and italic, so a figure's symbols match the formulas in the
text: `q`, `x`, `π`, digits), `.halo`. Set the SVG's font sizes in viewBox units in page
CSS; aim for at least 11 px on a 390 px phone (raise them in a `max-width: 600px` query
if needed). Give every SVG `role="img"`, `<title>` and `<desc>`; crop the viewBox to
the drawing.

## The teaching highlight: the madder pen

The highlight is a pen mark in madder drawn around the target, as a teacher circles a
thing on a printout. It never recolours the target, so it is safe where colour is
notation.

- HTML: put `data-highlight="N"` on the target (a `span` around an inline formula, a
  table cell, a tape cell). The tokens draw two imperfect ellipses around it.
- SVG: draw the mark as its own element next to the target, with the highlight on the
  mark: `<path class="mark-loop" data-highlight="N" pathLength="1" d="...">` for a loop
  around a thing (state, point, label, the contour just outside a new layer), or
  `<path class="mark-swipe" ...>` for a broad translucent stroke under a line (an edge,
  part of a curve; put it before the line so it lies beneath). Draw loops slightly
  irregular: a bit more than one turn, a little wobble, a small tilt. Several marks may
  circle the same target at different steps.
- Use one mark per step, on what the step is about. Leave it out when it does not help.

## Motion

The shell sets `data-motion` on `<html>`; the tokens do the rest. You only mark what may
move.

- **none**: nothing moves. Every step still appears, in order.
- **gentle**: the newest step settles into place (a short fade and rise, like ink
  drying); SVG parts of the step and the pen mark fade in.
- **full**: as gentle, plus every stroke with `pathLength="1"` inside the newest step
  draws in like a pen; shapes with class `.wash` ink their fill in after the outline;
  the pen mark is drawn round its target, then swells once. Put `pathLength="1"` on
  outlines, curves, edges and leaders, not on text, dots or arrowheads. A stroke that
  needs its own dash pattern must not carry `pathLength="1"`.

## Print

Printing gives a clean handout with no extra work: every step shown, no controls or pen
marks, white paper, black ink, spreads side by side. Never carry meaning by the accent
colour alone.

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
given content. Labels are verbatim. Words you add are frame only (an axis name, "input").

### Field notes

- Anatomy: arterial red and venous blue (`--arterial`, `--venous`); the standard anterior
  view.
- Databases: one ERD notation per course, the course's own.
- Signals: plots label the time axis with its units.
- Automata: state names in maths italic (`.tex-i`), accepting states as double circles,
  the start arrow from nowhere.
- Microbiology: keep the cell's length-to-width ratio and the envelope order from the
  inside out; say "not to scale" when layers are thickened.
