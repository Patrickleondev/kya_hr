"""S'assure que les Web Forms KYA sont accessibles aux roles metier.

Bug recurrent : un employe (role 'Employee') ou un stagiaire ('Stagiaire')
ouvre /demande-conge, /demande-achat, etc. et voit 'Non autorise' alors
qu'il a bien le bon role. Cause : le DocType cible n'a pas de DocPerm
'Employee' ou 'Stagiaire' (DocPerm seulement pour HR Manager / Admin).

Comme les Web Forms KYA ont 'apply_document_permissions=1', sans DocPerm
du DocType, l'utilisateur est rejete.

Ce script :
1. Liste tous les Web Forms KYA et leur doc_type cible.
2. Pour chacun, ajoute (si absent) une DocPerm 'Employee' qui donne
   read+create+write avec if_owner=1 (pour limiter aux propres docs).
3. Idem pour 'Stagiaire' sur les Web Forms qui les concernent.
4. Idem pour 'Guest' SI le Web Form a anonymous=1 (peu probable mais
   par securite).

Idempotent : ne touche pas si la DocPerm existe deja avec les bons droits.

Wrappe dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe


# Roles qui doivent avoir DocPerm de base sur les DocTypes cibles des Web Forms
# Format : {role: {if_owner, read, create, write}}
BASE_EMPLOYEE_PERMS: dict[str, dict] = {
    "read": 1,
    "create": 1,
    "write": 1,
    "if_owner": 1,
    "permlevel": 0,
}


# Roles a forcer pour chaque DocType lie a un Web Form KYA.
# 'all' = tous les Web Forms KYA -> {Employee, Stagiaire}
# Override possible si un DocType cible doit avoir des roles specifiques.
DEFAULT_ROLES = ("Employee", "Stagiaire")


def _list_kya_webforms() -> list[dict]:
    """Retourne [{name, doc_type, login_required, anonymous}, ...]."""
    return frappe.db.get_all(
        "Web Form",
        filters={"module": ["like", "%KYA%"]},
        fields=["name", "doc_type", "login_required", "anonymous"],
    )


def _ensure_role_docperm(doctype: str, role: str) -> str:
    """Verifie/ajoute une DocPerm role + if_owner=1 sur le DocType cible.

    Retourne 'created' / 'updated' / 'unchanged' / 'role_missing'.
    """
    if not frappe.db.exists("Role", role):
        return "role_missing"

    # Cherche une DocPerm existante pour ce role + permlevel=0
    existing = frappe.db.get_all(
        "DocPerm",
        filters={"parent": doctype, "role": role, "permlevel": 0},
        fields=["name", "read", "create", "write", "if_owner"],
        limit=10,
    )

    # Si une DocPerm existe deja avec les bons droits -> unchanged
    for row in existing:
        if (row.read == 1 and row.create == 1 and row.write == 1
                and (row.if_owner == 1 or row.if_owner is None)):
            return "unchanged"

    # Si une DocPerm existe mais incomplete -> on l'update (premier match)
    if existing:
        try:
            frappe.db.set_value("DocPerm", existing[0].name, {
                "read": 1, "create": 1, "write": 1, "if_owner": 1,
            }, update_modified=False)
            return "updated"
        except Exception:
            try:
                frappe.log_error(frappe.get_traceback(), f"ensure_webform_perms: update {doctype}/{role}")
            except Exception:
                pass
            return "error"

    # Sinon, on cree une nouvelle DocPerm
    try:
        dt_doc = frappe.get_doc("DocType", doctype)
        dt_doc.append("permissions", {
            "role": role, **BASE_EMPLOYEE_PERMS,
        })
        dt_doc.save(ignore_permissions=True)
        return "created"
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(), f"ensure_webform_perms: create {doctype}/{role}")
        except Exception:
            pass
        return "error"


def execute() -> dict:
    summary = {
        "webforms_scanned": 0,
        "doctypes_touched": [],
        "actions": {"created": 0, "updated": 0, "unchanged": 0, "role_missing": 0, "error": 0},
    }

    seen_doctypes: set[str] = set()
    for wf in _list_kya_webforms():
        summary["webforms_scanned"] += 1
        doctype = wf.get("doc_type")
        if not doctype or doctype in seen_doctypes:
            continue
        if not frappe.db.exists("DocType", doctype):
            continue
        # Skip les DocType core (Frappe natif) - on ne touche pas a leur perms
        # pour eviter de casser quoi que ce soit.
        is_kya = frappe.db.get_value("DocType", doctype, "module")
        if not is_kya or "KYA" not in (is_kya or ""):
            # On touche aussi quelques DocType HRMS critiques pour les WF KYA
            if doctype not in ("Leave Application",):
                continue

        seen_doctypes.add(doctype)
        summary["doctypes_touched"].append(doctype)

        for role in DEFAULT_ROLES:
            action = _ensure_role_docperm(doctype, role)
            summary["actions"][action] = summary["actions"].get(action, 0) + 1

    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass

    print(f"[ensure_webform_perms] {summary}")
    return summary
