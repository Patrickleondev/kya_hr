"""Garantit que TOUS les acteurs des workflows peuvent approuver.

PROBLEME CRITIQUE identifie : pour approuver/signer un document dans un
workflow (PV Sortie, Permission, Demande Achat, Conge...), l'approbateur
(Chef Service, Auditeur, DGA, DG, Responsable RH, etc.) doit pouvoir
ECRIRE sur un document qu'il NE possede PAS (c'est l'employe demandeur
qui l'a cree).

Or les permissions 'if_owner=1' (posees par ensure_webform_perms pour
les demandeurs) limitent l'ecriture au proprietaire. Resultat : le
'sup immediat' / chef voit le document mais ne peut PAS changer le
workflow_state -> impossible de signer/approuver. C'est LA cause du
'sup immediat n'a pas acces au champ de signature'.

Ce module parcourt chaque Workflow actif, recupere :
- le document_type (DocType cible)
- TOUS les roles utilises dans les transitions (champ 'allowed')
Puis garantit que chacun de ces roles a, sur le DocType :
- read = 1
- write = 1
- if_owner = 0  (CRUCIAL : ecriture sur les docs des AUTRES)
- + submit/cancel si le DocType est submittable

Idempotent. Wrappe dans safe_migrations.AFTER_MIGRATE (apres
ensure_webform_perms qui pose les droits des demandeurs).
"""
from __future__ import annotations

import frappe


def _workflow_roles_by_doctype() -> dict[str, set[str]]:
    """Retourne {doctype: {roles approbateurs}} depuis les Workflows actifs."""
    result: dict[str, set[str]] = {}

    workflows = frappe.db.get_all(
        "Workflow",
        filters={"is_active": 1},
        fields=["name", "document_type"],
    )
    for wf in workflows:
        dt = wf.document_type
        if not dt:
            continue
        roles = result.setdefault(dt, set())
        # Roles dans les transitions (qui peut declencher une action)
        transitions = frappe.db.get_all(
            "Workflow Transition",
            filters={"parent": wf.name},
            fields=["allowed"],
        )
        for t in transitions:
            if t.allowed:
                roles.add(t.allowed.strip())
        # Roles dans les etats (qui peut editer a cet etat)
        states = frappe.db.get_all(
            "Workflow Document State",
            filters={"parent": wf.name},
            fields=["allow_edit"],
        )
        for s in states:
            if s.allow_edit:
                roles.add(s.allow_edit.strip())

    return result


def _ensure_approver_perm(doctype: str, role: str, submittable: bool) -> str:
    """Garantit read+write (SANS if_owner) pour un role approbateur."""
    if not frappe.db.exists("Role", role):
        return "role_missing"

    from frappe.permissions import add_permission, update_permission_property

    # CRUCIAL : pour un DocType `custom=1`, Frappe lit UNIQUEMENT les
    # "Custom DocPerm" et IGNORE les "DocPerm" standard. Une perm standard
    # (ex. écrite via le JSON du doctype) ne donne donc AUCUN droit réel et
    # ne doit pas nous faire croire que tout est en ordre.
    is_custom = bool(frappe.db.get_value("DocType", doctype, "custom"))

    # Etat actuel : la perm donne-t-elle deja write sans if_owner ?
    std = frappe.db.get_value(
        "DocPerm",
        {"parent": doctype, "role": role, "permlevel": 0},
        ["read", "write", "if_owner"],
        as_dict=True,
    )
    custom = frappe.db.get_value(
        "Custom DocPerm",
        {"parent": doctype, "role": role, "permlevel": 0},
        ["name", "read", "write", "if_owner"],
        as_dict=True,
    )

    # Si une perm standard donne write SANS if_owner -> ok (sauf doctype custom,
    # où le DocPerm standard est ignoré par le moteur de permissions).
    if (not is_custom) and std and std.read and std.write and not std.if_owner:
        return "unchanged"
    if custom and custom.read and custom.write and not custom.if_owner:
        return "unchanged"

    try:
        if not custom:
            add_permission(doctype, role, 0)
        update_permission_property(doctype, role, 0, "read", "1")
        update_permission_property(doctype, role, 0, "write", "1")
        # CRUCIAL : retirer if_owner pour permettre l'ecriture sur les
        # documents des autres (les demandes a approuver).
        update_permission_property(doctype, role, 0, "if_owner", "0")
        if submittable:
            update_permission_property(doctype, role, 0, "submit", "1")
        return "updated" if custom else "created"
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(),
                             f"ensure_workflow_perms: {doctype}/{role}")
        except Exception:
            pass
        return "error"


def _repair_invalid_perms(doctype: str) -> int:
    """Repare les perms incoherentes (submit/cancel/amend sans write)."""
    repaired = 0
    for table in ("DocPerm", "Custom DocPerm"):
        rows = frappe.db.get_all(
            table,
            filters={"parent": doctype},
            fields=["name", "read", "write", "submit", "cancel", "amend"],
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
    return repaired


def execute() -> dict:
    summary = {
        "doctypes": 0,
        "actions": {"created": 0, "updated": 0, "unchanged": 0,
                    "role_missing": 0, "error": 0},
        "perms_repaired": 0,
        "details": [],
    }

    roles_map = _workflow_roles_by_doctype()
    for doctype, roles in roles_map.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        summary["doctypes"] += 1

        # Reparer les incoherences d'abord
        summary["perms_repaired"] += _repair_invalid_perms(doctype)

        submittable = bool(frappe.db.get_value("DocType", doctype, "is_submittable"))

        doctype_roles = []
        for role in sorted(roles):
            # On ne touche pas 'Employee'/'Stagiaire' ici : eux gardent
            # if_owner (ce sont les demandeurs, pas les approbateurs).
            if role in ("Employee", "Stagiaire", "All", "Guest"):
                continue
            action = _ensure_approver_perm(doctype, role, submittable)
            summary["actions"][action] = summary["actions"].get(action, 0) + 1
            doctype_roles.append(f"{role}:{action}")

        summary["details"].append({"doctype": doctype, "roles": doctype_roles})

    try:
        frappe.db.commit()
        frappe.clear_cache()
    except Exception:
        pass

    print(f"[ensure_workflow_perms] doctypes={summary['doctypes']} "
          f"actions={summary['actions']} repaired={summary['perms_repaired']}")
    return summary
