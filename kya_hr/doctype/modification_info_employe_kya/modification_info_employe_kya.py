# -*- coding: utf-8 -*-
"""Journal des modifications d'informations d'un employé.

Trace chaque changement porté sur la fiche d'un membre — par son chef d'équipe
(rôle, compétences, notes) ou par la RH/Direction (mutation : équipe, poste,
département). Sert la vue détaillée du DG et le suivi de l'employé (Phase 3).
"""
import frappe
from frappe.model.document import Document


class ModificationInfoEmployeKYA(Document):
    def before_insert(self):
        if not self.date_modif:
            self.date_modif = frappe.utils.now_datetime()
        if not self.modifie_par:
            self.modifie_par = frappe.session.user
        if not self.modifie_par_nom:
            self.modifie_par_nom = frappe.utils.get_fullname(self.modifie_par)
