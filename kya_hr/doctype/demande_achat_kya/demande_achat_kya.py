# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DemandeAchatKYA(Document):
    def validate(self):
        self.set_employee_details()
        self._fetch_chef_email()
        self.calculate_totals()
        self.set_palier()

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

    def _fetch_chef_email(self):
        """Auto-fetch email of employee's direct chef via Employee.reports_to."""
        if not self.get("employee") or self.chef_equipe_email:
            return
        reports_to = frappe.db.get_value("Employee", self.employee, "reports_to")
        if reports_to:
            user_id = frappe.db.get_value("Employee", reports_to, "user_id")
            if user_id:
                email = frappe.db.get_value("User", user_id, "email")
                self.chef_equipe_email = email or user_id

    def calculate_totals(self):
        total = 0
        for row in self.items or []:
            row.montant = (row.quantite or 0) * (row.prix_unitaire or 0)
            total += row.montant
        self.montant_total = total

    def set_palier(self):
        if self.montant_total >= 2000000:
            self.palier = "Palier 3 (> 2 000 000 XOF) — Chef + DAAF + DG"
        elif self.montant_total >= 100000:
            self.palier = "Palier 2 (100 000 – 2 000 000 XOF) — Chef + DAAF + DG"
        else:
            self.palier = "Palier 1 (< 100 000 XOF) — Chef + DAAF"

    def before_submit(self):
        if self.workflow_state == "Approuvé":
            self.statut = "Approuvé"

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self.capture_signature()

    def capture_signature(self):
        """Auto-fill approver name/date when they sign at their workflow level."""
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        name = emp or frappe.utils.get_fullname(user)
        today = frappe.utils.today()
        ws = self.workflow_state

        # Chef signs: state moves to En attente DAAF
        if ws == "En attente DAAF" and not self.get("signataire_chef"):
                self.db_set("signataire_chef", name, update_modified=False)
                self.db_set("date_signature_chef", today, update_modified=False)

        # DAAF signs: state moves to Approuvé (palier 1) or En attente DG (palier 2+)
        if ws in ("En attente DG", "Approuvé") and not self.get("signataire_dga"):
            if self.montant_total >= 0:
                self.db_set("signataire_dga", name, update_modified=False)
                self.db_set("date_signature_dga", today, update_modified=False)

        # DG signs: state moves to Approuvé (palier 3)
        if ws == "Approuvé" and self.montant_total >= 2000000 and not self.get("signataire_dg"):
            self.db_set("signataire_dg", name, update_modified=False)
            self.db_set("date_signature_dg", today, update_modified=False)
