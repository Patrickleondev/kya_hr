import frappe
from frappe import _
from frappe.model.document import Document


class ParametresStockKYA(Document):
    def validate(self):
        vus = set()
        for r in self.regles or []:
            if r.categorie in vus:
                frappe.throw(_("La catégorie « {0} » apparaît deux fois dans les règles.").format(r.categorie))
            vus.add(r.categorie)
            if (r.coefficient or 0) < 0 or (r.coefficient or 0) > 1:
                frappe.throw(_("Coefficient invalide pour « {0} » : doit être entre 0 et 1.").format(r.categorie))
            if (r.plancher or 0) < 0:
                frappe.throw(_("Plancher invalide pour « {0} ».").format(r.categorie))
