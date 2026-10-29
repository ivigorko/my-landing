const assert = require("node:assert/strict");

const registration = require("../assets/4-lapy/registration-state.js");

assert.equal(
  registration.stateAt(new Date("2026-10-31T20:59:59.999Z").getTime()).closed,
  false,
  "Регистрация закрылась раньше 1 ноября по Москве"
);
assert.equal(
  registration.stateAt(new Date("2026-10-31T21:00:00.000Z").getTime()).closed,
  true,
  "Регистрация осталась открытой после 00:00 1 ноября по Москве"
);
assert.equal(registration.stateAt(Date.now()).deadlineLabel, "31 октября 2026 года включительно");

console.log("registration-deadline.test.js: проверки дедлайна пройдены");
