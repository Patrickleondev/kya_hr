# -*- coding: utf-8 -*-
"""Client KYA — répertoire client maison (sans surcharge du Customer ERPNext).

Le Customer/Project natif reste réservé au CRM commercial ; ici on tient un
répertoire léger pour les DESTINATIONS de sorties de matériel."""

import frappe
from frappe.model.document import Document


class ClientKYA(Document):
    def validate(self):
        if self.nom_client:
            self.nom_client = " ".join(self.nom_client.split())


@frappe.whitelist()
def creer_ou_recuperer(nom_client):
    """Idempotent sur le nom : crée le Client KYA s'il manque, sinon le retourne."""
    nom_client = " ".join((nom_client or "").split())
    if not nom_client:
        frappe.throw(frappe._("Nom de client vide."))
    existing = frappe.db.get_value("Client KYA", {"nom_client": nom_client}, "name")
    if existing:
        return existing
    doc = frappe.new_doc("Client KYA")
    doc.nom_client = nom_client
    doc.flags.ignore_permissions = True
    doc.insert()
    return doc.name
