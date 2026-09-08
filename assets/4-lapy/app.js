(function () {
  "use strict";

  var runtimeConfig = window.FOUR_LAPY_CONFIG || {};
  var CONFIG = {
    endpoint: runtimeConfig.endpoint || "https://script.google.com/macros/s/AKfycbz4vYxgWoTGq7vcKPu0rAVkD0eXl09nwNkbbSiEuwbClYTkf_0FMWOTumbKdWj4lJ7V/exec",
    smartCaptchaClientKey: runtimeConfig.smartCaptchaClientKey || "",
    captchaRequired: runtimeConfig.captchaRequired === undefined ? false : runtimeConfig.captchaRequired !== false,
    allowedResponseHosts: ["script.google.com", "script.googleusercontent.com"],
    thanksUrl: "thanks.html"
  };

  function analyticsUrl(value) {
    if (!value) return "";
    try {
      var parsed = new URL(value, window.location.origin);
      return parsed.origin + parsed.pathname;
    } catch (error) { return ""; }
  }

  function configureYandexMetrika() {
    window.PR_M = window.PR_M || { id: 103646147, loaded: false };
    if (typeof window.loadYandexMetrika !== "function") {
      window.loadYandexMetrika = function () {
        if (window.PR_M.loaded) return;
        window.PR_M.loaded = true;
        (function (m, e, t, r, i, k, a) {
          m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
          m[i].l = 1 * new Date();
          for (var j = 0; j < document.scripts.length; j += 1) if (document.scripts[j].src === r) return;
          k = e.createElement(t); a = e.getElementsByTagName(t)[0]; k.async = 1; k.src = r; a.parentNode.insertBefore(k, a);
        }(window, document, "script", "https://mc.yandex.ru/metrika/tag.js?id=103646147", "ym"));
        window.ym(103646147, "init", {
          ssr: true,
          webvisor: false,
          clickmap: true,
          referrer: analyticsUrl(document.referrer),
          url: analyticsUrl(window.location.href),
          accurateTrackBounce: true,
          trackLinks: true
        });
      };
    }
    try {
      if (localStorage.getItem("probeg-consent") === "accept") window.loadYandexMetrika();
    } catch (error) {}
  }

  configureYandexMetrika();

  var form = document.getElementById("registrationForm");
  var submitButton = document.getElementById("submitButton");
  var statusNode = document.getElementById("formStatus");
  var errorSummary = document.getElementById("errorSummary");
  var errorList = document.getElementById("errorList");
  var dogFields = document.getElementById("dogFields");
  var requestIdInput = document.getElementById("requestId");
  var progressNode = document.getElementById("submissionProgress");
  var progressTitle = document.getElementById("submissionTitle");
  var progressHint = document.getElementById("submissionHint");
  var emailInput = document.getElementById("email");
  var emailAdvisory = document.getElementById("emailAdvisory");
  var draftKey = "four-lapy-registration-draft-v1";
  var submitting = false;
  var timeoutId = null;
  var progressTimers = [];
  var serviceWarmed = false;
  var summaryLabels = {
    participantName: "Имя",
    age: "Возраст",
    phone: "Телефон",
    email: "Электронная почта",
    participationFormat: "Формат участия",
    dogName: "Кличка собаки",
    dogBreed: "Порода или тип",
    dogAge: "Возраст собаки",
    dogSize: "Размер собаки",
    acceptRules: "Правила участия",
    acceptPrivacy: "Согласие на обработку данных"
  };

  function uuid() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") return window.crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (character) {
      var random = Math.random() * 16 | 0;
      var value = character === "x" ? random : (random & 3 | 8);
      return value.toString(16);
    });
  }

  function setHiddenContext() {
    var params = new URLSearchParams(window.location.search);
    requestIdInput.value = requestIdInput.value || uuid();
    document.getElementById("formStartedAt").value = String(Date.now());
    document.getElementById("pageUrl").value = window.location.origin + window.location.pathname;
    document.getElementById("referrer").value = safeReferrer(document.referrer);
    ["source", "medium", "campaign", "content", "term"].forEach(function (name) {
      var node = document.getElementById("utm" + name.charAt(0).toUpperCase() + name.slice(1));
      if (node) node.value = (params.get("utm_" + name) || "").slice(0, 120);
    });
  }

  function safeReferrer(value) {
    if (!value) return "";
    try {
      var parsed = new URL(value);
      return (parsed.origin + parsed.pathname).slice(0, 500);
    } catch (error) { return ""; }
  }

  function trackGoal(name) {
    if (typeof window.ym === "function") window.ym(103646147, "reachGoal", name);
  }

  function setStatus(message, type) {
    statusNode.textContent = message;
    statusNode.className = "form-status" + (type ? " " + type : "");
  }

  function setSubmitting(value) {
    submitting = value;
    submitButton.disabled = value;
    submitButton.textContent = value ? "Отправляем заявку…" : "Зарегистрироваться";
    form.setAttribute("aria-busy", value ? "true" : "false");
    if (!value) hideSubmissionProgress();
  }

  function clearProgressTimers() {
    progressTimers.forEach(function (timer) { window.clearTimeout(timer); });
    progressTimers = [];
  }

  function updateSubmissionProgress(title, hint) {
    progressTitle.textContent = title;
    progressHint.textContent = hint;
  }

  function showSubmissionProgress() {
    clearProgressTimers();
    updateSubmissionProgress("Регистрируем заявку", "Обычно это занимает несколько секунд.");
    progressNode.hidden = false;
    progressTimers.push(window.setTimeout(function () {
      updateSubmissionProgress("Сохраняем данные", "Проверяем заявку и защищаем её от повторной записи.");
    }, 2500));
    progressTimers.push(window.setTimeout(function () {
      updateSubmissionProgress("Получаем номер заявки", "Почти готово. Не закрывайте страницу.");
    }, 6000));
    progressTimers.push(window.setTimeout(function () {
      updateSubmissionProgress("Сервис отвечает дольше обычного", "Заявка всё ещё обрабатывается. Не нажимайте кнопку повторно.");
    }, 10000));
  }

  function hideSubmissionProgress() {
    clearProgressTimers();
    progressNode.hidden = true;
  }

  function toggleDogFields() {
    var selected = form.querySelector('input[name="participationFormat"]:checked');
    var ownDog = selected && selected.value === "own_dog";
    dogFields.hidden = !ownDog;
    ["dogName", "dogBreed", "dogAge", "dogSize"].forEach(function (id) {
      document.getElementById(id).required = ownDog;
    });
    if (selected) trackGoal(selected.value === "own_dog" ? "4lapy_format_own" : "4lapy_format_shelter");
  }

  function normalizePhone(value) {
    return value.trim().replace(/[\s()\-]/g, "");
  }

  function checkEmailDomain() {
    if (!emailInput || !emailAdvisory) return;
    var domain = (emailInput.value.split("@")[1] || "").toLowerCase();
    var commonTypos = ["ail.com", "gamil.com", "gmial.com", "yandex.r", "mail.r"];
    emailAdvisory.textContent = commonTypos.indexOf(domain) >= 0
      ? "Проверьте домен «" + domain + "». Если он указан верно, форму можно отправить."
      : "";
  }

  function fieldError(id, message, errors) {
    var field = document.getElementById(id);
    var error = document.getElementById(id + "Error");
    if (field) field.setAttribute("aria-invalid", message ? "true" : "false");
    if (error) error.textContent = message || "";
    if (message) errors.push({ id: id, message: message });
  }

  function validate() {
    var errors = [];
    var name = document.getElementById("participantName").value.trim();
    var age = Number(document.getElementById("age").value);
    var phone = normalizePhone(document.getElementById("phone").value);
    var email = document.getElementById("email").value.trim();
    var format = form.querySelector('input[name="participationFormat"]:checked');

    fieldError("participantName", name.length < 2 ? "Укажите имя, не короче двух символов." : "", errors);
    fieldError("age", !Number.isInteger(age) || age < 18 || age > 100 ? "Основная дистанция доступна участникам от 18 до 100 лет." : "", errors);
    fieldError("phone", !/^\+?[0-9]{7,15}$/.test(phone) ? "Укажите телефон из 7–15 цифр." : "", errors);
    fieldError("email", !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email) ? "Укажите корректный адрес электронной почты." : "", errors);
    fieldError("participationFormat", !format ? "Выберите формат участия." : "", errors);

    if (format && format.value === "own_dog") {
      fieldError("dogName", document.getElementById("dogName").value.trim() ? "" : "Укажите кличку собаки.", errors);
      fieldError("dogBreed", document.getElementById("dogBreed").value.trim() ? "" : "Укажите породу или тип собаки.", errors);
      fieldError("dogAge", document.getElementById("dogAge").value.trim() ? "" : "Укажите возраст собаки.", errors);
      fieldError("dogSize", document.getElementById("dogSize").value ? "" : "Выберите размер собаки.", errors);
    } else {
      ["dogName", "dogBreed", "dogAge", "dogSize"].forEach(function (id) { fieldError(id, "", errors); });
    }

    fieldError("acceptRules", document.getElementById("acceptRules").checked ? "" : "Примите правила участия.", errors);
    fieldError("acceptPrivacy", document.getElementById("acceptPrivacy").checked ? "" : "Дайте согласие на обработку персональных данных.", errors);

    errorList.textContent = "";
    errors.forEach(function (item) {
      var li = document.createElement("li");
      var link = document.createElement("a");
      link.href = "#" + item.id;
      link.textContent = summaryLabels[item.id] || item.message;
      li.appendChild(link);
      errorList.appendChild(li);
    });
    errorSummary.hidden = errors.length === 0;
    if (errors.length) errorSummary.focus();
    return errors.length === 0;
  }

  function saveDraft() {
    var data = {};
    ["participantName", "age", "phone", "email", "dogName", "dogBreed", "dogAge", "dogSize"].forEach(function (id) {
      data[id] = document.getElementById(id).value;
    });
    var format = form.querySelector('input[name="participationFormat"]:checked');
    data.participationFormat = format ? format.value : "";
    try { sessionStorage.setItem(draftKey, JSON.stringify(data)); } catch (error) {}
  }

  function restoreDraft() {
    var raw = null;
    try { raw = sessionStorage.getItem(draftKey); } catch (error) {}
    if (!raw) return;
    try {
      var data = JSON.parse(raw);
      Object.keys(data).forEach(function (key) {
        if (key === "participationFormat") {
          var radio = form.querySelector('input[name="participationFormat"][value="' + data[key] + '"]');
          if (radio) radio.checked = true;
        } else if (document.getElementById(key)) {
          document.getElementById(key).value = data[key];
        }
      });
      toggleDogFields();
    } catch (error) {}
  }

  function hostAllowed(origin) {
    try {
      var host = new URL(origin).hostname;
      return CONFIG.allowedResponseHosts.some(function (allowed) {
        if (host === allowed || host.endsWith("." + allowed)) return true;
        return allowed === "script.googleusercontent.com" && host.endsWith("-script.googleusercontent.com");
      });
    } catch (error) { return false; }
  }

  function handleResponse(event) {
    var data = event.data || {};
    if (!submitting || !hostAllowed(event.origin) || data.source !== "four-lapy-registration" || data.requestId !== requestIdInput.value) return;
    window.clearTimeout(timeoutId);
    clearProgressTimers();
    if (data.ok && /^4L-2026-[0-9]{4,}$/.test(data.applicationNumber)) {
      try {
        sessionStorage.removeItem(draftKey);
        sessionStorage.setItem("four-lapy-application-number", data.applicationNumber);
        sessionStorage.setItem("four-lapy-participation-format", form.querySelector('input[name="participationFormat"]:checked').value);
      } catch (error) {}
      updateSubmissionProgress("Заявка зарегистрирована", "Открываем страницу с вашим номером.");
      trackGoal("4lapy_submit_success");
      window.location.assign(CONFIG.thanksUrl + "?application=" + encodeURIComponent(data.applicationNumber));
      return;
    }
    setSubmitting(false);
    setStatus(errorMessage(data.code), "error");
    trackGoal("4lapy_submit_error");
  }

  function errorMessage(code) {
    var messages = {
      VALIDATION: "Проверьте данные и повторите отправку.",
      CAPTCHA: "Не удалось подтвердить, что заявку отправляет человек. Пройдите проверку ещё раз.",
      BUSY: "Сервис занят. Подождите минуту и повторите отправку.",
      STORAGE: "Не удалось сохранить заявку. Данные остались в форме, попробуйте ещё раз."
    };
    return messages[code] || "Заявка не отправлена. Попробуйте ещё раз или напишите клубу во ВКонтакте.";
  }

  function loadCaptcha() {
    var container = document.getElementById("captchaContainer");
    if (!CONFIG.captchaRequired || !CONFIG.smartCaptchaClientKey) return;
    if (!container) {
      container = document.createElement("div");
      container.id = "captchaContainer";
      container.className = "captcha-container";
      var actions = form.querySelector(".form-actions");
      actions.parentNode.insertBefore(container, actions);
    }
    container.textContent = "";
    var script = document.createElement("script");
    script.src = "https://smartcaptcha.cloud.yandex.ru/captcha.js";
    script.defer = true;
    script.onload = function () {
      if (window.smartCaptcha) window.smartCaptcha.render(container, { sitekey: CONFIG.smartCaptchaClientKey, hl: "ru" });
    };
    document.head.appendChild(script);
  }

  function warmRegistrationService() {
    if (serviceWarmed || !CONFIG.endpoint || window.location.protocol !== "https:") return;
    serviceWarmed = true;
    try {
      var separator = CONFIG.endpoint.indexOf("?") >= 0 ? "&" : "?";
      var transport = document.getElementById("registrationTransport");
      if (transport) transport.src = CONFIG.endpoint + separator + "warmup=1";
    } catch (error) {}
  }

  function scheduleServiceWarmup() {
    var section = document.getElementById("registration");
    if (!section || window.location.protocol !== "https:" || !("IntersectionObserver" in window)) return;
    var observer = new IntersectionObserver(function (entries) {
      if (!entries.some(function (entry) { return entry.isIntersecting; })) return;
      observer.disconnect();
      warmRegistrationService();
    }, { rootMargin: "900px 0px" });
    observer.observe(section);
  }

  function configureRegistrationState() {
    var ready = Boolean(CONFIG.endpoint && (!CONFIG.captchaRequired || CONFIG.smartCaptchaClientKey));
    document.querySelectorAll(".registration-cta").forEach(function (link) {
      link.textContent = ready ? (link.closest(".hero-actions") ? "Подать заявку" : "Регистрация") : "Регистрация скоро";
    });
    submitButton.disabled = !ready;
    submitButton.textContent = ready ? "Зарегистрироваться" : "Регистрация скоро откроется";
    if (!ready) setStatus("Форма будет доступна после подключения защищённой отправки.", "");
  }

  function showReturnedError() {
    var code = new URLSearchParams(window.location.search).get("registration_error");
    if (!code) return;
    setStatus(errorMessage(code), "error");
    if (window.history && window.history.replaceState) window.history.replaceState({}, "", window.location.pathname + "#registration");
  }

  if (form) {
    setHiddenContext();
    restoreDraft();
    configureRegistrationState();
    showReturnedError();
    loadCaptcha();
    scheduleServiceWarmup();
    form.addEventListener("input", saveDraft);
    if (emailInput) {
      emailInput.addEventListener("blur", checkEmailDomain);
      emailInput.addEventListener("input", function () { if (emailAdvisory) emailAdvisory.textContent = ""; });
    }
    form.querySelectorAll('input[name="participationFormat"]').forEach(function (input) { input.addEventListener("change", toggleDogFields); });
    form.addEventListener("focusin", function () {
      warmRegistrationService();
      if (!form.dataset.started) { form.dataset.started = "yes"; trackGoal("4lapy_form_start"); }
    });
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (submitting || !validate()) return;
      if (!CONFIG.endpoint) {
        saveDraft();
        setStatus("Приём заявок ещё не включён. Форма готова, но сервер регистрации ожидает настройки.", "error");
        trackGoal("4lapy_submit_error");
        return;
      }
      setStatus("Отправляем заявку…", "");
      setSubmitting(true);
      showSubmissionProgress();
      form.action = CONFIG.endpoint;
      form.target = "registrationTransport";
      timeoutId = window.setTimeout(function () {
        setSubmitting(false);
        saveDraft();
        setStatus("Не удалось получить подтверждение. Данные сохранены в этой вкладке, нажмите «Зарегистрироваться» ещё раз.", "error");
        trackGoal("4lapy_submit_error");
      }, 20000);
      form.submit();
    });

    var transport = document.getElementById("registrationTransport");
    if (transport) transport.addEventListener("load", function () {
      if (!submitting) return;
      updateSubmissionProgress("Ответ получен", "Получаем номер заявки.");
    });
  }

  window.addEventListener("message", handleResponse);

  var menuButton = document.querySelector(".menu-button");
  var mobileMenu = document.getElementById("mobileMenu");
  if (menuButton && mobileMenu) {
    var menuLabel = menuButton.querySelector("span");
    function setMenuState(open) {
      document.body.classList.toggle("menu-open", open);
      menuButton.setAttribute("aria-expanded", String(open));
      menuButton.setAttribute("aria-label", open ? "Закрыть меню" : "Открыть меню");
      if (menuLabel) menuLabel.textContent = open ? "Закрыть" : "Меню";
    }
    menuButton.addEventListener("click", function () {
      setMenuState(!document.body.classList.contains("menu-open"));
    });
    mobileMenu.querySelectorAll("a").forEach(function (link) { link.addEventListener("click", function () { setMenuState(false); }); });
    window.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && document.body.classList.contains("menu-open")) {
        setMenuState(false);
        menuButton.focus();
      }
    });
  }

  (function cookieConsent() {
    var key = "probeg-consent";
    var banner = document.getElementById("cookieBanner");
    var accept = document.getElementById("cookieAccept");
    var reject = document.getElementById("cookieReject");
    var open = document.getElementById("openCookiePrefs");
    var origin = document.createComment("cookie-banner-origin");
    var compactViewport = window.matchMedia("(max-width: 720px)");
    banner.parentNode.insertBefore(origin, banner);
    function placeBanner() {
      var header = document.querySelector(".site-header");
      if (compactViewport.matches && header) header.insertAdjacentElement("afterend", banner);
      else if (origin.parentNode) origin.parentNode.insertBefore(banner, origin.nextSibling);
    }
    function show() { banner.classList.add("show"); }
    function hide() { banner.classList.remove("show"); }
    function save(value) {
      try { localStorage.setItem(key, value); } catch (error) {}
      if (value === "accept" && typeof window.loadYandexMetrika === "function") window.loadYandexMetrika();
      hide();
    }
    var stored = null;
    try { stored = localStorage.getItem(key); } catch (error) {}
    placeBanner();
    if (typeof compactViewport.addEventListener === "function") compactViewport.addEventListener("change", placeBanner);
    else if (typeof compactViewport.addListener === "function") compactViewport.addListener(placeBanner);
    if (!stored) window.setTimeout(show, 500);
    accept.addEventListener("click", function () { save("accept"); });
    reject.addEventListener("click", function () { save("reject"); });
    if (open) open.addEventListener("click", function () {
      show();
      placeBanner();
      if (compactViewport.matches) {
        banner.scrollIntoView({ block: "start", behavior: "smooth" });
        accept.focus({ preventScroll: true });
      }
    });
  }());
}());

