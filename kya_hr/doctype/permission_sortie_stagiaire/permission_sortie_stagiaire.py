# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, today, get_fullname


class PermissionSortieStagiaire(Document):
    def validate(self):
        self.validate_employee_is_intern()
        self.set_employee_details()
        self.calc_nombre_jours()

    def validate_employee_is_intern(self):
        if self.employee:
            emp_type = frappe.db.get_value("Employee", self.employee, "employment_type")
            if emp_type and emp_type != "Stage":
                frappe.throw(
                    "Seuls les stagiaires peuvent utiliser ce formulaire. "
                    "Les employés doivent utiliser le module Permission de Sortie Employé."
                )

    def set_employee_details(self):
        if self.employee and not self.employee_name:
            self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")

    def calc_nombre_jours(self):
        """Calculate number of days when date_fin is set."""
        if self.date_fin and self.date_sortie:
            diff = date_diff(self.date_fin, self.date_sortie)
            if diff < 0:
                frappe.throw("La date de fin ne peut pas être antérieure à la date de début.")
            self.nombre_jours = diff + 1
        else:
            self.nombre_jours = 1

    def before_submit(self):
        if self.workflow_state == "Approuvé":
            self.statut = "Approuvé"

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_approver_signature()

    def _stamp_approver_signature(self):
        """Auto-fill approver name and date when they approve at their workflow level."""
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        name = emp or get_fullname(user)
        now = today()
        ws = self.workflow_state

        if ws == "En attente Resp. Stagiaires" and not self.get("signataire_chef"):
            self.db_set("signataire_chef", name, update_modified=False)
            self.db_set("date_signature_chef", now, update_modified=False)
        elif ws == "En attente DG" and not self.get("signataire_resp"):
            self.db_set("signataire_resp", name, update_modified=False)
            self.db_set("date_signature_resp", now, update_modified=False)
        elif ws == "Approuvé" and not self.get("signataire_dg"):
            self.db_set("signataire_dg", name, update_modified=False)
            self.db_set("date_signature_dg", now, update_modified=False)
