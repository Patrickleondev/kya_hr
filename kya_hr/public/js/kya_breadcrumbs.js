/* Espace affiché : celui du document ouvert, pas le dernier espace visité.
 *
 * Symptôme : en ouvrant « Salarié KYA » ou « Évolution Carrière KYA » après un
 * passage par l'Espace Stagiaires, la barre latérale ET le fil d'Ariane
 * restaient sur « Espace Stagiaires ». On croit s'être trompé d'endroit, et
 * les liens proposés à gauche (Stagiaires, Présences…) n'ont rien à voir avec
 * la fiche affichée.
 *
 * Cause réelle (Frappe v16, ui/sidebar/sidebar.js → set_workspace_sidebar) :
 * Frappe cherche l'espace cible via `get_workspace_sidebars(doctype)`, qui
 * parcourt les ITEMS de barre latérale. Nos doctypes ne sont déclarés que par
 * des « Workspace Link », pas par des items de barre latérale : la recherche
 * renvoie [] et Frappe conserve donc l'espace courant. Le fil d'Ariane, lui,
 * ne fait que recopier `frappe.app.sidebar.sidebar_title` (breadcrumbs.js →
 * set_workspace_breadcrumb) — corriger la barre latérale corrige les deux.
 *
 * Correctif GÉNÉRIQUE, sans liste de doctypes en dur : la métadonnée
 * `__workspaces` connaît, elle, le bon espace. Si un doctype n'appartient
 * qu'à UN espace, on bascule dessus. S'il en a plusieurs, on ne touche à
 * rien : le comportement « dernier espace visité » de Frappe est alors
 * légitime.
 */
(function () {
	"use strict";

	var VUES = ["List", "Form", "Report", "Dashboard", "print"];

	function espaceUnique(doctype) {
		try {
			var meta = frappe.get_meta(doctype);
			var ws = meta && meta.__workspaces;
			return ws && ws.length === 1 ? ws[0] : null;
		} catch (e) {
			return null;
		}
	}

	function corriger() {
		try {
			var sb = frappe.app && frappe.app.sidebar;
			if (!sb || typeof sb.setup !== "function") return;

			var route = frappe.get_route() || [];
			if (route.length < 2 || VUES.indexOf(route[0]) === -1) return;

			var doctype = route[1];
			// Frappe sait déjà résoudre ce doctype : ne pas s'en mêler.
			if (sb.get_workspace_sidebars && sb.get_workspace_sidebars(doctype).length) return;

			var cible = espaceUnique(doctype);
			if (!cible || cible === sb.sidebar_title) return;

			// L'espace doit exister comme barre latérale, sinon setup() échoue.
			var connus = frappe.boot.workspace_sidebar_item || {};
			if (!connus[String(cible).toLowerCase()]) return;

			sb.setup(cible);

			// Le fil d'Ariane est calculé UNE fois au chargement et recopie
			// `sidebar_title` : sans ce rafraîchissement il continuerait
			// d'afficher l'ancien espace alors que la barre latérale a changé.
			if (frappe.breadcrumbs && typeof frappe.breadcrumbs.update === "function") {
				frappe.breadcrumbs.update();
			}
		} catch (e) {
			/* jamais bloquer la navigation pour un fil d'Ariane */
		}
	}

	function brancher() {
		if (!window.frappe || !frappe.router || frappe.__kya_sidebar_route) return false;
		frappe.router.on("change", function () {
			setTimeout(corriger, 120);
		});
		frappe.__kya_sidebar_route = true;
		setTimeout(corriger, 400);
		return true;
	}

	if (!brancher()) {
		var essais = 0;
		var minuteur = setInterval(function () {
			if (brancher() || ++essais > 40) clearInterval(minuteur);
		}, 250);
	}
})();
