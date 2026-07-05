# Copyright (c) 2026, KYA-Energy Group
"""Évolution Carrière KYA — un évènement du parcours d'un salarié.

Champ calculé : duree = "X an(s) Y mois" (période close) ou
"En cours depuis le JJ/MM/AAAA" (date de fin vide)."""

import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, formatdate, getdate


class EvolutionCarriereKYA(Document):
    def validate(self):
        self.duree = self._compute_duree()

    def _compute_duree(self):
        if not self.date_debut:
            return ""
        if not self.date_fin:
            return "En cours depuis le " + formatdate(self.date_debut, "dd/MM/yyyy")
        jours = date_diff(getdate(self.date_fin), getdate(self.date_debut))
        if jours < 0:
            frappe.throw("La date de fin ne peut pas précéder la date de début.")
        annees = jours // 365
        mois = (jours % 365) // 30
        parts = []
        if annees:
            parts.append("%d an%s" % (annees, "s" if annees > 1 else ""))
        if mois:
            parts.append("%d mois" % mois)
        return " ".join(parts) if parts else "moins d'un mois"
