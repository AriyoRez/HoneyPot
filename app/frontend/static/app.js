// Live refresh: reload the current view (preserving filters) every 5s while Live
// is on. State persists in localStorage and is reflected in the status cluster.
(function () {
  var REFRESH_MS = 5000;
  var dot = document.getElementById("liveDot");
  var text = document.getElementById("liveText");
  var btn = document.getElementById("pauseBtn");
  var timer = null;

  function stamp() {
    return new Date().toLocaleTimeString([], { hour12: false });
  }

  function render(live) {
    if (!dot || !text || !btn) return;
    if (live) {
      dot.className = "dot dot-live";
      text.textContent = "Live · " + stamp();
      btn.textContent = "Pause";
    } else {
      dot.className = "dot dot-paused";
      text.textContent = "Paused · " + stamp();
      btn.textContent = "Resume";
    }
  }

  function start() { if (!timer) timer = setInterval(function () { location.reload(); }, REFRESH_MS); }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }

  var live = localStorage.getItem("live") !== "0";
  render(live);
  if (live) start();

  if (btn) {
    btn.addEventListener("click", function () {
      live = !live;
      localStorage.setItem("live", live ? "1" : "0");
      render(live);
      live ? start() : stop();
    });
  }
})();
