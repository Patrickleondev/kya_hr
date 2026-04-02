# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DemandeAchatKYA(Document):
    def validate(self):
        self.set_employee_details()
        self.calculate_totals()
        self.set_palier()

    def set_employee_details(self):
        if self.employee and not self.employee_name:
            self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")

    def calculate_totals(self):
        total = 0
        for row in self.items or []:
            row.montant = (row.quantite or 0) * (row.prix_unitaire or 0)
            total += row.montant
        self.montant_total = total

    def set_palier(self):
        if self.montant_total >= 2000000:
            self.palier = "Palier 3 (> 2 000 000 XOF) — Chef + DGA + DG"
        elif self.montant_total >= 100000:
            self.palier = "Palier 2 (100 000 – 2 000 000 XOF) — Chef + DGA"
        else:
            self.palier = "Palier 1 (< 100 000 XOF) — Chef seul"

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

        # Chef signs: state moves to En attente DAAF or Approuvé (palier 1)
        if ws in ("En attente DAAF", "Approuvé") and not self.get("signataire_chef"):
            if self.workflow_state != "Approuvé" or self.montant_total < 100000:
                self.db_set("signataire_chef", name, update_modified=False)
                self.db_set("date_signature_chef", today, update_modified=False)

        # DGA/DAAF signs: state moves to En attente DG or Approuvé (palier 2)
        if ws in ("En attente DG", "Approuvé") and not self.get("signataire_dga"):
            if self.montant_total >= 100000:
                self.db_set("signataire_dga", name, update_modified=False)
                self.db_set("date_signature_dga", today, update_modified=False)

        # DG signs: state moves to Approuvé (palier 3)
        if ws == "Approuvé" and self.montant_total >= 2000000 and not self.get("signataire_dg"):
            self.db_set("signataire_dg", name, update_modified=False)
            self.db_set("date_signature_dg", today, update_modified=False)
