(function () {
  "use strict";
  // Step reveal driven by markup (visual.py checked every value is a step 1..total):
  //   data-step="N"       hidden until step N is revealed (HTML or SVG, any element);
  //   data-highlight="N"  gets data-highlight-on while step N is the latest one.
  // Sets on the elements: data-revealed, data-latest, data-highlight-on. On the root:
  // class mimir-js (the tokens hide unrevealed steps on screen only), data-step-total,
  // data-step-current, --cur and --tot, and data-step-back after a step back (the tokens
  // then replay no animation).
  var root = document.documentElement;
  var steps = document.querySelectorAll("[data-step]");
  var marks = document.querySelectorAll("[data-highlight]");
  var total = 0;
  for (var i = 0; i < steps.length; i++) {
    total = Math.max(total, parseInt(steps[i].getAttribute("data-step"), 10));
  }
  if (!total) return;
  root.classList.add("mimir-js");
  root.setAttribute("data-step-total", String(total));
  root.style.setProperty("--tot", String(total));

  function button(id, label, keys) {
    var b = document.createElement("button");
    b.type = "button";
    b.id = id;
    b.textContent = label;
    b.setAttribute("aria-keyshortcuts", keys);
    return b;
  }
  var box = document.createElement("div");
  box.id = "mimir-controls";
  var back = button("mimir-back", "Back", "ArrowLeft ArrowUp");
  var progress = document.createElement("span");
  progress.id = "mimir-progress";
  var next = button("mimir-next", "Start", "ArrowRight ArrowDown");
  var status = document.createElement("p");
  status.id = "mimir-status";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  box.appendChild(back);
  box.appendChild(progress);
  box.appendChild(next);
  box.appendChild(status);
  (document.querySelector("main") || document.body).appendChild(box);

  var shown = 0;
  function flag(el, name, on) {
    if (on) el.setAttribute(name, "");
    else el.removeAttribute(name);
  }
  function inSvg(el) {
    return "ownerSVGElement" in el;
  }
  // The newest step's text, or when the step is only figure parts, the whole figure:
  // an SVG part's own box is a poor scroll target (and may sit in a pinned figure).
  function scrollTarget() {
    var first = null;
    for (var i = 0; i < steps.length; i++) {
      if (!steps[i].hasAttribute("data-latest")) continue;
      if (!inSvg(steps[i])) return steps[i];
      if (!first) first = steps[i];
    }
    while (first && first.ownerSVGElement) first = first.ownerSVGElement;
    return first;
  }
  function update(forward) {
    flag(root, "data-step-back", !forward);
    for (var i = 0; i < steps.length; i++) {
      var n = parseInt(steps[i].getAttribute("data-step"), 10);
      flag(steps[i], "data-revealed", n <= shown);
      flag(steps[i], "data-latest", n === shown);
    }
    for (var j = 0; j < marks.length; j++) {
      flag(marks[j], "data-highlight-on", parseInt(marks[j].getAttribute("data-highlight"), 10) === shown);
    }
    root.setAttribute("data-step-current", String(shown));
    root.style.setProperty("--cur", String(shown));
    progress.textContent = shown + " / " + total;
    back.setAttribute("aria-disabled", String(shown === 0));
    next.setAttribute("aria-disabled", String(shown === total));
    next.textContent = shown === 0 ? "Start" : shown === total ? "Done" : "Next step";
    var target = forward && shown ? scrollTarget() : null;
    if (target && target.scrollIntoView) {
      var still = root.getAttribute("data-motion") === "none";
      target.scrollIntoView({block: "nearest", behavior: still ? "auto" : "smooth"});
    }
  }
  function say(text) {
    status.textContent = text;
  }
  function forward() {
    if (shown >= total) {
      say("All " + total + " steps are shown.");
      return;
    }
    shown += 1;
    update(true);
    say("Step " + shown + " of " + total + (shown === total ? ", the last step." : "."));
  }
  function backward() {
    if (shown === 0) {
      say("No steps are shown.");
      return;
    }
    shown -= 1;
    update(false);
    say(shown === 0 ? "No steps are shown." : "Step " + shown + " of " + total + " is the last one shown.");
  }
  next.addEventListener("click", forward);
  back.addEventListener("click", backward);
  // Enter and Space work on the focused button; the arrows work anywhere except where
  // they already mean something (a field, an editable or focusable scroll area).
  document.addEventListener("keydown", function (event) {
    var target = event.target;
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey ||
        (target && target.closest &&
         target.closest("input, textarea, select, [contenteditable], [tabindex], .mimir-display"))) {
      return;
    }
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      forward();
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      backward();
    }
  });
  update(true);
  say(total + (total === 1 ? " step" : " steps") + " to reveal.");
})();
