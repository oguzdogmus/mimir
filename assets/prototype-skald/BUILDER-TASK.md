# Builder test task (prototype, issue #87)

You are a Mimir visual builder. Build ONE page in the Skald house style, "chalk and slate"
(candidate B3), from fixed content. This test compares builder models, so work only from
the documents named here.

Read, in full, before you write anything:
1. `/home/oguz/mimir/assets/prototype-skald/candidate-b3/guide.md`: the house-style guide.
   Follow it.
2. `/home/oguz/mimir/assets/prototype-skald/content.md`: the page contract and the fixed
   content. Read the "Page contract" section and the section for your piece only.
   Content is fixed: never add, solve, simplify, reorder or correct it.
3. `/home/oguz/mimir/assets/prototype-skald/shell.js`: the comment at the top is the
   markup contract.
4. `/home/oguz/mimir/assets/prototype-skald/candidate-b3/tokens.css`: you may read it to
   know the class names and tokens. Never edit it.

Do NOT open any `.html` file under `candidate-*` or `build-*` folders: those are other
builds, and copying them spoils the test.

Output: exactly one file, `<out-dir>/<piece>.html`. Use the skeleton from content.md, with
these path changes, because your folder sits next to `candidate-b3/`:
- the stylesheet: `<link rel="stylesheet" href="../candidate-b3/tokens.css">`
- KaTeX: `../../vendor/katex/...` as in the skeleton (unchanged)
- the shell: `<script src="../shell.js"></script>` (unchanged)
Write no JavaScript. Edit no other file.

Check your page:
- A server should serve `/home/oguz/mimir/assets` on port 8790. Check with
  `curl -s -o /dev/null -w '%{http_code}' http://localhost:8790/prototype-skald/candidate-b3/math.html`.
  If it is not 200, start it in the background with
  `python3 -m http.server 8790 -d /home/oguz/mimir/assets`.
- Page URL: `http://localhost:8790/prototype-skald/<out-folder>/<piece>.html?theme=<light|dark>&motion=none&step=<N>`
- Screenshot with
  `timeout 40 firefox --headless --profile "$(mktemp -d -p <scratch>)" --screenshot <out.png> --window-size=<W>,<H> '<url>'`,
  then look at the PNG with the Read tool.
- Check 390×844 and 1280×900, light and dark, at step 0, a middle step and the last step.
  Fix what you see.
- Keep scratch files in your scratch dir, never in the repo.

Reply with:
- the file path;
- every point where the guide was unclear, missing or contradictory, quoting the guide
  line, as a list (this is the most useful part of your reply);
- what you are unsure of in your page.
