# -*- coding: utf-8 -*-
"""Plan Formation Beneficiaire — un employé bénéficiaire d'une action de formation.

Permet le suivi PAR EMPLOYÉ (la RH marque Terminé pour chaque bénéficiaire),
là où Plan Formation Item ne peut pas contenir de sous-table (Frappe interdit
les child tables imbriquées). Rattaché à la ligne de formation via formation_ref.
"""
from frappe.model.document import Document


class PlanFormationBeneficiaire(Document):
    pass
