(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }
  var cursor = document.querySelector('.cursor');
  if (!cursor) {
    return;
  }
  setInterval(function () {
    cursor.classList.toggle('blink-off');
  }, 540);
})();
