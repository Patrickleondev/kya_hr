import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class KYAEvaluation(Document):
    def validate(self):
        self._compute_taux_moyen()

    def before_save(self):
        if self.statut == "Soumis" and not self.soumis_le:
            self.soumis_le = now_datetime()

    def _compute_taux_moyen(self):
        if not self.criteres:
            self.taux_moyen = 0.0
            return
        # Notes are on a 2-5 scale; convert to 0-100 via (note - 1) / 4 * 100
        notes = [c.note for c in self.criteres if c.note is not None]
        if notes:
            avg_raw = sum(notes) / len(notes)
            # Scale: 1=0%, 2=25%, 3=50%, 4=75%, 5=100%
            self.taux_moyen = round((avg_raw - 1) / 4 * 100, 1)
        else:
            self.taux_moyen = 0.0
