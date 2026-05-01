# -*- coding: utf-8 -*-
"""Patch: normaliser le rôle caisse en 'Caissier' (genre neutre).

Gère deux historiques :
- 'Caissière' (forme féminine d'origine)
- 'Caissier(ère)' (forme parenthésée intermédiaire)
→ tout est ramené à 'Caissier'.

Met à jour Has Role, DocPerm/Custom DocPerm et Notification Recipient.
"""
import frappe

NEW = "Caissier"
OLD_NAMES = ("Caissière", "Caissier(ère)")


def _migrate_role(old: str) -> None:
    if not frappe.db.exists("Role", old):
        return
    if not frappe.db.exists("Role", NEW):
        try:
            frappe.rename_doc("Role", old, NEW, force=True, ignore_permissions=True)
            frappe.db.commit()
            frappe.logger().info(f"[kya_hr] Role renamed: {old} -> {NEW}")
            return
        except Exception as e:
            frappe.logger().error(f"[kya_hr] Role rename failed: {e}")
    # Cible existe déjà : migrer les liens puis supprimer l'ancien
    frappe.db.sql(
        "UPDATE `tabHas Role` SET role=%s WHERE role=%s",
        (NEW, old),
    )
    frappe.db.delete("Role", {"name": old})
    frappe.db.commit()


def execute():
    for old in OLD_NAMES:
        _migrate_role(old)

    # Met à jour les permissions et notifications
    for old in OLD_NAMES:
        for table in ("tabNotification Recipient", "tabCustom DocPerm", "tabDocPerm"):
            try:
                frappe.db.sql(
                    f"UPDATE `{table}` SET role=%s WHERE role=%s",
                    (NEW, old),
                )
            except Exception:
                pass
        try:
            frappe.db.sql(
                "UPDATE `tabNotification Recipient` SET receiver_by_role=%s WHERE receiver_by_role=%s",
                (NEW, old),
            )
        except Exception:
            pass
    frappe.db.commit()
