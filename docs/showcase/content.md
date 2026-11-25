# Skald showcase: the content given to the builder

The three test pieces of spec #86, rebuilt for the README from the synthetic fixture course
`2026-Fall/CS301 Automata` (`tests/acceptance/make_fixture.py`: its notes on the languages of
context-free grammars, and the course conventions in `tests/acceptance/checker_benchmark.json`).
Everything here is synthetic. No real course material is used.

Each section below is what a dispatcher hands the visual builder (`helpers/visual-builder.md`)
as the content, with `kind: page` and the `name` in the heading. The builder composes it and
never adds, solves, simplifies, reorders or corrects it.

## Piece 1: a worked math answer (`name: cfg-language`)

- Title: The language of S → aSc | b
- Label (always shown, verbatim): `[practice question from your notes, answer checked]`
- Question (always shown, it is the page heading): Describe in set notation the language of
  \(S \to aSc \mid b\).
- Step 1: Base case: the rule \(S \to b\) ends every derivation and puts one \(b\) in the
  middle: \(S \Rightarrow b\).
- Step 2: Recursive rule: each use of \(S \to aSc\) adds one \(a\) on the left and one \(c\)
  on the right, around the \(S\) that is still to be replaced:
  \[ S \Rightarrow aSc \Rightarrow aaScc \Rightarrow aabcc \]
- Step 3: Count: applying \(S \to aSc\) \(n\) times, for any \(n \ge 0\), and then \(S \to b\)
  once gives
  \[ S \Rightarrow^{*} a^{n}Sc^{n} \Rightarrow a^{n}bc^{n} \]
- Step 4: The shortest strings:

  | \(n\) | 0 | 1 | 2 | 3 |
  |---|---|---|---|---|
  | string | b | abc | aabcc | aaabccc |

- Step 5: The parse tree of aabcc (\(n = 2\)): reading its leaves from left to right gives
  aabcc.
- Step 5 also carries the answer line: \(L = \{a^{n}bc^{n} \mid n \ge 0\}\)
- Step 5 ends with: As the course conventions ask, the range of \(n\) is stated.
- The figure, shown at step 5 (the work comes first): the parse tree of aabcc. The root S
  has the children a, S and c, left to right; that S has the children a, S and c; that S
  has the one child b.

Highlights: step 4 marks the column \(n = 2\) of the table; step 5 marks the leaf b of the
tree.

## Piece 2: an engineering diagram (`name: even-as-dfa`)

- Title: A DFA for an even number of a's
- Label (always shown, verbatim): `[example machine, made by Mimir, checked]`
- Intro (always shown): The alphabet is \(\{a, b\}\). State \(q_0\) means an even number of
  a's read so far, \(q_1\) an odd number. Every state has exactly one move on each symbol,
  as this course's DFAs must.
- The machine (always shown, the figure): states q0 and q1. Start q0. Accepting q0.
  Transitions: q0 –a→ q1, q0 –b→ q0, q1 –a→ q0, q1 –b→ q1.
- Machine for the simulator: `{"kind": "dfa", "states": ["q0", "q1"], "start": "q0",
  "accept": ["q0"], "transitions": [{"from": "q0", "read": "a", "to": "q1"}, {"from": "q0",
  "read": "b", "to": "q0"}, {"from": "q1", "read": "a", "to": "q0"}, {"from": "q1", "read":
  "b", "to": "q1"}]}`, example input `aba`.
- Then a trace of the input `aba`, one step per symbol:
  - Step 1: Start in \(q_0\): no a's read yet, and zero is even. Highlight q0.
  - Step 2: Read a: \(q_0 \to q_1\), one a, odd. Highlight q1 and the edge q0 → q1.
  - Step 3: Read b: \(q_1 \to q_1\); a b does not change the count. Highlight the self-loop
    on q1.
  - Step 4: Read a: \(q_1 \to q_0\), two a's, even. Highlight q0 and the edge q1 → q0.
  - Step 5: The input is finished in \(q_0\), an accepting state: aba is accepted.
- Show the input tape `a b a` under the diagram, with the symbol being read marked in steps
  2, 3 and 4.

## Piece 3: a layer-by-layer depiction (`name: pda-parts`)

- Title: A pushdown automaton, part by part
- Label (always shown, verbatim): `[diagram, made by Mimir, simplified]`
- Intro (always shown): A PDA is a finite automaton with a stack. Click through to build
  one from its parts, shown partway through the PDA for \(\{a^{n}b^{n} \mid n \ge 0\}\)
  reading aabb.
- The figure: the usual textbook picture of a PDA's parts. The input tape runs across the
  top with a head pointing at the cell being read; the finite control is a box below the
  head; the stack is a column of cells under the control, top up.
- Step 1: Input tape: the input aabb, one symbol per cell. The head reads from left to right
  and never moves back; here it has read aa and is on the first b.
- Step 2: Finite control: the states q0, q1, q2 and q3; the machine is now in q1. q3 is the
  accepting state: in this course a PDA accepts by final state.
- Step 3: Stack: only its top can be read, pushed or popped. $ marks the bottom; one X was
  pushed for each a read, so it holds X, X, $ from the top down.
- Step 4: Moves: the control reads the symbol under the head and the top of the stack, then
  changes state, pops and pushes. The next move here reads b with X on top:
  \(b, X \to \varepsilon\), into \(q_2\).
- Caption (always shown): A sketch of the parts, not of a state diagram; the stack has no
  fixed height.

Each step reveals its part in the figure and its text. The teaching highlight marks the
newest part's label.

## Piece 4: a non-engineering depiction, layer by layer (`name: bacterium-envelope`)

This piece belongs to a second made-up course, `2026-Fall/BIO110 Microbiology`, so the
showcase also shows a figure outside engineering. It has no fixture notes: the content
below is the whole of it, written for the showcase.

- Title: The envelope of a Gram-negative bacterium
- Label (always shown, verbatim): `[diagram, made by Mimir, simplified]`
- Intro (always shown): A Gram-negative bacterium such as E. coli is wrapped in layers.
  Click through to build its envelope from the inside out.
- The figure (a depiction of a real thing): one rod-shaped cell, a capsule with rounded
  ends, drawn whole and cut lengthwise so its layers show as nested outlines around the
  inside: the cytoplasm innermost, then the inner membrane, the periplasm with the thin
  cell wall in it, and the outer membrane outermost with a fringe of lipopolysaccharide
  on its outer face. Each layer is labelled at the side with a leader line.
- Step 1: Cytoplasm: the inside of the cell, a gel of water, proteins and ribosomes. The
  DNA lies in a region called the nucleoid, with no membrane around it.
- Step 2: Inner membrane: a phospholipid bilayer around the cytoplasm that controls what
  enters and leaves it.
- Step 3: Cell wall: outside the inner membrane lies the periplasm, a narrow space that
  holds a thin layer of peptidoglycan, the cell wall, which keeps the cell's shape.
- Step 4: Outer membrane: a second bilayer whose outer face carries lipopolysaccharide
  (LPS); porins in it let small molecules through.
- Caption (always shown): Not to scale: the whole envelope is a few tens of nanometres
  thick, and the cell about 2 µm long.

Each step reveals its layer in the figure and its text. The teaching highlight marks the
newest layer's label.
