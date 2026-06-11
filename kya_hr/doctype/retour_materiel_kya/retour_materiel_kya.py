"""Retour Matériel KYA — matériel rendu au magasin depuis un chantier/client.

Lifecycle :
  validate       → valide les articles + auto-fill retourneur
  on_update_after_submit → stamp magasin, crée Stock Entry (Material Receipt)
                           lorsque workflow_state == "Approuvé"
  on_cancel      → annule le Stock Entry associé
"""

import frappe
from frappe import _
from frappe.model.document import Document


REPAIR_WAREHOUSE_NAME = "Atelier-Reparation"


def _get_or_create_repair_warehouse(company):
    """Retourne le nom complet du warehouse Atelier-Réparation.
    Crée le warehouse à la volée s'il n'existe pas pour la company.
    Les articles endommagés y sont stockés en attendant réparation."""
    if not company:
        return None

    abbr = frappe.db.get_value("Company", company, "abbr")
    full_name = f"{REPAIR_WAREHOUSE_NAME} - {abbr}" if abbr else REPAIR_WAREHOUSE_NAME

    if frappe.db.exists("Warehouse", full_name):
        return full_name

    try:
        wh = frappe.new_doc("Warehouse")
        wh.warehouse_name = REPAIR_WAREHOUSE_NAME
        wh.company = company
        wh.is_group = 0
        wh.warehouse_type = None
        wh.insert(ignore_permissions=True)
        return wh.name
    except Exception:
        frappe.log_error(
            title="Retour Matériel — création warehouse Atelier-Réparation échouée",
            message=frappe.get_traceback(),
        )
        return None


