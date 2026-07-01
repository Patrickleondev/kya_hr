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
from kya_hr.api import stock_kya


class PVEntreeMateriel(Document):

    def validate(self):
        block_self_approval(self)
        self.validate_items()

    def _deja_poste(self):
        """Le mouvement de stock de cette fiche est-il déjà écrit au grand livre ?"""
        return bool(frappe.db.exists(
            "Mouvement Stock KYA",
            {"reference_doctype": "PV Entree Materiel", "reference_name": self.name}))

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
        if self.workflow_state == "Approuvé" and not self._deja_poste():
            self._post_stock_kya()

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_approvers()
        if self.workflow_state == "Approuvé" and not self._deja_poste():
            self._post_stock_kya()

    def on_cancel(self):
        # Stock KYA maison : on retire les mouvements de cette fiche du grand livre.
        stock_kya.supprimer_mouvements("PV Entree Materiel", self.name)

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

    def _post_stock_kya(self):
        """Écrit les entrées dans le grand livre maison (stock_kya), au lieu de
        passer par un Stock Entry ERPNext. Chaque ligne reçue = +qté en magasin,
        état « Bon état ». Crée les Items à la volée pour les lignes sans code."""
        for it in self.items:
            self._ensure_item_for_row(it)

        rows = []
        for it in self.items:
            qty = it.get("qte_recue") or 0
            if not (it.get("item_code") and it.get("warehouse")) or qty <= 0:
                continue
            rows.append({
                "item": it.item_code,
                "magasin": it.warehouse,
                "quantite": qty,
                "etat": it.get("etat") or "Bon état",
                "remarque": it.get("designation"),
            })
        if not rows:
            return
        try:
            n = stock_kya.enregistrer_mouvements(
                rows, "Entrée",
                reference_doctype="PV Entree Materiel", reference_name=self.name,
                date_mouvement=self.date_entree or frappe.utils.today(),
            )
            frappe.msgprint(
                _("Stock mis à jour : {0} entrée(s) enregistrée(s) au grand livre KYA.").format(n),
                indicator="green", alert=True,
            )
        except Exception as e:
            frappe.log_error(
                title=f"PV Réception {self.name} — échec écriture stock KYA",
                message=frappe.get_traceback() + f"\n\nPV: {self.name}\nError: {e}",
            )
            frappe.msgprint(
                _("⚠️ Impossible d'enregistrer le mouvement de stock : {0}.").format(str(e)),
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
