"""Custom fields KYA sur le DocType Attendance.

Le marquage de presence depuis le dashboard RH a besoin de tracer qui
a marque, quand, et combien de minutes de retard. ERPNext Attendance
n'a pas ces champs nativement.

Idempotent : verifie l'existence avant de creer. Wrapped try/except.
Appele depuis safe_migrations.py.execute en after_migrate.
"""
from __future__ import annotations

import frappe


KYA_ATTENDANCE_FIELDS = [
    {
        "fieldname": "kya_section_audit",
        "fieldtype": "Section Break",
        "label": "Marquage KYA",
        "insert_after": "shift",
        "collapsible": 1,
    },
    {
        "fieldname": "kya_marked_by",
        "fieldtype": "Link",
        "options": "User",
        "label": "Marque par (KYA)",
        "insert_after": "kya_section_audit",
        "read_only": 1,
        "description": "Utilisateur RH qui a saisi la presence depuis le dashboard.",
    },
    {
        "fieldname": "kya_marked_at",
        "fieldtype": "Datetime",
        "label": "Marque le (KYA)",
        "insert_after": "kya_marked_by",
        "read_only": 1,
    },
    {
        "fieldname": "kya_col_audit",
        "fieldtype": "Column Break",
        "insert_after": "kya_marked_at",
    },
    {
        "fieldname": "kya_lateness_minutes",
        "fieldtype": "Int",
        "label": "Retard (minutes)",
        "insert_after": "kya_col_audit",
        "default": 0,
        "description": "Nombre de minutes de retard par rapport au Shift Type (defaut 08:00 + 5 min tolerance).",
    },
    {
        "fieldname": "kya_motif_absence",
        "fieldtype": "Small Text",
        "label": "Motif absence (KYA)",
        "insert_after": "kya_lateness_minutes",
        "depends_on": "eval:doc.status==='Absent'",
    },
]


def _upsert_custom_field(field_def: dict) -> str:
    """Cree ou met a jour un Custom Field pour le DocType Attendance."""
    doctype = "Attendance"
    fieldname = field_def["fieldname"]
    cf_name = f"{doctype}-{fieldname}"

    if frappe.db.exists("Custom Field", cf_name):
        # Verifier si update necessaire (label, options, etc.)
        cf = frappe.get_doc("Custom Field", cf_name)
        changed = False
        for k, v in field_def.items():
            if getattr(cf, k, None) != v:
                setattr(cf, k, v)
                changed = True
        if changed:
            cf.save(ignore_permissions=True)
            return "updated"
        return "unchanged"

    cf = frappe.new_doc("Custom Field")
    cf.dt = doctype
    for k, v in field_def.items():
        setattr(cf, k, v)
    cf.insert(ignore_permissions=True)
    return "created"


def execute():
    """Idempotent entrypoint - safe a appeler plusieurs fois."""
    results = {"created": 0, "updated": 0, "unchanged": 0, "errors": []}
    for field_def in KYA_ATTENDANCE_FIELDS:
        try:
            action = _upsert_custom_field(field_def)
            results[action] = results.get(action, 0) + 1
        except Exception as exc:
            results["errors"].append({"field": field_def["fieldname"], "error": str(exc)})
            try:
                frappe.log_error(frappe.get_traceback(), f"setup_attendance_fields {field_def['fieldname']}")
            except Exception:
                pass

    try:
        frappe.db.commit()
        frappe.clear_cache(doctype="Attendance")
    except Exception:
        pass

    print(f"[setup_attendance_fields] {results}")
    return results
