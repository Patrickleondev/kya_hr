# -*- coding: utf-8 -*-
"""Entretien Vehicule KYA — enregistrement d'un entretien/réparation véhicule.

Saisie simple (web form tablette). Met à jour le kilométrage du véhicule et
sert de base aux rappels de prochaine échéance dans le dashboard logistique.
"""
import frappe
from frappe.model.document import Document
from frappe.utils import cint, now_datetime, today


class EntretienVehiculeKYA(Document):
    def validate(self):
        # Garde-fou : le web form pouvait envoyer le littéral "Today"
        if not self.date_entretien or str(self.date_entretien).strip().lower() == "today":
            self.date_entretien = today()

        if self.vehicle and not self.vehicle_make_model:
            make, model = frappe.db.get_value("Vehicle", self.vehicle, ["make", "model"]) or (None, None)
            self.vehicle_make_model = " ".join([p for p in (make, model) if p])

        if not self.enregistre_par or self.enregistre_par == "user":
            self.enregistre_par = frappe.session.user
        if not self.date_enregistrement:
            self.date_enregistrement = now_datetime()

    def on_update(self):
        if self.vehicle and cint(self.km_actuel) > 0:
            last = cint(frappe.db.get_value("Vehicle", self.vehicle, "last_odometer") or 0)
            if cint(self.km_actuel) > last:
                frappe.db.set_value("Vehicle", self.vehicle, "last_odometer",
                                    cint(self.km_actuel), update_modified=False)
