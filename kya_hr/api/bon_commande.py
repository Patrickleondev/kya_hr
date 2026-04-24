# -*- coding: utf-8 -*-
"""API Bon de Commande KYA — création depuis Demande d'Achat."""
import frappe
from frappe import _


@frappe.whitelist()
def create_from_demande_achat(demande_name):
    """Crée (ou retourne s'il existe) un Bon Commande KYA lié à la demande."""
    if not demande_name:
        frappe.throw(_("Demande d'achat manquante"))

    existing = frappe.db.get_value("Bon Commande KYA", {"demande_achat": demande_name, "docstatus": ["<", 2]}, "name")
    if existing:
        return {"name": existing, "existed": True}

    da = frappe.get_doc("Demande Achat KYA", demande_name)
    if da.docstatus != 1 or da.statut != "Approuvé":
        frappe.throw(_("La demande d'achat doit être approuvée et soumise."))

    bc = frappe.new_doc("Bon Commande KYA")
    bc.numero_bc = f"AUTO/{da.name}"
    bc.date_bc = frappe.utils.today()
    bc.demande_achat = da.name
    bc.objet = da.objet or f"Commande issue de {da.name}"
    bc.fournisseur_nom = ""

    for it in (da.items or []):
        bc.append("articles", {
            "item_code": getattr(it, "item_code", None),
            "description": getattr(it, "description", None) or getattr(it, "designation", None) or "",
            "unite": getattr(it, "unite", None) or "U",
            "quantite": getattr(it, "quantite", None) or 1,
            "prix_unitaire": getattr(it, "prix_unitaire", None) or 0,
        })

    bc.tva_taux = 18
    bc.statut = "Brouillon"
    bc.insert(ignore_permissions=False)
    return {"name": bc.name, "existed": False}
