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
        if not frappe.db.exists("Workflow", old_name):
            continue
        try:
            frappe.db.sql(
                "UPDATE `tabWorkflow` SET `name`=%s, modified=NOW() WHERE `name`=%s",
                (new_name, old_name),
            )
            # Child table in v16 is "Workflow Document State", not "Workflow State"
            for child_table in ("Workflow Document State", "Workflow Transition"):
                table_name = "tab{}".format(child_table)
                try:
                    frappe.db.sql(
                        "UPDATE `{t}` SET `parent`=%s WHERE `parent`=%s AND `parenttype`='Workflow'".format(t=table_name),
                        (new_name, old_name),
                    )
                except Exception:
                    pass  # Table structure may vary between v14/v15/v16
            frappe.db.commit()
            frappe.logger().info(f"[kya_hr] Workflow renamed: {old_name!r} → {new_name!r}")
        except Exception as e:
            frappe.log_error(f"[kya_hr] Workflow rename failed for {old_name!r}: {e}")
            frappe.db.rollback()
