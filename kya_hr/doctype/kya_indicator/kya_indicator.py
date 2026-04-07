import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class KYAIndicator(Document):
    def before_save(self):
        self.date_calcul = now_datetime()
