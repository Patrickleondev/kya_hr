/* KYA — briques KPI v2 partagées par les dashboards (design « KYA clair
   modernisé », validé 07/2026) : bandeau « À traiter en priorité »,
   chip de tendance, sparkline SVG et jauge semi-circulaire — sans Chart.js.
   Usage : window.KYAKPI.prio(rootEl, {chips:[{icon,count,label}], href, cta}) etc. */
(function () {
  var CSS = [
    ".kya-prio{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:linear-gradient(100deg,#fef2f2,#fff7ed);",
    "  border:1px solid #fecaca;border-left:6px solid #dc2626;border-radius:14px;padding:11px 16px;margin:14px 0 6px;",
    "  font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;}",
    ".kya-prio .pt{font-weight:800;color:#b42331;font-size:14px;}",
    ".kya-prio .chip{display:inline-flex;align-items:center;gap:6px;background:#fff;border:1px solid #fecaca;",
    "  border-radius:20px;padding:4px 12px;font-size:12.5px;font-weight:700;color:#344054;}",
    ".kya-prio .chip b{font-size:14px;}",
    ".kya-prio .go{margin-left:auto;background:#0d7377;color:#fff !important;border-radius:10px;padding:8px 14px;",
    "  font-size:12.5px;font-weight:700;text-decoration:none;white-space:nowrap;cursor:pointer;border:none;}",
    ".kya-prio.ok{background:#f2faf1;border-color:#cde8c8;border-left-color:#5f9e2b;}",
    ".kya-prio.ok .pt{color:#48781f;}",
    ".kya-trend{display:inline-flex;align-items:center;gap:3px;font-size:11.5px;font-weight:800;",
    "  padding:2px 8px;border-radius:12px;white-space:nowrap;}",
    ".kya-trend.up{background:#dcfce7;color:#166534}.kya-trend.down{background:#fee2e2;color:#991b1b}",
    ".kya-trend.flat{background:#f1f5f9;color:#64748b}",
  ].join("\n");

  function ensureCss() {
    if (document.getElementById("kya-kpi-css")) return;
    var st = document.createElement("style");
    st.id = "kya-kpi-css";
    st.textContent = CSS;
    document.head.appendChild(st);
  }
  function esc(s) {
    return (s == null ? "" : String(s)).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /* Bandeau priorités. opts = {chips:[{icon,count,label}], href, cta, okLabel} —
     seules les puces avec count>0 s'affichent ; 0 partout = variante verte. */
  function prio(root, opts) {
    ensureCss();
    if (!root) return;
    var chips = (opts.chips || []).filter(function (c) { return (c.count || 0) > 0; });
    var el = document.createElement("div");
    el.className = "kya-prio" + (chips.length ? "" : " ok");
    var h = "<span class='pt'>" + (chips.length ? "🔴 À traiter en priorité" : "🟢 Rien d'urgent") + "</span>";
    chips.forEach(function (c) {
      h += "<span class='chip'>" + (c.icon || "•") + " <b>" + c.count + "</b>&nbsp;" + esc(c.label) + "</span>";
    });
    if (!chips.length) h += "<span class='chip'>" + esc(opts.okLabel || "Aucun dossier en attente") + "</span>";
    if (opts.href) h += "<a class='go' href='" + opts.href + "'>" + esc(opts.cta || "Voir →") + "</a>";
    el.innerHTML = h;
    root.appendChild(el);
    return el;
  }

  /* Chip de tendance : delta numérique + suffixe (ex : " / 30 j"). */
  function trend(delta, suffix) {
    ensureCss();
    var s = suffix || "";
    var v = Math.round((delta || 0) * 10) / 10;
    if (v > 0) return "<span class='kya-trend up'>▲ +" + v + s + "</span>";
    if (v < 0) return "<span class='kya-trend down'>▼ " + v + s + "</span>";
    return "<span class='kya-trend flat'>= stable" + s + "</span>";
  }

  /* Sparkline SVG (valeurs centrées sur 0 si négatives présentes). */
  function spark(vals, color, height) {
    if (!vals || vals.length < 2) return "";
    var w = 100, h = height || 26;
    var hasNeg = vals.some(function (v) { return v < 0; });
    var max = Math.max.apply(null, vals.map(Math.abs).concat([1]));
    var pts = vals.map(function (v, i) {
      var y = hasNeg ? (h - 3 - ((v + max) / (2 * max)) * (h - 6))
                     : (h - 3 - (v / max) * (h - 6));
      return (i * (w / (vals.length - 1))).toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    return "<svg viewBox='0 0 " + w + " " + h + "' preserveAspectRatio='none' style='display:block;width:100%;height:" + h + "px'>" +
      (hasNeg ? "<line x1='0' y1='" + h / 2 + "' x2='" + w + "' y2='" + h / 2 + "' stroke='#e2e8f0' stroke-width='1'/>" : "") +
      "<polyline points='" + pts + "' fill='none' stroke='" + (color || "#0d7377") +
      "' stroke-width='2' stroke-linejoin='round' stroke-linecap='round'/></svg>";
  }

  /* Jauge semi-circulaire : pct 0-100, couleur auto par seuils (80/50). */
  function gauge(pct, size) {
    var p = Math.max(0, Math.min(100, pct || 0));
    var color = p >= 80 ? "#16a34a" : (p >= 50 ? "#d97706" : "#dc2626");
    var c = Math.PI * 42, sz = size || 104;
    return "<svg viewBox='0 0 104 60' style='width:" + sz + "px;height:" + Math.round(sz * 60 / 104) + "px;display:block'>" +
      "<path d='M10 55 A 42 42 0 0 1 94 55' fill='none' stroke='#e2e8f0' stroke-width='10' stroke-linecap='round'/>" +
      "<path d='M10 55 A 42 42 0 0 1 94 55' fill='none' stroke='" + color + "' stroke-width='10' stroke-linecap='round'" +
      " stroke-dasharray='" + (p / 100 * c).toFixed(1) + " " + c.toFixed(1) + "'/></svg>";
  }

  window.KYAKPI = { prio: prio, trend: trend, spark: spark, gauge: gauge };
})();
