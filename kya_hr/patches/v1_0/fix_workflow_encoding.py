"""
Patch: fix_workflow_encoding
Corrige les noms de workflows stockés avec encodage mojibake (CP437/Latin-1)
en base de données. Les noms concernés :
  - 'Flux RH Unifi├⌐'       → 'Flux RH Unifié'
  - 'Demande de mat├⌐riel'  → 'Demande de matériel'
  - 'Flux PV Sortie Mat├⌐riel' → 'Flux PV Sortie Matériel'
"""

import frappe


RENAME_MAP = {
    "Flux RH Unifi\u251c\u2310": "Flux RH Unifi\u00e9",
    "Demande de mat\u251c\u2310riel": "Demande de mat\u00e9riel",
    "Flux PV Sortie Mat\u251c\u2310riel": "Flux PV Sortie Mat\u00e9riel",
}


def execute():
    for old_name, new_name in RENAME_MAP.items():
        if frappe.db.exists("Workflow", old_name):
            frappe.db.sql(
                "UPDATE `tabWorkflow` SET `name`=%s, modified=NOW() WHERE `name`=%s",
                (new_name, old_name),
            )
            # Also update references in Workflow State / Action
            frappe.db.sql(
                "UPDATE `tabWorkflow State` SET `parent`=%s WHERE `parent`=%s AND `parenttype`='Workflow'",
                (new_name, old_name),
            )
            frappe.db.sql(
                "UPDATE `tabWorkflow Transition` SET `parent`=%s WHERE `parent`=%s AND `parenttype`='Workflow'",
                (new_name, old_name),
            )
            frappe.db.commit()
            frappe.logger().info(f"[kya_hr] Workflow renamed: {old_name!r} → {new_name!r}")
