"""Renomme le workspace `Espace Direction` en `Direction Generale`.

Diagnostic (15/05/2026) : l'icône bureau pointe vers `/app/direction-generale`
mais le workspace en BDD est nommé `Espace Direction` (slug
`espace-direction`). Conséquence : clic sur l'icône Direction → 404
"Page direction-generale introuvable".

Vérification BDD : aucun shortcut/link ne pointe vers `Espace Direction`,
donc le rename est sans risque.

Idempotent : si `Direction Generale` existe déjà, no-op.
"""
import frappe


def execute():
    if frappe.db.exists("Workspace", "Direction Generale"):
        print("[rename_espace_direction] 'Direction Generale' existe déjà, skip")
        return

    if not frappe.db.exists("Workspace", "Espace Direction"):
        print("[rename_espace_direction] 'Espace Direction' absent, skip")
        return

    try:
        frappe.rename_doc(
            "Workspace",
            "Espace Direction",
            "Direction Generale",
            force=True,
        )
        frappe.db.commit()
        frappe.clear_cache()
        print("[rename_espace_direction] OK — 'Espace Direction' → 'Direction Generale'")
    except Exception as e:
        frappe.log_error(
            title="rename_espace_direction échec",
            message=frappe.get_traceback() + f"\n\nError: {e}",
        )
        print(f"[rename_espace_direction] ÉCHEC : {e}")
