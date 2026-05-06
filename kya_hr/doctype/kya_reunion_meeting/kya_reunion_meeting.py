import frappe
from frappe.model.document import Document


class KYAReunionMeeting(Document):
    def validate(self):
        self.presence_count = len(self.presences or [])
