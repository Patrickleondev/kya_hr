"""Renomme la famille de stock industriel « Matière première » -> « Composants »
(demande RH, terme jugé plus juste pour l'assemblage). Le DocType Article KYA
est custom=0 : le migrate resynchronise déjà les options du Select depuis le
JSON (cf. article_kya.json). Il ne reste donc que les LIGNES EXISTANTES dont
`famille` porte encore l'ancienne valeur littérale à reclasser en base.

100 % idempotent (no-op si plus aucune ligne à l'ancien libellé).
"""
from __future__ import annotations

import frappe

ANCIEN = "Matière première"
NOUVEAU = "Composants"


def execute() -> dict:
    result = {"reclasses": 0}
    try:
        result["reclasses"] = frappe.db.count("Article KYA", {"famille": ANCIEN})
        if result["reclasses"]:
            frappe.db.set_value("Article KYA", {"famille": ANCIEN}, "famille", NOUVEAU,
                                update_modified=False)
            frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "rename_famille_composants")
    return result
