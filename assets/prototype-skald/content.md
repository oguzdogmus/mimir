# Skald prototype: fixed content and page contract

PROTOTYPE for issue #87, throwaway. Every candidate builds the SAME three pieces from
the content below. Content is fixed: never add, solve, simplify, reorder or correct it.
Candidates differ in look and composition only. All content is synthetic (no course
material).

## Page contract (stands in for visual.py)

Each piece is one HTML file in the candidate's folder. The builder writes the `<body>`
(HTML, may contain inline SVG) and may write one `<style>` block in the head. The
builder writes NO JavaScript. Everything dynamic comes from `../shell.js` through
markup (see the comment at the top of `shell.js` for the full contract):

- `data-step="N"` on any element (HTML or SVG `<g>`) reveals it at step N. Several
  elements may share one N (a text step and the diagram part it talks about).
- `data-highlight="N"` marks the teaching highlight's target while step N is the latest.
- The shell sets `data-theme` (preview only), `data-motion` (`none`, `gentle`, `full`),
  `data-revealed`, `data-latest`, `data-highlight-on` and renders the step controls into
  `<div id="mimir-controls"></div>` (buttons `#mimir-back`, `#mimir-next`, a
  `#mimir-progress` count, a `#mimir-status` live region). Style them in your tokens.
- Math: inline `\( ... \)`, display `\[ ... \]`, rendered by bundled KaTeX.

Skeleton (copy it; only `<title>`, the optional `<style>` and the body change):

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>...</title>
<link rel="stylesheet" href="../../vendor/katex/katex.min.css">
<link rel="stylesheet" href="tokens.css">
<style>/* optional page CSS */</style>
</head>
<body>
<main>
  ... body ...
  <div id="mimir-controls"></div>
