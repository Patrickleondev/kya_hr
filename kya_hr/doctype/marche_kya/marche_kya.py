import frappe
from frappe.model.document import Document
from frappe.utils import flt, date_diff


COUT_FIELDS = [
    "cout_supports_pv", "cout_supports_batteries", "cout_modules_pv", "cout_batteries",
    "cout_onduleurs", "cout_cables", "cout_terre", "cout_protection",
    "cout_accessoires_cablage", "cout_gestionnaire",
    "frais_carburant", "frais_location_camion", "frais_perdiems",
    "frais_hebergement", "frais_autres",
]


class MarcheKYA(Document):
    def validate(self):
        self._compute_duree()
        self._compute_cout_total()
        self._compute_marges()

    def _compute_duree(self):
        if self.date_debut and self.date_fin:
            self.duree_jours = date_diff(self.date_fin, self.date_debut)

    def _compute_cout_total(self):
        self.cout_total_realisation = sum(flt(self.get(f) or 0) for f in COUT_FIELDS)

    def _compute_marges(self):
        avance = flt(self.montant_avance_demarrage or 0)
        budget = flt(self.budget_previsionnel or 0)
        cout = flt(self.cout_total_realisation or 0)
        facture = flt(self.montant_total_facture or 0)
        taxes = flt(self.taxes or 0)

        self.ecart_avance = cout - avance
        self.ecart_budget_previsionnel = cout - budget
        self.marge_brute = facture - cout
        self.marge_nette = self.marge_brute - taxes
