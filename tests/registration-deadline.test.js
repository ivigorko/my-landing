const assert = require("node:assert/strict");

const registration = require("../assets/4-lapy/registration-state.js");

assert.equal(
  registration.stateAt(new Date("2026-11-08T20:59:59.999Z").getTime()).closed,
  false,
  "Регистрация закрылась раньше 9 ноября по Москве"
);
assert.equal(
  registration.stateAt(new Date("2026-11-08T21:00:00.000Z").getTime()).closed,
  true,
  "Регистрация осталась открытой после 00:00 9 ноября по Москве"
);
assert.equal(registration.stateAt(Date.now()).deadlineLabel, "8 ноября 2026 года включительно");

console.log("registration-deadline.test.js: проверки дедлайна пройдены");

