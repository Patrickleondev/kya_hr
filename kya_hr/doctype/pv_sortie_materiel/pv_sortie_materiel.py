# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from kya_hr.utils.approval_guards import block_self_approval
from kya_hr.api import stock_kya


class PVSortieMateriel(Document):
    def validate(self):
        block_self_approval(self)
        self.validate_items()
        self.set_demandeur_info()
        self._ensure_customer_project()

    def _ensure_customer_project(self):
        """Le remplisseur n'a nulle part où aller : s'il tape un nom de client
        ou de projet à la main (customer_manuel / project_manuel), on crée
        automatiquement le Customer / Project et on le LIE — ou on relie
        l'existant s'il porte déjà ce nom. Ça alimente le dashboard sorties
        par client/projet sans navigation manuelle.
        """
        nom_client = (self.get("customer_manuel") or "").strip()
        if not self.get("customer") and nom_client:
            existing = frappe.db.get_value("Customer", {"customer_name": nom_client}, "name")
            if existing:
                self.customer = existing
            else:
                cust = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": nom_client,
                    "customer_type": "Company",
                    "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
                        or "All Customer Groups",
                    "territory": frappe.db.get_value("Territory", {"is_group": 0}, "name")
                        or "All Territories",
                })
                cust.insert(ignore_permissions=True)
                self.customer = cust.name

        nom_projet = (self.get("project_manuel") or "").strip()
        if not self.get("project") and nom_projet:
            existing = frappe.db.get_value("Project", {"project_name": nom_projet}, "name")
            if existing:
                self.project = existing
            else:
                proj = frappe.get_doc({"doctype": "Project", "project_name": nom_projet})
                if self.get("customer"):
                    proj.customer = self.customer
                proj.insert(ignore_permissions=True)
                self.project = proj.name

    def _deja_poste(self):
        return bool(frappe.db.exists(
            "Mouvement Stock KYA",
            {"reference_doctype": "PV Sortie Materiel", "reference_name": self.name}))

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
    def on_submit(self):
        if self.workflow_state == "Approuvé" and not self._deja_poste():
            self._post_stock_kya()

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self._stamp_approver_signature()
        # Décrémente le stock maison dès que le PV passe « Approuvé »
        if self.workflow_state == "Approuvé" and not self._deja_poste():
            self._post_stock_kya()

    def on_cancel(self):
        """Annulation du PV → on retire ses mouvements du grand livre (le
        matériel est remis en stock)."""
        n = stock_kya.supprimer_mouvements("PV Sortie Materiel", self.name)
        if n:
            frappe.msgprint(_("Sortie annulée — {0} article(s) remis en stock.").format(n),
                            indicator="orange", alert=True)

    def _stamp_approver_signature(self):
        """Auto-fill approver name and date when they approve at their workflow level."""
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        today = frappe.utils.today()
        ws = self.workflow_state
        signer = emp or frappe.utils.get_fullname(user)

        if ws == "En attente Audit" and not self.get("audit_nom"):
            self.db_set("audit_nom", signer, update_modified=False)
            self.db_set("audit_date", today, update_modified=False)
        elif ws == "En attente Direction" and not self.get("dga_nom"):
            self.db_set("dga_nom", signer, update_modified=False)
            self.db_set("dga_date", today, update_modified=False)
        elif ws == "En attente Magasin" and not self.get("magasin_nom"):
            self.db_set("magasin_nom", signer, update_modified=False)
            self.db_set("magasin_date", today, update_modified=False)

    # ------------------------------------------------------------------
    # Stock KYA maison — sortie (décrémente le grand livre)
    # ------------------------------------------------------------------
    def _post_stock_kya(self):
        """Écrit les sorties dans le grand livre maison (−qté par magasin).
        Contrôle de disponibilité SOUPLE : on prévient si le solde devient
        négatif mais on NE bloque PAS (migration en cours, stock d'ouverture
        pas forcément complet ; régularisable par inventaire)."""
        rows, alertes = [], []
        for it in self.items:
            if not (it.get("item_code") and it.get("warehouse")):
                continue
            qty = it.get("qte_reellement_sortie") or it.get("qte_demandee") or 0
            if qty <= 0:
                continue
            solde = stock_kya.solde_item_magasin(it.item_code, it.warehouse)
            if qty > (solde.get("total") or 0):
                alertes.append(_("{0} dans {1} : sortie {2}, disponible {3}").format(
                    it.get("designation") or it.item_code, it.warehouse, qty, solde.get("total") or 0))
            rows.append({
                "item": it.item_code,
                "magasin": it.warehouse,
                "quantite": qty,  # signe appliqué par enregistrer_mouvements (Sortie)
                "etat": "Bon état",
                "remarque": it.get("designation"),
            })
        if not rows:
            return
        try:
            n = stock_kya.enregistrer_mouvements(
                rows, "Sortie",
                reference_doctype="PV Sortie Materiel", reference_name=self.name,
                date_mouvement=self.date_sortie or frappe.utils.today(),
            )
            frappe.msgprint(
                _("Stock mis à jour : {0} sortie(s) enregistrée(s) au grand livre KYA.").format(n),
                indicator="green", alert=True,
            )
            if alertes:
                frappe.msgprint(
                    _("⚠️ Stock négatif après cette sortie (à régulariser par inventaire) :<br>{0}")
                    .format("<br>".join(f"&bull; {a}" for a in alertes)),
                    indicator="orange")
        except Exception as e:
            frappe.log_error(
                title=f"PV Sortie {self.name} — échec écriture stock KYA",
                message=frappe.get_traceback() + f"\n\nPV: {self.name}\nError: {e}",
            )
            frappe.msgprint(
                _("⚠️ Impossible d'enregistrer la sortie de stock : {0}.").format(str(e)),
                indicator="orange",
            )
