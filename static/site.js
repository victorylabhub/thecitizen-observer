(function () {
  // Sections drawer
  var b = document.querySelector(".burger"), d = document.getElementById("drawer");
  if (b && d) b.addEventListener("click", function () {
    var open = b.getAttribute("aria-expanded") === "true";
    b.setAttribute("aria-expanded", String(!open)); d.hidden = open;
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && d && !d.hidden) { d.hidden = true; b.setAttribute("aria-expanded", "false"); b.focus(); }
  });

  // Election countdown (days, computed in the reader's browser)
  document.querySelectorAll("[data-countdown]").forEach(function (el) {
    var p = el.dataset.countdown.split("-"), e = new Date(+p[0], +p[1] - 1, +p[2]);
    var n = new Date(); n.setHours(0, 0, 0, 0);
    el.textContent = Math.max(0, Math.round((e - n) / 86400000));
  });

  // Hub tabs
  var tabs = document.querySelectorAll('[role="tab"]');
  function sel(t) {
    tabs.forEach(function (x) {
      var on = x === t; x.setAttribute("aria-selected", on); x.tabIndex = on ? 0 : -1;
      document.getElementById(x.getAttribute("aria-controls")).hidden = !on;
    });
    t.focus();
  }
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { sel(t); });
    t.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        sel(tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length]);
      }
    });
  });

  // Search (runs locally; nothing is sent anywhere)
  var q = document.getElementById("q");
  if (q) {
    var list = document.getElementById("results"), st = document.getElementById("search-status"), idx = [];
    var norm = function (s) { return (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); };
    var esc = function (s) { var e = document.createElement("span"); e.textContent = s; return e.innerHTML; };
    var run = function () {
      var v = norm(q.value.trim()); list.innerHTML = "";
      if (!v) { st.textContent = ""; return; }
      var terms = v.split(/\s+/);
      var hits = idx.filter(function (a) { var h = norm(a.t + " " + a.d + " " + a.s); return terms.every(function (t) { return h.indexOf(t) > -1; }); });
      st.textContent = hits.length + (hits.length === 1 ? " result" : " results");
      list.innerHTML = hits.slice(0, 50).map(function (a) {
        return '<li><a href="' + a.u + '">' + esc(a.t) + '</a><p>' + esc(a.s) + " · " + esc(a.dt) + (a.d ? " — " + esc(a.d) : "") + "</p></li>";
      }).join("");
    };
    fetch("/search.json").then(function (r) { return r.json(); }).then(function (j) {
      idx = j; var u = new URLSearchParams(location.search).get("q"); if (u) q.value = u; run();
    });
    q.addEventListener("input", run);
  }
})();
