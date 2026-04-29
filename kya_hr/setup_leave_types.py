"""KYA Leave Types per Code du Travail Togo + custom fields for justificatifs.

Idempotent. Called from hooks.py after_migrate.
"""

import frappe

KYA_LEAVE_TYPES = [
    # (name, max_days, is_lwp, is_carry_forward, max_continuous, includes_holiday)
    {"leave_type_name": "Congé Annuel", "max_leaves_allowed": 30, "is_lwp": 0, "is_carry_forward": 1, "max_continuous_days_allowed": 30, "include_holiday": 0},
    {"leave_type_name": "Congé Maternité", "max_leaves_allowed": 98, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 119, "include_holiday": 1},
    {"leave_type_name": "Congé Paternité", "max_leaves_allowed": 2, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 2, "include_holiday": 1},
    {"leave_type_name": "Décès Conjoint/Ascendant/Descendant", "max_leaves_allowed": 4, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 4, "include_holiday": 1},
    {"leave_type_name": "Décès Frère/Sœur", "max_leaves_allowed": 2, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 2, "include_holiday": 1},
    {"leave_type_name": "Décès Beau-père/Belle-mère", "max_leaves_allowed": 3, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 3, "include_holiday": 1},
    {"leave_type_name": "Mariage Travailleur", "max_leaves_allowed": 3, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 3, "include_holiday": 1},
    {"leave_type_name": "Mariage Enfant/Frère/Sœur", "max_leaves_allowed": 1, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 1, "include_holiday": 1},
    {"leave_type_name": "Naissance au Foyer", "max_leaves_allowed": 2, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 2, "include_holiday": 1},
    {"leave_type_name": "Baptême", "max_leaves_allowed": 1, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 1, "include_holiday": 1},
    {"leave_type_name": "Déménagement", "max_leaves_allowed": 1, "is_lwp": 0, "is_carry_forward": 0, "max_continuous_days_allowed": 1, "include_holiday": 1},
    {"leave_type_name": "Permission Discrétionnaire", "max_leaves_allowed": 0, "is_lwp": 1, "is_carry_forward": 0, "max_continuous_days_allowed": 5, "include_holiday": 1},
]

CUSTOM_FIELDS_LEAVE_APP = [
    {
        "doctype": "Custom Field",
        "dt": "Leave Application",
        "fieldname": "kya_justificatif",
        "label": "Justificatif (acte, certificat, ...)",
        "fieldtype": "Attach",
        "insert_after": "description",
        "description": "Joindre une pièce justificative (acte de décès, mariage, certificat médical, etc.)",
    },
    {
        "doctype": "Custom Field",
        "dt": "Leave Application",
        "fieldname": "kya_motif_detail",
        "label": "Détail du motif",
        "fieldtype": "Small Text",
        "insert_after": "kya_justificatif",
    },
]


def execute():
    if not frappe.db.has_table("Leave Type"):
        print("[kya_hr.setup_leave_types] Leave Type table absent, skip.")
        return

    created, updated = [], []
    for lt in KYA_LEAVE_TYPES:
        name = lt["leave_type_name"]
        try:
            if frappe.db.exists("Leave Type", name):
                doc = frappe.get_doc("Leave Type", name)
                changed = False
                for k, v in lt.items():
                    if k == "leave_type_name":
                        continue
                    if doc.get(k) != v:
                        doc.set(k, v)
                        changed = True
                if changed:
                    doc.flags.ignore_permissions = True
                    doc.save()
                    updated.append(name)
            else:
                doc = frappe.get_doc({"doctype": "Leave Type", **lt})
                doc.flags.ignore_permissions = True
                doc.insert()
                created.append(name)
        except Exception as e:
            print(f"[kya_hr.setup_leave_types] Erreur {name}: {e}")

    # Custom fields for justificatif on Leave Application
    for cf in CUSTOM_FIELDS_LEAVE_APP:
        try:
            cf_name = f"{cf['dt']}-{cf['fieldname']}"
            if frappe.db.exists("Custom Field", cf_name):
                continue
            doc = frappe.get_doc(cf)
            doc.flags.ignore_permissions = True
            doc.insert()
        except Exception as e:
            print(f"[kya_hr.setup_leave_types] CF erreur {cf['fieldname']}: {e}")

    if created:
        print(f"[kya_hr.setup_leave_types] Créés: {created}")
    if updated:
        print(f"[kya_hr.setup_leave_types] MAJ: {updated}")
