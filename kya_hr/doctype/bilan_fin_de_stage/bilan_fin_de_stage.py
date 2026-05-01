# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from kya_hr.utils.approval_guards import block_self_approval


class BilanFinDeStage(Document):
    def validate(self):
        block_self_approval(self)
        self.validate_dates()
        self.compute_mention()
        self.set_employee_details()

    def validate_dates(self):
        if self.date_debut and self.date_fin:
            if self.date_fin < self.date_debut:
                frappe.throw("La date de fin ne peut pas être antérieure à la date de début.")

    def compute_mention(self):
        """Calcule automatiquement la mention à partir de la note globale."""
        if self.note_globale is not None:
            note = int(self.note_globale)
            if note < 8:
                self.mention = "Insuffisant"
            elif note < 10:
                self.mention = "Passable"
            elif note < 12:
                self.mention = "Assez Bien"
            elif note < 16:
                self.mention = "Bien"
            else:
                self.mention = "Très Bien"

    def set_employee_details(self):
        if self.employee and not self.employee_name:
            self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
