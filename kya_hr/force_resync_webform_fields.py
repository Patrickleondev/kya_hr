"""Force resync des Web Form Field depuis les fichiers JSON sources.

Frappe v16 a un bug : pour les Web Forms avec `is_standard:1`, `bench migrate`
et `reload-doc` n'écrasent PAS la table enfant `Web Form Field` si elle
existe déjà en BDD. Conséquence : quand on ajoute/retire des champs dans
le JSON source, la BDD reste sur l'ancienne version.

Ce script :
  1. Lit chaque fichier JSON source des web forms KYA HR.
  2. Supprime tous les Web Form Field existants pour ce parent.
  3. Réinsère les fields depuis le JSON, dans l'ordre.

Idempotent. À lancer après chaque modification de `web_form_fields` dans un
JSON source.
"""
import json
import os

import frappe


WEB_FORMS_DIR = os.path.join(os.path.dirname(__file__), "web_form")


def execute():
    if not frappe.db.has_table("Web Form Field"):
        return

    synced = []
    skipped = []
    errors = []

    if not os.path.isdir(WEB_FORMS_DIR):
        print(f"[force_resync_webform_fields] Dossier introuvable: {WEB_FORMS_DIR}")
        return

    for folder in sorted(os.listdir(WEB_FORMS_DIR)):
        folder_path = os.path.join(WEB_FORMS_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        json_path = os.path.join(folder_path, f"{folder}.json")
        if not os.path.isfile(json_path):
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:  # pylint: disable=broad-except
            errors.append((folder, f"read error: {exc}"))
            continue

        if data.get("doctype") != "Web Form":
            continue

        web_form_name = data.get("name") or data.get("route")
        if not web_form_name or not frappe.db.exists("Web Form", web_form_name):
            skipped.append(web_form_name or folder)
            continue

        fields = data.get("web_form_fields") or []
        if not fields:
            skipped.append(f"{web_form_name} (0 fields in source)")
            continue

        try:
            _resync_fields(web_form_name, fields)
            synced.append(f"{web_form_name} ({len(fields)} fields)")
        except Exception as exc:  # pylint: disable=broad-except
            errors.append((web_form_name, str(exc)))
            frappe.log_error(
                title=f"force_resync_webform_fields {web_form_name}",
                message=frappe.get_traceback() + f"\n\nError: {exc}",
            )

    frappe.db.commit()
    frappe.clear_cache()

    print(f"[force_resync_webform_fields] Synced: {len(synced)}")
    for s in synced:
        print(f"  ✓ {s}")
    if skipped:
        print(f"[force_resync_webform_fields] Skipped: {skipped}")
    if errors:
        print(f"[force_resync_webform_fields] ⚠️ Errors:")
        for name, msg in errors:
            print(f"  ✗ {name}: {msg}")


def _resync_fields(parent_name, fields):
    """Replace all Web Form Field rows for `parent_name` with those from `fields`."""
    # 1. Wipe existing rows
    frappe.db.delete("Web Form Field", {"parent": parent_name, "parenttype": "Web Form"})

    # 2. Re-insert from source
    for idx, fld in enumerate(fields, start=1):
        row = {
            "doctype": "Web Form Field",
            "parent": parent_name,
            "parenttype": "Web Form",
            "parentfield": "web_form_fields",
            "idx": idx,
            "fieldname": fld.get("fieldname"),
            "fieldtype": fld.get("fieldtype"),
            "label": fld.get("label"),
            "options": fld.get("options"),
            "default": fld.get("default"),
            "description": fld.get("description"),
            "reqd": int(bool(fld.get("reqd"))),
            "read_only": int(bool(fld.get("read_only"))),
            "hidden": int(bool(fld.get("hidden"))),
            "max_length": fld.get("max_length"),
            "max_value": fld.get("max_value"),
        }
        # Strip None to let Frappe apply defaults
        row = {k: v for k, v in row.items() if v is not None}
        try:
            frappe.get_doc(row).insert(ignore_permissions=True)
        except Exception:
            # Fallback: raw SQL insert (idx + minimum fields)
            name = frappe.generate_hash(length=10)
            frappe.db.sql(
                """
                INSERT INTO `tabWeb Form Field`
                    (name, parent, parenttype, parentfield, idx, fieldname,
                     fieldtype, label, options, `default`, description,
                     reqd, read_only, hidden, creation, modified, owner)
                VALUES
                    (%(name)s, %(parent)s, 'Web Form', 'web_form_fields',
                     %(idx)s, %(fieldname)s, %(fieldtype)s, %(label)s,
                     %(options)s, %(default)s, %(description)s,
                     %(reqd)s, %(read_only)s, %(hidden)s,
                     NOW(), NOW(), 'Administrator')
                """,
                {
                    "name": name,
                    "parent": parent_name,
                    "idx": idx,
                    "fieldname": fld.get("fieldname"),
                    "fieldtype": fld.get("fieldtype"),
                    "label": fld.get("label"),
                    "options": fld.get("options"),
                    "default": fld.get("default"),
                    "description": fld.get("description"),
                    "reqd": int(bool(fld.get("reqd"))),
                    "read_only": int(bool(fld.get("read_only"))),
                    "hidden": int(bool(fld.get("hidden"))),
                },
            )
