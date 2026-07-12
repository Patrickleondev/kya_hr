# -*- coding: utf-8 -*-
"""Empêche les User Permissions « Employee/Company » de bloquer les approbateurs.

BUG RÉEL détecté (cause de « il a le rôle mais ne peut pas signer/viser ») :
HRMS crée automatiquement, pour chaque employé-utilisateur, une User Permission
`Employee = <sa propre fiche>`. Cette restriction s'applique à TOUT champ Link→Employee.
Résultat : un approbateur (Comptable, DFC, Chef, Audit, DG…) limité à SA fiche ne
peut PLUS lire un document dont le champ Employee pointe vers QUELQU'UN D'AUTRE
(ex. le Brouillard de Caisse d'un autre caissier) → PermissionError → signature/visa
impossible, alors même que le rôle est bon.

Correctif : sur les fiches opérationnelles à circuit d'approbation, on met
`ignore_user_permissions = 1` sur chaque lien Employee/Company. L'accès reste
verrouillé par le RÔLE (Custom DocPerm) et le WORKFLOW ; on retire seulement la
restriction « une seule fiche employé » qui n'a aucun sens pour un approbateur.

Ne touche PAS `if_owner` (le demandeur Employee/Stagiaire continue de ne voir que
les siens). Via Property Setter (réversible, rejoué au migrate). Idempotent.
"""
from __future__ import annotations

import frappe

# Types de lien concernés par les User Permissions gênantes.
_CIBLE_OPTIONS = {"Employee", "Company"}

# Doctypes NATIFS (module non-KYA) pilotés par un workflow KYA : eux aussi
# subissent le blocage User Permission sur les approbateurs. Ex. Leave
# Application (module HR) porte le workflow « Flux RH Unifié » — sans ce
# correctif, un Supérieur/RH/DG limité à sa propre fiche Employee ne peut pas
# viser le congé d'un autre (PermissionError alors que le rôle est bon).
_NATIFS_A_TRAITER = {"Leave Application"}


def _doctypes_a_traiter() -> list[str]:
    """Toutes les fiches à workflow actif où des approbateurs de rôles
    différents doivent agir sur les documents d'autrui : fiches KYA + natifs
    explicitement pilotés par un workflow KYA."""
    dts = set()
    for wf in frappe.get_all("Workflow", filters={"is_active": 1},
                             fields=["document_type"]):
        dt = wf.document_type
        if not dt:
            continue
        module = frappe.db.get_value("DocType", dt, "module")
        if (module and "KYA" in module) or dt in _NATIFS_A_TRAITER:
            dts.add(dt)
    return sorted(dts)


def _set_iup(doctype: str, fieldname: str) -> str:
    existing = frappe.db.get_value(
        "Property Setter",
        {"doc_type": doctype, "field_name": fieldname,
         "property": "ignore_user_permissions"},
        "name",
    )
    if existing:
        if frappe.db.get_value("Property Setter", existing, "value") != "1":
            frappe.db.set_value("Property Setter", existing, "value", "1")
            return "updated"
        return "unchanged"
    frappe.make_property_setter(
        {"doctype": doctype, "fieldname": fieldname,
         "property": "ignore_user_permissions", "value": "1",
         "property_type": "Check"},
        is_system_generated=False,
    )
    return "created"


def execute() -> dict:
    out = {"doctypes": {}, "created": 0, "updated": 0, "unchanged": 0}
    for dt in _doctypes_a_traiter():
        meta = frappe.get_meta(dt)
        champs = []
        for f in meta.fields:
            if f.fieldtype == "Link" and f.options in _CIBLE_OPTIONS:
                action = _set_iup(dt, f.fieldname)
                out[action] = out.get(action, 0) + 1
                champs.append(f"{f.fieldname}:{action}")
        if champs:
            out["doctypes"][dt] = champs
    frappe.clear_cache()
    frappe.db.commit()
    print(f"[fix_user_permission_links] created={out['created']} "
          f"updated={out['updated']} unchanged={out['unchanged']}")
    return out
