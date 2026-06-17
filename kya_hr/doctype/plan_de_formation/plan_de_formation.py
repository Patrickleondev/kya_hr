# -*- coding: utf-8 -*-
"""Plan de Formation — la RH compile les besoins retenus, le DG sélectionne, la RH chiffre.

Circuit : Compilé → Soumis au DG → Sélection DG (coche par ligne) → Chiffrage RH
(coûts) → Validé → En suivi. Les totaux (nb, coût) sont recalculés à chaque save.
Le suivi est fait PAR EMPLOYÉ bénéficiaire (table `beneficiaires`).
"""
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, now_datetime


class PlandeFormation(Document):
    def validate(self):
        if self.workflow_state and self.workflow_state != self.statut:
            self.statut = self.workflow_state
        # Coût total de chaque ligne = direct + accessoire
        for l in (self.lignes or []):
            l.cout = flt(l.cout_direct) + flt(l.cout_accessoire)
        self.nb_formations = len(self.lignes or [])
        retenues = [l for l in (self.lignes or []) if l.retenu_dg]
        self.nb_retenues_dg = len(retenues)
        # Coût total = somme des coûts des lignes retenues par le DG
        self.cout_total = sum(flt(l.cout) for l in retenues)
        # Suivi par employé
        benes = self.beneficiaires or []
        self.nb_beneficiaires = len(benes)
        self.nb_beneficiaires_termines = len([b for b in benes if b.statut == "Terminé"])
        if self.statut == "Soumis au DG" and not self.date_soumission_dg:
            self.date_soumission_dg = now_datetime()

    @frappe.whitelist()
    def compiler_depuis_besoins(self, annee=None):
        """Importe toutes les lignes 'Retenu' des Besoins de Formation traités.

        Évite les doublons (par besoin source + intitulé). Sème aussi les
        bénéficiaires (employés concernés) pour le suivi par employé.
        Retourne le nb de lignes ajoutées.
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
                    "objectifs_vises": l.get("objectif"),
                    "priorite": l.priorite,
                    "nb_participants": l.nb_participants,
                    "justification": l.justification,
                    "statut_suivi": "À planifier",
                })
                existing.add(key)
                added += 1
                self._seed_beneficiaires(b.equipe, l.intitule, l.get("employes_concernes"))
        return added

    def _seed_beneficiaires(self, equipe, intitule, employes_concernes):
        """Crée des lignes bénéficiaires (best-effort) à partir du texte libre
        `employes_concernes` du besoin. Résout les noms vers des Employee de
        l'équipe quand c'est possible ; sinon laisse la RH compléter à la main.
        """
        if not employes_concernes:
            return
        existing = {(b.formation_ref, b.employee) for b in (self.beneficiaires or [])}
        # liste des employés de l'équipe pour le matching nom -> Employee
        emp_by_name = {}
        if equipe:
            for e in frappe.get_all("Employee",
                                    filters={"custom_kya_equipe": equipe, "status": "Active"},
                                    fields=["name", "employee_name"]):
                emp_by_name[(e.employee_name or "").strip().lower()] = e.name
        for raw in str(employes_concernes).replace(";", ",").replace("\n", ",").split(","):
            nom = raw.strip()
            if not nom or nom.lower() in ("toute l'équipe", "toute l equipe", "équipe", "equipe"):
                continue
            emp = emp_by_name.get(nom.lower())
            if not emp:
                # match partiel (prénom/nom)
                for k, v in emp_by_name.items():
                    if nom.lower() in k or k in nom.lower():
                        emp = v
                        break
            if not emp:
                continue
            if (intitule, emp) in existing:
                continue
            self.append("beneficiaires", {
                "formation_ref": intitule,
                "equipe": equipe,
                "employee": emp,
                "statut": "À planifier",
            })
            existing.add((intitule, emp))
