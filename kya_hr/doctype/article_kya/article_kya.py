# -*- coding: utf-8 -*-
# Copyright (c) 2026, KYA-Energy Group and contributors
"""Article KYA (maison, SANS code) — catalogue du stock.

Décision métier (03/07/2026) : on abandonne l'Item ERPNext et son code. Un
article = une **désignation** (la clé que voit la magasinière, telle quelle sur
la fiche d'inventaire) + une **catégorie** + une **unité**. Le `name` interne
(ART-#####) est purement technique et n'est jamais saisi ni affiché (title_field
= designation, show_title_field_in_link = 1).

Le grand-livre `Mouvement Stock KYA` référence désormais ce doctype.
"""
import frappe
from frappe.model.document import Document


class ArticleKYA(Document):
    def validate(self):
        # Normalise la désignation (espaces multiples, bornes) pour éviter les
        # quasi-doublons (« CABLE  1X25 » vs « CABLE 1X25 »).
        if self.designation:
            self.designation = " ".join(self.designation.split())
        if not self.unite:
            self.unite = "Unité"


@frappe.whitelist()
def creer_ou_recuperer(designation, categorie=None, unite=None, type_article=None,
                       type_stock=None, famille=None, groupe=None):
    """Retourne le `name` de l'Article portant cette désignation, en le créant si
    besoin. Utilisé par les imports / saisies pour ne jamais dupliquer un article
    et ne jamais demander de code. Idempotent sur la désignation (unique).
    `type_article` est accepté mais ignoré (champ retiré — la catégorie suffit).

    Classification (additive) : `type_stock` (Ingénierique/Industriel), `famille`
    (Matière première/Produit fini), `groupe`. Sur un article DÉJÀ existant, on met
    à jour ces champs s'ils sont fournis (permet de reclasser sans dupliquer) ;
    sur un nouvel article, le défaut du doctype (Ingénierique) s'applique si non
    précisé — jamais de valeur nulle."""
    designation = " ".join((designation or "").split())
    if not designation:
        frappe.throw("Désignation vide.")
    existing = frappe.db.get_value("Article KYA", {"designation": designation}, "name")
    if existing:
        # Réimport / re-saisie : on reclasse l'article existant si une classification
        # est fournie (sans jamais l'effacer avec du vide).
        maj = {}
        if type_stock:
            maj["type_stock"] = type_stock
        if famille:
            maj["famille"] = famille
        if groupe:
            maj["groupe"] = groupe
        if categorie:
            maj["categorie"] = categorie
        if maj:
            frappe.db.set_value("Article KYA", existing, maj, update_modified=False)
        return existing
    doc = frappe.new_doc("Article KYA")
    doc.designation = designation
    # Catégorie facultative à la création (les articles industriels du fichier
    # n'en ont pas). On la laisse VIDE plutôt que d'inventer un « Non classé »
    # trompeur → l'éditeur de classement signale les articles à renseigner, et
    # le magasin la remplit sur la plateforme (elle sert aussi aux sorties).
    if categorie:
        doc.categorie = categorie
    doc.unite = unite or "Unité"
    if type_stock:
        doc.type_stock = type_stock   # sinon défaut doctype = « Ingénierique »
    if famille:
        doc.famille = famille
    if groupe:
        doc.groupe = groupe
    doc.flags.ignore_permissions = True
    doc.insert()
    return doc.name


def _categorie_par_defaut():
    """Garantit une catégorie « Non classé » et la retourne."""
    nom = "Non classé"
    if not frappe.db.exists("Categorie Article KYA", nom):
        c = frappe.new_doc("Categorie Article KYA")
        c.categorie = nom
        c.ordre = 999
        c.flags.ignore_permissions = True
        c.insert()
    return nom
