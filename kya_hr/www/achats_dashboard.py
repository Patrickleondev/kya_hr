import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate, add_months, today

no_cache = 1

_ALLOWED_ROLES = {
    "Responsable Achats", "Purchase Manager", "Purchase User",
    "Chef Service", "DAAF", "DFC", "Auditeur Interne",
    "Directeur Général", "DG", "DGA", "Responsable RH",
    "Comptable", "Accounts Manager", "System Manager",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not _ALLOWED_ROLES.intersection(user_roles):
        frappe.throw(_("Accès réservé à la chaîne achats."), frappe.PermissionError)

    stats = {
        "demandes_en_cours": 0,
        "bons_commande_mois": 0,
        "montant_en_cours": 0,
        "appels_offre_actifs": 0,
    }
    par_palier = {"Palier 1 (Chef)": 0, "Palier 2 (DAAF)": 0, "Palier 3 (DG)": 0}
    derniers_bons = []
    demandes_attente = []
    appels = []

    end_states = ("Approuvé", "Approuve", "Rejeté", "Rejete", "Annulé", "Annule")

    try:
        # Demandes en cours (workflow non final)
        demandes = frappe.get_all(
            "Demande Achat KYA",
            filters=[["workflow_state", "not in", end_states]],
            fields=["name", "objet", "montant_total", "workflow_state", "modified",
                    "demandeur_nom", "date_demande"],
            order_by="modified desc",
            limit_page_length=15,
        )
        stats["demandes_en_cours"] = len(demandes)
        stats["montant_en_cours"] = sum(flt(d.montant_total) for d in demandes)
        for d in demandes:
            d.date_label = formatdate(d.date_demande) if d.date_demande else ""
            m = flt(d.montant_total)
            if m >= 2_000_000:
                par_palier["Palier 3 (DG)"] += 1
            elif m >= 100_000:
                par_palier["Palier 2 (DAAF)"] += 1
            else:
                par_palier["Palier 1 (Chef)"] += 1
        demandes_attente = demandes
    except Exception:
        frappe.log_error(frappe.get_traceback(), "achats-dashboard: demandes")

    try:
        # Bons de commande du mois en cours
        cutoff = add_months(today(), -1)
        bons = frappe.get_all(
            "Bon Commande KYA",
            filters=[["creation", ">=", cutoff]],
            fields=["name", "objet", "montant_total", "supplier", "workflow_state",
                    "creation", "modified"],
            order_by="creation desc",
            limit_page_length=10,
        )
        stats["bons_commande_mois"] = len(bons)
        for b in bons:
            b.date_label = formatdate(b.creation) if b.creation else ""
        derniers_bons = bons
    except Exception:
        frappe.log_error(frappe.get_traceback(), "achats-dashboard: bons")

    try:
        # Appels d'offres actifs (non clôturés)
        appels = frappe.get_all(
            "Appel Offre",
            filters=[["workflow_state", "not in", end_states + ("Attribué", "Attribue")]],
            fields=["name", "objet", "workflow_state", "date_publication", "modified"],
            order_by="modified desc",
            limit_page_length=10,
        )
        stats["appels_offre_actifs"] = len(appels)
        for a in appels:
            a.date_label = formatdate(a.date_publication) if a.date_publication else ""
    except Exception:
        # Le DocType Appel Offre peut être absent sur certains sites
        pass

    context.stats = stats
    context.par_palier = par_palier
    context.demandes = demandes_attente
    context.bons = derniers_bons
    context.appels = appels
    context.no_breadcrumbs = True

    try:
        import json as _json
        context.overview_json = _json.dumps(get_achats_overview(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "achats-dashboard: overview")
    return context


# ════════════════════════════════════════════════════════════════════
#  Vue d'ensemble Achats & Approvisionnement (maquette boards/Dashboard
#  Achats) — données réelles, libellés neutres
# ════════════════════════════════════════════════════════════════════
_END_STATES = ("Approuvé", "Approuve", "Rejeté", "Rejete", "Annulé", "Annule",
               "Clôturé", "Cloture", "Terminé", "Termine", "Attribué", "Attribue")


def _exists(dt):
    try:
        return bool(frappe.db.exists("DocType", dt))
    except Exception:
        return False


def _count(dt, filters=None):
    if not _exists(dt):
        return 0
    try:
        return frappe.db.count(dt, filters or {})
    except Exception:
        return 0


def _fmt_m(xof):
    m = (flt(xof) or 0) / 1_000_000.0
    if abs(m) < 0.05:
        m = 0.0
    return f"{m:,.1f}".replace(",", " ").replace(".", ",")


def _state_badge(state):
    s = (state or "").lower()
    if "rejet" in s:
        return "red"
    if "approuv" in s or "validé" in s or "valide" in s:
        return "green"
    if "brouillon" in s or not s:
        return "slate"
    return "teal"


@frappe.whitelist()
def get_achats_overview() -> dict:
    """Indicateurs Achats (demandes, paliers d'approbation, bons de commande,
    appels d'offre, marchés, engagements 6 mois). Réel et défensif."""
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la chaîne achats."), frappe.PermissionError)

    from frappe.utils import add_days, today, formatdate, get_first_day

    month_start = str(get_first_day(today()))
    six_m = str(add_days(today(), -185))

    # ── Demandes d'achat (non finalisées) ──
    demandes = []
    if _exists("Demande Achat KYA"):
        try:
            demandes = frappe.get_all(
                "Demande Achat KYA",
                fields=["name", "objet", "montant_total", "workflow_state",
                        "employee_name", "au_nom_de_nom", "date_demande", "palier"],
                order_by="date_demande desc, modified desc",
                limit_page_length=400)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "achats-overview: demandes")

    en_cours = [d for d in demandes if (d.workflow_state or "") not in _END_STATES]
    p_chef = p_daaf = p_dg = 0
    montant_attente = 0.0
    for d in en_cours:
        s = (d.workflow_state or "").lower()
        montant_attente += flt(d.montant_total)
        if "chef" in s:
            p_chef += 1
        elif "daaf" in s or "dga" in s or "audit" in s or "compta" in s:
            p_daaf += 1
        elif "dg" in s or "direction" in s:
            p_dg += 1

    # ── Bons de commande ──
    bons = []
    if _exists("Bon Commande KYA"):
        try:
            bons = frappe.get_all(
                "Bon Commande KYA",
                fields=["name", "numero_bc", "objet", "total_ttc", "fournisseur_nom",
                        "workflow_state", "date_bc", "creation"],
                order_by="date_bc desc, creation desc",
                limit_page_length=400)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "achats-overview: bons")
    bons_en_cours = [b for b in bons if (b.workflow_state or "") not in _END_STATES]
    engage_mois = sum(flt(b.total_ttc) for b in bons
                      if str(b.date_bc or b.creation or "")[:10] >= month_start)

    # ── Appels d'offre ouverts ──
    ao_ouverts = 0
    if _exists("Appel Offre KYA"):
        try:
            ao_ouverts = sum(1 for a in frappe.get_all(
                "Appel Offre KYA", fields=["workflow_state"], limit_page_length=400)
                if (a.workflow_state or "") not in _END_STATES)
        except Exception:
            pass

    # ── Marchés en exécution (Marche KYA → statut, pas de workflow_state) ──
    marches_total = _count("Marche KYA")
    marches_cours = marches_total
    if _exists("Marche KYA"):
        try:
            fin = ("Terminé", "Termine", "Clôturé", "Cloture", "Annulé", "Annule",
                   "Soldé", "Solde", "Livré", "Livre")
            marches_cours = sum(1 for m in frappe.get_all(
                "Marche KYA", fields=["statut"], limit_page_length=400)
                if (m.statut or "") not in fin)
        except Exception:
            pass

    # ── Hero (5) ──
    hero = [
        {"label": "Demandes en attente", "value": str(len(en_cours)), "sub": "tous paliers", "icon": "cart"},
        {"label": "Bons de commande en cours", "value": str(len(bons_en_cours)), "sub": "à livrer", "icon": "file"},
        {"label": "Appels d'offres ouverts", "value": str(ao_ouverts), "sub": "consultations", "icon": "megaphone"},
        {"label": "Marchés en cours", "value": str(marches_cours), "sub": f"{marches_total} au total", "icon": "briefcase"},
        {"label": "Montant engagé (mois)", "value": _fmt_m(engage_mois), "unit": "M FCFA",
         "sub": "bons de commande", "icon": "wallet"},
    ]

    # ── Paliers d'approbation (4) ──
    palier_cards = [
        {"label": "En attente — Chef de service", "value": str(p_chef), "sub": "1er palier", "icon": "user", "accent": "teal"},
        {"label": "En attente — DAAF / Audit", "value": str(p_daaf), "sub": "2e palier", "icon": "building", "accent": "orange"},
        {"label": "En attente — Direction", "value": str(p_dg), "sub": "seuil élevé", "icon": "check", "accent": "teal"},
        {"label": "Montant en attente", "value": _fmt_m(montant_attente), "unit": "M FCFA", "sub": "à valider", "icon": "wallet", "accent": "green"},
    ]

    # ── Documents en cours (4) ──
    doc_cards = [
        {"label": "Demandes Achat (mois)", "value": str(sum(1 for d in demandes if str(d.date_demande or "")[:10] >= month_start)),
         "sub": f"{len(en_cours)} en attente", "icon": "cart", "accent": "teal"},
        {"label": "Bons de Commande", "value": str(len(bons_en_cours)), "sub": "en cours", "icon": "file", "accent": "orange"},
        {"label": "Appels d'Offre", "value": str(ao_ouverts), "sub": "ouverts", "icon": "megaphone", "accent": "teal"},
        {"label": "Marchés", "value": str(marches_cours), "sub": "en exécution", "icon": "briefcase", "accent": "green"},
    ]

    # ── Dernières demandes (table) ──
    demande_rows = []
    for d in demandes[:8]:
        demande_rows.append({
            "ref": d.name, "objet": d.objet or "—",
            "demandeur": d.employee_name or d.au_nom_de_nom or "—",
            "montant": _fmt_m(d.montant_total) + " M",
            "etat": d.workflow_state or "Brouillon", "accent": _state_badge(d.workflow_state),
        })

    # ── Engagements par mois (bons de commande, 6 mois) ──
    flux = {"labels": [], "data": []}
    by_month = {}
    for b in bons:
        d = str(b.date_bc or b.creation or "")[:10]
        if not d or d < six_m:
            continue
        by_month[d[:7]] = by_month.get(d[:7], 0.0) + flt(b.total_ttc)
    for k in sorted(by_month):
        flux["labels"].append(k)
        flux["data"].append(round(by_month[k] / 1_000_000, 2))

    # ── Répartition par fournisseur (bons de commande) ──
    four = {}
    for b in bons:
        nom = b.fournisseur_nom or "—"
        four[nom] = four.get(nom, 0.0) + flt(b.total_ttc)
    four_sorted = sorted(four.items(), key=lambda kv: kv[1], reverse=True)[:6]
    fourn = {"labels": [k for k, _v in four_sorted],
             "data": [round(v / 1_000_000, 2) for _k, v in four_sorted]}

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero, "palier_cards": palier_cards, "doc_cards": doc_cards,
        "demande_rows": demande_rows, "flux": flux, "fourn": fourn,
        "en_attente_label": f"{len(en_cours)} en attente",
    }
