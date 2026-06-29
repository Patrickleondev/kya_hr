"""PV Réception de Matériels — fidèle fiche AEA-ENG-32-V01.

3 signataires dans l'ordre :
  1. Achats & Stock  (En attente Achats & Stock)
  2. Service Comptabilité (En attente Comptable)
  3. Audit Interne   (En attente Audit)

Stock Entry "Material Receipt" créé automatiquement à l'état Approuvé.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from kya_hr.utils.approval_guards import block_self_approval


class PVEntreeMateriel(Document):

    def validate(self):
        block_self_approval(self)
        self.validate_items()

    def validate_items(self):
        if not self.items:
            frappe.throw(_("Veuillez ajouter au moins un article dans la liste du matériel."))
        for it in self.items:
            if it.qte_recue and it.qte_recue <= 0:
                frappe.throw(_("La quantité reçue pour '{0}' doit être positive.").format(it.designation))

    # ------------------------------------------------------------------ #
    def on_submit(self):
        """Transition workflow en UNE action vers « Approuvé » (docstatus=1) →
        submit() s'exécute, pas on_update_after_submit. Garde anti-doublon."""
        if self.workflow_state == "Approuvé" and not self.get("stock_entry"):
            self._create_stock_entry()

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_approvers()
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

    def _stamp_approvers(self):
        """Auto-fill nom + date de chaque signataire à son tour."""
        ws = self.workflow_state
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        signer = emp or frappe.utils.get_fullname(user)
        today = frappe.utils.today()

        if ws == "En attente Achats & Stock" and not self.get("achats_stock_nom"):
            self.db_set("achats_stock_nom", signer, update_modified=False)
            self.db_set("achats_stock_date", today, update_modified=False)
        elif ws == "En attente Comptable" and not self.get("comptable_nom"):
            self.db_set("comptable_nom", signer, update_modified=False)
            self.db_set("comptable_date", today, update_modified=False)
        elif ws == "En attente Audit" and not self.get("audit_nom"):
            self.db_set("audit_nom", signer, update_modified=False)
            self.db_set("audit_date", today, update_modified=False)

    # ------------------------------------------------------------------ #
    def _ensure_item_for_row(self, it):
        """Si la ligne n'a qu'une designation (pas d'item_code), cree l'Item.

        Permet a l'utilisateur de receptionner un article jamais reference
        sans devoir aller le creer manuellement dans /app/item. L'Item cree
        herite de la designation + UOM saisies. Idempotent : si un Item au
        meme nom existe deja, on reutilise son code.
        """
        if it.get("item_code"):
            return
        designation = (it.get("designation") or "").strip()
        if not designation:
            return

        # Recherche par item_name exact (case-insensitive via collation MySQL)
        existing = frappe.db.get_value("Item", {"item_name": designation}, "name")
        if existing:
            it.item_code = existing
            return

        # Choix du groupe : si fournisseur est lie a une categorie connue,
        # on pourrait raffiner. Pour l'instant on prend "Articles divers - KYA"
        # comme fourre-tout, ou "All Item Groups" en fallback.
        item_group = "Articles divers - KYA"
        if not frappe.db.exists("Item Group", item_group):
            item_group = "All Item Groups"

        new_code = f"KYA-AUTO-{frappe.generate_hash(length=6).upper()}"
        try:
            doc = frappe.new_doc("Item")
            doc.item_code = new_code
            doc.item_name = designation
            doc.item_group = item_group
            doc.stock_uom = it.get("uom") or "Nos"
            doc.is_stock_item = 1
            doc.is_purchase_item = 1
            doc.is_sales_item = 1
            doc.insert(ignore_permissions=True)
            it.item_code = new_code
            frappe.msgprint(
                _("Article cree automatiquement : {0} (code: {1})").format(designation, new_code),
                indicator="blue", alert=True,
            )
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"PV Reception {self.name} - auto-creation Item '{designation}'",
            )

    def _create_stock_entry(self):
        # Etape 1 : creer les Items a la volee pour les lignes sans item_code
        for it in self.items:
            self._ensure_item_for_row(it)

        # Etape 2 : ne garder que les lignes qui ont maintenant un item_code + warehouse
        rows = [it for it in self.items if it.get("item_code") and it.get("warehouse")]
        if not rows:
            return

        company = frappe.defaults.get_user_default("Company") \
            or frappe.db.get_single_value("Global Defaults", "default_company")

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Receipt"
        se.purpose = "Material Receipt"
        se.posting_date = self.date_entree or frappe.utils.today()
        se.company = company
        se.project = self.get("project") or None
        se.remarks = _("Auto-créé depuis PV Réception {0} — Fournisseur: {1}").format(
            self.name,
            self.get("fournisseur") or self.get("fournisseur_libre") or "—"
        )
        se.pv_entree_materiel = self.name

        for it in rows:
            qty = it.qte_recue or 0
            if qty <= 0:
                continue
            se.append("items", {
                "item_code": it.item_code,
                "qty": qty,
                "uom": it.uom or frappe.db.get_value("Item", it.item_code, "stock_uom"),
                "t_warehouse": it.warehouse,
                "basic_rate": it.prix_unitaire or frappe.db.get_value("Item", it.item_code, "last_purchase_rate") or 0,
            })

        if not se.items:
            return

        try:
            se.insert(ignore_permissions=True)
            se.submit()
            self.db_set("stock_entry", se.name, update_modified=False)
            frappe.msgprint(
                _("Stock Entry {0} créé — stocks mis à jour.").format(
                    frappe.utils.get_link_to_form("Stock Entry", se.name)
                ),
                indicator="green", alert=True,
            )
        except Exception as e:
            frappe.log_error(
                title=f"PV Réception {self.name} — échec Stock Entry",
                message=frappe.get_traceback() + f"\n\nPV: {self.name}\nError: {e}",
            )
            frappe.msgprint(
                _("⚠️ Impossible de créer le Stock Entry automatique : {0}.").format(str(e)),
                indicator="orange",
            )


# ───────────────────────────────────────────────────────────────────────────
# Entrypoints doc_events (cf. hooks.py)
# ───────────────────────────────────────────────────────────────────────────
# Ce DocType est `custom: 1` : Frappe NE charge PAS la classe ci-dessus comme
# controller (il instancie frappe.model.document.Document). Conséquence : ni
# validate() ni on_update_after_submit() ne s'exécutaient -> le Material Receipt
# n'était jamais créé et le stock n'augmentait pas à la réception.
# On recâble donc le cycle de vie via doc_events. _bind() re-caste le Document
# de base vers notre classe pour réutiliser TOUT le code métier ci-dessus sans
# le dupliquer (la classe n'ajoute ni __slots__ ni __init__, le re-cast est sûr).

def _bind(doc):
    if doc.__class__ is not PVEntreeMateriel:
        doc.__class__ = PVEntreeMateriel
    return doc


def validate(doc, method=None):
    _bind(doc).validate()


def on_submit(doc, method=None):
    _bind(doc).on_submit()


def on_update_after_submit(doc, method=None):
    _bind(doc).on_update_after_submit()


def on_cancel(doc, method=None):
    _bind(doc).on_cancel()
