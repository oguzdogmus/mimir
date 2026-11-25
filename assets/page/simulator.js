(function () {
  "use strict";
  // The page's machine simulator: feeds an input through MimirSim (machine.js) and marks the
  // current states in the builder's diagram (the elements with id state-<i>) with the teaching highlight.
  var machine = JSON.parse(document.getElementById("mimir-machine").textContent);
  var section = document.getElementById("mimir-sim");
  var input = document.getElementById("mimir-sim-input");
  var status = document.getElementById("mimir-sim-status");
  var history = document.getElementById("mimir-sim-history");
  var result = null, at = 0;

  function where(frame) {
    if (!frame.configs.length) {
      return "no state";
    }
    var parts = [], seen = {};
    for (var i = 0; i < frame.configs.length; i++) {
      var c = frame.configs[i];
      var text = machine.kind === "pda" ? c.state + " (stack " + (c.stack || "empty") + ")" : c.state;
      if (!Object.prototype.hasOwnProperty.call(seen, text)) {
        seen[text] = true;
        parts.push(text);
      }
    }
    return (parts.length > 1 ? "in states " : "in ") + parts.join(", ");
  }
  function describe(index) {
    var frame = result.frames[index], total = result.input.length;
    var rest = result.input.slice(frame.read).join("");
    var text;
    if (index === 0) {
      text = "Start: " + where(frame) + ".";
    } else {
      text = "Read '" + frame.symbol + "' (" + frame.read + " of " + total + "): " + where(frame) + ".";
    }
    if (frame.configs.length) {
      text += rest ? " Remaining: " + rest + "." : " Input fully read.";
    }
    if (index === result.frames.length - 1) {
      var v = MimirSim.verdict(machine, result);
      if (v.result === "accepted") {
        text += " Accepted: the whole input was read and an accepting state was reached.";
      } else if (frame.limited) {
        text += " No verdict: the search was cut, so an accepting path may have been missed.";
      } else if (v.result === "rejected") {
        text += " Rejected: the whole input was read, but no accepting state was reached.";
      } else {
        text += " Stuck on '" + v.symbol + "': no move from the previous state, so the input is rejected.";
      }
    }
    if (frame.limited) {
      text += " Search limit reached: some paths were not followed.";
    }
    return text;
  }
  function highlight(frame) {
    var current = {};
    if (frame) {
      for (var i = 0; i < frame.configs.length; i++) {
        current[frame.configs[i].state] = true;
      }
    }
    for (var s = 0; s < machine.states.length; s++) {
      var node = document.getElementById("state-" + (s + 1));
      if (node) {
        if (Object.prototype.hasOwnProperty.call(current, machine.states[s])) {
          node.setAttribute("data-highlight-on", "");
        } else {
          node.removeAttribute("data-highlight-on");
        }
      }
    }
  }
  function show() {
    while (history.firstChild) {
      history.removeChild(history.firstChild);
    }
    for (var i = 0; i <= at; i++) {
      var item = document.createElement("li");
      item.textContent = describe(i);
      history.appendChild(item);
    }
    highlight(result.frames[at]);
    status.textContent = describe(at);
  }
  function start() {
    if (MimirSim.symbols(input.value).length > machine.max_symbols) {
      result = null;
      highlight(null);
      status.textContent = "Use at most " + machine.max_symbols + " symbols.";
      return;
    }
    result = MimirSim.run(machine, input.value);
    at = 0;
    show();
  }
  function next() {
    if (!result) {
      start();
      return;
    }
    if (at >= result.frames.length - 1) {
      status.textContent = "Done. " + describe(at);
      return;
    }
    at += 1;
    show();
  }
  function back() {
    if (!result || at === 0) {
      status.textContent = result ? "Already at the start. " + describe(0) : "Press Start first.";
      return;
    }
    at -= 1;
    show();
  }
  document.getElementById("mimir-sim-start").addEventListener("click", start);
  document.getElementById("mimir-sim-next").addEventListener("click", next);
  document.getElementById("mimir-sim-back").addEventListener("click", back);
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      event.preventDefault();
      start();
    }
  });
  input.addEventListener("input", function () {
    result = null;
    highlight(null);
    while (history.firstChild) {
      history.removeChild(history.firstChild);
    }
    status.textContent = "Press Start to run the new input.";
  });
  // the arrow keys act inside the simulator only, so they never clash with a step reveal on the same page
  section.addEventListener("keydown", function (event) {
    if (event.target === input || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      next();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      back();
    }
  });
  document.getElementById("mimir-sim-controls").hidden = false;
  status.textContent = "Type an input and press Start.";
})();
