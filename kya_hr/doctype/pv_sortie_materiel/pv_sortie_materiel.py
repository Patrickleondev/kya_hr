# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PVSortieMateriel(Document):
    def validate(self):
        self.validate_items()
        self.set_demandeur_info()
        self._compute_valorisation()

    def _compute_valorisation(self):
        """Compute valeur_totale per item line + total PV (XOF)."""
        total = 0.0
        nb = 0
        items_list = list(self.get("items") or [])
        frappe.logger().info(f"[PV {self.name}] _compute_valorisation: {len(items_list)} items")
        for it in items_list:
            qty = it.qte_reellement_sortie or it.qte_demandee or 0
            unit = it.get("valeur_unitaire") or 0
            if it.get("item_code") and not unit:
                unit = frappe.db.get_value("Item", it.item_code, "valuation_rate") or 0
                it.valeur_unitaire = unit
            line_total = (qty or 0) * (unit or 0)
            it.valeur_totale = line_total
            total += line_total
            nb += 1
        self.valeur_totale_xof = total
        self.nb_lignes = nb

    def validate_items(self):
        if not self.items:
            frappe.throw(_("Veuillez ajouter au moins un article dans la liste du matériel."))
        for item in self.items:
            if item.qte_demandee and item.qte_demandee <= 0:
                frappe.throw(_("La quantité demandée pour '{0}' doit être positive.").format(item.designation))

    def set_demandeur_info(self):
        """Auto-fill demandeur from session user's Employee record."""
        if not self.demandeur_nom:
            emp = frappe.db.get_value(
                "Employee", {"user_id": frappe.session.user},
                ["employee_name"], as_dict=True
            )
            if emp:
                self.demandeur_nom = emp.employee_name
                self.demandeur_date = frappe.utils.today()

    # ------------------------------------------------------------------
    # Workflow lifecycle
    # ------------------------------------------------------------------
    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_approver_signature()
        # Auto-create Stock Entry the moment PV becomes "Approuvé"
        if self.workflow_state == "Approuvé" and not self.get("stock_entry"):
            self._create_stock_entry()

    def on_cancel(self):
        """If the PV is cancelled, cancel the associated Stock Entry too."""
        if self.get("stock_entry"):
            try:
                se = frappe.get_doc("Stock Entry", self.stock_entry)
                if se.docstatus == 1:
                    se.cancel()
                    frappe.msgprint(_("Stock Entry {0} annulé — les articles sont remis en stock.").format(se.name),
                                    indicator="orange", alert=True)
            except frappe.DoesNotExistError:
                pass

    def _stamp_approver_signature(self):
        """Auto-fill approver name and date when they approve at their workflow level."""
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        today = frappe.utils.today()
        ws = self.workflow_state
        signer = emp or frappe.utils.get_fullname(user)

        if ws == "En attente Magasin" and not self.get("magasin_nom"):
            self.db_set("magasin_nom", signer, update_modified=False)
            self.db_set("magasin_date", today, update_modified=False)
        elif ws == "En attente Audit" and not self.get("audit_nom"):
            self.db_set("audit_nom", signer, update_modified=False)
            self.db_set("audit_date", today, update_modified=False)
        elif ws == "En attente Direction" and not self.get("dga_nom"):
            self.db_set("dga_nom", signer, update_modified=False)
            self.db_set("dga_date", today, update_modified=False)

    # ------------------------------------------------------------------
    # ERPNext Stock integration — Material Issue
    # ------------------------------------------------------------------
    def _create_stock_entry(self):
        """
        Create a Stock Entry (Material Issue) that decrements stock for all items
        with an item_code + warehouse. Items without item_code are skipped (non-ERPNext
        articles) but still tracked on the PV for traceability.
        """
        rows = [it for it in self.items if it.get("item_code") and it.get("warehouse")]
        if not rows:
            # No ERPNext-linked articles → nothing to decrement, pure paper PV
            return

        default_wh = frappe.db.get_single_value("Stock Settings", "default_warehouse") or None
        company = self.get("company") or frappe.defaults.get_user_default("Company") \
            or frappe.db.get_single_value("Global Defaults", "default_company")

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Issue"
        se.purpose = "Material Issue"
        se.posting_date = self.date_sortie or frappe.utils.today()
        se.company = company
        se.project = self.get("project") or None
        se.remarks = _("Auto-créé depuis PV Sortie Matériel {0}").format(self.name)
        # Custom reference back to the PV for traceability (see Custom Field in fixtures)
        se.pv_sortie_materiel = self.name

        for it in rows:
            qty = it.qte_reellement_sortie or it.qte_demandee or 0
            if qty <= 0:
                continue
            se.append("items", {
                "item_code": it.item_code,
                "qty": qty,
                "uom": it.uom or frappe.db.get_value("Item", it.item_code, "stock_uom"),
                "s_warehouse": it.warehouse or default_wh,
                "basic_rate": frappe.db.get_value("Item", it.item_code, "last_purchase_rate") or 0,
                "cost_center": frappe.db.get_value("Company", company, "cost_center") if company else None,
            })

        if not se.items:
            return

        try:
            se.insert(ignore_permissions=True)
            se.submit()
            self.db_set("stock_entry", se.name, update_modified=False)
            frappe.msgprint(
                _("Stock Entry {0} créé et soumis automatiquement — les stocks ont été mis à jour.").format(
                    frappe.utils.get_link_to_form("Stock Entry", se.name)
                ),
                indicator="green", alert=True,
            )
        except Exception as e:
            # Do not block PV approval if stock is insufficient — log and notify
            frappe.log_error(
                title=f"PV Sortie {self.name} — échec création Stock Entry",
                message=frappe.get_traceback() + f"\n\nPV: {self.name}\nError: {e}",
            )
            frappe.msgprint(
                _("⚠️ Impossible de créer le Stock Entry automatique : {0}. "
                  "Le PV reste approuvé, mais la déduction de stock doit être faite manuellement.").format(str(e)),
                indicator="orange",
            )
