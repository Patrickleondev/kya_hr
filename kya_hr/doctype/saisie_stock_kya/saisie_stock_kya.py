# -*- coding: utf-8 -*-
"""Saisie Stock KYA — saisie directe du stock par magasin (sans import).

La Responsable Stock (ou son assistante) ouvre ce formulaire, choisit le
magasin, et saisit les matériels ligne par ligne (désignation / catégorie /
unité / bon état / en réparation). À la validation (submit) :

  - chaque désignation crée/récupère l'Article KYA correspondant (SANS code) ;
  - les quantités sont écrites au grand livre `Mouvement Stock KYA`
    (type « Inventaire », + en bon état / + en réparation) référencées à CETTE
    fiche → l'annulation (cancel) les retire proprement.

DocType custom=0 : Frappe charge bien cette classe comme controller (pas de
recâblage doc_events nécessaire, contrairement aux PV custom=1).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today

from kya_hr.kya_hr.api import stock_kya


class SaisieStockKYA(Document):

    def validate(self):
        if not self.date_saisie:
            self.date_saisie = today()
        if not self.lignes:
            frappe.throw(_("Ajoutez au moins une ligne de matériel."))
        for l in self.lignes:
            if l.designation:
                l.designation = " ".join(l.designation.split())
            if not l.designation:
                frappe.throw(_("Chaque ligne doit avoir une désignation."))
            if flt(l.bon_etat) < 0 or flt(l.en_reparation) < 0 or flt(l.get("defectueux")) < 0:
                frappe.throw(_("Ligne « {0} » : les quantités ne peuvent pas être négatives.").format(l.designation))
            if flt(l.bon_etat) == 0 and flt(l.en_reparation) == 0 and flt(l.get("defectueux")) == 0:
                frappe.throw(_("Ligne « {0} » : indiquez une quantité (bon état, à réparer et/ou défectueux).").format(l.designation))

    def on_submit(self):
        self.db_set("statut", "Validée", update_modified=False)
        self._poster_stock()

    def on_cancel(self):
        stock_kya.supprimer_mouvements("Saisie Stock KYA", self.name)
        self.db_set("statut", "Annulée", update_modified=False)

    # ------------------------------------------------------------------ #
    def _poster_stock(self):
        """Crée les articles manquants et pose les quantités au grand livre KYA."""
        from kya_hr.kya_hr.doctype.article_kya.article_kya import creer_ou_recuperer

        rows = []
        for l in self.lignes:
            art = creer_ou_recuperer(
                l.designation, categorie=l.categorie or None,
                unite=l.unite or "Unité")
            if flt(l.bon_etat):
                rows.append({"item": art, "magasin": self.magasin,
                             "quantite": flt(l.bon_etat), "etat": "Bon état",
                             "remarque": l.designation})
            if flt(l.en_reparation):
                rows.append({"item": art, "magasin": self.magasin,
                             "quantite": flt(l.en_reparation), "etat": "À réparer",
                             "remarque": l.designation})
            if flt(l.get("defectueux")):
                rows.append({"item": art, "magasin": self.magasin,
                             "quantite": flt(l.get("defectueux")), "etat": "Défectueux",
                             "remarque": l.designation})
        if not rows:
            return
        n = stock_kya.enregistrer_mouvements(
            rows, "Inventaire",
            reference_doctype="Saisie Stock KYA", reference_name=self.name,
            date_mouvement=self.date_saisie or today())
        frappe.msgprint(
            _("Stock enregistré : {0} mouvement(s) écrit(s) au grand livre KYA pour le magasin {1}.").format(n, self.magasin),
            indicator="green", alert=True)
