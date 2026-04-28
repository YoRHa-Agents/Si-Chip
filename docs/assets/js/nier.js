(function () {
  var STORAGE_THEME = "si-chip-theme";
  var STORAGE_LANG  = "si-chip-lang";

  function getInitialTheme() {
    try {
      var saved = window.localStorage.getItem(STORAGE_THEME);
      if (saved === "day" || saved === "night") return saved;
    } catch (e) { /* localStorage may be blocked */ }
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "night";
    }
    return "day";
  }

  function getInitialLang() {
    try {
      var saved = window.localStorage.getItem(STORAGE_LANG);
      if (saved === "en" || saved === "zh") return saved;
    } catch (e) { /* localStorage may be blocked */ }
    var nav = (navigator.language || navigator.userLanguage || "en").toLowerCase();
    if (nav.indexOf("zh") === 0) return "zh";
    return "en";
  }

  function applyTheme(theme) {
    document.body.setAttribute("data-theme", theme);
    var t = document.querySelector("[data-toggle-theme]");
    if (t) t.textContent = theme === "night" ? "[ THEME / NIGHT ]" : "[ THEME / DAY ]";
    var f = document.querySelector("[data-footer-theme]");
    if (f) f.textContent = theme === "night" ? "[ THEME: NIGHT ]" : "[ THEME: DAY ]";
    try { window.localStorage.setItem(STORAGE_THEME, theme); } catch (e) { /* ignore */ }
  }

  function applyLang(lang) {
    document.body.setAttribute("data-lang", lang);
    var t = document.querySelector("[data-toggle-lang]");
    if (t) t.textContent = lang === "zh" ? "[ LANG / 中 ]" : "[ LANG / EN ]";
    var f = document.querySelector("[data-footer-lang]");
    if (f) f.textContent = lang === "zh" ? "[ 语言: 中 ]" : "[ LANG: EN ]";
    document.documentElement.setAttribute("lang", lang);
    try {
      var island = document.getElementById("si-chip-i18n");
      if (island) {
        var dict = JSON.parse(island.textContent || "{}");
        var nodes = document.querySelectorAll("[data-i18n]");
        for (var i = 0; i < nodes.length; i++) {
          var key = nodes[i].getAttribute("data-i18n");
          if (dict[lang] && dict[lang][key]) {
            nodes[i].textContent = dict[lang][key];
          }
        }
      }
    } catch (e) {
      if (window.console && console.warn) {
        console.warn("si-chip i18n: failed to apply translations", e);
      }
    }
    try { window.localStorage.setItem(STORAGE_LANG, lang); } catch (e) { /* ignore */ }
  }

  function bindToggles() {
    var themeBtn = document.querySelector("[data-toggle-theme]");
    if (themeBtn) {
      themeBtn.addEventListener("click", function () {
        var current = document.body.getAttribute("data-theme") || "day";
        applyTheme(current === "day" ? "night" : "day");
      });
    }
    var langBtn = document.querySelector("[data-toggle-lang]");
    if (langBtn) {
      langBtn.addEventListener("click", function () {
        var current = document.body.getAttribute("data-lang") || "en";
        applyLang(current === "en" ? "zh" : "en");
      });
    }
  }

  function startCursorBlink() {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var cursor = document.querySelector(".cursor");
    if (!cursor) return;
    setInterval(function () {
      cursor.classList.toggle("blink-off");
    }, 540);
  }

  function init() {
    applyTheme(getInitialTheme());
    applyLang(getInitialLang());
    bindToggles();
    startCursorBlink();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
