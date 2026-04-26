# Copyright (c) 2026, KYA-Energy Group and contributors
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, add_days


class DocumentVehicule(Document):
    def validate(self):
        if self.date_emission and self.date_expiration:
            if getdate(self.date_expiration) <= getdate(self.date_emission):
                frappe.throw(_("La date d'expiration doit être postérieure à la date d'émission."))

    @property
    def is_expiring(self):
        if not self.date_expiration:
            return False
        return getdate(self.date_expiration) <= add_days(today(), self.alerte_jours_avant or 30)


def send_expiry_reminders():
    """Tâche planifiée quotidienne : alerte le Gestionnaire de Flotte
    pour tous les documents véhicule expirant sous N jours.
    """
    rows = frappe.get_all(
        "Document Vehicule",
        fields=["name", "vehicle", "license_plate", "type_document", "date_expiration", "alerte_jours_avant"],
        filters={"date_expiration": ["<=", add_days(today(), 60)]},
    )
    expiring = []
    for r in rows:
        seuil = add_days(today(), r.alerte_jours_avant or 30)
        if getdate(r.date_expiration) <= seuil:
            expiring.append(r)
    if not expiring:
        return

    recipients = frappe.get_all(
        "Has Role",
        filters={"role": "Gestionnaire de Flotte", "parenttype": "User"},
        pluck="parent",
    )
    recipients = [u for u in recipients if u and u not in ("Administrator", "Guest")]
    if not recipients:
        return

    rows_html = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee;'>{r.license_plate or r.vehicle}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;'>{r.type_document}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;color:#d84315;'>{r.date_expiration}</td></tr>"
        for r in expiring
    )
    message = f"""
    <div style='font-family:Arial,sans-serif;max-width:700px;margin:0 auto;'>
      <div style='background:linear-gradient(135deg,#ff6f00,#ff8f00);padding:20px;border-radius:12px 12px 0 0;color:white;'>
        <h2 style='margin:0;'>🚗 Documents véhicules à renouveler</h2>
      </div>
      <div style='background:white;padding:20px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>
        <p>Bonjour,</p>
        <p>Les documents véhicule suivants arrivent à expiration :</p>
        <table style='width:100%;border-collapse:collapse;margin-top:10px;'>
          <thead>
            <tr style='background:#f5f5f5;'>
              <th style='padding:8px 10px;text-align:left;'>Véhicule</th>
              <th style='padding:8px 10px;text-align:left;'>Document</th>
              <th style='padding:8px 10px;text-align:left;'>Expire le</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </div>
    """
    frappe.sendmail(
        recipients=recipients,
        subject=f"[KYA Logistique] {len(expiring)} document(s) véhicule à renouveler",
        message=message,
    )
