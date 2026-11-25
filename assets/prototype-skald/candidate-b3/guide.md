# Skald house style: Chalk and slate (candidate B3)

Read this in full before every visual. You write the body (HTML and inline SVG) and at
most one `<style>` block, never JavaScript: the shell reveals steps and switches the
highlight from your markup.

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

Every page carries this block once, first inside `<main>` (the chalk and marker
edges; copy it as is):

```html
<svg class="sk-defs" aria-hidden="true" focusable="false">
  <filter id="sk-chalk" filterUnits="userSpaceOnUse" x="-300" y="-300" width="1600" height="1400" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency=".45" numOctaves="2" seed="4" result="warp"/>
    <feDisplacementMap in="SourceGraphic" in2="warp" scale="3.2" xChannelSelector="R" yChannelSelector="G" result="rough"/>
    <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="2" seed="9" result="grain"/>
    <feColorMatrix in="grain" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.1 1.8" result="dust"/>
    <feComposite in="rough" in2="dust" operator="in"/>
  </filter>
  <filter id="sk-marker" filterUnits="userSpaceOnUse" x="-300" y="-300" width="1600" height="1400" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency=".3" numOctaves="1" seed="4" result="warp"/>
    <feDisplacementMap in="SourceGraphic" in2="warp" scale="1.8" xChannelSelector="R" yChannelSelector="G"/>
  </filter>
</svg>
```

Then, in order:

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
- `.step[data-step="N"]` inside `.work`: `div.n` (the number, handwritten, the latest
  one in the mark colour), then the text (`p`, or `.body` holding several blocks).
  Start with `<span class="runin">Capsule.</span>` when the content begins with a name
  or a name and a colon (`Amplitude:`); keep the content's own punctuation.
- `p.answer`: the answer line, boxed by hand in the second colour, inside the step
  that states it. Only when the content has an answer line; otherwise leave it out.
- The `<title>` element is the title, or for a question a short name of what it asks
  (it is frame, not content).

On phone (under 900 px) the board becomes one column: the figure pins to the top
(caption hidden there; repeat it as `p.caption.caption-phone aria-hidden="true"` at the
end of `.work`), the work scrolls under it. In `.work-first` the figure simply follows
the work. Check 390 px: nothing may overflow sideways.

**The mascot's corner is reserved.** The shell fixes a mascot to the bottom right.
From 1200 px up he is 104 px wide and stands above the ledge at the right edge of the
page column. `main` gets a right lane (`--mascot-lane`, his width plus `--sp-4`) that
no content enters, at any scroll position. Below 1200 px he is 56 px wide and sits on
the ledge, right of Next, and `#mimir-controls` gets right padding for him. The tokens
do all of this. Never put content, or anything positioned or fixed, in that corner,
and never override `main`'s right padding or the controls' padding.

Put `data-step` on the step and on the figure parts it talks about (same N), in the
content's order. Always-shown text has no `data-step`.

Input tapes (automata): put the tape inside the `figure`, under the SVG, so it pins
with it: `<div class="tape-row"><span class="frame-word">input</span><ol class="tape"
role="group" aria-label="Input tape"><li data-highlight="2">1</li>…</ol></div>`. The
`…` is drawn for you. Mark the symbol being read with `data-highlight` on its cell.

Tables: plain `<table>` in `.table-wrap`; you get a teacher's value table (one line
under the first row, one after the row heads, no box). `th scope="row"` for row heads,
`\dfrac` in cells. Inline symbols such as input strings: `span.sym`. Small frame words
outside SVG (such as "input"): `span.frame-word`.

## Tokens

Use variables, never raw colours: `--board`, `--board-deep`, `--ink`, `--ink-soft`,
`--ink-faint`, `--rule`, `--mark` (the pen), `--mark-wash`, `--second` (answers,
curves). Figures: `--fig-ink` (the one neutral ink for notation), `--fig-soft` (axes,
grids, leaders, ghosts), `--fig-paper` (knock-outs), `--fig-curve`. Pigments and
washes for depictions: `--pig-ochre|moss|violet|sky`, `--wash-ochre|moss|violet|sky`;
conventional colours `--arterial`, `--venous`. Type: `--font-title` (Familjen
Grotesk), `--font-text` (Atkinson Hyperlegible Next), `--font-hand` (Kalam),
`--font-tex`. Space: `--sp-1` to `--sp-8`.

