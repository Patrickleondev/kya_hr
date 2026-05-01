# -*- coding: utf-8 -*-
import frappe
from frappe.model.document import Document
from frappe.utils import flt

from kya_hr.utils.approval_guards import block_self_approval


class BonCommandeKYA(Document):
    def validate(self):
        block_self_approval(self)
        self.calculate_totals()
        if self.fournisseur and not self.fournisseur_nom:
            self.fournisseur_nom = frappe.db.get_value("Supplier", self.fournisseur, "supplier_name")

    def calculate_totals(self):
        sous_total = 0.0
        for row in (self.articles or []):
            row.total = flt(row.quantite) * flt(row.prix_unitaire)
            sous_total += row.total
        self.sous_total = sous_total
        base = sous_total - flt(self.remise)
        self.tva_montant = base * flt(self.tva_taux) / 100.0
        self.total_ttc = base + flt(self.tva_montant)

    def on_submit(self):
        if self.statut == "Brouillon":
            self.db_set("statut", "Émis")
