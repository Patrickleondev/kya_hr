"""Tableau de bord « Marchés & Clients ».

Le suivi des marchés n'existait que sous forme d'un compteur sur le tableau
de bord Achats : impossible de savoir quel chantier gagne ou perd de l'argent,
ni ce qu'un client doit encore. Cette page répond à trois questions :

  1. Combien rapportent réellement les marchés (marge brute / nette, écart au
     budget prévisionnel) ?
  2. Quels chantiers dérapent (marge négative, avance qui ne couvre pas les
     dépenses engagées, dépassement de budget) ?
  3. Où en est chaque client — marchés réalisés d'un côté, contrats SoP et
     soldes dus de l'autre.

Lecture seule. Tout est recalculé en direct : aucune valeur figée.
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate, today

no_cache = 1

_ALLOWED_ROLES = {
    "Comptable", "DFC", "DAAF", "Accounts Manager", "Accounts User",
    "Auditeur Interne", "Directeur Général", "DG", "DGA", "System Manager",
    "Chef Service", "Responsable Commercial",
}

# Postes de coût du doctype Marche KYA, dans l'ordre d'affichage.
_POSTES = [
    ("cout_modules_pv", "Modules PV"),
    ("cout_batteries", "Batteries"),
    ("cout_onduleurs", "Onduleurs"),
    ("cout_supports_pv", "Supports PV"),
    ("cout_supports_batteries", "Supports batteries"),
    ("cout_cables", "Câbles"),
    ("cout_protection", "Protections"),
    ("cout_terre", "Mise à la terre"),
    ("cout_accessoires_cablage", "Accessoires câblage"),
    ("cout_gestionnaire", "Gestionnaire"),
    ("frais_carburant", "Carburant"),
    ("frais_location_camion", "Location camion"),
    ("frais_perdiems", "Perdiems"),
    ("frais_hebergement", "Hébergement"),
    ("frais_autres", "Autres frais"),
]


def _exists(doctype):
    try:
        return bool(frappe.db.exists("DocType", doctype))
    except Exception:
        return False


def _fmt_m(v):
    """Montant en millions de FCFA, une décimale — lisible sur une tuile."""
    return "{:,.1f}".format(flt(v) / 1_000_000.0).replace(",", " ")


def get_overview():
    marches, sops = [], []
    if _exists("Marche KYA"):
        marches = frappe.get_all(
            "Marche KYA",
            fields=["name", "nom_marche", "numero_marche", "type_marche", "statut",
                    "client_beneficiaire", "date_debut", "date_fin", "puissance_kwc",
                    "montant_total_facture", "montant_avance_demarrage",
                    "budget_previsionnel", "cout_total_realisation",
                    "marge_brute", "taxes", "marge_nette",
                    "ecart_avance", "ecart_budget_previsionnel"]
            + [f for f, _l in _POSTES],
            limit_page_length=0) or []
    if _exists("KYA SoP Client"):
        sops = frappe.get_all(
            "KYA SoP Client",
            fields=["name", "nom_client", "type_client", "mode_paiement", "statut",
                    "statut_paiement", "montant_total", "montant_avance", "solde_du",
                    "date_prevue_solde", "date_installation"],
            limit_page_length=0) or []

    ca = sum(flt(m.montant_total_facture) for m in marches)
    cout = sum(flt(m.cout_total_realisation) for m in marches)
    marge_b = sum(flt(m.marge_brute) for m in marches)
    marge_n = sum(flt(m.marge_nette) for m in marches)
    budget = sum(flt(m.budget_previsionnel) for m in marches)

    en_cours = [m for m in marches if m.statut == "En cours"]
    termines = [m for m in marches if m.statut in ("Terminé", "Clôturé")]

    # ── Alertes : ce qui doit faire réagir ────────────────────────────────
    alertes = []
    for m in marches:
        if flt(m.montant_total_facture) and flt(m.marge_nette) < 0:
            alertes.append({
                "marche": m.name, "nom": m.nom_marche or m.name,
                "client": m.client_beneficiaire or "—", "niveau": "grave",
                "libelle": "Marge nette négative",
                "detail": "{} FCFA".format("{:,.0f}".format(flt(m.marge_nette)).replace(",", " ")),
            })
        # Rappel des formules du doctype : écart = COÛT - référence.
        # Un écart POSITIF est donc un dépassement, pas une économie.
        elif flt(m.budget_previsionnel) and flt(m.ecart_budget_previsionnel) > 0:
            alertes.append({
                "marche": m.name, "nom": m.nom_marche or m.name,
                "client": m.client_beneficiaire or "—", "niveau": "moyen",
                "libelle": "Budget dépassé",
                "detail": "{} FCFA au-delà".format(
                    "{:,.0f}".format(flt(m.ecart_budget_previsionnel)).replace(",", " ")),
            })
        elif (m.statut == "En cours" and flt(m.montant_avance_demarrage)
              and flt(m.ecart_avance) > 0):
            alertes.append({
                "marche": m.name, "nom": m.nom_marche or m.name,
                "client": m.client_beneficiaire or "—", "niveau": "info",
                "libelle": "Avance insuffisante",
                "detail": "l'avance ne couvre pas les dépenses engagées",
            })

    # ── Lignes marché, triées de la pire marge à la meilleure ─────────────
    lignes = []
    for m in marches:
        fac = flt(m.montant_total_facture)
        lignes.append({
            "nom": m.name,
            "libelle": m.nom_marche or m.name,
            "numero": m.numero_marche or "",
            "client": m.client_beneficiaire or "—",
            "type": m.type_marche or "—",
            "statut": m.statut or "—",
            "date_fin": str(m.date_fin) if m.date_fin else "",
            "ca": fac,
            "cout": flt(m.cout_total_realisation),
            "marge_nette": flt(m.marge_nette),
            "taux": round(flt(m.marge_nette) / fac * 100.0, 1) if fac else None,
            "ecart_budget": flt(m.ecart_budget_previsionnel),
        })
    lignes.sort(key=lambda x: (x["taux"] if x["taux"] is not None else 999))

    # ── Suivi client : marchés + SoP réconciliés sur le nom ───────────────
    clients = {}

    def _cle(nom):
        return (nom or "—").strip().upper()

    for m in marches:
        c = clients.setdefault(_cle(m.client_beneficiaire), {
            "nom": (m.client_beneficiaire or "—").strip() or "—",
            "nb_marches": 0, "ca": 0.0, "marge": 0.0,
            "nb_sop": 0, "sop_total": 0.0, "solde_du": 0.0, "retard": 0})
        c["nb_marches"] += 1
        c["ca"] += flt(m.montant_total_facture)
        c["marge"] += flt(m.marge_nette)

    auj = getdate(today())
    for s in sops:
        c = clients.setdefault(_cle(s.nom_client), {
            "nom": (s.nom_client or "—").strip() or "—",
            "nb_marches": 0, "ca": 0.0, "marge": 0.0,
            "nb_sop": 0, "sop_total": 0.0, "solde_du": 0.0, "retard": 0})
        c["nb_sop"] += 1
        c["sop_total"] += flt(s.montant_total)
        c["solde_du"] += flt(s.solde_du)
        en_retard = s.statut == "En retard" or (
            s.date_prevue_solde and getdate(s.date_prevue_solde) < auj
            and flt(s.solde_du) > 0)
        if en_retard:
            c["retard"] += 1

    clients_l = sorted(clients.values(), key=lambda c: -(c["ca"] + c["sop_total"]))

    # ── Répartitions ──────────────────────────────────────────────────────
    postes = {"labels": [], "data": []}
    for f, lab in _POSTES:
        v = sum(flt(m.get(f)) for m in marches)
        if v:
            postes["labels"].append(lab)
            postes["data"].append(round(v))

    par_type = {}
    for m in marches:
        par_type[m.type_marche or "—"] = par_type.get(m.type_marche or "—", 0.0) + flt(m.montant_total_facture)

    par_statut = {}
    for m in marches:
        par_statut[m.statut or "—"] = par_statut.get(m.statut or "—", 0) + 1

    top = [l for l in lignes if l["ca"]][:10]

    solde_du_total = sum(flt(s.solde_du) for s in sops)
    sop_retard = sum(c["retard"] for c in clients.values())

    return {
        "module_present": bool(_exists("Marche KYA")),
        "kpis": [
            {"label": "Chiffre d'affaires", "value": _fmt_m(ca), "unit": "M FCFA",
             "sub": "{} marché(s)".format(len(marches)), "accent": "blue"},
            {"label": "Coût de réalisation", "value": _fmt_m(cout), "unit": "M FCFA",
             "sub": "budget prévu {} M".format(_fmt_m(budget)), "accent": "amber"},
            {"label": "Marge nette", "value": _fmt_m(marge_n), "unit": "M FCFA",
             "sub": ("{:.1f} % du CA".format(marge_n / ca * 100.0) if ca else "—"),
             "accent": "green" if marge_n >= 0 else "red"},
            {"label": "Marge brute", "value": _fmt_m(marge_b), "unit": "M FCFA",
             "sub": "avant taxes", "accent": "teal"},
            {"label": "Marchés en cours", "value": str(len(en_cours)),
             "sub": "{} terminé(s)".format(len(termines)), "accent": "violet"},
            {"label": "Solde client dû", "value": _fmt_m(solde_du_total), "unit": "M FCFA",
             "sub": "{} contrat(s) SoP · {} en retard".format(len(sops), sop_retard),
             "accent": "red" if sop_retard else "teal"},
        ],
        "alertes": alertes,
        "lignes": lignes,
        "clients": clients_l,
        "postes": postes,
        "par_type": {"labels": list(par_type), "data": [round(v) for v in par_type.values()]},
        "par_statut": {"labels": list(par_statut), "data": list(par_statut.values())},
        "top_marges": {"labels": [l["libelle"][:22] for l in top],
                       "data": [round(l["marge_nette"]) for l in top]},
    }


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la comptabilité et à la direction."),
                     frappe.PermissionError)
    context.no_cache = 1
    context.overview = get_overview()
    context.overview_json = frappe.as_json(context.overview)
    return context


@frappe.whitelist()
def overview_json():
    """Rafraîchissement sans rechargement de page."""
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès refusé."), frappe.PermissionError)
    return get_overview()
