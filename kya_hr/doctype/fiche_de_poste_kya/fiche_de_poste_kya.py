# -*- coding: utf-8 -*-
"""Fiche de poste KYA — un exemplaire nominatif par employé, fidèle au modèle
d'organisation KYA-ORG-CIBLE. Complète les données natives ERPNext (Employee)
par les sections « métier » : mission, attributions/tâches, autorité, indicateurs
de performance, profil requis, interfaces.

Édition partagée : la RH renseigne l'administratif ; le chef d'équipe / N+1
renseigne les ATTRIBUTIONS (tâches concrètes) et les COMPÉTENCES clés — la partie
qu'il connaît le mieux et que la RH n'a pas. Le partage d'édition est appliqué
côté client (grisage) et devra être durci en permlevel au prochain déploiement.
"""
import frappe
from frappe.model.document import Document
from frappe.utils import today


# Champs que le chef d'équipe (non-RH) peut éditer.
CHEF_FIELDS = ("attributions", "competences_cle")


class FicheDePosteKYA(Document):
    def before_insert(self):
        self.autofill()
        if not self.date_document:
            self.date_document = today()

    def validate(self):
        self.autofill()
        nom = self.employee_name or ""
        poste = self.intitule_poste or ""
        self.titre_affiche = (f"{nom} — {poste}").strip(" —") or self.name

    def autofill(self):
        if not self.employee:
            return
        emp = frappe.db.get_value(
            "Employee", self.employee,
            ["employee_name", "designation", "department", "reports_to"],
            as_dict=True) or {}
        if not self.employee_name:
            self.employee_name = emp.get("employee_name")
        if not self.intitule_poste:
            self.intitule_poste = emp.get("designation")
        if not self.departement:
            self.departement = emp.get("department")
        if not self.superieur_hierarchique and emp.get("reports_to"):
            self.superieur_hierarchique = frappe.db.get_value(
                "Employee", emp.get("reports_to"), "employee_name")
