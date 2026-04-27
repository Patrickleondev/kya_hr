import frappe
from frappe.model.document import Document


class PlanTrimestriel(Document):
    def before_save(self):
        self._update_stats()

    def _update_stats(self):
        taches = frappe.get_all(
            "Tache Equipe",
            filters={"plan": self.name},
            fields=["name", "statut", "attributions"],
        )
        self.nombre_taches = len(taches)
        terminees = sum(1 for t in taches if t.statut == "Termin\u00e9")
        self.taches_terminees = terminees
        if self.nombre_taches:
            self.score_collectif = round(terminees / self.nombre_taches * 100, 1)
        else:
            self.score_collectif = 0.0
