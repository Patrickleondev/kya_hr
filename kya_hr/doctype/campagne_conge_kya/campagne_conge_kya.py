# -*- coding: utf-8 -*-
"""Campagne de Congé KYA — objet piloté par la RH.

Une campagne = l'année de congés à planifier + la période de saisie
(ouverture/échéance) + le message envoyé aux chefs. Elle sert de point
d'entrée RH : définir → ouvrir (générer les brouillons par équipe + liens
aux chefs) → suivre les soumissions. La logique métier est dans
kya_hr.api.campagne_conges ; ce contrôleur ne fait que du calcul de titre.
"""
import frappe
from frappe.model.document import Document


class CampagneCongeKYA(Document):
    def before_save(self):
        self.titre = "Campagne congés {0}".format(self.annee or "")
