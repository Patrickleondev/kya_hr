# -*- coding: utf-8 -*-
"""Projet KYA — répertoire projet/chantier maison (destinations de sorties)."""

import frappe
from frappe.model.document import Document


class ProjetKYA(Document):
    def validate(self):
        if self.nom_projet:
            self.nom_projet = " ".join(self.nom_projet.split())


@frappe.whitelist()
def creer_ou_recuperer(nom_projet, client=None):
    """Idempotent sur le nom : crée le Projet KYA s'il manque, sinon le retourne.
    Lie le Client KYA si fourni."""
    nom_projet = " ".join((nom_projet or "").split())
    if not nom_projet:
        frappe.throw(frappe._("Nom de projet vide."))
    existing = frappe.db.get_value("Projet KYA", {"nom_projet": nom_projet}, "name")
    if existing:
        if client and not frappe.db.get_value("Projet KYA", existing, "client"):
            frappe.db.set_value("Projet KYA", existing, "client", client)
        return existing
    doc = frappe.new_doc("Projet KYA")
    doc.nom_projet = nom_projet
    if client:
        doc.client = client
    doc.flags.ignore_permissions = True
    doc.insert()
    return doc.name
