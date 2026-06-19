# -*- coding: utf-8 -*-
"""Controller léger pour Planning Conge Equipe.

Le DocType est `custom: 1` : Frappe ne charge donc PAS automatiquement cette
classe. Toute la logique métier (calculs, génération des plannings
individuels, synchro statut) est câblée via doc_events dans hooks.py et
implémentée dans `kya_hr.planning_conge_equipe_logic`.
"""
from frappe.model.document import Document


class PlanningCongeEquipe(Document):
    pass
