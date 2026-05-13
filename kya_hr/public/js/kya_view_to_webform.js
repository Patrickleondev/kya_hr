/**
 * KYA — Redirige la vue "fiche desk" (form view d'un enregistrement existant)
 * vers le web form public correspondant.
 *
 * Complémentaire à kya_new_doc_to_webform.js (qui couvre "+ Nouveau" / /new).
 *
 * Surfaces interceptées :
 *  - Liens vers /app/<doctype-slug>/<docname> (listes, notifs, dashboards, etc.)
 *  - Routes hash legacy #Form/<DocType>/<docname>
 *  - Chargement direct du desk sur /app/<doctype-slug>/<docname> (URL bar / refresh)
 *  - Navigation SPA via pushState / replaceState
 *
 * Bypass : Ctrl / Cmd / Shift / Alt + clic préservent le comportement natif
 * (utile pour les admins qui veulent ouvrir la fiche desk dans un onglet).
 */
(function () {
  // DocType slug (lowercase, hyphens) -> Web Form route (sans slash initial, sans /new)
  const WEBFORM_VIEW_MAP = {
    "demande-achat-kya": "demande-achat",
    "bon-commande-kya": "bon-commande",
    "appel-offre-kya": "appel-offre",
    "pv-sortie-materiel": "pv-sortie-materiel",
    "pv-entree-materiel": "pv-entree-materiel",
    "inventaire-kya": "inventaire-kya",
    "brouillard-caisse": "brouillard-caisse",
    "etat-recap-cheques": "etat-recap",
    "kya-compta-import": "comptabilite-import",
    "permission-sortie-stagiaire": "permission-sortie-stagiaire",
    "permission-sortie-employe": "permission-sortie-employe",
    "demande-conge-kya": "demande-conge",
    "leave-application": "demande-conge",
    "planning-conge": "planning-conge",
    "bilan-fin-de-stage": "bilan-fin-de-stage",
  };

  // Segments réservés Frappe qui ne sont pas des noms de document
  const RESERVED = new Set([
    "new", "view", "list", "tree", "calendar", "report",
    "kanban", "dashboard", "gantt", "report-view", "image"
  ]);

  function build_target(href) {
    if (!href || typeof href !== "string") return null;

    let slug = null;
    let docname = null;

    // 1. Path style : /app/<slug>/<docname>[?query][#hash]
    const path_match = href.match(/\/app\/([^/?#]+)\/([^/?#]+)(?:[/?#].*)?$/);
    if (path_match) {
      slug = path_match[1].toLowerCase();
      docname = path_match[2];
    } else {
      // 2. Hash style : #Form/<DocType>/<docname>
      const hash_match = href.match(/#[Ff]orm\/([^/?#]+)\/([^/?#]+)/);
      if (hash_match) {
        slug = hash_match[1]
          .toLowerCase()
          .replace(/%20/g, "-")
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-|-$/g, "");
        docname = hash_match[2];
      }
    }

    if (!slug || !docname) return null;
    if (RESERVED.has(docname.toLowerCase())) return null;

    const route = WEBFORM_VIEW_MAP[slug];
    if (!route) return null;

    let decoded;
    try { decoded = decodeURIComponent(docname); } catch (e) { decoded = docname; }
    return "/" + route + "/" + encodeURIComponent(decoded);
  }

  function already_on_target(target) {
    if (!target) return true;
    const current = (window.location.pathname || "").replace(/\/+$/, "");
    const want = target.replace(/\/+$/, "");
    return current.toLowerCase() === want.toLowerCase();
  }

  function check_current_url() {
    const here = window.location.pathname + window.location.search + window.location.hash;
    const target = build_target(here);
    if (!target || already_on_target(target)) return;
    window.location.replace(target);
  }

  // ── Clic sur lien ───────────────────────────────────────────────────
  document.addEventListener("click", function (event) {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest && event.target.closest("a[href]");
    if (!link) return;
    const target = build_target(link.getAttribute("href"));
    if (!target) return;
    event.preventDefault();
    window.location.href = target;
  }, true);

  // ── Chargement direct ───────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", check_current_url);
  } else {
    check_current_url();
  }

  // ── Navigation SPA (hashchange + pushState/replaceState) ────────────
  window.addEventListener("hashchange", check_current_url);
  window.addEventListener("popstate", check_current_url);

  ["pushState", "replaceState"].forEach(function (method) {
    const orig = history[method];
    if (!orig || orig._kya_view_patched) return;
    const wrapped = function () {
      const ret = orig.apply(this, arguments);
      setTimeout(check_current_url, 0);
      return ret;
    };
    wrapped._kya_view_patched = true;
    history[method] = wrapped;
  });

  // Listener Frappe router si dispo (utile sur les premiers chargements desk)
  function hook_frappe_router() {
    if (window.frappe && frappe.router && typeof frappe.router.on === "function" && !frappe.router._kya_view_hooked) {
      try {
        frappe.router.on("change", check_current_url);
        frappe.router._kya_view_hooked = true;
        return true;
      } catch (e) { /* noop */ }
    }
    return false;
  }
  if (!hook_frappe_router()) {
    let attempts = 0;
    const itv = window.setInterval(function () {
      attempts += 1;
      if (hook_frappe_router() || attempts >= 40) {
        window.clearInterval(itv);
      }
    }, 250);
  }
})();
