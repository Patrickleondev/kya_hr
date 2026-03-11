# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PermissionSortieStagiaire(Document):
    def validate(self):
        self.validate_employee_is_intern()
        self.set_employee_details()

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

    def before_submit(self):
        if self.workflow_state == "Approuvé":
            self.statut = "Approuvé"

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_approver_signature()

    def _stamp_approver_signature(self):
        """Auto-fill approver name when they approve at their workflow level."""
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        today = frappe.utils.today()
        ws = self.workflow_state

        if ws == "En attente Resp. Stagiaires" and not self.get("chef_nom"):
            self.db_set("chef_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
        elif ws == "En attente DG" and not self.get("resp_stagiaires_nom"):
            self.db_set("resp_stagiaires_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
        elif ws == "Approuvé" and not self.get("dg_nom"):
            self.db_set("dg_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
