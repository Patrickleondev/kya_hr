"""Patch : force is_active=1 sur tous les KYA Contract Template.

Symptôme corrigé : `_select_template` (kya_contrat.py) filtre sur `is_active=1`.
Si un template a is_active=0 (parce que le fixture sync a importé une vieille
version, ou qu'un admin l'a désactivé sans raison), la sélection automatique
échoue et le contrat est généré avec un template incorrect (mauvais genre).

Idempotent : ne fait rien si déjà actif.
"""
import frappe


def execute():
    templates = frappe.get_all(
        "KYA Contract Template",
        filters={"is_active": 0},
        fields=["name"],
    )
    if not templates:
        return
    for t in templates:
        frappe.db.set_value("KYA Contract Template", t.name, "is_active", 1)
    frappe.db.commit()
    print(f"[ensure_contract_templates_active] {len(templates)} template(s) réactivés")
