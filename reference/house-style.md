# Skald: Mimir's house style

Read this in full before every visual, together with the course's field pack or packs and
its notation section. This guide is the look and the markup the shell accepts; the packs hold
the field's conventions, and the course's own notation wins over both.
You write either the body of a `page` (HTML that may hold inline SVG) or one standalone
`svg`, never JavaScript. Mimir's visual script (the shell) does the rest from your
markup.

## What the shell does, and what it refuses

The shell puts your body inside `<main>` and adds: the Skald tokens (fonts, colours,
light and dark themes, type, spacing, motion, print), the chalk and marker filters
(`#sk-chalk`, `#sk-marker`, first in `<main>`), KaTeX when the text holds `\(...\)` or
`\[...\]`, the step controls, the step reveal, the highlight switching and, for a
machine, the simulator. Into a standalone SVG it adds the tokens as the root's last
`<style>`. You write none of these, and no `<main>`, `<html>`, `<head>` or `<title>`.

It refuses, so never write:

- Script of any kind: `<script>`, `on*` attributes, `javascript:`.
- Forms, buttons, inputs, `<img>`, `<iframe>`, `<object>`, `<embed>`, `<link>`,
  `<meta>`, `<foreignObject>`; in SVG anything outside svg, g, defs, symbol, use,
  title, desc, style, path, rect, circle, ellipse, line, polyline, polygon, text,
  tspan, marker, linearGradient, radialGradient, stop, clipPath, mask (so no
  `<pattern>`, no `<filter>` or `fe*` elements).
- Links or resources outside the page: `href` only as `#id`, `url()` only as
  `url(#id)`, no `@import`, no other CSS function that loads something
  (`image()`, `image-set()`, `cross-fade()`, `element()`, `src()`, `paint()`).
- A backslash anywhere in CSS or an SVG attribute: write a character such as `…`
  itself, never `content: "\2026"`.
- `<` or `&` inside `<style>`, not even in a CSS comment. Never paste markup into a
  comment.
- An id that repeats or starts with `mimir-` or `sk-`; an element left open or
  closed out of order.
- An inline `<svg>` whose first two children are not a non-empty `<title>` then
  `<desc>` (unless it is decorative and has `aria-hidden="true"`).
- A label that crosses a stroke or leaves the viewBox.

The error names what it refused. Fix your markup, never the content, and build again.

## The feel

A Mimir visual is a well-planned lecture board. In dark theme it is a deep blue-grey
board with chalk-white writing and two coloured chalks (yellow for the teacher's mark,
sky blue for answers and curves). In light theme it is a cool pale whiteboard with
teal-black marker, a blue marker for the mark and a green one for answers and curves.
Titles in a plain, slightly condensed grotesk; reading text in a highly legible sans;
small frame words (tag, step numbers, figure labels, captions) handwritten. Leave a
lot of empty board. Stay calm: long study happens here.

Avoid the stock looks: no cream or parchment paper, serif display headlines, terracotta
or rust accents, drop caps, ornamental dividers, giant margin numerals, black page with
one neon colour, purple-blue gradients, emoji, centred everything, rounded cards with
shadows.

## Composing a page

The body is yours: give it the shape its content needs. Write at most one `<style>`
block, first in the body. For a worked answer, a diagram explained step by step or a
structure built up layer by layer, compose in this order:

- `header.head`: `p.tag` (the provenance label, verbatim), `h1` (the title), `p.intro`
  (the intro). A question with no title becomes the heading itself: `h1.question`.
  Never invent a title or an intro.
- `.board`: the figure and the work side by side, with a seam between the two panels.
  Children: `figure` (the centrepiece, left, stays in view while the reader steps) and
  `.work` (right, the numbered board work). When the work comes before the figure (a
  worked answer whose sketch is the last step), use `.board.work-first`: the work sits
  left and the figure right. On a `.board` that is not `.work-first`, set
  `--sticky-fig` to the pinned figure's height on phone, padding included (e.g.
  `style="--sticky-fig: 15rem"`; estimate it as the SVG's height at 350 px wide plus
  2rem). A `.work-first` board pins nothing, so leave it unset there.
