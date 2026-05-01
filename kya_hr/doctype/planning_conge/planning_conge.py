# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from kya_hr.utils.approval_guards import block_self_approval


class PlanningConge(Document):
    def validate(self):
        block_self_approval(self)
        self.set_employee_details()
        self.calculate_total_days()
        self.validate_periods()

    def set_employee_details(self):
        if self.employee and not self.employee_name:
            self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")

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
