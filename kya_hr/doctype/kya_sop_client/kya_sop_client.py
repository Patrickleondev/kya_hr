import frappe
from frappe.model.document import Document
from frappe.utils import flt


class KYASoPClient(Document):
    def validate(self):
        self._compute_solde_du()
        self._compute_statut_paiement()

    def _compute_solde_du(self):
        if self.mode_paiement == "Tranche":
            total_paye = sum(flt(l.montant_paye or 0) for l in (self.echeancier or []))
            self.solde_du = flt(self.montant_total or 0) - total_paye
        elif self.mode_paiement == "Cash":
            self.solde_du = flt(self.montant_total or 0) - flt(self.montant_avance or 0)
        elif self.mode_paiement == "Location":
            total_paye = sum(flt(l.montant_paye or 0) for l in (self.etat_paiement_location or []))
            self.solde_du = flt(self.montant_total or 0) - total_paye

    def _compute_statut_paiement(self):
        if flt(self.solde_du or 0) <= 0:
            self.statut_paiement = "Soldé"
            self.statut = "Soldé"
        elif flt(self.solde_du or 0) < flt(self.montant_total or 0):
            self.statut_paiement = "Partiel"
        else:
            self.statut_paiement = "Non soldé"
