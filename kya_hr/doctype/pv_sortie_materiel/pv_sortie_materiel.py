# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PVSortieMateriel(Document):
    def validate(self):
        self.validate_items()
        self.set_demandeur_info()

    def validate_items(self):
        if not self.items:
            frappe.throw("Veuillez ajouter au moins un article dans la liste du matériel.")
        for item in self.items:
            if item.qte_demandee and item.qte_demandee <= 0:
                frappe.throw(f"La quantité demandée pour '{item.designation}' doit être positive.")

    def set_demandeur_info(self):
        """Auto-fill demandeur from session user's Employee record."""
        if not self.demandeur_nom:
            emp = frappe.db.get_value(
                "Employee", {"user_id": frappe.session.user},
                ["employee_name"], as_dict=True
            )
            if emp:
                self.demandeur_nom = emp.employee_name
                self.demandeur_date = frappe.utils.today()

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_approver_signature()

    def _stamp_approver_signature(self):
        """Auto-fill approver name and date when they approve at their workflow level."""
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        today = frappe.utils.today()
        ws = self.workflow_state

        if ws == "En attente Magasin" and not self.get("magasin_nom"):
            self.db_set("magasin_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
            self.db_set("magasin_date", today, update_modified=False)
        elif ws == "En attente Audit" and not self.get("audit_nom"):
            self.db_set("audit_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
            self.db_set("audit_date", today, update_modified=False)
        elif ws == "En attente Direction" and not self.get("dga_nom"):
            self.db_set("dga_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
            self.db_set("dga_date", today, update_modified=False)
