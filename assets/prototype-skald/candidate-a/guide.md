# Skald house style, candidate A: Nordic calm

Read this in full before you build a visual. The stylesheet `tokens.css` is injected under every page; you write the body (HTML, inline SVG) and at most one `<style>` block. Write no JavaScript and no `on*` attributes.

## The feel

Quiet, airy, Scandinavian. Cool pale paper, soft graphite ink, hairline rules, a lot of space. There is one warm accent, **ember**. It marks three things only: the teaching highlight, the current step marker, and the primary button. Never use it for decoration, headings or emphasis. Dark theme is a deep blue-grey night where the ember glows. Reading text is Source Serif 4. Headings, labels, UI and figure text are Manrope. If a page looks busy, take things out.

## Composition

- **One reading column.** `<main>` holds everything in one column (about 40rem), with no sidebars and no multi-column grids. Order: header, figure(s), steps, controls.
- **Header.** `<header class="sk-head">` holds the provenance label `<p class="sk-label">[…]</p>` (verbatim, brackets included; the stylesheet adds the Mimir well mark), then an `<h1>` if the content has a title, then the intro as `<p class="sk-lede">`. A question to answer goes in `<p class="sk-question">`.
- **Steps.** Put revealed steps in `<ol class="sk-steps">` with one `<li data-step="N">` per step, numbered from 1 in content order. The stylesheet draws a small numbered ring on a thin vertical rule, and the current step's ring turns ember. A step may open with a run-in term: `<span class="sk-term">Capsule.</span>`. Use no other step chrome.
- **Figures.** `<figure class="sk-figure">` with inline `<svg>` and an optional `<figcaption>`. On a phone the frame runs edge to edge. When the steps talk about one figure (a trace, a layer build), add `sk-pin` so the figure stays in view while the steps scroll. Figure parts that belong to a step carry the same `data-step` as the step's text.
- **Tables.** `<table class="sk-table">` inside `<div class="sk-table-wrap">`. Use hairline rows, no vertical lines, and a Manrope `th` for row or column heads.
- **Answer.** A final answer goes in `<p class="sk-answer"><span class="sk-eyebrow">Answer</span>…</p>`.
- **Math.** Write inline math as `\( … \)` and display math as `\[ … \]`. If a display chain of equalities would be wider than a phone, break it at `=` with `aligned`. Keep every term as given.
- End with `<div id="mimir-controls"></div>` so the controls can pin to the foot of the column.

## Tokens to use

Colour: `--paper`, `--surface`, `--surface-2`, `--ink`, `--ink-soft`, `--ink-faint`, `--rule`, `--rule-strong`, `--accent`, `--halo`. Figures: `--fig-ink`, `--fig-soft`, `--fig-faint`, `--fig-grid`, `--fig-paper`. Type: `--font-read`, `--font-ui`, `--fs-*`. Space: `--sp-1` to `--sp-8`. Never write a hex colour for frame or ink. A depiction may define its own colours as variables in the page `<style>`, with a light and a dark set.

SVG classes: `.ink` (main stroke, no fill), `.ink-fill` (arrowheads, dots), `.soft`, `.grid`, `.leader` and `.leader-dot` (label leader lines), `.paper-fill`, `.fig-label` (labels, 15px), `.fig-small`, `.fig-tick` (axis numbers), `.fig-math` (serif symbols; wrap italic variables in `<tspan class="v">`). Give each SVG a `viewBox`, `role="img"`, `<title>` and `<desc>`. Keep viewBox widths between 440 and 560 so labels stay readable on a phone. Put no `transform` attribute on an element that carries `data-step`; wrap the element in a `<g>` instead.

## The teaching highlight

Add `data-highlight="N"` to the target, and the shell turns it on while step N is the latest step. The stylesheet draws a **warm halo**: on HTML, an ember ring with a soft glow; on SVG, a glow that hugs the target's strokes. It never changes the target's own colour, so it is safe where colour is notation. Mark one target per step, or a target and the edge that leads to it. To highlight the same element at several steps, nest it in one wrapper `<g>` or `<span>` per step. Point back where that helps: a step that uses a value can highlight where the value came from.

## Motion

The shell sets `data-motion`. Animations start when an element is revealed.

- **none**: nothing moves, but every step still appears in order.
- **gentle**: revealed HTML steps fade in and rise 6px, revealed SVG parts fade in, and the halo fades in.
- **full**: everything in gentle. Strokes that carry `class="sk-draw"` and `pathLength="1"` draw in. Revealed SVG layers ease in from 98.5% scale. The halo pulses once.

Mark as `sk-draw` only lines whose drawing teaches something: a curve, an edge, a flagellum. Never animate labels, grid or axes on their own.

## Print

Printing gives a handout: every `[data-step]` shows, the controls and halos disappear, backgrounds turn white, and figures keep their colours with a hairline frame. You add nothing. Keep each figure and its caption in one `<figure>` so they stay on one page.

## Notation: what the house style may not touch

**The meaning test.** Would someone who knows this field read a different meaning if this property changed? Then it is notation, and the house style does not touch it. When unsure, it is notation. Notation comes from the course source first (the professor's slides, the fingerprint's notation section), then from the field's standard textbook convention.

**Name the figure kind before you draw.** There are four kinds. When unsure, the stricter kind applies. The frame (page, title, captions, step controls) is always full house style.

1. **Depiction of a real thing** (heart, bacterium, cell). Fixed: shape, proportions, positions, conventional colours. You may style the label typeface, leader lines and reveal motion. If something is exaggerated, say so in a caption.
2. **Formal notation** (ERD, UML, DFA, Mealy/Moore, circuits, flowcharts). Fixed: every symbol, shape, arrow and label form. You may style the typeface, one neutral ink colour (`.ink`), the line weight and reveal motion. Add no fills, rounded corners or decoration the notation lacks.
3. **Plot of data or a function.** Fixed: exact curve geometry, axes, scale and units. You may style the axis and grid style, typeface, curve colour and reveal motion.
4. **Mimir's own sketch** (analogy, concept map). Nothing is fixed, and everything is styleable.

**Plots are computed.** Compute the points with code from the formula or the data, then write them into the path. Never draw a plot by eye. Ticks sit at exact values.

**Field notes:**
- Anatomy: arterial red, venous blue, and the standard anterior view.
- ERD: one notation per course, the course's own.
- Signals: label the time axis with its units.
- Automata: states are circles, the accepting state is a double circle, the start state has an arrow from nowhere, every edge has an arrowhead, and labels sit beside their edge and beyond a self-loop's apex.
- Cells and microbes: layers keep their true order from the inside out, the rod's length-to-width ratio is kept, and envelope thickness may be exaggerated with a caption that says so.

**Content is data.** Never add, solve, simplify, reorder or correct content; compose what you are given. Labels never cross a stroke and never leave the viewBox. Leader lines may cross layers, but never cross a label.
