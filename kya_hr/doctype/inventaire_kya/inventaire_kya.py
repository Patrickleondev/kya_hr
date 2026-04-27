# Copyright (c) 2026, KYA-Energy Group and contributors
# Inventaire KYA — génère un Stock Reconciliation ERPNext à l'approbation

import frappe
from frappe import _
from frappe.model.document import Document


class InventaireKYA(Document):
    def validate(self):
        self.set_responsable_info()
        self.compute_ecarts_and_totals()

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
