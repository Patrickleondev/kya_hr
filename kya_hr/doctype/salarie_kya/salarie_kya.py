# Copyright (c) 2026, KYA-Energy Group
"""Salarié KYA — registre du personnel (base RH maison, hors paie ERPNext).

Champs calculés (recalculés à chaque save, et à la volée côté dashboard/API) :
  - nom_complet             = "NOM Prénoms"
  - age                     = années depuis la date de naissance
  - anciennete_annees       = années (1 décimale) embauche → aujourd'hui (ou débauche)
  - date_admission_retraite = date de naissance + âge de retraite (Paramètres RH KYA)
  - statut_emploi           = Actif / Sorti / Retraité (Retraité = sortie motif Retraite)
"""

import frappe
from frappe.model.document import Document
from frappe.utils import add_years, date_diff, getdate, today


def _age_retraite() -> int:
    """Âge de retraite configurable (Paramètres RH KYA), défaut 60."""
    try:
        v = frappe.db.get_single_value("Parametres RH KYA", "age_retraite")
        return int(v) if v else 60
    except Exception:
        return 60


class SalarieKYA(Document):
    def validate(self):
        self.nom_complet = " ".join(
            p for p in [(self.nom or "").strip().upper(), (self.prenoms or "").strip()] if p)
        self._compute_age()
        self._compute_anciennete()
        self._compute_retraite()
        self._compute_statut()

    def _compute_age(self):
        if self.date_naissance:
            self.age = int(date_diff(today(), self.date_naissance) // 365.25)
        else:
            self.age = 0

    def _compute_anciennete(self):
        if self.date_embauche:
            fin = self.date_debauchage or today()
            self.anciennete_annees = round(date_diff(fin, self.date_embauche) / 365.25, 1)
        else:
            self.anciennete_annees = 0

    def _compute_retraite(self):
        self.date_admission_retraite = (
            add_years(getdate(self.date_naissance), _age_retraite())
            if self.date_naissance else None)

    def _compute_statut(self):
        if not self.date_debauchage:
            self.statut_emploi = "Actif"
        elif (self.motif_debauchage or "").strip().lower() == "retraite":
            self.statut_emploi = "Retraité"
        else:
            self.statut_emploi = "Sorti"
