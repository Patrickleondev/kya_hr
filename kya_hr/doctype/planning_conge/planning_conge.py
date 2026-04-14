# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PlanningConge(Document):
    def validate(self):
        self.set_employee_details()
        self.calculate_total_days()
        self.validate_periods()

    def set_employee_details(self):
        if self.employee:
            emp = frappe.db.get_value(
                "Employee", self.employee,
                ["employee_name", "user_id"], as_dict=True
            )
            if emp:
                if not self.employee_name:
                    self.employee_name = emp.employee_name
                if emp.user_id:
                    self.employee_email = emp.user_id

    def calculate_total_days(self):
        total = 0
        for row in self.periodes or []:
            if row.date_debut and row.date_fin:
                days = frappe.utils.date_diff(row.date_fin, row.date_debut) + 1
                row.nb_jours = max(days, 0)
                total += row.nb_jours
        self.total_jours = total

    def validate_periods(self):
        for row in self.periodes or []:
            if row.date_debut and row.date_fin:
                if frappe.utils.getdate(row.date_fin) < frappe.utils.getdate(row.date_debut):
                    frappe.throw(
                        f"Ligne {row.idx} : la date de fin doit être postérieure à la date de début."
                    )

    def before_submit(self):
        if self.workflow_state == "Approuvé":
            self.statut = "Approuvé"

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self.capture_signature()

    def capture_signature(self):
        """Auto-fill approver name/date when workflow transitions."""
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        name = emp or frappe.utils.get_fullname(user)
        today = frappe.utils.today()
        ws = self.workflow_state

        # RH approves → state moves to "En attente DG"
        if ws == "En attente DG" and not self.get("signataire_rh"):
            self.db_set("signataire_rh", name, update_modified=False)
            self.db_set("date_signature_rh", today, update_modified=False)

        # DG approves → state moves to "Approuvé"
        if ws == "Approuvé" and not self.get("signataire_dg"):
            self.db_set("signataire_dg", name, update_modified=False)
            self.db_set("date_signature_dg", today, update_modified=False)

    def on_submit(self):
        """Capture employee signature on submit."""
        if not self.get("signataire_employe"):
            emp_name = self.employee_name or frappe.utils.get_fullname(frappe.session.user)
            self.db_set("signataire_employe", emp_name, update_modified=False)
            self.db_set("date_signature_employe", frappe.utils.today(), update_modified=False)
