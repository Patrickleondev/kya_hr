# -*- coding: utf-8 -*-
"""Tests d'ACCÈS (dev) : « not permitted » via le flux + pages dashboard.

Complète `multirole_test` (qui teste les transitions). Ici on vérifie que :
  1. l'APPROBATEUR qui arrive par le LIEN MAIL (web form de la fiche d'un AUTRE)
     peut bien OUVRIR le web form (pas de « not permitted ») ;
  2. chaque rôle métier peut OUVRIR le dashboard qui le concerne.

Réutilise les utilisateurs mono-rôle de `multirole_test`.
Lancement : `bench --site frontend execute kya_hr.maintenance.access_test.run`
"""
from __future__ import annotations

import frappe

from kya_hr.maintenance import multirole_test as mt

# (route web form, doctype, [(action, soumetteur)], approbateur arrivant par mail)
WEBFORM_CASES = [
    ("demande-achat", "Demande Achat KYA", [("Soumettre", "employee")], "chef"),
    ("permission-sortie-employe", "Permission Sortie Employe", [("Soumettre", "employee")], "chef"),
    ("pv-sortie-materiel", "PV Sortie Materiel", [("Envoyer pour Approbation", "employee")], "chef"),
    ("brouillard-caisse", "Brouillard Caisse", [("Soumettre au Comptable", "caissier")], "comptable"),
    ("etat-recap", "Etat Recap Cheques", [("Soumettre au DFC", "comptable")], "dfc"),
    ("retour-materiel", "Retour Materiel KYA", [("Déclarer le Retour", "employee")], "stock"),
]

# (page, rôle qui DOIT y accéder)
DASHBOARD_CASES = [
    ("kya-tableau-de-bord", "dg"), ("kya-tableau-de-bord", "dga"),
    ("comptabilite-dashboard", "caissier"), ("comptabilite-dashboard", "dfc"),
    ("comptabilite-dashboard", "dg"),
    ("achats-dashboard", "achats"), ("achats-dashboard", "dg"),
    ("kya-stocks-dashboard", "stock"), ("kya-stocks-dashboard", "dg"),
    ("kya-dashboard-equipe", "chef"), ("formation-dashboard", "rh"),
    ("kya-reunion-dashboard", "dg"), ("recap-brouillards", "dg"),
]

_DENY = ("réservé", "acces refuse", "accès refusé", "not permitted",
         "veuillez vous connecter", "n'êtes pas autorisé")


def _flow_by_dt(dt):
    for f in mt._flows(mt._ref_employee()):
        if f["doctype"] == dt:
            return f
    return None


def _denied(html):
    low = (html or "").lower()
    return len(html) < 600 or any(x in low for x in _DENY)


def run():
    mt.ensure_test_users()
    from frappe.website.serve import get_response_content
    res = []

    # 1) accès web form approbateur (lien mail)
    for route, dt, steps, approver in WEBFORM_CASES:
        f = _flow_by_dt(dt)
        try:
            doc = mt._create(f, mt._ref_employee(), mt._email(f["submitter"]))
            for action, key in steps:
                mt._apply(dt, doc.name, action, mt._email(key))
            frappe.set_user(mt._email(approver))
            frappe.local.form_dict = frappe._dict({"name": doc.name})
            try:
                html = get_response_content("%s/%s" % (route, doc.name))
                res.append(("webform", route + " <- " + approver, not _denied(html)))
            except Exception as e:
                res.append(("webform", route + " <- " + approver, False))
            finally:
                frappe.set_user("Administrator")
        except Exception:
            res.append(("webform", route + " <- " + approver, False))
        finally:
            frappe.set_user("Administrator")

    # 2) accès pages dashboard par rôle
    for page, key in DASHBOARD_CASES:
        frappe.set_user(mt._email(key))
        frappe.local.form_dict = frappe._dict({})
        try:
            html = get_response_content(page)
            res.append(("dashboard", page + " <- " + key, not _denied(html)))
        except Exception:
            res.append(("dashboard", page + " <- " + key, False))
        finally:
            frappe.set_user("Administrator")

    frappe.db.rollback()
    npass = sum(1 for r in res if r[2])
    print("\n========= TEST ACCÈS (flux mail + dashboards) =========")
    cur = None
    for kind, label, ok in res:
        if kind != cur:
            print("\n###", kind.upper())
            cur = kind
        print("   %s %s" % ("OK  " if ok else "XXX ", label))
    print("\n   %d / %d OK" % (npass, len(res)))
    return {"pass": npass, "total": len(res)}
