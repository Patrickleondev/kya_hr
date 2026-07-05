# Copyright (c) 2026, KYA-Energy Group and contributors
# Inventaire KYA — génère un Stock Reconciliation ERPNext à l'approbation

import frappe
from frappe import _
from frappe.model.document import Document

from kya_hr.utils.approval_guards import block_self_approval
from kya_hr.api import stock_kya


class InventaireKYA(Document):
    def validate(self):
        block_self_approval(self)
        self.set_responsable_info()
        self.fill_theoretical_qty()
        self.compute_ecarts_and_totals()

    def _deja_poste(self):
        return bool(frappe.db.exists(
            "Mouvement Stock KYA",
            {"reference_doctype": "Inventaire KYA", "reference_name": self.name}))

    def fill_theoretical_qty(self):
        """Qté « système » = solde ACTUEL au journal de stock maison (total),
        pour calculer l'écart avec le compté. (Plus de Bin ERPNext.)"""
        if self.docstatus and self.docstatus != 0:
            return
        for row in self.items or []:
            if not row.item_code or not row.warehouse:
                continue
            solde = stock_kya.solde_item_magasin(row.item_code, row.warehouse)
            row.qte_theorique = solde.get("total") or 0

    def set_responsable_info(self):
        if not self.responsable_nom:
            emp = frappe.db.get_value(
                "Employee", {"user_id": frappe.session.user},
                "employee_name"
            )
            if emp:
                self.responsable_nom = emp
                self.responsable_date = frappe.utils.today()

    def compute_ecarts_and_totals(self):
        total_lignes = 0
        lignes_ecart = 0
        for row in self.items or []:
            total_lignes += 1
            # Qté totale comptée = bon état + à réparer + défectueux (format fiche KYA)
            row.qte_comptee = ((row.qte_bon_etat or 0) + (row.qte_en_reparation or 0)
                               + (row.get("qte_defectueux") or 0))
            theo = row.qte_theorique or 0
            row.ecart = (row.qte_comptee or 0) - theo
            if row.ecart:
                lignes_ecart += 1
        self.total_lignes = total_lignes
        self.lignes_avec_ecart = lignes_ecart
        self.valeur_ecart_total = 0  # pas de valorisation dans le stock maison

    # ------------------------------------------------------------------
    def on_submit(self):
        if self.workflow_state == "Approuvé" and not self._deja_poste():
            self._post_stock_kya()

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_magasin_signature()
        if self.workflow_state == "Approuvé" and not self._deja_poste():
            self._post_stock_kya()

    def on_cancel(self):
        stock_kya.supprimer_mouvements("Inventaire KYA", self.name)

    def _stamp_magasin_signature(self):
        if self.workflow_state == "En attente Magasin" and not self.get("magasin_nom"):
            user = frappe.session.user
            emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
            self.db_set("magasin_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
            self.db_set("magasin_date", frappe.utils.today(), update_modified=False)

    def _post_stock_kya(self):
        """Cale le stock maison sur le COMPTÉ : pour chaque (article, magasin),
        écrit un AJUSTEMENT = compté − solde actuel, par bucket d'état (bon état /
        en réparation). C'est l'inventaire qui fait foi."""
        rows = []
        for it in self.items:
            if not (it.item_code and it.warehouse):
                continue
            solde = stock_kya.solde_item_magasin(it.item_code, it.warehouse)
            delta_bon = (it.qte_bon_etat or 0) - (solde.get("bon_etat") or 0)
            delta_rep = (it.qte_en_reparation or 0) - (solde.get("reparation") or 0)
            delta_def = (it.get("qte_defectueux") or 0) - (solde.get("defectueux") or 0)
            if delta_bon:
                rows.append({"item": it.item_code, "magasin": it.warehouse,
                             "quantite": delta_bon, "etat": "Bon état",
                             "remarque": it.get("remarque") or _("Ajustement inventaire")})
            if delta_rep:
                rows.append({"item": it.item_code, "magasin": it.warehouse,
                             "quantite": delta_rep, "etat": "À réparer",
                             "remarque": it.get("remarque") or _("Ajustement inventaire")})
            if delta_def:
                rows.append({"item": it.item_code, "magasin": it.warehouse,
                             "quantite": delta_def, "etat": "Défectueux",
                             "remarque": it.get("remarque") or _("Ajustement inventaire")})
        if not rows:
            frappe.msgprint(_("Inventaire validé — aucun écart, stock inchangé."),
                            indicator="green", alert=True)
            return
        try:
            n = stock_kya.enregistrer_mouvements(
                rows, "Inventaire",
                reference_doctype="Inventaire KYA", reference_name=self.name,
                date_mouvement=self.date_inventaire or frappe.utils.today(),
            )
            frappe.msgprint(
                _("Inventaire validé — {0} ajustement(s) appliqué(s) au stock.").format(n),
                indicator="green", alert=True)
        except Exception as e:
            frappe.log_error(title=f"Inventaire {self.name} — échec ajustement stock KYA",
                             message=frappe.get_traceback())
            frappe.msgprint(_("⚠️ Impossible d'appliquer l'inventaire au stock : {0}").format(str(e)),
                            indicator="orange")


# ───────────────────────────────────────────────────────────────────────────
# Entrypoints doc_events (cf. hooks.py)
# ───────────────────────────────────────────────────────────────────────────
# `custom: 1` -> la classe ci-dessus n'est pas chargée comme controller. Sans
# ces entrypoints, l'inventaire ne générait jamais la Stock Reconciliation
# (les écarts comptés n'étaient pas répercutés sur le stock réel).
# _bind() re-caste le Document de base vers la classe pour réutiliser son code.

def _bind(doc):
    if doc.__class__ is not InventaireKYA:
        doc.__class__ = InventaireKYA
    return doc


def validate(doc, method=None):
    _bind(doc).validate()


def on_submit(doc, method=None):
    _bind(doc).on_submit()


def on_update_after_submit(doc, method=None):
    _bind(doc).on_update_after_submit()


def on_cancel(doc, method=None):
    _bind(doc).on_cancel()


# ----------------------------------------------------------------------
# Whitelisted — loader utilisé par le bouton "Charger Articles"
# ----------------------------------------------------------------------
@frappe.whitelist()
def load_items_from_warehouse(inventaire_name: str = None, warehouse: str | None = None):
    """Pré-remplit les lignes depuis le SOLDE ACTUEL du journal de stock maison
    pour un magasin : bon état / en réparation / total. Appelé par le bouton
    « Charger Articles » (desk) et le web form."""
    if not warehouse:
        frappe.throw(_("Veuillez renseigner un magasin."))
    rows = []
    for d in stock_kya.soldes(magasin=warehouse, only_nonzero=1):
        rows.append({
            "item_code": d["item"], "designation": d["item_name"], "warehouse": warehouse,
            "qte_bon_etat": d["bon_etat"], "qte_en_reparation": d["reparation"],
            "qte_defectueux": d.get("defectueux", 0),
            "qte_comptee": d["total"], "qte_theorique": d["total"], "ecart": 0,
        })
    return rows
