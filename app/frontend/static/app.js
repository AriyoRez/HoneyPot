// Simple live refresh: reload the current view (preserving filters) every 5s
// while the "Live" checkbox is on. Choice persisted in localStorage.
(function () {
  var REFRESH_MS = 5000;
  var box = document.getElementById("autorefresh");
  var stamp = document.getElementById("refreshed");
  var timer = null;

  if (stamp) {
    stamp.textContent = "updated " + new Date().toLocaleTimeString();
  }

  function start() { if (!timer) timer = setInterval(function () { location.reload(); }, REFRESH_MS); }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }

  if (box) {
    var saved = localStorage.getItem("autorefresh");
    if (saved !== null) box.checked = saved === "1";
    box.addEventListener("change", function () {
      localStorage.setItem("autorefresh", box.checked ? "1" : "0");
      box.checked ? start() : stop();
    });
    if (box.checked) start();
  }
})();
