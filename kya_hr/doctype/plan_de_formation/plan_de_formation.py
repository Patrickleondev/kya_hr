# -*- coding: utf-8 -*-
"""Plan de Formation — la RH compile les besoins retenus, le DG sélectionne, la RH chiffre.

Circuit : Compilé → Soumis au DG → Sélection DG (coche par ligne) → Chiffrage RH
(coûts) → Validé → En suivi. Les totaux (nb, coût) sont recalculés à chaque save.
"""
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, now_datetime


class PlandeFormation(Document):
    def validate(self):
        if self.workflow_state and self.workflow_state != self.statut:
            self.statut = self.workflow_state
        self.nb_formations = len(self.lignes or [])
        retenues = [l for l in (self.lignes or []) if l.retenu_dg]
        self.nb_retenues_dg = len(retenues)
        # Coût total = somme des coûts des lignes retenues par le DG
        self.cout_total = sum(flt(l.cout) for l in retenues)
        if self.statut == "Soumis au DG" and not self.date_soumission_dg:
            self.date_soumission_dg = now_datetime()

    @frappe.whitelist()
    def compiler_depuis_besoins(self, annee=None):
        """Importe toutes les lignes 'Retenu' des Besoins de Formation traités.

        Évite les doublons (par besoin source + intitulé). Retourne le nb ajouté.
        """
        annee = cint(annee or self.annee)
        besoins = frappe.get_all(
            "Besoin de Formation",
            filters={"annee": annee, "statut": ["in", ["En revue RH", "Traité"]]},
            fields=["name", "equipe"],
        )
        existing = {(l.besoin_source, l.intitule) for l in (self.lignes or [])}
        added = 0
        for b in besoins:
            doc = frappe.get_doc("Besoin de Formation", b.name)
            for l in doc.lignes:
                if l.statut_rh != "Retenu":
                    continue
                key = (b.name, l.intitule)
                if key in existing:
                    continue
                self.append("lignes", {
                    "besoin_source": b.name,
                    "equipe": b.equipe,
                    "intitule": l.intitule,
                    "priorite": l.priorite,
                    "nb_participants": l.nb_participants,
                    "justification": l.justification,
                    "statut_suivi": "À planifier",
                })
                existing.add(key)
                added += 1
        return added
