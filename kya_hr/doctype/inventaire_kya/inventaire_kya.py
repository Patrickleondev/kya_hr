# Copyright (c) 2026, KYA-Energy Group and contributors
# Inventaire KYA — génère un Stock Reconciliation ERPNext à l'approbation

import frappe
from frappe import _
from frappe.model.document import Document

from kya_hr.utils.approval_guards import block_self_approval


class InventaireKYA(Document):
    def validate(self):
        block_self_approval(self)
        self.set_responsable_info()
        self.fill_theoretical_qty()
        self.compute_ecarts_and_totals()

    def fill_theoretical_qty(self):
        """Renseigne la qté théorique (stock système) + la valorisation depuis le
        Bin tant que l'inventaire est en brouillon. Indispensable côté WEB FORM
        où il n'y a pas le bouton desk « Charger Articles » : sans ça, la qté
        théorique reste vide et l'écart est faux."""
        if self.docstatus and self.docstatus != 0:
            return
        for row in self.items or []:
            if not row.item_code or not row.warehouse:
                continue
            bin_data = frappe.db.get_value(
                "Bin", {"item_code": row.item_code, "warehouse": row.warehouse},
                ["actual_qty", "valuation_rate"], as_dict=True,
            )
            row.qte_theorique = (bin_data.actual_qty if bin_data else 0) or 0
            if bin_data and bin_data.valuation_rate and not row.valuation_rate:
                row.valuation_rate = bin_data.valuation_rate

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
        valeur_ecart = 0
        for row in self.items or []:
            total_lignes += 1
            theo = row.qte_theorique or 0
            cpt = row.qte_comptee or 0
            row.ecart = cpt - theo
            if row.ecart:
                lignes_ecart += 1
                valeur_ecart += row.ecart * (row.valuation_rate or 0)
        self.total_lignes = total_lignes
        self.lignes_avec_ecart = lignes_ecart
        self.valeur_ecart_total = valeur_ecart

    # ------------------------------------------------------------------
    def on_submit(self):
        """Transition workflow en UNE action vers « Approuvé » (docstatus=1) →
        submit() s'exécute, pas on_update_after_submit. Sans ce hook, la Stock
        Reconciliation n'était pas créée (écarts non répercutés). Garde anti-doublon."""
        if self.workflow_state == "Approuvé" and not self.get("stock_reconciliation"):
            self._create_stock_reconciliation()

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_magasin_signature()
        if self.workflow_state == "Approuvé" and not self.get("stock_reconciliation"):
            self._create_stock_reconciliation()

    def on_cancel(self):
        if self.get("stock_reconciliation"):
            try:
                sr = frappe.get_doc("Stock Reconciliation", self.stock_reconciliation)
                if sr.docstatus == 1:
                    sr.cancel()
            except frappe.DoesNotExistError:
                pass

    def _stamp_magasin_signature(self):
        if self.workflow_state == "En attente Magasin" and not self.get("magasin_nom"):
            user = frappe.session.user
            emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
            self.db_set("magasin_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
            self.db_set("magasin_date", frappe.utils.today(), update_modified=False)

    def _create_stock_reconciliation(self):
        """Create Stock Reconciliation only for lines with an ecart != 0."""
        rows = [it for it in self.items if it.item_code and it.warehouse
                and (it.qte_comptee is not None) and ((it.qte_comptee or 0) != (it.qte_theorique or 0))]
        if not rows:
            return

        company = frappe.defaults.get_user_default("Company") \
            or frappe.db.get_single_value("Global Defaults", "default_company")

        sr = frappe.new_doc("Stock Reconciliation")
        sr.purpose = "Stock Reconciliation"
        sr.posting_date = self.date_inventaire or frappe.utils.today()
        sr.posting_time = frappe.utils.nowtime()
        sr.company = company
        sr.expense_account = (
            frappe.db.get_value("Company", company, "stock_adjustment_account") or None
        )
        sr.cost_center = frappe.db.get_value("Company", company, "cost_center") if company else None
        sr.inventaire_kya = self.name

        for it in rows:
            sr.append("items", {
                "item_code": it.item_code,
                "warehouse": it.warehouse,
                "qty": it.qte_comptee or 0,
                "valuation_rate": it.valuation_rate or 0,
            })

        try:
            sr.insert(ignore_permissions=True)
            sr.submit()
            self.db_set("stock_reconciliation", sr.name, update_modified=False)
            frappe.msgprint(
                _("Stock Reconciliation {0} créée — {1} écart(s) enregistré(s).").format(
                    frappe.utils.get_link_to_form("Stock Reconciliation", sr.name),
                    len(rows),
                ),
                indicator="green", alert=True,
            )
        except Exception as e:
            frappe.log_error(
                title=f"Inventaire {self.name} — échec Stock Reconciliation",
                message=frappe.get_traceback(),
            )
            frappe.msgprint(
                _("⚠️ Impossible de créer la Stock Reconciliation : {0}").format(str(e)),
                indicator="orange",
            )


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
def load_items_from_warehouse(inventaire_name: str, warehouse: str | None = None):
    """Return current Bin qty + valuation_rate for every item in a given warehouse.

    Called by the Desk client script.
    """
    if not warehouse:
        frappe.throw(_("Veuillez renseigner un magasin."))

    rows = frappe.db.sql(
        """
        SELECT b.item_code, b.warehouse, b.actual_qty AS qte_theorique, b.valuation_rate,
               i.item_name AS designation, i.stock_uom AS uom
        FROM `tabBin` b
        INNER JOIN `tabItem` i ON i.name = b.item_code
        WHERE b.warehouse = %s AND b.actual_qty > 0 AND i.disabled = 0
        ORDER BY i.item_name
        """,
        (warehouse,),
        as_dict=True,
    )
    return rows