Contrast: `--ink-faint` is the faintest text colour (step numbers, the tape's "…"); it
holds about 3.7:1 on the board in both themes. Never use `--rule` or `--fig-soft` for
text you need read.

SVG classes: `.ink`, `.ink-fill` (arrowheads), `.soft`, `.curve`, `.leader`, `.label`
(handwritten label), `.small` (secondary readable text, `--ink-soft`), `.tex` and
`.tex-i` (KaTeX upright and italic, so a figure's symbols match the text), `.halo`,
`.anchor` (a leader's end dot), `.ghost` (a dashed outline in `--fig-soft`), `.wash`
(a fill that inks in after its outline under full motion). Every SVG gets `role="img"`,
`<title>`, `<desc>` and a viewBox cropped to the drawing. Subscripts in SVG text:
`q<tspan dy=".3em" font-size=".7em">0</tspan>` (then `dy="-.3em"` on what follows);
Firefox ignores `baseline-shift`. A fraction such as π/4 in a tick label is written
inline with a slash (`<tspan class="tex-i">π</tspan>/4`), not stacked.

**SVG text size.** Set SVG font sizes in page CSS, in viewBox units, from the size you
want on screen:

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

## The teaching highlight: the chalk loop

The highlight is a chalk (dark) or marker (light) stroke drawn round the target, with a
dry, slightly rough edge. It never recolours the target, so it is safe where colour is
notation. The rough edge is only ever on marks, never on notation or text.

- HTML: `data-highlight="N"` on the target (a `span` round an inline formula, a table
  cell, a tape cell). The tokens draw two rough loops round it. A
  `span[data-highlight]` gets `margin: 0 .2em` whether or not the loop is shown, so
  write the punctuation right after the `</span>` with no space (`</span>, `), and
  the text never jumps when the loop comes and goes. For a boxed cell (a tape cell),
  pull the loop's insets in to about `.3em` so it does not cut the next cell.
- SVG: the mark is its own element next to the target, highlight on the mark:
  `<path class="mark-loop" data-highlight="N" pathLength="1" d="...">` round a thing (a
  state, a point, a label), or `class="mark-swipe"` for a broad smear under a line (an
  edge, part of a curve; put it before the line). In a depiction, loop the new part's
  label, not its outline, so the mark is never read as another layer.
- **What to mark.** The content says what each step highlights; mark exactly that,
  nothing more. A state with its edge: loop the state and swipe the edge, both with
  the same `data-highlight="N"`. A step that names no target: mark its newest part,
  once. In a depiction, a step with two parts (such as "Flagella and pili") gets one
  loop, round the first one named. Repeat the mark element for another step.

**Drawing a loop.** Compute the path; never draw it by eye. The loop is a tilted
ellipse, drawn as a little more than one turn, with a small wobble. It drifts outward
slightly, so the overshoot runs beside the start and does not lie on top of it:

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

- **none**: nothing moves. Every step still appears, in order.
- **gentle**: the newest step fades up; its figure parts and the mark fade in.
- **full**: the newest step is written in from left to right; every stroke with
  `pathLength="1"` in it is drawn; `.wash` fills ink in after their outline; the mark
  is drawn round its target. Put `pathLength="1"` on outlines, curves, edges, leaders,
  never on text, dots, arrowheads, or a stroke with its own dash pattern.
  A stroke is drawn whether `data-step` sits on its SVG group or on the whole
  `figure`. If a dashed stroke needs `pathLength="1"` (for dashes in path fractions),
  give it its own full-motion rule in the page style that keeps its dash pattern and
  fades it in instead.

**Step 0 of a figure built part by part.** When every part has a step, show the
whole outline at step 0 as a `.ghost` (always shown, no `data-step`), so the pinned
figure is not empty. It is frame: the ghost has no label.

## Print

Printing gives a handout for free: white page, black ink, no board, every step shown,
no controls or marks. Never carry meaning by the mark colour alone.

## Notation: what the house style may not touch

**The meaning test.** Would someone who knows this field read a different meaning if this
property changed? Then it is notation and the house style does not touch it. When
unsure, it is notation. Notation comes from the course source first (the professor's
slides, the fingerprint's notation section), then the field's standard textbook
convention.

Name the figure's kind before you draw; when unsure, the stricter kind applies. The
frame (page, title, captions, controls) is always full house style.

1. **Depiction of a real thing** (heart, bacterium, cell). Fixed: shape, proportions,
   positions, conventional colours. You may style: label typeface, leader lines,
   reveal motion. Exaggeration (such as layer thickness) is said in a caption.
2. **Formal notation** (ERD, UML, DFA, circuits, flowcharts). Fixed: every symbol,
   shape, arrow and label form. You may style: typeface, one neutral ink
   (`--fig-ink`), line weight, reveal motion. No fills, no rough edges, no decoration
   the notation lacks.
3. **Plot of data or a function.** Fixed: exact curve geometry, axes, scale, units.
   You may style: axis and grid style, typeface, curve colour, reveal motion.
4. **Mimir's own sketch** (analogy, concept map). Nothing fixed; chalk edges allowed.

**Plots are computed.** Compute the points from the formula or data with code (60 or
more samples per period), never by eye. Ticks and labels sit at the exact values.

**Labels** never cross a stroke and never leave the viewBox: edge labels beside the
edge, self-loop labels beyond the apex, tick labels on the side the curve leaves free.

**Content.** Never add, solve, simplify, reorder or correct content; compose it.
Labels are verbatim. Words you add are frame only (an axis name, "input").

### Field notes

- Anatomy: `--arterial` and `--venous`; the standard anterior view.
- Databases: one ERD notation per course, the course's own.
- Signals: label the time axis with its units.
- Automata: state names in `.tex-i`, edge symbols in `.tex`, accepting states as
  double circles, the start arrow from nowhere, no "start" word. Keep loops round
  states wide and tilted so they never read as a second circle. Geometry, in viewBox
  units, for states of radius r on one row:
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
- Microbiology: keep the length-to-width ratio (on the outer membrane, the cell
  proper; inner layers may be thinner and outer ones rounder) and the envelope order
  from the inside out; say "not to scale" when layers are thickened. Label each layer
  with the step's name as written; sub-parts named in the text (nucleoid, ribosomes)
  may be drawn but stay unlabelled.
