# Copyright (c) 2026, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kya_hr.utils.approval_guards import block_self_approval


class PVEntreeMateriel(Document):
    def validate(self):
        block_self_approval(self)
        self.validate_items()
        self.set_livreur_info()

    def validate_items(self):
        if not self.items:
            frappe.throw(_("Veuillez ajouter au moins un article dans la liste du matériel."))
        for it in self.items:
            if it.qte_recue and it.qte_recue <= 0:
                frappe.throw(_("La quantité reçue pour '{0}' doit être positive.").format(it.designation))

    def set_livreur_info(self):
        if not self.livreur_nom:
            emp = frappe.db.get_value(
                "Employee", {"user_id": frappe.session.user},
                ["employee_name"], as_dict=True,
            )
            if emp:
                self.livreur_nom = emp.employee_name
                self.livreur_date = frappe.utils.today()

    # ------------------------------------------------------------------
    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_magasin_signature()
        if self.workflow_state == "Approuvé" and not self.get("stock_entry"):
            self._create_stock_entry()

    def on_cancel(self):
        if self.get("stock_entry"):
            try:
                se = frappe.get_doc("Stock Entry", self.stock_entry)
                if se.docstatus == 1:
                    se.cancel()
            except frappe.DoesNotExistError:
                pass

    def _stamp_magasin_signature(self):
        ws = self.workflow_state
        if ws == "En attente Magasin" and not self.get("magasin_nom"):
            user = frappe.session.user
            emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
            self.db_set("magasin_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
            self.db_set("magasin_date", frappe.utils.today(), update_modified=False)

    def _create_stock_entry(self):
        rows = [it for it in self.items if it.get("item_code") and it.get("warehouse")]
        if not rows:
            return

        default_wh = frappe.db.get_single_value("Stock Settings", "default_warehouse") or None
        company = frappe.defaults.get_user_default("Company") \
            or frappe.db.get_single_value("Global Defaults", "default_company")

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Receipt"
        se.purpose = "Material Receipt"
        se.posting_date = self.date_entree or frappe.utils.today()
        se.company = company
        se.remarks = _("Auto-créé depuis PV Entrée Matériel {0}").format(self.name)
        se.pv_entree_materiel = self.name

        for it in rows:
            qty = it.qte_recue or 0
            if qty <= 0:
                continue
            se.append("items", {
                "item_code": it.item_code,
                "qty": qty,
                "uom": it.uom or frappe.db.get_value("Item", it.item_code, "stock_uom"),
                "t_warehouse": it.warehouse or default_wh,
                "basic_rate": it.prix_unitaire or frappe.db.get_value("Item", it.item_code, "last_purchase_rate") or 0,
                "cost_center": frappe.db.get_value("Company", company, "cost_center") if company else None,
            })

        if not se.items:
            return

        try:
            se.insert(ignore_permissions=True)
            se.submit()
            self.db_set("stock_entry", se.name, update_modified=False)
            frappe.msgprint(
                _("Stock Entry {0} créé et soumis — stocks mis à jour.").format(
                    frappe.utils.get_link_to_form("Stock Entry", se.name)
                ),
                indicator="green", alert=True,
            )
        except Exception as e:
            frappe.log_error(
                title=f"PV Entrée {self.name} — échec création Stock Entry",
                message=frappe.get_traceback() + f"\n\nPV: {self.name}\nError: {e}",
            )
            frappe.msgprint(
                _("⚠️ Impossible de créer le Stock Entry automatique : {0}.").format(str(e)),
                indicator="orange",
            )
