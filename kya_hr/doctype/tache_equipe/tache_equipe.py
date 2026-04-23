import frappe
from frappe.model.document import Document


class TacheEquipe(Document):
    def validate(self):
        if self.taux_effectif and self.taux_effectif > 0:
            if self.taux_effectif >= 100:
                self.statut = "Termin\u00e9"
            elif self.taux_effectif > 0:
                self.statut = "En cours"
