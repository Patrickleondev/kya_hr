"""Registre RH des prestataires externes (feuille « Prestataires » du
classeur RH) — hors effectif salarié. Durée et statut calculés."""
from frappe.model.document import Document

from kya_hr.kya_hr.doctype.stagiaire_rh_kya.stagiaire_rh_kya import (
    duree_lisible, statut_periode,
)


class PrestataireKYA(Document):
    def validate(self):
        self.duree = duree_lisible(self.date_debut_contrat, self.date_fin_contrat)
        self.statut = statut_periode(self.date_debut_contrat, self.date_fin_contrat)
