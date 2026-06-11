"""Pose les Website Route Redirect KYA pour les anciennes routes Frappe v13/v14.

En Frappe v16, les routes /desk/people et /desk/hrms ne sont plus
disponibles (l'UI Desk a ete restructuree). Les anciens bookmarks +
liens dans les emails internes generent des 404 frustrants.

Solution : poser des Website Route Redirect en BD qui redirigent :
- /desk/people -> /app/leaves (workspace HR v16)
- /desk/hrms -> /app/leaves
- /desk/accounts -> /app/invoicing
- /desk/stock -> /app/stock

Ces redirects sont stockes en DB et appliques par le middleware
Frappe avant le 404. Plus fiable qu'editer hooks.website_redirects
(qui necessite restart).

Idempotent. Wrappe dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


KYA_REDIRECTS: list[tuple[str, str]] = [
    ("/desk/people", "/app/leaves"),
    ("/desk/hrms", "/app/leaves"),
    ("/desk/accounts", "/app/invoicing"),
    ("/desk/stock", "/app/stock"),
    ("/desk/buying", "/app/buying"),
    ("/desk/selling", "/app/selling"),
    ("/desk", "/app"),
]


def execute() -> dict:
    """Website Route Redirect est un CHILD table de Website Settings en v16.

    On charge Website Settings, parcourt la table 'route_redirects',
    et ajoute les entrees manquantes (idempotent par source).
    """
    summary = {"added": 0, "updated": 0, "unchanged": 0, "errors": []}

    try:
        ws = frappe.get_doc("Website Settings")
    except Exception as exc:
        summary["skipped"] = f"Website Settings inaccessible : {exc}"
        print(f"[setup_kya_redirects] {summary}")
        return summary

    existing_sources: dict[str, object] = {
        (row.source or "").strip(): row for row in (ws.get("route_redirects") or [])
    }

    changed = False
    for source, target in KYA_REDIRECTS:
        try:
            row = existing_sources.get(source)
            if row is None:
                # Ajouter une ligne enfant
                ws.append("route_redirects", {
                    "source": source,
                    "target": target,
                    "redirect_http_status": 301,
                })
                summary["added"] += 1
                changed = True
            elif row.target != target:
                row.target = target
                row.redirect_http_status = 301
                summary["updated"] += 1
                changed = True
            else:
                summary["unchanged"] += 1
        except Exception as exc:
            summary["errors"].append({"source": source, "error": str(exc)})
            try:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"setup_kya_redirects: {source}",
                )
            except Exception:
                pass

    if changed:
        try:
            ws.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.clear_cache()
        except Exception as exc:
            summary["save_error"] = str(exc)
            try:
                frappe.log_error(frappe.get_traceback(), "setup_kya_redirects: save")
            except Exception:
                pass

    print(f"[setup_kya_redirects] {summary}")
    return summary
