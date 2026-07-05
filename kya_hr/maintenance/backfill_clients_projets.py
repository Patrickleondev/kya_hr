# -*- coding: utf-8 -*-
"""Backfill Client KYA / Projet KYA depuis les PV Sortie existants.

Les fiches PV Sortie référençaient auparavant le Customer/Project natif ERPNext.
On a repointé ces Links vers les répertoires maison (Client KYA / Projet KYA).
Pour que les anciennes fiches gardent des liens VALIDES (et non un lien cassé
en rouge), on crée les Client KYA / Projet KYA correspondant aux valeurs déjà
enregistrées. Idempotent : ne crée que ce qui manque.
"""

import frappe


def execute():
    if not (frappe.db.table_exists("PV Sortie Materiel")
            and frappe.db.exists("DocType", "Client KYA")
            and frappe.db.exists("DocType", "Projet KYA")):
        return {"skipped": True}

    from kya_hr.kya_hr.doctype.client_kya.client_kya import creer_ou_recuperer as _client
    from kya_hr.kya_hr.doctype.projet_kya.projet_kya import creer_ou_recuperer as _projet

    clients = 0
    projets = 0

    # Clients : valeurs distinctes du champ customer OU du texte libre customer_manuel
    noms_clients = set()
    for f in ("customer", "customer_manuel"):
        for v in frappe.db.sql_list(
                f"SELECT DISTINCT `{f}` FROM `tabPV Sortie Materiel` "
                f"WHERE `{f}` IS NOT NULL AND `{f}` != ''"):
            noms_clients.add(v.strip())
    for nom in noms_clients:
        if not frappe.db.exists("Client KYA", nom):
            try:
                _client(nom)
                clients += 1
            except Exception:
                frappe.log_error(frappe.get_traceback(), "backfill Client KYA")

    # Projets : idem
    noms_projets = set()
    for f in ("project", "project_manuel"):
        for v in frappe.db.sql_list(
                f"SELECT DISTINCT `{f}` FROM `tabPV Sortie Materiel` "
                f"WHERE `{f}` IS NOT NULL AND `{f}` != ''"):
            noms_projets.add(v.strip())
    for nom in noms_projets:
        if not frappe.db.exists("Projet KYA", nom):
            try:
                _projet(nom)
                projets += 1
            except Exception:
                frappe.log_error(frappe.get_traceback(), "backfill Projet KYA")

    frappe.db.commit()
    return {"clients_crees": clients, "projets_crees": projets}
