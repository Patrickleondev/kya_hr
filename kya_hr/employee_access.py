# -*- coding: utf-8 -*-
"""Garantit qu'un employé connecté VOIT bien son « Espace Employés ».

Deux causes empêchaient l'affichage de l'Espace Employés (module « KYA HR ») :

1. Rôle manquant — le User lié à l'Employee n'avait pas le rôle « Employee »
   (le sync ne se déclenche qu'au save de l'Employee AVEC user_id).
2. **Module bloqué** — le User avait « KYA HR » (et souvent « HR », « Desk »…)
   dans ses *Block Modules*. Or `get_workspace_sidebar_items` filtre les
   workspaces avec `module NOT IN blocked_modules` : un employé qui bloque
   « KYA HR » ne voit AUCUN espace KYA, donc pas d'« Espace Employés » ni de
   lien « Mon Espace ». C'était la cause principale en prod (comptes créés en
   masse avec une longue liste de modules bloqués).

Correctif idempotent : pose le rôle « Employee » (+ « Stagiaire » si Stage) et
débloque les modules KYA indispensables. Appelé :
- à chaque login (self-heal, cf. link_employees_users.on_session_creation) ;
- en batch (after_migrate + exécution manuelle) via execute().
"""
from __future__ import annotations

import frappe

# Modules à NE JAMAIS laisser bloqués pour un employé (sinon ses espaces KYA
# et son self-service RH disparaissent de la barre latérale).
_MUST_SEE_MODULES = ("KYA HR", "HR")


def _add_role(user: str, role: str) -> bool:
    if user in ("Administrator", "Guest") or not frappe.db.exists("Role", role):
        return False
    if frappe.db.exists("Has Role", {"parent": user, "parenttype": "User", "role": role}):
        return False
    try:
        frappe.get_doc({
            "doctype": "Has Role", "parent": user, "parenttype": "User",
            "parentfield": "roles", "role": role,
        }).insert(ignore_permissions=True, ignore_if_duplicate=True)
        return True
    except Exception as exc:
        if "Duplicate" not in str(exc):
            frappe.log_error(frappe.get_traceback(), f"employee_access role {user}/{role}")
        return False


def _unblock_modules(user: str) -> list:
    """Retire les modules KYA indispensables de la liste Block Module du User.

    Block Module est une table enfant → on la purge par SQL direct
    (frappe.db.delete), car delete_doc sur une ligne enfant ne persiste pas."""
    unblocked = []
    for module in _MUST_SEE_MODULES:
        if frappe.db.exists("Block Module",
                            {"parent": user, "parenttype": "User", "module": module}):
            frappe.db.delete("Block Module",
                             {"parent": user, "parenttype": "User", "module": module})
            unblocked.append(module)
    return unblocked


def ensure_access_for_user(user: str) -> dict:
    """Pose rôle Employee (+Stagiaire) et débloque KYA HR/HR pour `user` s'il
    est lié à un Employee actif. Idempotent, silencieux."""
    out = {"role_added": [], "modules_unblocked": []}
    try:
        if not user or user in ("Administrator", "Guest"):
            return out
        emp = frappe.db.get_value(
            "Employee", {"user_id": user, "status": "Active"},
            ["name", "employment_type"], as_dict=True,
        )
        if not emp:
            return out

        if _add_role(user, "Employee"):
            out["role_added"].append("Employee")
        if (emp.employment_type or "").strip() == "Stage":
            if _add_role(user, "Stagiaire"):
                out["role_added"].append("Stagiaire")

        out["modules_unblocked"] = _unblock_modules(user)

        if out["role_added"] or out["modules_unblocked"]:
            # clear_document_cache est indispensable : get_workspace_sidebar_items
            # lit les Block Modules via get_cached_doc("User"), que clear_cache
            # (user=…) seul n'invalide PAS.
            frappe.clear_document_cache("User", user)
            frappe.clear_cache(user=user)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"ensure_access_for_user {user}")
    return out


def execute() -> dict:
    """Batch : applique ensure_access_for_user à tous les employés actifs liés.
    Pour after_migrate et exécution manuelle sur prod."""
    res = {"scanned": 0, "roles_added": 0, "modules_unblocked": 0, "fixed_users": []}
    try:
        employees = frappe.get_all(
            "Employee", filters={"status": "Active", "user_id": ["is", "set"]},
            fields=["user_id"],
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "employee_access.execute list")
        return res

    seen = set()
    for emp in employees:
        user = emp.get("user_id")
        if not user or user in seen:
            continue
        seen.add(user)
        res["scanned"] += 1
        r = ensure_access_for_user(user)
        if r["role_added"] or r["modules_unblocked"]:
            res["roles_added"] += len(r["role_added"])
            res["modules_unblocked"] += len(r["modules_unblocked"])
            res["fixed_users"].append(user)

    frappe.db.commit()
    print("[employee_access] %s" % {k: res[k] for k in
          ("scanned", "roles_added", "modules_unblocked")})
    return res
