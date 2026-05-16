"""KYA Import RH — DocType conteneur des imports Excel RH.

Stocke métadonnées + résultats + traces des imports. Le parsing et l'écriture
dans les doctypes cibles (Attendance, Leave Allocation, etc.) sont déléguées
à `kya_hr.api.rh_imports`.
"""
from frappe.model.document import Document


class KYAImportRH(Document):
    pass
