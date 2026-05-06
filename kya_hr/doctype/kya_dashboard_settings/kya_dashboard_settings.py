# Copyright (c) 2026, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import now_datetime
import hashlib
import json


class KYADashboardSettings(Document):
    def validate(self):
        seen = set()
        for row in self.entries or []:
            self._hydrate_from_web_form(row)
            self._validate_entry(row)

            key = (row.doctype_name or "", row.web_form_route or "")
            if key in seen:
                frappe.throw(_("Entrée dashboard dupliquée pour {0} / {1}").format(row.doctype_name, row.web_form_route or "sans route"))
            seen.add(key)

            row.last_synced_on = now_datetime()
            row.sync_fingerprint = self._fingerprint(row)

    def _hydrate_from_web_form(self, row):
        route = (row.web_form_route or "").strip().strip("/")
        web_form_name = row.web_form_name

        if route and not web_form_name:
            web_form_name = frappe.db.get_value("Web Form", {"route": route}, "name")
        if web_form_name and not route:
            route = frappe.db.get_value("Web Form", web_form_name, "route") or ""

        if not web_form_name:
            return

        web_form = frappe.db.get_value(
            "Web Form",
            web_form_name,
            ["name", "title", "route", "doc_type", "print_format"],
            as_dict=True,
        )
        if not web_form:
            frappe.throw(_("Web Form introuvable: {0}").format(web_form_name))

        if (row.sync_mode or "Synchronisé depuis Web Form") != "Manuel verrouillé":
            row.web_form_name = web_form.name
            row.web_form_route = "/" + (web_form.route or route).strip("/")
            row.doctype_name = web_form.doc_type or row.doctype_name
            row.dt_label = row.dt_label or web_form.title or web_form.doc_type
            row.list_url = row.list_url or f"/app/{frappe.scrub(row.doctype_name).replace('_', '-')}"
            row.print_format = row.print_format or web_form.print_format or self._default_print_format(row.doctype_name)

    def _validate_entry(self, row):
        if not row.doctype_name or not frappe.db.exists("DocType", row.doctype_name):
            frappe.throw(_("DocType dashboard invalide: {0}").format(row.doctype_name or "vide"))

        meta = frappe.get_meta(row.doctype_name)
        for fieldname, label in ((row.status_field, _("champ statut")), (row.date_field, _("champ date"))):
            if fieldname and fieldname not in {"docstatus", "creation", "modified"} and not meta.has_field(fieldname):
                frappe.throw(_("{0} invalide pour {1}: {2}").format(label, row.doctype_name, fieldname))

        if row.amount_field and not meta.has_field(row.amount_field):
            frappe.throw(_("Champ montant invalide pour {0}: {1}").format(row.doctype_name, row.amount_field))

        if row.print_format:
            owner_dt = frappe.db.get_value("Print Format", row.print_format, "doc_type")
            if owner_dt and owner_dt != row.doctype_name:
                frappe.throw(_("Le Print Format {0} appartient à {1}, pas à {2}").format(row.print_format, owner_dt, row.doctype_name))

    def _default_print_format(self, doctype_name):
        if not doctype_name:
            return None
        preferred = frappe.db.get_value(
            "Print Format",
            {"doc_type": doctype_name, "name": ["like", "%KYA%"]},
            "name",
        )
        return preferred or frappe.db.get_value("Print Format", {"doc_type": doctype_name, "standard": "Yes"}, "name")

    def _fingerprint(self, row):
        payload = {
            "module_key": row.module_key,
            "module_label": row.module_label,
            "department": row.department,
            "service_label": row.service_label,
            "team_label": row.team_label,
            "doctype_name": row.doctype_name,
            "web_form_name": row.web_form_name,
            "web_form_route": row.web_form_route,
            "status_field": row.status_field,
            "date_field": row.date_field,
            "amount_field": row.amount_field,
            "print_format": row.print_format,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
