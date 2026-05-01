import frappe
from frappe.model.document import Document
from frappe.utils import flt, formatdate, today

from kya_hr.utils.approval_guards import block_self_approval


MOIS_FR = {
    1: "JANVIER", 2: "FÉVRIER", 3: "MARS", 4: "AVRIL", 5: "MAI", 6: "JUIN",
    7: "JUILLET", 8: "AOÛT", 9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DÉCEMBRE",
}


class EtatRecapCheques(Document):
    """État récapitulatif hebdomadaire des chèques émis.

    Workflow: Comptable/DFC rédige → DFC valide → Envoi DG + DGA.
    """

    def validate(self):
        block_self_approval(self)
        self._compute_totals()
        self._compute_libelle_periode()
        self._auto_sign_redacteur()

    def _compute_totals(self):
        self.total_montant = sum(flt(l.montant or 0) for l in (self.lignes or []))
        self.nombre_cheques = len(self.lignes or [])

    def _compute_libelle_periode(self):
        if self.semaine_du and self.semaine_au:
            d1 = frappe.utils.getdate(self.semaine_du)
            d2 = frappe.utils.getdate(self.semaine_au)
            mois = MOIS_FR.get(d2.month, d2.strftime("%B").upper())
            if d1.month == d2.month:
                self.libelle_periode = f"du {d1.day} au {d2.day} {mois} {d2.year}"
            else:
                mois1 = MOIS_FR.get(d1.month, d1.strftime("%B").upper())
                self.libelle_periode = f"du {d1.day} {mois1} au {d2.day} {mois} {d2.year}"

    def _auto_sign_redacteur(self):
        if self.redacteur and not self.signataire_redacteur:
            emp_name = frappe.db.get_value("Employee", self.redacteur, "employee_name")
            self.signataire_redacteur = emp_name or self.redacteur
            self.date_signature_redacteur = today()
