(function () {
  "use strict";
  if (typeof renderMathInElement === "undefined") return;
  renderMathInElement(document.querySelector("main"), {
    output: "htmlAndMathml", throwOnError: false, trust: false,
    delimiters: [{left: "\\(", right: "\\)", display: false},
                 {left: "\\[", right: "\\]", display: true}],
    ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "option", "svg"]
  });
})();
