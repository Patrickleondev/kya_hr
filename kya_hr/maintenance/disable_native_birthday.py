# -*- coding: utf-8 -*-
"""Désactive TOUS les rappels d'anniversaire redondants, sauf le rappel KYA.

On garde UNIQUEMENT le rappel maison
`kya_hr.reminders.send_kya_birthday_reminders` (envoyé à la RH + DG, logo inline,
SANS mention d'âge). On éteint :
  1. le rappel natif ERPNext/HRMS (HR Settings → Send Birthday Reminders) ;
  2. les Notifications KYA doublons « Anniversaire Employé » / « Anniversaire
     Professionnel » (elles écrivaient à l'employé lui-même).

`sync_fixtures` ne met pas à jour le champ `enabled` d'une Notification déjà
présente → on force la désactivation ici, explicitement. Idempotent.
"""
from __future__ import annotations

import frappe

# Champs de rappel natifs à éteindre s'ils existent (birthday + éventuel
# anniversaire de service natif selon la version HRMS).
_NATIVE_REMINDER_FIELDS = (
    "send_birthday_reminders",
    "send_work_anniversary_reminders",
)

# Notifications KYA doublons à désactiver (le rappel maison les remplace).
_KYA_ANNIV_NOTIFICATIONS = (
    "KYA - Anniversaire Employé",
    "KYA - Anniversaire Professionnel",
)


def execute() -> dict:
    out = {"native_disabled": [], "notifications_disabled": []}

    # 1) Rappel natif ERPNext/HRMS
    try:
        if frappe.db.exists("DocType", "HR Settings"):
            hs = frappe.get_single("HR Settings")
            meta = hs.meta
            for field in _NATIVE_REMINDER_FIELDS:
                if meta.has_field(field) and hs.get(field):
                    hs.set(field, 0)
                    out["native_disabled"].append(field)
            if out["native_disabled"]:
                hs.flags.ignore_permissions = True
                hs.save(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "disable_native_birthday: HR Settings")

    # 2) Notifications KYA doublons
    for name in _KYA_ANNIV_NOTIFICATIONS:
        try:
            if frappe.db.exists("Notification", name) and \
                    frappe.db.get_value("Notification", name, "enabled"):
                frappe.db.set_value("Notification", name, "enabled", 0)
                out["notifications_disabled"].append(name)
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"disable_native_birthday: {name}")

    frappe.db.commit()
    print("[disable_native_birthday] %s" % out)
    return out