</main>
<script src="../../vendor/katex/katex.min.js"></script>
<script src="../../vendor/katex/contrib/auto-render.min.js"></script>
<script src="../shell.js"></script>
</body>
</html>
```

Theme rules in `tokens.css`: light values on `:root`; dark values under
`@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { ... } }` AND
again under `:root[data-theme="dark"] { ... }`. Motion rules act on
`:root[data-motion="none|gentle|full"]`; none means no animation or transition at all,
but every step still appears in order. Fonts load from `../fonts/` with `@font-face`.

Every piece must work at 390 px wide (phone) and at 1280 px wide (desktop), in light and
dark, at all three motion levels, and print sensibly (`@media print`: all steps shown,
no controls, no backgrounds that waste ink).

## Piece 1: worked math answer (`math.html`)

Figure kind of the sketch: plot of a function. Compute the curve's points from the
formula (for example 60+ samples of `y = 3 sin(2x − π/2)` over the period), never by eye;
axes, ticks and labels at the exact values. Write the computed points into the SVG
`path` yourself (run a script to get them).

- Label (always shown, verbatim): `[practice question, made by Mimir, answer checked]`
- Question (always shown): Find the amplitude, period and phase shift of
  \( f(x) = 3\sin\left(2x - \frac{\pi}{2}\right) \), then sketch one period.
- Step 1: Write \(f\) in the form \(A\sin\big(B(x - C)\big)\):
  \[ f(x) = 3\sin\left(2x - \frac{\pi}{2}\right) = 3\sin\left(2\left(x - \frac{\pi}{4}\right)\right) \]
  so \(A = 3\), \(B = 2\), \(C = \frac{\pi}{4}\).
- Step 2: Amplitude: \( |A| = 3 \).
- Step 3: Period: \[ T = \frac{2\pi}{B} = \frac{2\pi}{2} = \pi \]
- Step 4: Phase shift: \( C = \frac{\pi}{4} \), so the graph is shifted \( \frac{\pi}{4} \) to the right.
- Step 5: Key points of one period, from \(x = \frac{\pi}{4}\) to \(x = \frac{5\pi}{4}\):
  | x | π/4 | π/2 | 3π/4 | π | 5π/4 |
  | f(x) | 0 | 3 | 0 | −3 | 0 |
- Step 6: Sketch of one period (the plot), with the five key points marked.
- Step 6 also carries the answer line: Amplitude 3, period \(\pi\), phase shift
  \(\frac{\pi}{4}\) to the right.

Suggested highlights: step 2 highlights the amplitude in the plot area if the plot is
already visible; otherwise use the teaching highlight on the matching part of the
formula or table (e.g. step 5's table, step 6's peak point). Use it where it helps.

## Piece 2: engineering diagram (`diagram.html`)

Figure kind: formal notation (a DFA). Standard textbook DFA notation: circles for
states, a double circle for an accepting state, an incoming arrow from nowhere for the
start state, arrowheads on every edge, edge labels next to (never on) the edge,
self-loops with the label beyond the apex. One neutral ink colour, no fills, no
decoration the notation lacks. Labels never touch a stroke or leave the viewBox.

- Title: A DFA for binary numbers divisible by 3
- Label (always shown, verbatim): `[example machine, made by Mimir, checked]`
- Intro (always shown): The machine reads a binary number from the most significant bit.
  State \(q_r\) means "the bits read so far have value \(\equiv r \pmod 3\)". Reading bit
  \(b\) in state \(q_r\) moves to \(q_{(2r+b) \bmod 3}\).
- The machine (always shown, step 0): states q0, q1, q2. Start q0. Accepting q0.
  Transitions: q0 –0→ q0, q0 –1→ q1, q1 –0→ q2, q1 –1→ q0, q2 –0→ q1, q2 –1→ q2.
- Then a trace of the input `110` (decimal 6), one step per symbol:
  - Step 1: Start in \(q_0\) (value 0). Highlight q0.
  - Step 2: Read `1`: \(q_0 \to q_1\) (value 1). Highlight q1 and the edge q0→q1.
  - Step 3: Read `1`: \(q_1 \to q_0\) (value 3). Highlight q0 and the edge q1→q0.
  - Step 4: Read `0`: \(q_0 \to q_0\) (value 6). Highlight q0 and its self-loop.
  - Step 5: Input finished in \(q_0\), an accepting state: `110` is accepted, and
    \(6 = 2 \cdot 3\) is divisible by 3.
- Show the input tape `1 1 0` somewhere, with the symbol being read marked per step.

## Piece 3: non-engineering depiction, layer by layer (`bacterium.html`)

Figure kind: depiction of a real thing. Keep the real shape and arrangement: a rod
(bacillus) with rounded ends, about 2 µm long and 0.5 to 1 µm wide (length about 2 to 3
times the width); the envelope layers concentric and in the true order from inside out.
Envelope thickness is exaggerated, as in textbook diagrams; say so in a caption. Style
may change label typeface, leader lines, reveal motion; not shape, proportion or order.

- Title: A Gram-negative bacterium, built layer by layer
- Label (always shown, verbatim): `[diagram, made by Mimir, simplified]`
- Intro (always shown): *Escherichia coli* is a rod-shaped, Gram-negative bacterium.
  Click through to build its cell from the inside out.
- Step 1: Cytoplasm. The gel-like interior holds the nucleoid (the region with the single
  circular chromosome), ribosomes, and often small DNA rings called plasmids.
- Step 2: Plasma membrane (inner membrane). A phospholipid bilayer that controls what
  enters and leaves the cell.
- Step 3: Periplasm and peptidoglycan. A thin layer of peptidoglycan sits in the
  periplasmic space between the two membranes. It is far thinner than in Gram-positive
  bacteria, which is why Gram-negative cells do not keep the crystal violet stain.
- Step 4: Outer membrane. A second bilayer whose outer leaflet carries
  lipopolysaccharide (LPS); porins in it let small molecules through.
- Step 5: Capsule. Many strains add a slimy polysaccharide capsule that helps them
  avoid the host's immune system.
- Step 6: Flagella and pili. Flagella spread over the surface turn like propellers to
  swim; the shorter, thinner pili (fimbriae) help the cell stick to surfaces.
- Caption (always shown): Not to scale: the envelope layers are drawn much thicker than
  they are, as in textbook diagrams.

Each step reveals its layer in the figure and its text; leader lines connect each label
to its layer. The teaching highlight marks the newest layer.
