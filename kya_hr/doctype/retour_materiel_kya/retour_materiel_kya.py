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

from kya_hr.api import stock_kya


def _map_etat_retour(etat_au_retour):
    """Mappe l'état saisi au retour vers un bucket du grand livre stock."""
    e = (etat_au_retour or "").strip().lower()
    if "répar" in e or "repar" in e or "à réparer" in e:
        return "En réparation"
    if "endommag" in e or "hors" in e or "rebut" in e:
        return "Hors service"
    return "Bon état"


class RetourMaterielKYA(Document):

    def validate(self):
        self._validate_items()
        self._set_retourneur_info()
        self._fetch_context_from_sortie()

    def _deja_poste(self):
        return bool(frappe.db.exists(
            "Mouvement Stock KYA",
            {"reference_doctype": "Retour Materiel KYA", "reference_name": self.name}))

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
    def on_submit(self):
        """Quand le workflow passe en UNE action vers « Approuvé » (docstatus=1),
        c'est submit() qui s'exécute — PAS on_update_after_submit. Sans ce hook,
        le Stock Entry n'était jamais créé (articles non remis en stock). Garde
        anti-doublon via stock_entry."""
        if self.workflow_state == "Approuvé" and not self._deja_poste():
            self._post_stock_kya()

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_magasin()
        if self.workflow_state == "Approuvé" and not self._deja_poste():
            self._post_stock_kya()

    def on_cancel(self):
        n = stock_kya.supprimer_mouvements("Retour Materiel KYA", self.name)
        if n:
            frappe.msgprint(
                _("Retour annulé — {0} article(s) ré-sortis du stock.").format(n),
                indicator="orange", alert=True)

    def _stamp_magasin(self):
        if self.workflow_state == "En attente Magasin" and not self.get("magasin_nom"):
            user = frappe.session.user
            emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
            self.db_set("magasin_nom", emp or frappe.utils.get_fullname(user), update_modified=False)
            self.db_set("magasin_date", frappe.utils.today(), update_modified=False)

    # ------------------------------------------------------------------ #
    def _post_stock_kya(self):
        """Remet les articles retournés en stock dans le grand livre maison
        (+qté par magasin). L'ÉTAT au retour porte le bucket de solde :
          - Bon état   → stock disponible
          - À réparer  → bucket « En réparation » (immobilisé, pas disponible)
          - Endommagé  → bucket « Hors service » (candidat rebut)
        Même magasin ; c'est l'état (colonne de l'inventaire) qui distingue."""
        rows = []
        for it in self.items:
            if not (it.get("item_code") and it.get("warehouse")):
                continue
            qty = it.get("qte_retournee") or 0
            if qty <= 0:
                continue
            rows.append({
                "item": it.item_code,
                "magasin": it.warehouse,
                "quantite": qty,
                "etat": _map_etat_retour(it.get("etat_au_retour")),
                "remarque": it.get("designation"),
            })
        if not rows:
            return
        try:
            n = stock_kya.enregistrer_mouvements(
                rows, "Retour",
                reference_doctype="Retour Materiel KYA", reference_name=self.name,
                date_mouvement=self.date_retour or frappe.utils.today(),
            )
            frappe.msgprint(
                _("Stock mis à jour : {0} article(s) retourné(s) au grand livre KYA "
                  "(état pris en compte).").format(n),
                indicator="green", alert=True,
            )
        except Exception as e:
            frappe.log_error(
                title=f"Retour Matériel {self.name} — échec écriture stock KYA",
                message=frappe.get_traceback() + f"\n\nRetour: {self.name}\nError: {e}",
            )
            frappe.msgprint(
                _("⚠️ Impossible d'enregistrer le retour de stock : {0}.").format(str(e)),
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


def on_submit(doc, method=None):
    _bind(doc).on_submit()


def on_update_after_submit(doc, method=None):
    _bind(doc).on_update_after_submit()


def on_cancel(doc, method=None):
    _bind(doc).on_cancel()
