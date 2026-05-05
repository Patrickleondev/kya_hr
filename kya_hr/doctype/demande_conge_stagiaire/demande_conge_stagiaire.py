import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, today

from kya_hr.utils.approval_guards import block_self_approval


class DemandeCongeStagiaire(Document):
    def validate(self):
        block_self_approval(self)
        self._calculate_nombre_jours()
        self._auto_sign_stagiaire()

    def _calculate_nombre_jours(self):
        if self.date_debut and self.date_fin:
            nb = date_diff(self.date_fin, self.date_debut) + 1
            if nb < 1:
                frappe.throw("La date de fin doit être postérieure à la date de début.")
            self.nombre_jours = nb

    def _auto_sign_stagiaire(self):
        if not self.signataire_stagiaire and self.employee_name:
            self.signataire_stagiaire = self.employee_name
            self.date_signature_stagiaire = today()
