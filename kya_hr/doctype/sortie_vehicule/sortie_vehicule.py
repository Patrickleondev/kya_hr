# Copyright (c) 2026, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class SortieVehicule(Document):
    def validate(self):
        self._validate_chauffeur_actif()
        self._validate_dates()
        self._validate_unique_active_per_vehicle()
        self._enrich_make_model()
        self._compute_km()
        self._sync_statut_from_workflow()

    def before_submit(self):
        if not self.workflow_state:
            self.workflow_state = "Approuvée"
        if not self.statut:
            self.statut = "Approuvée"

    def on_update_after_submit(self):
        self._sync_statut_from_workflow()
        self._compute_km()
        # Persist computed value after submit (read_only fields aren't auto-saved)
        if self.docstatus == 1:
            self.db_set("km_parcourus", self.km_parcourus or 0, update_modified=False)
            self.db_set("statut", self.statut, update_modified=False)
        self._capture_controleur()
        self._update_vehicle_state()

    def on_submit(self):
        self._update_vehicle_state()

    def on_cancel(self):
        if self.vehicle:
            frappe.db.set_value("Vehicle", self.vehicle, "kya_statut", "Disponible")

    # ───── Validations ──────────────────────────────────────────────
    def _validate_chauffeur_actif(self):
        if not self.chauffeur:
            return
        info = frappe.db.get_value(
            "Employee", self.chauffeur, ["status", "employee_name"], as_dict=True
        )
        if not info or info.status != "Active":
            frappe.throw(
                _("Le chauffeur sélectionné n'est pas un employé actif.")
            )

    def _validate_dates(self):
        if not (self.date_depart and self.date_retour_prevue):
            return
        if get_datetime(self.date_retour_prevue) <= get_datetime(self.date_depart):
            frappe.throw(_("La date de retour prévue doit être postérieure à la date de départ."))

    def _validate_unique_active_per_vehicle(self):
        """Empêche deux sorties simultanées approuvées pour le même véhicule."""
        if not self.vehicle or self.docstatus == 2:
            return
        if self.statut in ("Retour confirmé", "Annulée", "Brouillon"):
            return
        overlap = frappe.db.sql(
            """
            SELECT name FROM `tabSortie Vehicule`
            WHERE vehicle = %(v)s
              AND name != %(n)s
              AND docstatus < 2
              AND statut IN ('Approuvée', 'En mission')
              AND date_depart < %(retour)s
              AND date_retour_prevue > %(depart)s
            LIMIT 1
            """,
            {
                "v": self.vehicle,
                "n": self.name or "",
                "depart": self.date_depart,
                "retour": self.date_retour_prevue,
            },
        )
        if overlap:
            frappe.throw(
                _("Le véhicule {0} a déjà une sortie active sur cette plage horaire ({1}).").format(
                    self.license_plate or self.vehicle, overlap[0][0]
                )
            )

    # ───── Enrichissements ──────────────────────────────────────────
    def _enrich_make_model(self):
        if self.vehicle:
            make, model = frappe.db.get_value("Vehicle", self.vehicle, ["make", "model"]) or ("", "")
            self.vehicle_make_model = f"{make or ''} {model or ''}".strip()

    def _compute_km(self):
        if self.km_depart and self.km_retour and self.km_retour >= self.km_depart:
            self.km_parcourus = self.km_retour - self.km_depart
        elif not self.km_retour:
            self.km_parcourus = 0

    def _sync_statut_from_workflow(self):
        if self.workflow_state and self.workflow_state in (
            "Brouillon", "Approuvée", "En mission", "Retour confirmé", "Annulée"
        ):
            self.statut = self.workflow_state

    def _capture_controleur(self):
        # Quand quelqu'un passe à "Approuvée" / "En mission" / "Retour confirmé"
        if self.workflow_state in ("Approuvée", "En mission", "Retour confirmé") and not self.controle_par:
            self.db_set("controle_par", frappe.session.user, update_modified=False)
            self.db_set("date_controle", now_datetime(), update_modified=False)

    def _update_vehicle_state(self):
        """Synchronise Vehicle.kya_statut + Vehicle.last_odometer."""
        if not self.vehicle:
            return
        if self.statut == "En mission":
            frappe.db.set_value("Vehicle", self.vehicle, "kya_statut", "En mission")
        elif self.statut in ("Retour confirmé", "Annulée"):
            frappe.db.set_value("Vehicle", self.vehicle, "kya_statut", "Disponible")
            if self.km_retour:
                last = frappe.db.get_value("Vehicle", self.vehicle, "last_odometer") or 0
                if self.km_retour > last:
                    frappe.db.set_value("Vehicle", self.vehicle, "last_odometer", self.km_retour)
