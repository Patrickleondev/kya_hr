import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class KYASoPClient(Document):
    def validate(self):
        self._compute_solde_du()
        self._compute_statut_paiement()
        self._avertir_avance_non_deduite()

    def _compute_solde_du(self):
        if self.mode_paiement == "Tranche":
            total_paye = sum(flt(l.montant_paye or 0) for l in (self.echeancier or []))
            self.solde_du = flt(self.montant_total or 0) - total_paye
        elif self.mode_paiement == "Cash":
            self.solde_du = flt(self.montant_total or 0) - flt(self.montant_avance or 0)
        elif self.mode_paiement == "Location":
            total_paye = sum(flt(l.montant_paye or 0) for l in (self.etat_paiement_location or []))
            self.solde_du = flt(self.montant_total or 0) - total_paye

    def _avertir_avance_non_deduite(self):
        """En Tranche et en Location, le solde se calcule sur les paiements
        SAISIS dans le tableau, pas sur le champ « Avance versée ». Une avance
        renseignée sans aucun paiement dans le tableau passait silencieusement
        à la trappe : le client apparaissait comme devant la totalité, ce qui
        fausse le suivi des encours. On alerte sans bloquer l'enregistrement,
        car la règle de gestion reste celle du tableau (l'avance y figure
        normalement comme première ligne)."""
        if self.mode_paiement not in ("Tranche", "Location"):
            return
        if flt(self.montant_avance or 0) <= 0:
            return
        lignes = (self.echeancier if self.mode_paiement == "Tranche"
                  else self.etat_paiement_location) or []
        if sum(flt(l.montant_paye or 0) for l in lignes) > 0:
            return
        frappe.msgprint(
            _("Une avance de {0} est renseignée, mais aucun paiement n'est saisi dans le "
              "tableau ci-dessous. En mode « {1} », le solde dû se calcule UNIQUEMENT à "
              "partir de ce tableau : l'avance doit y figurer comme première ligne, sinon "
              "le client apparaîtra comme devant la totalité.").format(
                  frappe.format_value(flt(self.montant_avance), {"fieldtype": "Currency"}),
                  self.mode_paiement),
            title=_("Avance non déduite du solde"), indicator="orange")

    def _compute_statut_paiement(self):
        if flt(self.solde_du or 0) <= 0:
            self.statut_paiement = "Soldé"
            self.statut = "Soldé"
        elif flt(self.solde_du or 0) < flt(self.montant_total or 0):
            self.statut_paiement = "Partiel"
        else:
            self.statut_paiement = "Non soldé"
