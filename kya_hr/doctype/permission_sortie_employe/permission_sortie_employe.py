# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PermissionSortieEmploye(Document):
    def validate(self):
        self.validate_employee_is_not_intern()
        self.set_employee_details()

    def before_insert(self):
        """When HR creates manually via Desk, start workflow at 'En attente RH'
        to skip the Chef step (RH is the creator)."""
        if not self.flags.via_web_form:
            user_roles = frappe.get_roles(frappe.session.user)
            if "HR Manager" in user_roles or "HR User" in user_roles:
                self.workflow_state = "En attente RH"
                # Auto-fill chef bypass
                name = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "employee_name")
                if not name:
                    name = frappe.utils.get_fullname(frappe.session.user)
                self.signataire_chef = (name or "") + " (Créé par RH)"
                self.date_signature_chef = frappe.utils.today()

    def validate_employee_is_not_intern(self):
        if self.employee:
            emp_type = frappe.db.get_value("Employee", self.employee, "employment_type")
            if emp_type and emp_type == "Stage":
                frappe.throw(
                    "Les stagiaires doivent utiliser le formulaire Permission de Sortie Stagiaire."
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
        self.capture_signature()

    def capture_signature(self):
        """Auto-fill approver name/date when they sign at their workflow level."""
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        name = emp or frappe.utils.get_fullname(user)
        today = frappe.utils.today()
        ws = self.workflow_state

        # Chef signs → state moves to "En attente RH"
        if ws == "En attente RH" and not self.get("signataire_chef"):
            self.db_set("signataire_chef", name, update_modified=False)
            self.db_set("date_signature_chef", today, update_modified=False)

        # RH signs → state moves to "En attente Direction"
        if ws == "En attente Direction" and not self.get("signataire_rh"):
            self.db_set("signataire_rh", name, update_modified=False)
            self.db_set("date_signature_rh", today, update_modified=False)
            # If Chef was bypassed (Absence Chef → En attente RH), mark it
            if not self.get("signataire_chef"):
                self.db_set("signataire_chef", name + " (Absence Chef)", update_modified=False)
                self.db_set("date_signature_chef", today, update_modified=False)

        # DGA signs → state moves to "Approuvé"
        if ws == "Approuvé" and not self.get("signataire_dga"):
            self.db_set("signataire_dga", name, update_modified=False)
            self.db_set("date_signature_dga", today, update_modified=False)
            # If DGA was bypassed (Absence DGA), mark it
            if not self.get("signataire_rh") and self.get("signataire_chef"):
                # RH bypassed to DGA directly — shouldn't happen normally
                pass
            # If Chef was bypassed earlier, keep that mark
            # If DGA absent and someone else validated
            if self.workflow_state == "Approuvé" and not self.get("signature_dga"):
                # Validated via "Valider (Absence DGA)" — no DGA signature drawn
                bypass_action = frappe.db.get_value(
                    "Workflow Action",
                    {"reference_name": self.name, "status": "Completed"},
                    "workflow_action",
                    order_by="creation desc"
                )
                if bypass_action and "Absence DGA" in (bypass_action or ""):
                    self.db_set("signataire_dga", name + " (Absence DGA)", update_modified=False)
