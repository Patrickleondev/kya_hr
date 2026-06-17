# -*- coding: utf-8 -*-
"""Garantit que l'expression de besoin de formation cible une ÉQUIPE (Equipe KYA),
pas un département.

Retour user : « équipe n'est pas département : l'équipe est dans le département ».
Le champ `equipe` de `Besoin de Formation` pointait sur `Department`. On le
recible sur **Equipe KYA** ; le **département se déduit** de l'équipe
(fetch_from equipe.departement) et le **chef** aussi (equipe.chef_equipe).

Le DocType se synchronise normalement depuis son JSON au migrate, mais les
**Web Form Field** ne se resynchronisent pas toujours en v16 → on les force ici.
Idempotent. Branché dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe

WF = "besoin-formation"


def execute() -> dict:
    out = []
    if not frappe.db.exists("Web Form", WF):
        return {"skipped": "web form absent"}

    # equipe -> Equipe KYA
    eq = frappe.db.get_value("Web Form Field", {"parent": WF, "fieldname": "equipe"}, "name")
    if eq:
        cur = frappe.db.get_value("Web Form Field", eq, "options")
        if cur != "Equipe KYA":
            frappe.db.set_value("Web Form Field", eq,
                                {"options": "Equipe KYA", "label": "Équipe", "reqd": 1})
            out.append("equipe->Equipe KYA")

    # chef_equipe lecture seule (auto depuis l'équipe)
    ch = frappe.db.get_value("Web Form Field", {"parent": WF, "fieldname": "chef_equipe"}, "name")
    if ch and not frappe.db.get_value("Web Form Field", ch, "read_only"):
        frappe.db.set_value("Web Form Field", ch, {"read_only": 1, "label": "Chef d'équipe (auto)"})
        out.append("chef_equipe read_only")

    # departement (déduit) inséré après equipe
    if eq and not frappe.db.exists("Web Form Field", {"parent": WF, "fieldname": "departement"}):
        eq_idx = frappe.db.get_value("Web Form Field", eq, "idx") or 1
        frappe.db.sql("UPDATE `tabWeb Form Field` SET idx=idx+1 WHERE parent=%s AND idx>%s",
                      (WF, eq_idx))
        d = frappe.get_doc({
            "doctype": "Web Form Field", "parent": WF, "parenttype": "Web Form",
            "parentfield": "web_form_fields", "fieldname": "departement",
            "fieldtype": "Link", "options": "Department", "label": "Département",
            "read_only": 1, "idx": eq_idx + 1,
        })
        d.name = frappe.generate_hash(length=10)
        d.db_insert()
        out.append("+departement")

    if out:
        frappe.db.commit()
        frappe.clear_cache(doctype="Web Form")
    print(f"[fix_formation_equipe] {out or 'déjà conforme'}")
    return {"changes": out}
