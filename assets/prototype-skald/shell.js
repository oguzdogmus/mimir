/*
 * PROTOTYPE (issue #87), throwaway. Stands in for what visual.py will inject
 * under every page: theme and motion attributes, KaTeX rendering, step reveal
 * driven by markup, the teaching highlight switch, and the step controls.
 * Candidate pages write NO JavaScript; they only load this file.
 *
 * Markup contract for candidate pages:
 *   data-step="N"        element (HTML or SVG) hidden until step N is revealed.
 *                        Several elements may share one N. N starts at 1.
 *   data-highlight="N"   element gets data-highlight-on while step N is the
 *                        latest revealed step (the teaching highlight).
 *   <div id="mimir-controls"></div>  where the step controls go (optional;
 *                        appended to <main> or <body> when missing).
 * Attributes the shell sets, for candidate CSS to style:
 *   <html data-theme="light|dark">   only when ?theme= is given (preview).
 *   <html data-motion="none|gentle|full">   always; default none.
 *   data-revealed        on every revealed step element.
 *   data-latest          on the elements of the latest revealed step.
 *   data-highlight-on    see above.
 *   <html data-step-current="N" data-step-total="T">
 * Controls markup: #mimir-controls > button#mimir-back, button#mimir-next,
 *   span#mimir-progress, p#mimir-status[role=status].
 * Mascot: the shell inlines ../mascot/<name>.svg (?mascot=<name>, default
 *   MASCOT_DEFAULT; ?mascot=off hides it) into div#mimir-mascot.mimir-mascot[aria-hidden],
 *   fixed at the bottom right, and sets data-mood on it per step:
 *   step 0 "curious", the last step "proud", steps between cycle
 *   "explaining", "thinking", "surprised", "pleased".
 */
