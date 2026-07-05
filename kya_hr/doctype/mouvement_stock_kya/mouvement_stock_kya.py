# -*- coding: utf-8 -*-
"""Mouvement Stock KYA — grand livre de stock maison.

Chaque ligne = un mouvement élémentaire (entrée +, sortie −, retour +,
inventaire/ajustement Δ) pour un article, dans un magasin, avec un état
(bon état / en réparation…). Le SOLDE n'est PAS stocké : il se calcule en
sommant les mouvements (cf. kya_hr.api.stock_kya). Cela évite tout
désync solde↔mouvements. Les fiches (PV entrée/sortie/retour, inventaire)
écrivent ici à la validation au lieu de passer par ERPNext Stock Entry.
"""
import frappe
from frappe.model.document import Document


class MouvementStockKYA(Document):
    pass
