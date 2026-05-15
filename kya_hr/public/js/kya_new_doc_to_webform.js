/**
 * KYA — Redirige les boutons "+ Nouveau" du Desk vers les Web Forms publics
 * pour les DocTypes métier KYA (Stock, Achats, Comptabilité).
 *
 * Surfaces interceptées :
 *  - Tuile raccourci d'Espace (workspace shortcut tile, pastille `+`)
 *  - Bouton "Add <DocType>" de la List View
 *  - Bouton "+" de la sidebar / link cards
 *  - Tout appel à `frappe.new_doc(doctype)` côté client
 *
 * Centralise tout via un monkey-patch unique de `frappe.new_doc`.
 */
(function () {
	// DocType -> route web form publique
	const WEBFORM_MAP = {
		"Demande Achat KYA": "/demande-achat/new",
		"Bon Commande KYA": "/bon-commande/new",
		"Appel Offre KYA": "/appel-offre/new",
		"PV Sortie Materiel": "/pv-sortie-materiel/new",
		"PV Entree Materiel": "/pv-entree-materiel/new",
		"Inventaire KYA": "/inventaire-kya/new",
		"Brouillard Caisse": "/brouillard-caisse/new",
		"Etat Recap Cheques": "/etat-recap/new",
		"KYA Compta Import": "/comptabilite-import/new",
		"Permission Sortie Stagiaire": "/permission-sortie-stagiaire/new",
		"Permission Sortie Employe": "/permission-sortie-employe/new",
		"Demande Conge KYA": "/demande-conge/new",
		"Leave Application": "/demande-conge/new",
		"Planning Conge": "/planning-conge/new",
		"Bilan Fin de Stage": "/bilan-fin-de-stage/new",
	};

	const ROUTE_MAP = Object.keys(WEBFORM_MAP).reduce((routes, doctype) => {
		const slug = doctype.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
		routes[slug] = WEBFORM_MAP[doctype];
		routes[encodeURIComponent(doctype).toLowerCase()] = WEBFORM_MAP[doctype];
		return routes;
	}, {});

	function webform_route_from_href(href) {
		if (!href) return null;
		const normalized = href.toLowerCase();
		// Frappe v16 : `/app/<slug>/new` (URL directe) ou `/app/<slug>/new-<slug>-<hash>`
		// (depuis list view "+ Add"). Les 2 patterns doivent être matchés.
		const match = normalized.match(
			/(?:#|\/app\/)form\/([^/?#]+)\/new(?:-[^/?#]*)?(?:[/?#]|$)|\/app\/([^/?#]+)\/new(?:-[^/?#]*)?(?:[/?#]|$)/
		);
		const route_key = match && (match[1] || match[2]);
		return route_key ? ROUTE_MAP[route_key] : null;
	}

	function patch_new_doc() {
		if (!window.frappe || !frappe.new_doc || frappe._kya_new_doc_patched) {
			return Boolean(window.frappe && frappe._kya_new_doc_patched);
		}

		const original_new_doc = frappe.new_doc.bind(frappe);

		frappe.new_doc = function (doctype) {
			const route = WEBFORM_MAP[doctype];
			if (route) {
				window.location.href = route;
				return Promise.resolve();
			}
			return original_new_doc.apply(frappe, arguments);
		};

		frappe._kya_new_doc_patched = true;
		return true;
	}

	document.addEventListener("click", function (event) {
		if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) {
			return;
		}
		const link = event.target.closest && event.target.closest("a[href]");
		if (!link) return;
		const route = webform_route_from_href(link.getAttribute("href"));
		if (route) {
			event.preventDefault();
			window.location.href = route;
		}
	}, true);

	patch_new_doc();
	let attempts = 0;
	const interval = window.setInterval(function () {
		attempts += 1;
		if (patch_new_doc() || attempts >= 40) {
			window.clearInterval(interval);
		}
	}, 250);
})();
