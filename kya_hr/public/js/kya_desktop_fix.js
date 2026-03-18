/**
 * KYA Desktop Icon Fix v4
 * Supprime l'erreur "Icon is not correctly configured" sur les icônes HRMS.
 * Couches: msgprint + throw + dialog + workspace click interception
 */
(function () {
	"use strict";

	var ICON_ERROR_PATTERNS = [
		"Icon is not correctly configured",
		"not correctly configured",
		"pas correctement configur",
		"icône n'est pas",
		"icon_link",
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
				text = msg.message || msg.title || msg.indicator || "";
			}
			if (isIconError(text)) {
				console.log("[KYA] Suppressed icon config error (msgprint)");
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

	// Try immediately, then on DOMContentLoaded, frappe.ready
	applyAllPatches();
	document.addEventListener("DOMContentLoaded", function () {
		applyAllPatches();
	});

	// === Layer 2: Fix desktop icons after page renders ===
	function fixDesktopIcons() {
		// Find all desktop icon anchors that have click handlers but no href
		var icons = document.querySelectorAll(".desk-sidebar .sidebar-item, .desktop-icon-grid .app-icon, .desk-page .app-icon");
		icons.forEach(function (el) {
			var anchor = el.tagName === "A" ? el : el.querySelector("a");
			if (!anchor) return;
			var href = anchor.getAttribute("href");
			if (!href || href === "#" || href === "javascript:void(0)") {
				// Try to extract workspace name from icon data or label
				var label = el.getAttribute("data-name") ||
					el.querySelector(".icon-label, .ellipsis")?.textContent?.trim() || "";
				if (label) {
					var slug = label.toLowerCase()
						.replace(/[éèê]/g, "e")
						.replace(/[àâ]/g, "a")
						.replace(/[ùû]/g, "u")
						.replace(/[ôö]/g, "o")
						.replace(/[ç]/g, "c")
						.replace(/&/g, "-")
						.replace(/\s+/g, "-")
						.replace(/-+/g, "-")
						.replace(/^-|-$/g, "");
					anchor.setAttribute("href", "/desk/" + slug);
					// Remove any click handlers that would show the error
					var newAnchor = anchor.cloneNode(true);
					anchor.parentNode.replaceChild(newAnchor, anchor);
					console.log("[KYA] Fixed icon route: " + label + " -> /desk/" + slug);
				}
			}
		});
	}

	// === Layer 3: Patch frappe desktop_icons array after page load ===
	function patchDesktopIconObjects() {
		if (!frappe.desktop_icons_objects || !frappe.desktop_icons_objects.length) return;
		frappe.desktop_icons_objects.forEach(function (iconObj) {
			if (!iconObj.icon_route && iconObj.icon_data) {
				var data = iconObj.icon_data;
				var label = data.label || data.name || "";
				if (label) {
					var slug = label.toLowerCase()
						.replace(/[éèê]/g, "e")
						.replace(/[àâ]/g, "a")
						.replace(/[ùû]/g, "u")
						.replace(/[ôö]/g, "o")
						.replace(/[ç]/g, "c")
						.replace(/&/g, "-")
						.replace(/\s+/g, "-")
						.replace(/-+/g, "-")
						.replace(/^-|-$/g, "");
					iconObj.icon_route = "/desk/" + slug;
					if (iconObj.icon) {
						iconObj.icon.attr("href", "/desk/" + slug);
						// Remove click handler that shows error by cloning
						var oldIcon = iconObj.icon[0];
						if (oldIcon) {
							var newIcon = oldIcon.cloneNode(true);
							oldIcon.parentNode.replaceChild(newIcon, oldIcon);
							iconObj.icon = $(newIcon);
						}
					}
					console.log("[KYA] Patched icon object: " + label + " -> /desk/" + slug);
				}
			}
		});
	}

	// Hook into frappe page-change events
	$(document).ready(function () {
		patchMsgprint();

		// Run fixes after page renders
		function runFixes() {
			setTimeout(function () {
				fixDesktopIcons();
				patchDesktopIconObjects();
			}, 500);
			setTimeout(function () {
				fixDesktopIcons();
				patchDesktopIconObjects();
			}, 1500);
		}

		// On initial load
		if (frappe.after_ajax) {
			frappe.after_ajax(runFixes);
		}
		runFixes();

		// On route changes (SPA navigation)
		if (frappe.router && frappe.router.on) {
			frappe.router.on("change", runFixes);
		}

		// MutationObserver as ultimate fallback
		var observer = new MutationObserver(function (mutations) {
			var hasDesktop = false;
			mutations.forEach(function (m) {
				if (m.addedNodes.length) {
					m.addedNodes.forEach(function (node) {
						if (node.classList &&
							(node.classList.contains("app-icon") ||
								node.classList.contains("desktop-icon-grid"))) {
							hasDesktop = true;
						}
					});
				}
			});
			if (hasDesktop) {
				setTimeout(fixDesktopIcons, 200);
			}
		});
		observer.observe(document.body, { childList: true, subtree: true });
	});
})();
