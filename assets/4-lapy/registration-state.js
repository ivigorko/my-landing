(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FOUR_LAPY_REGISTRATION = api;
}(typeof window !== "undefined" ? window : this, function () {
  "use strict";

  var closesAt = Date.parse("2026-11-01T00:00:00+03:00");

  function stateAt(now) {
    return {
      closed: Number(now) >= closesAt,
      closesAt: closesAt,
      deadlineLabel: "31 октября 2026 года включительно"
    };
  }

  return { stateAt: stateAt };
}));
