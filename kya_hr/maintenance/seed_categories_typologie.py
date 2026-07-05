# -*- coding: utf-8 -*-
"""Sème les 14 catégories (typologies d'équipement) de la fiche officielle KYA
AEA-ENG-13-V01. Le picker « Catégorie » de la saisie/import propose ainsi
d'emblée la vraie nomenclature du magasin (au lieu d'un champ libre au hasard).

Idempotent : on n'ajoute que ce qui manque, on ne renomme et ne supprime rien
(les catégories libres déjà saisies par la magasinière restent intactes).
"""
import frappe

# Ordre = celui du classeur « Répartition par typologie d'équipement ».
TYPOLOGIES = [
    "Appareillage & protection électrique",
    "Composants & produits luminaires",
    "Stockage d'énergie (batteries & composants)",
    "Outillage & équipements de chantier",
    "Câbles & conducteurs",
    "Cheminement & accessoires de pose",
    "Onduleurs & électronique de puissance",
    "Modules PV & supports",
    "Visserie & fixations",
    "Éclairage & luminaires",
    "Connectique & cosses",
    "Divers, sécurité & mobilier",
    "Régulateurs & gestion de charge",
    "Solutions KYA-SOP & coffrets",
]


def execute() -> dict:
    if not frappe.db.table_exists("Categorie Article KYA"):
        return {"cree": 0, "skipped": "doctype absent"}
    cree = 0
    for nom in TYPOLOGIES:
        if not frappe.db.exists("Categorie Article KYA", nom):
            doc = frappe.new_doc("Categorie Article KYA")
            doc.categorie = nom
            doc.flags.ignore_permissions = True
            doc.insert()
            cree += 1
    if cree:
        frappe.db.commit()
    return {"cree": cree, "total_typologies": len(TYPOLOGIES)}
