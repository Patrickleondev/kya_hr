/**
 * KYA Desktop Icon Fix v3
 * Multi-layer approach to prevent "Icon is not correctly configured" error:
 * 1. Intercept frappe.msgprint early to suppress the error message
 * 2. Patch desktop page render to fix icons with missing routes
 * 3. MutationObserver fallback to catch dynamically rendered icons
 */
(function () {
	"use strict";

	// === Layer 1: Intercept frappe.msgprint ===
	function patchMsgprint() {
		if (!frappe || !frappe.msgprint) return false;
		if (frappe._kya_msgprint_patched) return true;

		var _orig = frappe.msgprint;
		frappe.msgprint = function (msg) {
			var text = "";
			if (typeof msg === "string") {
				text = msg;
			} else if (msg && typeof msg === "object") {
				text = msg.message || msg.title || msg.indicator || "";
			}
			if (
				text.indexOf("Icon is not correctly configured") >= 0 ||
				text.indexOf("not correctly configured") >= 0 ||
				text.indexOf("pas correctement configur") >= 0
			) {
				console.log("[KYA] Suppressed icon config error");
				return;
			}
			return _orig.apply(this, arguments);
		};
		frappe._kya_msgprint_patched = true;
		return true;
	}

	// Try patching immediately
	patchMsgprint();

	// Also patch on DOMContentLoaded (in case frappe wasn't ready)
	document.addEventListener("DOMContentLoaded", function () {
		patchMsgprint();
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
