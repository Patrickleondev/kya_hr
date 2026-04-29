"""KYA Locale Setup — force date_format dd-mm-yyyy globally.

Hook : appelé par after_migrate dans hooks.py.
"""
import frappe


def execute():
    """Set System Settings date_format = dd-mm-yyyy + first_day_of_the_week=Monday."""
    try:
        ss = frappe.get_single("System Settings")
        changed = False
        if ss.date_format != "dd-mm-yyyy":
            ss.date_format = "dd-mm-yyyy"
            changed = True
        if ss.first_day_of_the_week != "Monday":
            ss.first_day_of_the_week = "Monday"
            changed = True
        if ss.language != "fr":
            ss.language = "fr"
            changed = True
        if changed:
            ss.flags.ignore_permissions = True
            ss.save()
            frappe.db.commit()
            print("[kya_hr.setup_locale] date_format=dd-mm-yyyy, first_day=Monday, language=fr")
    except Exception as e:
        print(f"[kya_hr.setup_locale] warning: {e}")
