# -*- coding: utf-8 -*-
"""Plein Carburant KYA — enregistrement d'un plein de carburant véhicule.

Saisie simple (web form tablette). Calcule le prix/litre et met à jour le
kilométrage du véhicule. Traçabilité : qui a enregistré, quand.
"""
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, now_datetime, today


class PleinCarburantKYA(Document):
    def validate(self):
        # Garde-fou : le web form pouvait envoyer le littéral "Today"
        if not self.date_plein or str(self.date_plein).strip().lower() == "today":
            self.date_plein = today()

        # Prix au litre auto
        if flt(self.litres) > 0:
            self.prix_litre = flt(self.montant) / flt(self.litres)
        else:
            self.prix_litre = 0

        # Marque / modèle lisible
        if self.vehicle and not self.vehicle_make_model:
            make, model = frappe.db.get_value("Vehicle", self.vehicle, ["make", "model"]) or (None, None)
            self.vehicle_make_model = " ".join([p for p in (make, model) if p])

        # Traçabilité
        if not self.enregistre_par or self.enregistre_par == "user":
            self.enregistre_par = frappe.session.user
        if not self.date_enregistrement:
            self.date_enregistrement = now_datetime()

    def on_update(self):
        # Met à jour le kilométrage du véhicule si plus récent
        if self.vehicle and cint(self.km_actuel) > 0:
            last = cint(frappe.db.get_value("Vehicle", self.vehicle, "last_odometer") or 0)
            if cint(self.km_actuel) > last:
                frappe.db.set_value("Vehicle", self.vehicle, "last_odometer",
                                    cint(self.km_actuel), update_modified=False)
