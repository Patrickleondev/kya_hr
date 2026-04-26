import frappe
from frappe.model.document import Document


class KYAContractTemplate(Document):
    def validate(self):
        if self.is_active:
            # Désactiver les autres templates du même type
            frappe.db.sql(
                """UPDATE `tabKYA Contract Template`
                   SET is_active = 0
                   WHERE contract_type = %s AND name != %s""",
                (self.contract_type, self.name),
            )
