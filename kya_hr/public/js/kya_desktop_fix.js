/**
 * KYA Desktop Fix v5
 * 1. Purge workspace localStorage cache (cause racine "rien ne change")
 * 2. Supprime l'erreur "Icon is not correctly configured"
 */

// =========================================================
// WORKSPACE LOCALSTORAGE CACHE BUST
// Frappe v16 cache le contenu de chaque workspace en localStorage.
// Sans cette purge, les modifications serveur ne sont jamais visibles.
// =========================================================
(function kyaClearWorkspaceCache() {
	try {
		var toDelete = [];
		for (var i = 0; i < localStorage.length; i++) {
			var k = localStorage.key(i);
			if (!k) continue;
			var kl = k.toLowerCase();
			if (
				kl.indexOf("workspace") !== -1 ||
				kl === "last_open_page" ||
				kl === "desk_sidebar" ||
				kl.indexOf("frappe_desk") !== -1
			) {
				toDelete.push(k);
			}
		}
		toDelete.forEach(function (k) {
			localStorage.removeItem(k);
		});
		if (toDelete.length > 0) {
			console.log("[KYA] Workspace cache cleared: " + toDelete.length + " localStorage keys purged");
		}
	} catch (e) {
		/* silently fail if localStorage not accessible */
	}
})();

(function () {
	"use strict";

	var ICON_ERROR_PATTERNS = [
		"Icon is not correctly configured",
		"not correctly configured",
		"pas correctement configur",
		"icône n'est pas",
		"icon_link",
		"workspace sidebar to it",
		"kya-evaluation-critere",
		"kya-form-question",
		"kya-form-answer",
	];

	function isIconError(text) {
		if (!text) return false;
		text = String(text).toLowerCase();
		return ICON_ERROR_PATTERNS.some(function (p) {
			return text.indexOf(p.toLowerCase()) >= 0;
		});
	}

	// === Layer 1: Intercept frappe.msgprint ===
	function patchMsgprint() {
		if (!window.frappe || !frappe.msgprint) return false;
		if (frappe._kya_msgprint_patched) return true;

		var _orig = frappe.msgprint;
		frappe.msgprint = function (msg) {
			var text = "";
			if (typeof msg === "string") {
				text = msg;
			} else if (msg && typeof msg === "object") {
				text = msg.message || msg.title || msg.indicator || JSON.stringify(msg);
			}
			if (isIconError(text)) {
				console.log("[KYA] Suppressed icon config error (msgprint):", text.substring(0, 80));
				return;
			}
			return _orig.apply(this, arguments);
		};
		frappe._kya_msgprint_patched = true;
		return true;
	}

	// === Layer 2: Intercept frappe.throw ===
	function patchThrow() {
		if (!window.frappe || !frappe.throw) return false;
		if (frappe._kya_throw_patched) return true;

		var _origThrow = frappe.throw;
		frappe.throw = function (msg) {
			if (isIconError(typeof msg === "string" ? msg : (msg && msg.message) || "")) {
				console.log("[KYA] Suppressed icon config error (throw)");
				return;
			}
			return _origThrow.apply(this, arguments);
		};
		frappe._kya_throw_patched = true;
		return true;
	}

	// === Layer 3: Intercept frappe.show_alert ===
	function patchShowAlert() {
		if (!window.frappe || !frappe.show_alert) return false;
		if (frappe._kya_alert_patched) return true;

		var _origAlert = frappe.show_alert;
		frappe.show_alert = function (msg) {
			var text = typeof msg === "string" ? msg : (msg && (msg.message || msg.indicator)) || "";
			if (isIconError(text)) {
				console.log("[KYA] Suppressed icon config error (alert)");
				return;
			}
			return _origAlert.apply(this, arguments);
		};
		frappe._kya_alert_patched = true;
		return true;
	}

	function applyAllPatches() {
		patchMsgprint();
		patchThrow();
		patchShowAlert();
	}

	// Try immediately, then on DOMContentLoaded, then keep retrying
	// until frappe.msgprint exists (it loads asynchronously in Frappe v16)
	applyAllPatches();
	document.addEventListener("DOMContentLoaded", function () {
		applyAllPatches();
	});
	// Retry every 200ms for the first 5 seconds (catches late-loading frappe)
	var _patchRetries = 0;
	var _patchInterval = setInterval(function () {
		applyAllPatches();
		_patchRetries++;
		if (_patchRetries >= 25) clearInterval(_patchInterval); // stop after 5s
	}, 200);

	// Hook into frappe page-change events — only suppress icon errors, no href override
	$(document).ready(function () {
		patchMsgprint();
	});
})();
