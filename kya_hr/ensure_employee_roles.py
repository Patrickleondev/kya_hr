"""Garantit que tout User lie a un Employee actif possede les roles necessaires.

Bug observe en prod : des employes (et stagiaires) connectes n'avaient aucun
role 'metier', meme pas 'Employee'. Resultat : ils ne pouvaient pas
soumettre de demandes (workflow.allowed=Employee), ne voyaient aucun
workspace (workspace.roles ne contenait pas 'All Users'), et ne pouvaient
pas signer leur propres documents au palier Brouillon.

Cette fonction tourne en after_migrate (cf hooks.after_migrate
-> safe_migrations.AFTER_MIGRATE). Elle est idempotente et silencieuse.

Pour la re-jouer a la main :
    bench --site frontend execute kya_hr.ensure_employee_roles.execute
"""
from __future__ import annotations

import frappe


def _ensure_role_on_user(user: str, role: str) -> bool:
    """Ajoute `role` a `user` si absent. Retourne True si ajoute."""
    if not user or not role:
        return False
    if user in ("Administrator", "Guest"):
        return False
    if not frappe.db.exists("User", user):
        return False
    if not frappe.db.exists("Role", role):
        return False
    if frappe.db.exists(
        "Has Role",
        {"parent": user, "parenttype": "User", "role": role},
    ):
        return False
    try:
        frappe.get_doc({
            "doctype": "Has Role",
            "parent": user,
            "parenttype": "User",
            "parentfield": "roles",
            "role": role,
        }).insert(ignore_permissions=True, ignore_if_duplicate=True)
        return True
    except Exception as exc:
        # Duplicate race conditions etc. - silencieux
        if "Duplicate" not in str(exc):
            try:
                frappe.log_error(frappe.get_traceback(), f"ensure_employee_roles {user}/{role}")
            except Exception:
                pass
        return False


def execute():
    """Assure rôles Employee + Stagiaire aux Users liés à Employee actif."""
    result = {"employee_added": 0, "stagiaire_added": 0, "scanned": 0}

    try:
        employees = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            fields=["name", "user_id", "employment_type"],
        )
    except Exception as exc:
        try:
            frappe.log_error(str(exc), "ensure_employee_roles: list Employee failed")
        except Exception:
            pass
        return result

    for emp in employees:
        user = emp.get("user_id")
        if not user:
            continue
        result["scanned"] += 1

        # Tout employe actif (CDI/CDD/Stage/Prestataire) doit avoir 'Employee'.
        if _ensure_role_on_user(user, "Employee"):
            result["employee_added"] += 1

        # Stagiaire en plus si employment_type = Stage.
        if (emp.get("employment_type") or "") == "Stage":
            if _ensure_role_on_user(user, "Stagiaire"):
                result["stagiaire_added"] += 1

    try:
        frappe.db.commit()
    except Exception:
        pass
    print(f"[ensure_employee_roles] scanned={result['scanned']} "
          f"employee_added={result['employee_added']} "
          f"stagiaire_added={result['stagiaire_added']}")
    return result