(function () {
  "use strict";
  var root = document.documentElement;
  var params = new URLSearchParams(location.search);
  var theme = params.get("theme");
  if (theme === "light" || theme === "dark") root.setAttribute("data-theme", theme);
  var motion = params.get("motion");
  root.setAttribute("data-motion", motion === "gentle" || motion === "full" ? motion : "none");
  root.classList.add("mimir-js");
  var MASCOT_DEFAULT = "m4";
  var MOODS_MID = ["explaining", "thinking", "surprised", "pleased"];
  var mascotName = params.get("mascot") || MASCOT_DEFAULT;
  var mascot = null;
  function moodFor(shown, total) {
    if (!shown) return "curious";
    if (shown >= total) return "proud";
    return MOODS_MID[(shown - 1) % MOODS_MID.length];
  }
  function setMood(shown, total) {
    if (mascot) mascot.setAttribute("data-mood", moodFor(shown, total));
  }
  function setupMascot() {
    if (mascotName === "off" || !/^[a-z0-9-]+$/.test(mascotName)) return;
    mascot = document.createElement("div");
    mascot.id = "mimir-mascot";
    mascot.className = "mimir-mascot";
    mascot.setAttribute("aria-hidden", "true");
    setMood(parseInt(root.getAttribute("data-step-current") || "0", 10),
            parseInt(root.getAttribute("data-step-total") || "0", 10));
    document.body.appendChild(mascot);
    fetch("../mascot/" + mascotName + ".svg").then(function (r) { return r.ok ? r.text() : ""; })
      .then(function (svg) { mascot.innerHTML = svg; }).catch(function () {});
  }

  var hide = document.createElement("style");
  hide.textContent = ".mimir-js [data-step]:not([data-revealed]){display:none !important}" +
    "#mimir-mascot{position:fixed;z-index:40;pointer-events:none;" +
    "right:var(--mimir-mascot-right,max(12px,env(safe-area-inset-right,0px)));" +
    "bottom:var(--mimir-mascot-bottom,calc(76px + env(safe-area-inset-bottom,0px)));" +
    "width:var(--mimir-mascot-size,72px);" +
    "--mm-ink:var(--fig-ink,var(--ink,#222));--mm-paper:var(--fig-paper,#fff);" +
    "--mm-soft:var(--fig-soft,var(--ink-soft,#777));--mm-accent:var(--pen,var(--mark,var(--accent,#c33)))}" +
    "@media (min-width:901px){#mimir-mascot{width:var(--mimir-mascot-size-wide,104px)}}" +
    "#mimir-mascot svg{display:block;width:100%;height:auto;overflow:visible}" +
    "@media print{#mimir-mascot{display:none}}";
  document.head.appendChild(hide);

  function renderMath() {
    if (typeof renderMathInElement === "undefined") return;
    renderMathInElement(document.body, {
      output: "htmlAndMathml", throwOnError: false, trust: false,
      delimiters: [{left: "\\[", right: "\\]", display: true},
                   {left: "\\(", right: "\\)", display: false}]
    });
  }

  function setupSteps() {
    var all = document.querySelectorAll("[data-step]");
    var total = 0;
    for (var i = 0; i < all.length; i++) {
      var n = parseInt(all[i].getAttribute("data-step"), 10);
      if (n > total) total = n;
    }
    root.setAttribute("data-step-total", String(total));
    root.setAttribute("data-step-current", "0");
    if (!total) return;

    var box = document.getElementById("mimir-controls");
    if (!box) {
      box = document.createElement("div");
      box.id = "mimir-controls";
      (document.querySelector("main") || document.body).appendChild(box);
    }
    box.innerHTML =
      '<button type="button" id="mimir-back">Back</button>' +
      '<span id="mimir-progress"></span>' +
      '<button type="button" id="mimir-next">Next step</button>' +
      '<p id="mimir-status" role="status" aria-live="polite"></p>';
    var back = document.getElementById("mimir-back");
    var next = document.getElementById("mimir-next");
    var progress = document.getElementById("mimir-progress");
    var status = document.getElementById("mimir-status");
    var shown = 0;

    function update(scroll) {
      for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var n = parseInt(el.getAttribute("data-step"), 10);
        if (n <= shown) el.setAttribute("data-revealed", "");
        else el.removeAttribute("data-revealed");
        if (n === shown) el.setAttribute("data-latest", "");
        else el.removeAttribute("data-latest");
      }
      var hl = document.querySelectorAll("[data-highlight]");
      for (var j = 0; j < hl.length; j++) {
        if (parseInt(hl[j].getAttribute("data-highlight"), 10) === shown) hl[j].setAttribute("data-highlight-on", "");
        else hl[j].removeAttribute("data-highlight-on");
      }
      root.setAttribute("data-step-current", String(shown));
      setMood(shown, total);
      progress.textContent = shown + " / " + total;
      back.disabled = shown === 0;
      next.disabled = shown === total;
      next.textContent = shown === 0 ? "Start" : shown === total ? "Done" : "Next step";
      if (scroll) {
        var first = document.querySelector("[data-latest]");
        if (first && first.scrollIntoView && !(first instanceof SVGElement)) {
          var still = root.getAttribute("data-motion") === "none" ||
            (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
          first.scrollIntoView({block: "nearest", behavior: still ? "auto" : "smooth"});
        }
      }
    }
    function forward() {
      if (shown >= total) { status.textContent = "All " + total + " steps are shown."; return; }
      shown += 1; update(true);
      status.textContent = "Step " + shown + " of " + total + (shown === total ? ", the last step." : ".");
    }
    function backward() {
      if (shown === 0) { status.textContent = "No steps are shown."; return; }
      shown -= 1; update(false);
      status.textContent = shown === 0 ? "No steps are shown." : "Step " + shown + " of " + total + " is the last one shown.";
    }
    next.addEventListener("click", forward);
    back.addEventListener("click", backward);
    document.addEventListener("keydown", function (e) {
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      if (e.key === "ArrowRight" || e.key === "ArrowDown" || e.key === " ") { e.preventDefault(); forward(); }
      else if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); backward(); }
    });
    // ?step=N jumps straight to step N (preview convenience).
    var jump = parseInt(params.get("step") || "0", 10);
    if (jump > 0) shown = Math.min(jump, total);
    update(false);
    status.textContent = shown ? "Step " + shown + " of " + total + "." : total + " steps to reveal.";
  }

  function start() { renderMath(); setupSteps(); setupMascot(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
