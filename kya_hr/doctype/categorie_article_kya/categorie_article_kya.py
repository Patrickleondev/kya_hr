# -*- coding: utf-8 -*-
# Copyright (c) 2026, KYA-Energy Group and contributors
"""Catégorie d'article (maison) — typologie du stock KYA.

Master simple : sert à classer les Articles KYA (Modules PV, Onduleurs,
Batteries, Câbles, Protection, Luminaires, Outillage, Consommables…), comme
demandé par le manuel de procédures (chaque article rattaché à une catégorie).
"""
from frappe.model.document import Document


class CategorieArticleKYA(Document):
    pass
