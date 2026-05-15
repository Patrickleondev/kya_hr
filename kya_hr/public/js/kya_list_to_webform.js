/*
 * Force le bouton "+ Ajouter ..." (depuis list view) ET la route /app/{doctype}/new
 * (accès direct via URL, Quick New, etc.) à ouvrir le Web Form KYA brandé
 * au lieu du Desk Form standard.
 *
 * Bypass via querystring ?desk=1 pour les développeurs/admins qui ont besoin
 * d'éditer dans le Desk Form (debug, modifications spéciales).
 */
(function () {
  if (!window.frappe) return;

  // Mapping DocType -> route web form KYA (sans le /new final)
  var WEBFORM_ROUTES = {
    "Permission Sortie Employe": "permission-sortie-employe",
    "Permission Sortie Stagiaire": "permission-sortie-stagiaire",
    "Planning Conge": "planning-conge",
    "Leave Application": "demande-conge",
    "Demande Achat KYA": "demande-achat",
    "PV Sortie Materiel": "pv-sortie-materiel",
    "PV Entree Materiel": "pv-entree-materiel",
    "Bon Commande KYA": "bon-commande",
    "Appel Offre KYA": "appel-offre",
    "Bilan Fin de Stage": "bilan-fin-de-stage",
    "Brouillard Caisse": "brouillard-caisse",
    "Etat Recap Cheques": "etat-recap",
    "Inventaire KYA": "inventaire-kya"
  };

  // Permet aux dev/admin de bypasser via ?desk=1 dans l'URL si besoin de debug
  function bypassRequested() {
    try {
      var params = new URLSearchParams(window.location.search);
      return params.get("desk") === "1";
    } catch (e) { return false; }
  }

  /* ─── 1. Intercepte la route /app/{doctype}/new (couvre Quick New, URL directe,
        breadcrumb "Nouveau", etc.) ─────────────────────────────────────── */
  function maybeRedirectFromRoute(route) {
    if (!route || route.length < 3) return;
    var routeType = route[0];
    if (routeType !== "Form" && routeType !== "form") return;
    // Frappe v16 utilise soit "new" exact (URL directe `/app/<slug>/new`), soit
    // "new-<doctype-slug>-<hash>" pour les documents pas encore sauvegardés
    // (clic "+ Add" depuis list view). Les 2 doivent être interceptés.
    var thirdSeg = route[2] || "";
    if (thirdSeg !== "new" && thirdSeg.indexOf("new-") !== 0) return;
    if (bypassRequested()) return;

    // Le route[1] est le doctype slug (en kebab-case). Frappe garde aussi
    // le doctype original sur frappe.get_route_str() / current_form context.
    var doctypeSlug = route[1];
    // Reverse mapping slug -> proper name
    for (var dt in WEBFORM_ROUTES) {
      if (!Object.prototype.hasOwnProperty.call(WEBFORM_ROUTES, dt)) continue;
      var slug = dt.toLowerCase().replace(/\s+/g, "-");
      if (slug === doctypeSlug) {
        window.location.href = "/" + WEBFORM_ROUTES[dt] + "/new";
        return;
      }
    }
  }

  function installRouteHook() {
    if (!frappe.router || !frappe.router.on) {
      // Frappe.router pas encore prêt — retry
      setTimeout(installRouteHook, 200);
      return;
    }
    frappe.router.on("change", function () {
      try { maybeRedirectFromRoute(frappe.get_route()); } catch (e) {}
    });
    // Premier check au chargement initial
    setTimeout(function () {
      try { maybeRedirectFromRoute(frappe.get_route()); } catch (e) {}
    }, 100);
  }

  /* ─── 2. Override aussi le bouton "+" des list views (filet de sécurité,
        et garde une UX claire avec le label "Nouveau (formulaire web)") ── */
  function installListViewRedirect(doctype, webformRoute) {
    if (!frappe.listview_settings) frappe.listview_settings = {};
    var existing = frappe.listview_settings[doctype] || {};
    var previousOnload = existing.onload;

    frappe.listview_settings[doctype] = Object.assign({}, existing, {
      onload: function (listview) {
        if (typeof previousOnload === "function") {
          previousOnload.call(this, listview);
        }
        if (bypassRequested()) return;
        if (listview.page && listview.page.set_primary_action) {
          listview.page.set_primary_action(
            "+ Nouveau (formulaire web)",
            function () { window.location.href = "/" + webformRoute + "/new"; },
            "octicon octicon-plus"
          );
        }
      }
    });
  }

  Object.keys(WEBFORM_ROUTES).forEach(function (dt) {
    installListViewRedirect(dt, WEBFORM_ROUTES[dt]);
  });

  installRouteHook();
})();
