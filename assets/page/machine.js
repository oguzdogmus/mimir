var MimirSim = (function () {
  "use strict";
  function key(config) {
    return config.state + "\u0000" + config.stack;
  }
  function moves(machine, config, symbol) {
    var out = [];
    for (var i = 0; i < machine.transitions.length; i++) {
      var t = machine.transitions[i];
      if (t.from !== config.state || t.read !== symbol) {
        continue;
      }
      if (machine.kind === "pda") {
        if (t.pop !== "" && config.stack.charAt(0) !== t.pop) {
          continue;
        }
        out.push({state: t.to, stack: t.push + config.stack.slice(t.pop.length)});
      } else {
        out.push({state: t.to, stack: ""});
      }
    }
    return out;
  }
  function closure(machine, configs) {
    var seen = {}, out = [], queue = configs.slice(), limited = false;
    while (queue.length) {
      var config = queue.shift();
      if (Object.prototype.hasOwnProperty.call(seen, key(config))) {
        continue;
      }
      if (config.stack.length > machine.max_stack) {
        limited = true;
        continue;
      }
      if (out.length >= machine.max_configs) {
        limited = true;
        break;
      }
      seen[key(config)] = true;
      out.push(config);
      queue = queue.concat(moves(machine, config, ""));
    }
    return {configs: out, limited: limited};
  }
  function symbols(text) {
    return Array.from(text.replace(/\s+/g, ""));
  }
  function run(machine, text) {
    var input = symbols(text);
    var first = closure(machine, [{state: machine.start, stack: machine.kind === "pda" ? machine.stack_start : ""}]);
    var frames = [{read: 0, symbol: null, configs: first.configs, limited: first.limited}];
    for (var i = 0; i < input.length; i++) {
      var current = frames[frames.length - 1];
      if (!current.configs.length) {
        break;
      }
      var next = [];
      for (var j = 0; j < current.configs.length; j++) {
        next = next.concat(moves(machine, current.configs[j], input[i]));
      }
      var step = closure(machine, next);
      frames.push({read: i + 1, symbol: input[i], configs: step.configs,
                   limited: current.limited || step.limited});
    }
    return {input: input, frames: frames};
  }
  function verdict(machine, result) {
    var last = result.frames[result.frames.length - 1];
    if (!last.configs.length) {
      return {result: "stuck", symbol: last.symbol, read: last.read};
    }
    for (var i = 0; i < last.configs.length; i++) {
      if (machine.accept.indexOf(last.configs[i].state) >= 0) {
        return {result: "accepted"};
      }
    }
    return {result: "rejected"};
  }
  return {run: run, verdict: verdict, symbols: symbols};
})();
