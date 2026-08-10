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
from frappe.utils import flt


class MouvementStockKYA(Document):
    def validate(self):
        """Garde-fou de signe : une Sortie DOIT décrémenter, une Entrée/Retour
        DOIT incrémenter — quel que soit le chemin de saisie (API métier via
        enregistrer_mouvements, ou fiche créée/éditée à la main depuis le Desk).
        Sans ce contrôle, une « Sortie » saisie en positif ajoute au lieu de
        retirer du grand livre (incident constaté le 05/08/2026 sur ART-00449,
        saisi directement hors des fonctions métier qui, elles, forcent déjà
        le signe)."""
        qte = flt(self.quantite)
        if self.type_mouvement == "Sortie" and qte > 0:
            self.quantite = -qte
        elif self.type_mouvement in ("Entrée", "Retour") and qte < 0:
            self.quantite = -qte
