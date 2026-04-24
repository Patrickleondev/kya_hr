# -*- coding: utf-8 -*-
"""Patch: miroir 'HR Manager' -> 'Responsable RH'.

Objectif: KYA-Energy Group utilise le rôle métier 'Responsable RH' (config
production) tandis que les fixtures et workflows standards Frappe/ERPNext
référencent 'HR Manager'. Pour éviter de casser les permissions standard, ce
patch duplique toutes les permissions, transitions de workflow et
notifications 'HR Manager' vers 'Responsable RH' (sans supprimer 'HR Manager').

Idempotent: re-exécutable sans effet secondaire.
"""
import frappe


SRC = "HR Manager"
DST = "Responsable RH"


def _ensure_role():
    if not frappe.db.exists("Role", DST):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": DST,
            "desk_access": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()


def _mirror_docperms():
    """Duplique les DocPerm/Custom DocPerm de SRC vers DST (sur tous les DocType)."""
    for table in ("tabDocPerm", "tabCustom DocPerm"):
        try:
            rows = frappe.db.sql(
                f"SELECT * FROM `{table}` WHERE role=%s",
                (SRC,),
                as_dict=True,
            )
        except Exception:
            continue
        for r in rows:
            parent = r.get("parent")
            permlevel = r.get("permlevel", 0)
            if not parent:
                continue
            exists = frappe.db.sql(
                f"SELECT name FROM `{table}` WHERE parent=%s AND role=%s AND permlevel=%s LIMIT 1",
                (parent, DST, permlevel),
            )
            if exists:
                continue
            new_name = frappe.generate_hash(length=10)
            cols = [k for k in r.keys() if k not in ("name", "creation", "modified", "modified_by", "owner")]
            placeholders = ", ".join(["%s"] * (len(cols) + 1))
            col_sql = ", ".join(["`name`"] + [f"`{c}`" for c in cols])
            values = [new_name] + [(DST if c == "role" else r[c]) for c in cols]
            try:
                frappe.db.sql(
                    f"INSERT INTO `{table}` ({col_sql}) VALUES ({placeholders})",
                    values,
                )
            except Exception as e:
                frappe.logger().warning(f"[mirror_hr] DocPerm mirror skip {parent}: {e}")


def _mirror_workflow_transitions():
    """Pour chaque Workflow Transition dont allowed=HR Manager, crée une transition identique allowed=Responsable RH."""
    rows = frappe.db.sql(
        """SELECT `name`, `parent`, `parenttype`, `parentfield`, `idx`, `state`, `action`, `next_state`,
                  `allow_self_approval`, `condition`
           FROM `tabWorkflow Transition` WHERE `allowed`=%s""",
        (SRC,),
        as_dict=True,
    )
    for r in rows:
        dup = frappe.db.sql(
            """SELECT name FROM `tabWorkflow Transition`
               WHERE parent=%s AND state=%s AND action=%s AND next_state=%s AND allowed=%s LIMIT 1""",
            (r.parent, r.state, r.action, r.next_state, DST),
        )
        if dup:
            continue
        try:
            parent_doc = frappe.get_doc("Workflow", r.parent)
            parent_doc.append("transitions", {
                "state": r.state,
                "action": r.action,
                "next_state": r.next_state,
                "allowed": DST,
                "allow_self_approval": r.allow_self_approval or 0,
                "condition": r.condition,
            })
            parent_doc.flags.ignore_permissions = True
            parent_doc.flags.ignore_validate = True
            parent_doc.save()
        except Exception as e:
            frappe.logger().warning(f"[mirror_hr] WF transition mirror skip {r.parent}: {e}")


def _mirror_notifications():
    """Duplique les Notification Recipient (receiver_by_role)."""
    rows = frappe.db.sql(
        "SELECT parent FROM `tabNotification Recipient` WHERE receiver_by_role=%s",
        (SRC,),
        as_dict=True,
    )
    seen = set()
    for r in rows:
        if r.parent in seen:
            continue
        seen.add(r.parent)
        dup = frappe.db.sql(
            "SELECT name FROM `tabNotification Recipient` WHERE parent=%s AND receiver_by_role=%s LIMIT 1",
            (r.parent, DST),
        )
        if dup:
            continue
        try:
            notif = frappe.get_doc("Notification", r.parent)
            notif.append("recipients", {"receiver_by_role": DST})
            notif.flags.ignore_permissions = True
            notif.save()
        except Exception as e:
            frappe.logger().warning(f"[mirror_hr] Notif mirror skip {r.parent}: {e}")


def execute():
    _ensure_role()
    _mirror_docperms()
    _mirror_workflow_transitions()
    _mirror_notifications()
    frappe.db.commit()
    frappe.clear_cache()
    frappe.logger().info(f"[kya_hr] Mirror {SRC} -> {DST} applied")
