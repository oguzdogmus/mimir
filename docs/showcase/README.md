# Skald showcase

The README's "What it looks like" pictures: the four test pieces of the Skald house style
(spec #86, tickets #95 and the review fixes), built from synthetic content only, for the made-up
fixture course `2026-Fall/CS301 Automata` and, for the bacterium, a made-up course
`2026-Fall/BIO110 Microbiology`. No real course material is used anywhere here.

- `content.md`: the content each piece was given, as a dispatcher hands it to the visual
  builder.
- `pieces/<name>.json`: the exact `visual.py page` input the builder (`helpers/visual-builder.md`,
  Sonnet) wrote for each piece, body and all.
- `shoot.py`: rebuilds every piece through the current `scripts/visual.py` and takes the
  pictures in `assets/showcase/`.

## Retake the pictures

After any change to the shell (tokens, fonts, step controls, a mascot), run from the repo root:

```sh
uv run --with playwright playwright install chromium   # once
uv run --with playwright python docs/showcase/shoot.py
```

It builds each piece in a throwaway workspace (motion level none), opens it in headless
Chromium at 1280 × 1080, clicks Next until every step is revealed and saves
`assets/showcase/<name>-light.png` and `<name>-dark.png`. Look at the eight pictures before
committing them. `python3 docs/showcase/shoot.py --html-only DIR` only writes the pages, to
look at them in a browser; `tests/test_showcase.py` runs that, so a shell change that would
refuse a piece fails the tests.

## Rebuild a piece

Only when the guide or the content changes. Make a fixture course with
`python3 tests/acceptance/make_fixture.py --out DIR --axis support --level method-first`, so
nothing touches your real learning folder; for the bacterium, add its course with
`echo '{"term": "2026-Fall", "course": "BIO110 Microbiology"}' | HOME=DIR/home python3 scripts/workspace.py course`.
The builder's shell commands must then run with
`HOME=DIR/home`: give it as `script` a small wrapper at `W/scripts/visual.py` that sets `HOME`
and `USERPROFILE` to `DIR/home`, runs the repo's `scripts/visual.py` with the same arguments
and stdin, and keeps a copy of each stdin (and answers `open` without opening a browser); `W/reference` is a link to the repo's `reference/`,
so the builder finds the guide. Dispatch the builder (the body of `helpers/visual-builder.md`,
Sonnet) with that `script`, `term` `2026-Fall`, the piece's `course`, `kind` `page`, the
piece's `name` and its section of `content.md`. Save the input of its last successful
`visual.py page` run as `pieces/<name>.json`, pretty-printed, and retake the pictures.
