# -*- coding: utf-8 -*-
"""Besoin de Formation — un chef d'équipe soumet les besoins en formation de son équipe.

Circuit : le chef saisit les lignes (intitulé, compétence, pourquoi) puis soumet
à la RH. La RH s'entretient avec lui, marque chaque ligne Retenu/Écarté, puis
compile les lignes retenues dans un Plan de Formation (soumis au DG).
"""
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class BesoindeFormation(Document):
    def validate(self):
        # Le workflow pilote workflow_state ; on reflète dans statut (affichage/filtres)
        if self.workflow_state and self.workflow_state != self.statut:
            self.statut = self.workflow_state
        # Défaut chef = employé de l'utilisateur courant
        if not self.chef_equipe:
            emp = frappe.db.get_value(
                "Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
            )
            if emp:
                self.chef_equipe = emp
        # Horodatage de soumission
        if self.statut == "Soumis à la RH" and not self.date_soumission:
            self.date_soumission = now_datetime()

    def nb_retenus(self):
        return len([l for l in (self.lignes or []) if l.statut_rh == "Retenu"])