- `.step[data-step="N"]` inside `.work`, N counting from 1: `div.n` (the number,
  handwritten, the latest one in the mark colour), then the text (`p`, or `.body`
  holding several blocks). Start with `<span class="runin">Capsule.</span>` when the
  content begins with a name or a name and a colon (`Amplitude:`); keep the content's
  own punctuation.
- `p.answer`: the answer line, boxed by hand in the second colour, inside the step
  that states it. Only when the content has an answer line; otherwise leave it out.

Put `data-step` on the step and on the figure parts it talks about (same N, an SVG
`<g>` is fine), in the content's order. Always-shown text has no `data-step`.

A page with no centrepiece (a review sheet, a cheat sheet, a drill page) drops the
`.board`: after the header, `section`s with `h2` headings, text in `p`, lists and
tables, in the content's order.

On phone (under 900 px) the board becomes one column: the figure pins to the top
(caption hidden there; repeat it as `p.caption.caption-phone aria-hidden="true"` at the
end of `.work`), the work scrolls under it. In `.work-first` the figure simply follows
the work. Check 390 px: nothing may overflow sideways.

**The bottom-right corner belongs to the shell** (the step controls and, on a page
with steps, the mascot, whose mood follows the steps). The tokens reserve it. Never put content, or anything positioned or fixed, in that
corner, and never override `main`'s right padding. Your `<style>` must not name the
shell's own ids and classes (`mimir-...`, `sk-...`, e.g. `#mimir-controls`): the shell
refuses it. `url(#sk-chalk)` and `url(#sk-marker)` are fine.

**Originals.** The original of a scanned question goes right beside its transcription,
before or after it, as `<mimir-original path="<registry path>" page="N"></mimir-original>`
(outside any SVG). The shell puts in the image or the link.

**Math.** In text, `\(...\)` inline and `\[...\]` display, in the content's own LaTeX.
KaTeX does not reach inside SVG: there, write symbols as Unicode text in `.tex` or
`.tex-i` (below).

A row of cells (a sequence the figure reads or indexes cell by cell, when the field
pack draws one): put it inside the `figure`, under the SVG, so it pins with it:
`<div class="tape-row"><span class="frame-word">input</span><ol class="tape"
role="group" aria-label="Name of the row"><li data-highlight="2">1</li>…</ol></div>`.
The `…` after the last cell is drawn for you. Mark the cell being read with
`data-highlight` on it.

Tables: plain `<table>` in `.table-wrap`; you get a teacher's value table (one line
under the first row, one after the row heads, no box). `th scope="row"` for row heads,
`\(\dfrac{a}{b}\)` in cells. Inline symbols such as input strings: `span.sym`. Small
frame words outside SVG (such as "input"): `span.frame-word`.

A skeleton (replace every word with the given content):

```html
<style>
#fig text.label { font-size: 16px; }
@media (max-width: 600px) { #fig text.label { font-size: 26px; } }
</style>
<header class="head">
  <p class="tag">[practice, not from a real paper]</p>
  <h1>Title as given</h1>
  <p class="intro">Intro as given, with \(x^2\) inline.</p>
</header>
<div class="board" style="--sticky-fig: 13rem">
  <figure>
    <svg id="fig" viewBox="0 0 400 210" role="img">
      <title>What the figure is</title>
      <desc>Every part and label of the figure, in words.</desc>
      <rect class="ghost" x="40" y="60" width="320" height="120" rx="60"/>
      <g data-step="1">
        <rect class="ink" x="40" y="60" width="320" height="120" rx="60" pathLength="1"/>
        <text class="label" x="200" y="36" text-anchor="middle">First part</text>
      </g>
    </svg>
    <figcaption>Caption as given.</figcaption>
  </figure>
  <div class="work">
    <div class="step" data-step="1">
      <div class="n">1</div>
      <p><span class="runin">First part.</span> Step text as given.</p>
      <p class="answer">Answer line as given.</p>
    </div>
    <p class="caption caption-phone" aria-hidden="true">Caption as given.</p>
  </div>
</div>
```

