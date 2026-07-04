"""Moteur de calcul des indemnités RH KYA — 100 % maison (aucune paie ERPNext).

Basé sur la Convention Collective Interprofessionnelle, avec des barèmes
ENTIÈREMENT configurables par la RH via le doctype Single « Paramètres RH KYA » :

  - Indemnité de licenciement       (Art. 25) : % du salaire mensuel moyen par
        année, par tranches d'ancienneté (35 % / 40 % / 45 %), fractions incluses.
  - Prime d'ancienneté              (Art. 40) : 2 % au seuil + 1 %/an dès la 4e
        année, plafonnée (35 %). Majoration du salaire de base.
  - Indemnité de départ à la retraite (Art. 70) : % de l'indemnité de licenciement
        (45 / 50 / 60 %), plancher de 3 mois de salaire.
  - Permissions exceptionnelles     (Art. 50) : barème jours par évènement.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

_RH_ROLES = {"System Manager", "Responsable RH", "HR Manager", "HR User",
             "Assistant(e) RH", "Directeur Général", "DG", "DGA"}


def _guard():
    if not _RH_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé aux Ressources Humaines."), frappe.PermissionError)


def _params():
    """Barèmes configurables (Paramètres RH KYA) avec valeurs de repli sûres."""
    p = frappe.get_single("Parametres RH KYA")
    g = lambda f, d: flt(p.get(f)) if p.get(f) not in (None, "") else d
    return {
        "age_retraite": int(g("age_retraite", 60)),
        "lic": (g("lic_taux_1_5", 35), g("lic_taux_6_10", 40), g("lic_taux_11_plus", 45)),
        "lic_mois": int(g("lic_mois_moyenne", 12)),
        "anc": {"seuil": int(g("anc_seuil_annees", 2)), "taux_seuil": g("anc_taux_seuil", 2),
                "debut": int(g("anc_annee_debut_annuel", 4)), "taux_an": g("anc_taux_annuel", 1),
                "plafond": g("anc_plafond", 35)},
        "ret": (g("ret_taux_1_5", 45), g("ret_taux_6_10", 50), g("ret_taux_11_plus", 60)),
        "ret_min_mois": int(g("ret_min_mois", 3)),
    }


def anciennete_annees(date_embauche, date_reference=None):
    if not date_embauche:
        return 0.0
    ref = getdate(date_reference or today())
    return round((ref - getdate(date_embauche)).days / 365.25, 2)


def indemnite_licenciement(salaire_moyen, anciennete, params=None):
    """Art. 25 : par tranches d'années (fractions incluses)."""
    p = params or _params()
    sm = flt(salaire_moyen)
    a = flt(anciennete)
    t1, t2, t3 = p["lic"]
    y1 = min(a, 5)
    y2 = min(max(a - 5, 0), 5)
    y3 = max(a - 10, 0)
    lignes = [
        {"tranche": "1re à 5e année", "annees": round(y1, 2), "taux": t1, "montant": round(sm * y1 * t1 / 100, 0)},
        {"tranche": "6e à 10e année", "annees": round(y2, 2), "taux": t2, "montant": round(sm * y2 * t2 / 100, 0)},
        {"tranche": "au-delà de la 10e", "annees": round(y3, 2), "taux": t3, "montant": round(sm * y3 * t3 / 100, 0)},
    ]
    total = sum(l["montant"] for l in lignes)
    return {"total": round(total, 0), "lignes": lignes, "salaire_moyen": sm, "anciennete": a}


def taux_prime_anciennete(anciennete, params=None):
    p = (params or _params())["anc"]
    a = flt(anciennete)
    if a < p["seuil"]:
        return 0.0
    taux = p["taux_seuil"]
    if a >= p["debut"]:
        taux += p["taux_an"] * (int(a) - (p["debut"] - 1))
    return round(min(taux, p["plafond"]), 2)


def prime_anciennete(salaire_base, anciennete, params=None):
    """Art. 40 : majoration % du salaire de base."""
    taux = taux_prime_anciennete(anciennete, params)
    montant = round(flt(salaire_base) * taux / 100, 0)
    return {"taux": taux, "montant": montant, "salaire_base": flt(salaire_base)}


def indemnite_retraite(salaire_moyen, salaire_base, anciennete, params=None):
    """Art. 70 : % de l'indemnité de licenciement, plancher 3 mois."""
    p = params or _params()
    a = flt(anciennete)
    lic = indemnite_licenciement(salaire_moyen, a, p)["total"]
    r1, r2, r3 = p["ret"]
    if a <= 5:
        taux, bracket = r1, "1 à 5 ans"
    elif a <= 10:
        taux, bracket = r2, "6 à 10 ans"
    else:
        taux, bracket = r3, "plus de 10 ans"
    brut = round(lic * taux / 100, 0)
    prime = prime_anciennete(salaire_base, a, p)["montant"]
    plancher = round(p["ret_min_mois"] * (flt(salaire_base) + prime), 0)
    montant = max(brut, plancher)
    return {"total": round(montant, 0), "base_licenciement": lic, "taux": taux,
            "tranche": bracket, "brut": brut, "plancher": plancher,
            "plancher_applique": montant == plancher and plancher > brut}


@frappe.whitelist()
def solde_tout_compte(salarie, motif_depart=None, salaire_moyen=None, date_reference=None):
    """Calcul complet du solde de tout compte pour un salarié, selon le motif.

    Renvoie un détail complet, prêt pour l'affichage et le PDF. `salaire_moyen`
    par défaut = salaire de base (aucun historique de paie n'est tenu ici)."""
    _guard()
    s = frappe.get_doc("Salarie KYA", salarie)
    p = _params()
    sb = flt(s.salaire_base)
    sm = flt(salaire_moyen) if salaire_moyen not in (None, "", 0) else sb
    # Référence = date de sortie si connue (sinon aujourd'hui).
    ref = date_reference or s.date_debauchage or today()
    a = anciennete_annees(s.date_embauche, ref)
    motif = (motif_depart or s.motif_debauchage or "").strip()

    prime = prime_anciennete(sb, a, p)
    resultat = {
        "salarie": s.name, "nom_complet": s.nom_complet, "poste": s.poste_occupe,
        "date_embauche": str(s.date_embauche or ""), "date_reference": str(getdate(date_reference or today())),
        "anciennete": a, "salaire_base": sb, "salaire_moyen": sm, "motif_depart": motif,
        "prime_anciennete": prime, "composantes": [], "total": 0.0,
    }

    m = motif.lower()
    if "licenc" in m:
        lic = indemnite_licenciement(sm, a, p)
        resultat["indemnite_licenciement"] = lic
        resultat["composantes"].append({"libelle": "Indemnité de licenciement (Art. 25)", "montant": lic["total"]})
    elif "retraite" in m:
        ret = indemnite_retraite(sm, sb, a, p)
        resultat["indemnite_retraite"] = ret
        resultat["composantes"].append({"libelle": "Indemnité de départ à la retraite (Art. 70)", "montant": ret["total"]})

    # La prime d'ancienneté s'ajoute dans tous les cas où elle est due.
    if prime["montant"]:
        resultat["composantes"].append({"libelle": "Prime d'ancienneté (Art. 40)", "montant": prime["montant"]})

    resultat["total"] = round(sum(c["montant"] for c in resultat["composantes"]), 0)
    return resultat


@frappe.whitelist()
def bareme_permissions():
    """Barème des permissions exceptionnelles (Art. 50), configurable."""
    _guard()
    p = frappe.get_single("Parametres RH KYA")
    return [{"evenement": r.evenement, "jours": r.jours} for r in (p.permissions or [])]
