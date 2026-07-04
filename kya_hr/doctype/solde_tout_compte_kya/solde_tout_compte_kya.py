# Copyright (c) 2026, KYA-Energy Group
"""Solde de Tout Compte KYA — décompte des indemnités (calcul maison).

À l'enregistrement, appelle le moteur `api.rh_indemnites` (barèmes configurables
via Paramètres RH KYA) et remplit le détail + le total. Aucune paie ERPNext."""

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from kya_hr.kya_hr.api import rh_indemnites as I


class SoldeToutCompteKYA(Document):
    def validate(self):
        if not self.salaire_mensuel_moyen:
            self.salaire_mensuel_moyen = self.salaire_base or 0
        self._calculer()

    def _calculer(self):
        res = I.solde_tout_compte(
            self.salarie, motif_depart=self.motif_depart,
            salaire_moyen=self.salaire_mensuel_moyen, date_reference=self.date_calcul)

        self.anciennete_annees = res["anciennete"]
        self.prime_taux = res["prime_anciennete"]["taux"]
        self.total_indemnites = res["total"]

        self.set("lignes", [])
        sm = flt(res["salaire_moyen"])

        lic = res.get("indemnite_licenciement")
        if lic:
            for l in lic["lignes"]:
                if l["montant"]:
                    self.append("lignes", {
                        "libelle": "Indemnité de licenciement — %s" % l["tranche"],
                        "detail": "%.2f an(s) × %s%% × %s" % (l["annees"], l["taux"], _fmt(sm)),
                        "montant": l["montant"]})

        ret = res.get("indemnite_retraite")
        if ret:
            self.append("lignes", {
                "libelle": "Indemnité de départ à la retraite (Art. 70)",
                "detail": "%s%% de l'indemnité de licenciement (%s)%s" % (
                    ret["taux"], _fmt(ret["base_licenciement"]),
                    " — plancher 3 mois appliqué" if ret["plancher_applique"] else ""),
                "montant": ret["total"]})

        prime = res["prime_anciennete"]
        if prime["montant"]:
            self.append("lignes", {
                "libelle": "Prime d'ancienneté (Art. 40)",
                "detail": "%s%% × salaire de base (%s)" % (prime["taux"], _fmt(prime["salaire_base"])),
                "montant": prime["montant"]})


def _fmt(v):
    return "{:,.0f}".format(flt(v)).replace(",", " ")
