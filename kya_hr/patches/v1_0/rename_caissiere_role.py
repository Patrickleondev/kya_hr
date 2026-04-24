# -*- coding: utf-8 -*-
"""Patch: rename role 'Caissière' -> 'Caissier(ère)'.
Met à jour aussi toutes les Has Role qui référencent l'ancien nom.
"""
import frappe


def execute():
    old, new = "Caissière", "Caissier(ère)"
    if frappe.db.exists("Role", old) and not frappe.db.exists("Role", new):
        try:
            frappe.rename_doc("Role", old, new, force=True, ignore_permissions=True)
            frappe.db.commit()
            frappe.logger().info(f"[kya_hr] Role renamed: {old} -> {new}")
        except Exception as e:
            frappe.logger().error(f"[kya_hr] Role rename failed: {e}")
    elif frappe.db.exists("Role", old) and frappe.db.exists("Role", new):
        # Migrate Has Role from old to new, then delete old
        frappe.db.sql(
            "UPDATE `tabHas Role` SET role=%s WHERE role=%s",
            (new, old),
        )
        frappe.db.delete("Role", {"name": old})
        frappe.db.commit()

    # Update notifications & permissions referring to old role
    for table in ("tabNotification Recipient", "tabCustom DocPerm", "tabDocPerm"):
        try:
            frappe.db.sql(
                f"UPDATE `{table}` SET role=%s WHERE role=%s",
                (new, old),
            )
        except Exception:
            pass
    # Notification Recipient uses receiver_by_role
    try:
        frappe.db.sql(
            "UPDATE `tabNotification Recipient` SET receiver_by_role=%s WHERE receiver_by_role=%s",
            (new, old),
        )
    except Exception:
        pass
    frappe.db.commit()