class RetourMaterielKYA(Document):

    def validate(self):
        self._validate_items()
        self._set_retourneur_info()
        self._fetch_context_from_sortie()

    def _validate_items(self):
        if not self.items:
            frappe.throw(_("Veuillez lister les articles à retourner."))
        for it in self.items:
            if it.qte_retournee and it.qte_retournee <= 0:
                frappe.throw(_("La quantité retournée pour '{0}' doit être positive.").format(
                    it.designation or it.item_code))

    def _set_retourneur_info(self):
        """L'employé retourneur = employé qui avait fait la demande de sortie.
        Si pas de PV Sortie origine, fallback sur l'utilisateur connecté."""
        if self.retourneur_nom:
            return
        # Chercher depuis le PV Sortie d'origine
        if self.pv_sortie_origine:
            pv_emp = frappe.db.get_value(
                "PV Sortie Materiel", self.pv_sortie_origine,
                ["demandeur_nom", "employee_name"], as_dict=True)
            if pv_emp:
                emp_name = pv_emp.demandeur_nom or pv_emp.employee_name
                if emp_name:
                    self.retourneur_nom = emp_name
                    self.retourneur_date = frappe.utils.today()
                    return
        # Fallback : utilisateur connecté
        emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "employee_name")
        if emp:
            self.retourneur_nom = emp
            self.retourneur_date = frappe.utils.today()

    def _fetch_context_from_sortie(self):
        """Auto-remplir projet, client et retourneur depuis le PV Sortie d'origine."""
        if not self.pv_sortie_origine:
            return
        pv = frappe.db.get_value(
            "PV Sortie Materiel",
            self.pv_sortie_origine,
            ["project", "customer", "customer_manuel", "demandeur_nom", "employee_name"],
            as_dict=True,
        )
        if not pv:
            return
        if pv.project and not self.project:
            self.project = pv.project
        if pv.customer and not self.customer:
            self.customer = pv.customer
        if pv.customer_manuel and not self.customer_libre:
            self.customer_libre = pv.customer_manuel
        # Auto-fill retourneur from original demandeur
        if not self.retourneur_nom:
            emp_name = pv.demandeur_nom or pv.employee_name
            if emp_name:
                self.retourneur_nom = emp_name
                self.retourneur_date = frappe.utils.today()

    # ------------------------------------------------------------------ #
    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_magasin()
        if self.workflow_state == "Approuvé" and not self.get("stock_entry"):
            self._create_stock_entry()

    def on_cancel(self):
        if self.get("stock_entry"):
            try:
                se = frappe.get_doc("Stock Entry", self.stock_entry)
                if se.docstatus == 1:
                    se.cancel()
                    frappe.msgprint(
                        _("Stock Entry {0} annulé — les articles sont ré-sortis du stock.").format(se.name),
                        indicator="orange", alert=True,
                    )
            except frappe.DoesNotExistError:
                pass

    def _stamp_magasin(self):
        if self.workflow_state == "En attente Magasin" and not self.get("magasin_nom"):
            user = frappe.session.user
            emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
            self.db_set("magasin_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
            self.db_set("magasin_date", frappe.utils.today(), update_modified=False)

    # ------------------------------------------------------------------ #
    def _create_stock_entry(self):
        """Stock Entry Material Receipt pour remettre les articles en stock.

        Routage par état :
          - Bon état            → warehouse choisi par l'utilisateur
          - Endommagé / À réparer → warehouse 'Atelier-Reparation' (créé si absent)
            Le Responsable Magasin décide ensuite : Material Transfer
            vers le magasin d'origine si réparé, ou Material Issue vers
            le rebut s'il est définitivement hors service.
        """
        rows = [it for it in self.items if it.get("item_code")]
        if not rows:
            return

        company = frappe.defaults.get_user_default("Company") \
            or frappe.db.get_single_value("Global Defaults", "default_company")

        repair_wh = _get_or_create_repair_warehouse(company)

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Receipt"
        se.purpose = "Material Receipt"
        se.posting_date = self.date_retour or frappe.utils.today()
        se.company = company
        se.project = self.get("project") or None
        se.remarks = _("Retour matériel — PV Retour {0} — Sortie origine : {1}").format(
            self.name, self.get("pv_sortie_origine") or "—"
        )

        for it in rows:
            qty = it.qte_retournee or 0
            if qty <= 0:
                continue

            etat = (it.get("etat_au_retour") or "Bon état").strip()
            if etat in ("Endommagé", "À réparer"):
                target_wh = repair_wh
            else:
                target_wh = it.get("warehouse")
            if not target_wh:
                continue

            se.append("items", {
                "item_code": it.item_code,
                "qty": qty,
                "uom": it.uom or frappe.db.get_value("Item", it.item_code, "stock_uom"),
                "t_warehouse": target_wh,
                "basic_rate": frappe.db.get_value("Item", it.item_code, "last_purchase_rate") or 0,
            })

        if not se.items:
            return

        try:
            se.insert(ignore_permissions=True)
            se.submit()
            self.db_set("stock_entry", se.name, update_modified=False)
            frappe.msgprint(
                _("Stock Entry {0} créé — les articles retournés sont remis en stock.").format(
                    frappe.utils.get_link_to_form("Stock Entry", se.name)
                ),
                indicator="green", alert=True,
            )
        except Exception as e:
            frappe.log_error(
                title=f"Retour Matériel {self.name} — échec Stock Entry",
                message=frappe.get_traceback() + f"\n\nRetour: {self.name}\nError: {e}",
            )
            frappe.msgprint(
                _("⚠️ Impossible de créer le Stock Entry automatique : {0}. "
                  "Le retour est approuvé mais la mise à jour du stock doit être faite manuellement.").format(str(e)),
                indicator="orange",
            )


# ───────────────────────────────────────────────────────────────────────────
# Entrypoints doc_events (cf. hooks.py)
# ───────────────────────────────────────────────────────────────────────────
# `custom: 1` -> la classe ci-dessus n'est pas chargée comme controller. Sans
# ces entrypoints, le retour matériel ne remettait jamais les articles en stock.
# _bind() re-caste le Document de base vers la classe pour réutiliser son code.

def _bind(doc):
    if doc.__class__ is not RetourMaterielKYA:
        doc.__class__ = RetourMaterielKYA
    return doc


def validate(doc, method=None):
    _bind(doc).validate()


def on_update_after_submit(doc, method=None):
    _bind(doc).on_update_after_submit()


def on_cancel(doc, method=None):
    _bind(doc).on_cancel()
