# -*- coding: utf-8 -*-
"""API État de Salaire KYA — registre de paie (livre de paie) construit à partir
des « Bulletin Paie KYA ». Restitution/consultation + KPIs pour la Comptabilité.

La paie KYA est 100 % maison : aucun module de paie ERPNext natif. Les montants
proviennent des bulletins, eux-mêmes calculés par le moteur
`kya_hr.auto_calc_logic.compute_bulletin` qui lit la configuration
« Parametres Paie KYA » (taux/barèmes saisis par le Comptable).

Endpoints (réservés Comptabilité / Direction) :
- get_etat_salaire(annee, mois=None) : lignes + totaux du registre
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

RH_COMPTA_ROLES = {
    "Comptable", "Accounts Manager", "DFC", "Responsable Comptable",
    "Directeur Général", "DGA", "System Manager",
}

MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
        "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def _check_role():
    if not (RH_COMPTA_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la Comptabilité et à la Direction."),
                     frappe.PermissionError)


@frappe.whitelist()
def get_etat_salaire(annee=None, mois=None, statut=None):
    """Registre de paie : pour l'année (et le mois si fourni), la liste des
    bulletins avec brut, retenues, net, coût employeur + totaux généraux."""
    _check_role()
    annee = int(annee or getdate(today()).year)

    filters = {"annee": annee}
    if mois:
        filters["mois"] = mois
    if statut == "valides":
        filters["docstatus"] = 1
    elif statut == "brouillons":
        filters["docstatus"] = 0
    else:
        filters["docstatus"] = ["<", 2]

    rows = frappe.get_all(
        "Bulletin Paie KYA", filters=filters,
        fields=["name", "employee", "employee_name", "poste", "departement",
                "mois", "mois_num", "annee", "salaire_base", "brut_total",
                "cnss_salarie", "irpp", "autres_retenues", "total_retenues",
                "net_a_payer", "cnss_patronal", "cout_employeur", "docstatus"],
        order_by="mois_num asc, employee_name asc",
    )

    tot = {"brut": 0.0, "cnss": 0.0, "irpp": 0.0, "autres": 0.0,
           "retenues": 0.0, "net": 0.0, "cnss_pat": 0.0, "cout": 0.0}
    for r in rows:
        r["statut_libelle"] = "Validé" if r["docstatus"] == 1 else "Brouillon"
        tot["brut"] += flt(r.brut_total)
        tot["cnss"] += flt(r.cnss_salarie)
        tot["irpp"] += flt(r.irpp)
        tot["autres"] += flt(r.autres_retenues)
        tot["retenues"] += flt(r.total_retenues)
        tot["net"] += flt(r.net_a_payer)
        tot["cnss_pat"] += flt(r.cnss_patronal)
        tot["cout"] += flt(r.cout_employeur)

    for k in tot:
        tot[k] = round(tot[k], 2)

    return {
        "annee": annee, "mois": mois or "",
        "lignes": rows, "nb": len(rows), "totaux": tot,
        "mois_dispo": MOIS,
    }


@frappe.whitelist()
def kpis_paie(annee=None):
    """KPIs paie de l'année : masse salariale (net), charges patronales,
    effectif payé, coût employeur — + série mensuelle du net pour un graphe."""
    _check_role()
    annee = int(annee or getdate(today()).year)
    rows = frappe.get_all(
        "Bulletin Paie KYA", filters={"annee": annee, "docstatus": 1},
        fields=["mois_num", "net_a_payer", "cout_employeur", "cnss_patronal",
                "employee"])
    serie = {f"{i:02d}": 0.0 for i in range(1, 13)}
    net = cout = charges = 0.0
    effectif = set()
    for r in rows:
        serie[r.mois_num] = serie.get(r.mois_num, 0.0) + flt(r.net_a_payer)
        net += flt(r.net_a_payer)
        cout += flt(r.cout_employeur)
        charges += flt(r.cnss_patronal)
        effectif.add(r.employee)
    return {
        "annee": annee,
        "masse_net": round(net, 2),
        "cout_employeur": round(cout, 2),
        "charges_patronales": round(charges, 2),
        "effectif": len(effectif),
        "serie_mensuelle": [round(serie[f"{i:02d}"], 2) for i in range(1, 13)],
    }
