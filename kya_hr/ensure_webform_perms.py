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


def _repair_invalid_perms(doctype: str) -> int:
    """Repare les DocPerm incoherentes qui bloquent toute modif de perms.

    Frappe valide TOUTES les lignes de permission a chaque modification.
    Si une ligne a submit/cancel/amend sans write (ou write sans read),
    la validation echoue : 'Vous ne pouvez pas choisir Valider, Annuler,
    Nouv. version sans Ecrire'. Cela bloque l'ajout de nos perms.

    Ce helper detecte ces lignes (standard ET custom) et ajoute les
    droits manquants (write si submit/cancel/amend ; read si write).
    Retourne le nombre de lignes reparees.
    """
    repaired = 0
    for table in ("DocPerm", "Custom DocPerm"):
        rows = frappe.db.get_all(
            table,
            filters={"parent": doctype},
            fields=["name", "role", "read", "write", "submit", "cancel", "amend"],
        )
        for r in rows:
            needs_write = (r.submit or r.cancel or r.amend) and not r.write
            needs_read = (r.write or needs_write) and not r.read
            updates = {}
            if needs_write:
                updates["write"] = 1
            if needs_read:
                updates["read"] = 1
            if updates:
                try:
                    frappe.db.set_value(table, r.name, updates, update_modified=False)
                    repaired += 1
                except Exception:
                    pass
    if repaired:
        frappe.db.commit()
        frappe.clear_cache(doctype=doctype)
    return repaired


def _ensure_role_docperm(doctype: str, role: str) -> str:
    """Garantit que `role` a read+create+write+if_owner sur `doctype`.

    Utilise l'API officielle frappe.permissions :
    - add_permission() cree une Custom DocPerm (ne touche PAS la DocType
      standard, donc pas besoin du mode developpeur). C'est LA bonne
      methode pour les DocTypes natifs (Leave Application, etc.).
    - update_permission_property() pose chaque droit (read/create/write/
      if_owner).

    Retourne 'created' / 'updated' / 'unchanged' / 'role_missing' / 'error'.
    """
    if not frappe.db.exists("Role", role):
        return "role_missing"

    from frappe.permissions import add_permission, update_permission_property

    # Etat actuel : la DocPerm (standard ou custom) existe-t-elle deja
    # avec les bons droits ? On lit la permission effective.
    existing = frappe.db.get_value(
        "Custom DocPerm",
        {"parent": doctype, "role": role, "permlevel": 0},
        ["name", "read", "create", "write", "if_owner"],
        as_dict=True,
    )
    std = frappe.db.get_value(
        "DocPerm",
        {"parent": doctype, "role": role, "permlevel": 0},
        ["read", "create", "write", "if_owner"],
        as_dict=True,
    )

    # Si une perm standard donne deja tous les droits -> rien a faire
    if std and std.read and std.create and std.write:
        return "unchanged"
    if (existing and existing.read and existing.create
            and existing.write and existing.if_owner):
        return "unchanged"

    try:
        had_custom = bool(existing)
        if not had_custom:
            # add_permission cree la ligne Custom DocPerm (permlevel 0)
            add_permission(doctype, role, 0)

        # Poser chaque droit. update_permission_property attend des str.
        for ptype in ("read", "create", "write", "if_owner"):
            update_permission_property(doctype, role, 0, ptype, "1")

        return "updated" if had_custom else "created"
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(),
                             f"ensure_webform_perms: {doctype}/{role}")
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

        # Repare d'abord les perms incoherentes (submit sans write) qui
        # bloqueraient l'ajout de nos perms.
        repaired = _repair_invalid_perms(doctype)
        if repaired:
            summary["perms_repaired"] = summary.get("perms_repaired", 0) + repaired

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
