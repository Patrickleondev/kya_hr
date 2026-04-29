# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DemandeAchatKYA(Document):
    def validate(self):
        self.set_employee_details()
        self.calculate_totals()
        self.set_palier()

    def set_employee_details(self):
        if self.employee and not self.employee_name:
            self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")

    def calculate_totals(self):
        """Recalcule la somme des items.

        Si l'utilisateur a saisi un montant_total manuel ET qu'il n'y a pas
        d'items renseignés avec prix, on conserve la valeur saisie.
        Sinon on écrase avec la somme des lignes.
        """
        items = self.items or []
        items_total = 0
        items_have_values = False
        for row in items:
            row.montant = (row.quantite or 0) * (row.prix_unitaire or 0)
            if row.montant:
                items_have_values = True
            items_total += row.montant

        if items_have_values:
            # Items renseignés = source de vérité
            self.montant_total = items_total
        elif not self.montant_total:
            # Aucune saisie manuelle ni items → 0
            self.montant_total = 0
        # Sinon : on conserve la valeur manuelle saisie

    def set_palier(self):
        m = self.montant_total or 0
        urg = (self.urgence or "Normal").strip()
        urgent = urg in ("Urgent", "Très Urgent")
        if m > 15000000:
            base = "Palier 4 (> 15 000 000 XOF) — Appel d'offre international (60j) — Chef + DAAF + DG"
        elif m > 2000000:
            base = "Palier 3 (2 000 001 – 15 000 000 XOF) — Appel d'offre national (30j) — Chef + DAAF + DG"
        elif m > 100000:
            base = "Palier 2 (100 001 – 2 000 000 XOF) — 3 devis (1 sem.) — Chef + DAAF + DG"
        else:
            if urgent:
                base = "Palier 1 URGENT (≤ 100 000 XOF) — Validation DG requise (proc. accélérée)"
            else:
                base = "Palier 1 (≤ 100 000 XOF) — Procédure simplifiée (72h) — Chef + DAAF"
        if urgent:
            base += f" — 🚨 {urg}"
        self.palier = base

    def before_submit(self):
        if self.workflow_state == "Approuvé":
            self.statut = "Approuvé"

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self.capture_signature()

    def capture_signature(self):
        """Auto-fill approver name/date when they sign at their workflow level.

        Workflow chain (procédure AEA-PRO-01-V01) :
          Brouillon → En attente Chef → En attente DAAF
            → (palier 1 normal, ≤100k) Approuvé
            → (palier >1 OU urgent) En attente DG → Approuvé

        Audit Interne et Comptabilité signent en lecture seule via leur rôle
        respectif (visas optionnels post-approbation).
        """
        user = frappe.session.user
        roles = set(frappe.get_roles(user))
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        name = emp or frappe.utils.get_fullname(user)
        today = frappe.utils.today()
        ws = self.workflow_state
        m = self.montant_total or 0
        urg = (self.urgence or "Normal").strip()
        urgent = urg in ("Urgent", "Très Urgent")
        needs_dg = m > 100000 or urgent

        # Chef signs: state moves from "En attente Chef" → "En attente DAAF"
        if ws == "En attente DAAF" and not self.get("signataire_chef"):
            self.db_set("signataire_chef", name, update_modified=False)
            self.db_set("date_signature_chef", today, update_modified=False)

        # DAAF signs: when state moves out of "En attente DAAF"
        daaf_signed_now = (
            ws == "En attente DG"
            or (ws == "Approuvé" and not needs_dg)
        )
        if daaf_signed_now and not self.get("signataire_dga"):
            self.db_set("signataire_dga", name, update_modified=False)
            self.db_set("date_signature_dga", today, update_modified=False)

        # DG signs: state "En attente DG" → "Approuvé" (paliers 2/3/4 ou urgent)
        if ws == "Approuvé" and needs_dg and not self.get("signataire_dg"):
            self.db_set("signataire_dg", name, update_modified=False)
            self.db_set("date_signature_dg", today, update_modified=False)

        # Audit Interne (visa post-approbation, optionnel)
        if "Auditeur Interne" in roles and self.get("signature_audit") and not self.get("signataire_audit"):
            self.db_set("signataire_audit", name, update_modified=False)
            self.db_set("date_signature_audit", today, update_modified=False)

        # Comptabilité (visa post-approbation, fiche caisse)
        if "Comptable" in roles and self.get("signature_compta") and not self.get("signataire_compta"):
            self.db_set("signataire_compta", name, update_modified=False)
            self.db_set("date_signature_compta", today, update_modified=False)
