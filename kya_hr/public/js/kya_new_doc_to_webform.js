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
	if (!window.frappe || !frappe.new_doc) {
		return;
	}
	if (frappe._kya_new_doc_patched) {
		return;
	}

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
		"Permission Sortie Stagiaire": "/permission-sortie-stagiaire/new",
		"Permission Sortie Employe": "/permission-sortie-employe/new",
		"Demande Conge KYA": "/demande-conge/new",
		"Planning Conge": "/planning-conge/new",
		"Bilan Fin De Stage": "/bilan-fin-de-stage/new",
	};

	const ORIGINAL_NEW_DOC = frappe.new_doc.bind(frappe);

	frappe.new_doc = function (doctype) {
		const route = WEBFORM_MAP[doctype];
		if (route) {
			// Système Manager / Admin gardent l'accès Desk via Shift+clic / URL directe.
			window.location.href = route;
			return Promise.resolve();
		}
		return ORIGINAL_NEW_DOC.apply(frappe, arguments);
	};

	frappe._kya_new_doc_patched = true;
})();