## Tokens

Use variables, never raw colours: `--board`, `--board-deep`, `--ink`, `--ink-soft`,
`--ink-faint`, `--rule`, `--mark` (the pen), `--mark-wash`, `--second` (answers,
curves). Figures: `--fig-ink` (the one neutral ink for notation), `--fig-soft` (axes,
grids, leaders, ghosts), `--fig-paper` (knock-outs), `--fig-curve`. Pigments and
washes for depictions: `--pig-ochre`, `--pig-moss`, `--pig-violet`, `--pig-sky`,
`--wash-ochre`, `--wash-moss`, `--wash-violet`, `--wash-sky`; conventional colours
`--arterial`, `--venous`. Type: `--font-title` (Familjen Grotesk), `--font-text`
(Atkinson Hyperlegible Next), `--font-hand` (Kalam), `--font-tex`. Space: `--sp-1` to
`--sp-8`.

Contrast: `--ink-faint` is the faintest text colour (step numbers, a cell row's "…"); it
holds about 3.7:1 on the board in both themes. Never use `--rule` or `--fig-soft` for
text you need read.

SVG classes: `.ink`, `.ink-fill` (arrowheads), `.soft`, `.curve`, `.leader`, `.label`
(handwritten label), `.small` (secondary readable text, `--ink-soft`), `.tex` and
`.tex-i` (KaTeX upright and italic, so a figure's symbols match the text), `.halo`,
`.anchor` (a leader's end dot), `.ghost` (a dashed outline in `--fig-soft`), `.wash`
(a fill that inks in after its outline under full motion). Every SVG gets `role="img"`,
`<title>`, `<desc>` (every part, state, edge and label in words, so it is complete
without the picture) and a viewBox cropped to the drawing. Subscripts in SVG text:
`q<tspan dy=".3em" font-size=".7em">0</tspan>` (then `dy="-.3em"` on what follows);
Firefox ignores `baseline-shift`. A fraction such as π/4 in a tick label is written
inline with a slash (`<tspan class="tex-i">π</tspan>/4`), not stacked.

**SVG text size.** Set SVG font sizes in your `<style>` (for a standalone SVG, in its
own `<style>`), in viewBox units, from the size you want on screen:

```
viewBox units = target px × viewBox width ÷ rendered width (px)
```

The tokens cap every figure's SVG at 36rem (576 px), so there are exactly two sizes:
the default for 560 px wide (desktop and tablet), and a `@media (max-width: 600px)`
rule for the phone, where the figure is about 350 px wide. Handwritten labels follow
the same two sizes. Targets: labels and state names 14-16 px; tick and edge labels
12-14 px; small notes 11-12 px, never less than 11 px. Example: a 600-unit-wide plot
needs 13 × 600 ÷ 560 ≈ 14 units for its tick labels by default and 13 × 600 ÷ 350 ≈
22 units on the phone. Lay labels out for the phone size (the larger one in viewBox
units), so nothing collides when they grow, and size label loops for it too.

A standalone SVG has the same classes and tokens:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120" role="img">
  <title>What the diagram is</title>
  <desc>Every part, edge and label of the diagram, in words.</desc>
  <style>
    text.label { font-size: 16px; }
    @media (max-width: 600px) { text.label { font-size: 22px; } }
  </style>
  <circle class="ink" cx="120" cy="70" r="24"/>
  <text class="label" x="120" y="28" text-anchor="middle">Part</text>
</svg>
```

## The teaching highlight: the chalk loop

The highlight is a chalk (dark) or marker (light) stroke drawn round the target, with a
dry, slightly rough edge. It never recolours the target, so it is safe where colour is
notation. The rough edge is only ever on marks, never on notation or text. The shell
shows a mark when its step is the newest one.

- HTML: `data-highlight="N"` on the target (a `span` round an inline formula, a table
  cell, a cell of a row). The tokens draw two rough loops round it. A
  `span[data-highlight]` gets `margin: 0 .2em` whether or not the loop is shown, so
  write the punctuation right after the `</span>` with no space (`</span>, `), and
  the text never jumps when the loop comes and goes. For a boxed cell (a cell of a row),
  pull the loop's insets in to about `.3em` so it does not cut the next cell.
- SVG: the mark is its own element next to the target, highlight on the mark:
  `<path class="mark-loop" data-highlight="N" pathLength="1" d="...">` round a thing (a
  state, a point, a label), or `class="mark-swipe"` for a broad smear under a line (an
  edge, part of a curve; put it before the line). In a depiction, loop the new part's
  label, not its outline, so the mark is never read as another layer.
- **What to mark.** The content says what each step highlights; mark exactly that,
  nothing more. `data-highlight` takes one step number. A state with its edge: loop
  the state and swipe the edge, both with the same `data-highlight="N"`. A step that
  names no target: mark its newest part, once. In a depiction, a step with two parts
  (such as "Flagella and pili") gets one loop, round the first one named. Repeat the
  mark element for another step.

**Drawing a loop.** Compute the path with code; never draw it by eye. The loop is a
tilted ellipse, drawn as a little more than one turn, with a small wobble. It drifts
outward slightly, so the overshoot runs beside the start and does not lie on top of it:

```
for u from 0 to 1 in about 60 steps:
  t = t0 + 400° · u                        # 1.1 turns
  s = (1 + 0.07·u) · (1 + 0.025·sin(3t + φ))   # 7 % drift outward, 2.5 % wobble
  (x, y) = (1.7·r·cos t · s, 1.4·r·sin t · s)
  point = centre + rotate((x, y), tilt)     # tilt ±12°
```

Then join the points with a smooth curve (Catmull-Rom to cubic Béziers). Write it as
a `<path d="…">` with `pathLength="1"`.

- *Size round a state or point.* `r` is the outer ring's radius (13 units for a
  point). Use half-axes of 1.7r × 1.35-1.5r, which leaves 10-15 viewBox units clear of
  a state's outer ring at the top and about 20 at the sides. That way the loop never
  reads as another circle round a state. A loop round a point on a curve may cross the
  curve.
- *Size round a label (wide text).* Half-axes: half the label's width + 0.5 × its font
  size, by 0.62 × font size + 9 units, with the label's centre as centre; tilt only
  ±3°, so the ends do not sweep through the text. Estimate text width as 0.5 × font
  size per character for the handwritten face.
- *Where it starts.* Set `t0` (the start angle) so that the start and the overshoot,
  `t0` to `t0 + 40°`, fall in a free sector, away from every arrow, arrowhead and
  label. `t0` is the ellipse parameter before tilting. Below a state is usually free
  (`t0` about 70°, in SVG coordinates where +y points down). Round q0 the start arrow
  comes in from the left, so start below. Round a label with a leader, start on the
  side away from the leader, and start the leader just outside the loop.
- *Tilt.* Pick the sign of the tilt that keeps the loop at least 6 units from every
  arrowhead. Measure that, do not judge it by eye. Raise the 1.35 to 1.5 if the loop
  runs into an arrowhead above or below.
- *Each step.* Vary `φ` (the wobble phase) a little, so that repeated marks on the
  same state are not identical.

## Motion

The student's motion level is set on the page by the shell; you write the same markup
for every level.

- **none**: nothing moves. Every step still appears, in order.
- **gentle**: the newest step fades up; its figure parts and the mark fade in.
- **full**: the newest step is written in from left to right; every stroke with
  `pathLength="1"` in it is drawn; `.wash` fills ink in after their outline; the mark
  is drawn round its target. Put `pathLength="1"` on outlines, curves, edges, leaders,
  never on text, dots, arrowheads, or a stroke with its own dash pattern.
  A stroke is drawn whether `data-step` sits on its SVG group or on the whole
  `figure`. If a dashed stroke needs `pathLength="1"` (for dashes in path fractions),
  give it its own full-motion rule in your style that keeps its dash pattern and
  fades it in instead.

**Step 0 of a figure built part by part.** When every part has a step, show the
whole outline at step 0 as a `.ghost` (always shown, no `data-step`), so the pinned
figure is not empty. It is frame: the ghost has no label.

## A machine page

When the content gives a machine (a DFA, NFA, PDA or labelled tree the student feeds an
input into), draw its diagram inline in the page body and give the element that draws
each state `id="state-<i>"`, numbering the states from 1 in the order the machine lists
them: a `<g>` round the state's circles and name, or its outer circle. The shell adds
the simulator after your body: the input field, the buttons, the history of steps and
the machine as a table. Write none of these. While the simulator runs, the shell marks
the current states in your diagram; draw no marks for it.

## Print

Printing gives a handout for free: white page, black ink, no board, every step shown,
no controls or marks. Never carry meaning by the mark colour alone.

## Notation: the meaning test

Would someone who knows this field read a different meaning if this
property changed? Then it is notation and the house style does not touch it. When
unsure, it is notation. Notation comes from the course's own materials first (the
fingerprint's notation section, the professor's slides and diagrams), then the course's
field pack, then this core guide.

### The four figure kinds

Name each figure's kind before you draw; when unsure, the stricter kind applies (the
one that fixes more). The frame (page, title, captions, controls) is always full house
style.

1. **Depiction of a real thing** (heart, bacterium, cell). Fixed: shape, proportions,
   positions, conventional colours. You may style: label typeface, leader lines,
   reveal motion. Exaggeration (such as layer thickness) is said in a caption.
2. **Formal notation** (ERD, UML, DFA, Mealy and Moore machines, circuits,
   flowcharts). Fixed: every symbol, shape, arrow and label form. You may style:
   typeface, one neutral ink (`--fig-ink`), line weight, reveal motion. No fills, no
   rounded corners, no rough edges, no decoration the notation lacks.
3. **Plot of data or a function.** Fixed: exact curve geometry, axes, scale, units.
   You may style: axis and grid style, typeface, curve colour, reveal motion.
4. **Mimir's own sketch** (analogy, concept map). Nothing fixed; chalk edges allowed.

### Plots are computed

Compute a plot's points from the formula or data with code (60 or more samples per
period), never by eye, and draw the path from those points. Ticks and labels sit at
the exact values. Label every curve with its function or series as the content names it
(e.g. `f(x) = 3 sin(2x)`), beside the curve or in a free corner of the plot, with
variables in `.tex-i` and function names and numbers in `.tex`.

**Labels** never cross a stroke and never leave the viewBox: edge labels beside the
edge, self-loop labels beyond the apex, tick labels on the side the curve leaves free.
The shell measures this and refuses a label that breaks it, naming the label.

**Content.** Never add, solve, simplify, reorder or correct content; compose it.
Labels are verbatim. Words you add are frame only (an axis name, "input").

### Cross-field recipes

Field conventions come from the course's field pack, not from this guide. Only recipes
that several fields share live here.

Graph geometry, for the state diagrams of computer science, electrical engineering and
linguistics. Keep highlight loops round states wide and tilted so they never read as a
second circle. Geometry, in viewBox units, for states of radius r on one row:

- *Arrowhead:* a filled triangle (`.ink-fill`), 11 long and 8 wide, its tip on the
  target ring, pointing along the edge's end tangent; the edge path stops at the
  arrowhead's base.
- *Edges between neighbours:* two arcs, the forward one above and the back one
  below, each a quadratic curve leaving and entering the rings at ±25° from the
  centre line, with its control point 0.45 × the centre distance above (or below)
  the midpoint. Labels sit 12 units beyond the arc's apex.
- *Self-loop:* on top of the state. It leaves the ring at −115° and returns at −65°
  (angles from the +x axis, +y down), as a cubic curve with both control points
  2.6r above the centre and 0.9r either side of it. The arrowhead ends at −65°.
  The label sits 12 units above the apex. Draw all loops the same way, so they are
  symmetric.
