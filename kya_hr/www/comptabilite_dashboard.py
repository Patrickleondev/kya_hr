import frappe
from frappe import _
from frappe.utils import flt, formatdate

no_cache = 1

_ALLOWED_ROLES = {
    "Caissier", "Comptable", "DFC", "DAAF", "Accounts Manager", "Accounts User",
    "Auditeur Interne", "Directeur Général", "DG", "DGA", "System Manager",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not _ALLOWED_ROLES.intersection(user_roles):
        frappe.throw(_("Accès réservé à la comptabilité."), frappe.PermissionError)

    imports = []
    stats = {"imports": 0, "lignes": 0, "debit": 0, "credit": 0, "salaires": 0, "factures": 0}
    type_counts = {}

    try:
        imports = frappe.get_all(
            "KYA Compta Import",
            fields=[
                "name", "type_document", "periode", "statut_import", "total_lignes",
                "total_debit", "total_credit", "total_salaire_net", "total_facture",
                "imported_by", "date_import", "source_file", "modified",
            ],
            order_by="modified desc",
            limit_page_length=20,
        )

        stats = {
            "imports": len(imports),
            "lignes": sum(flt(row.total_lignes) for row in imports),
            "debit": sum(flt(row.total_debit) for row in imports),
            "credit": sum(flt(row.total_credit) for row in imports),
            "salaires": sum(flt(row.total_salaire_net) for row in imports),
            "factures": sum(flt(row.total_facture) for row in imports),
        }

        for row in imports:
            type_counts[row.type_document] = type_counts.get(row.type_document, 0) + 1
            row.date_import_label = formatdate(row.date_import) if row.date_import else ""

    except Exception:
        frappe.log_error(frappe.get_traceback(), "comptabilite-dashboard: erreur chargement")

    # --- Brouillards de Caisse (vrais flux quotidiens de trésorerie) ---
    brouillards = []
    caisse = {"nb": 0, "en_attente": 0, "solde_actuel": 0,
              "total_entrees": 0, "total_sorties": 0}
    try:
        brouillards = frappe.get_all(
            "Brouillard Caisse",
            fields=[
                "name", "date_brouillard", "caissiere_name", "total_entrees",
                "total_sorties", "solde_final", "total_reel_caisse",
                "workflow_state", "statut", "modified",
            ],
            order_by="date_brouillard desc, modified desc",
            limit_page_length=15,
        )
        caisse["nb"] = frappe.db.count("Brouillard Caisse")
        caisse["en_attente"] = sum(
            1 for b in brouillards if "En attente" in (b.workflow_state or ""))
        caisse["total_entrees"] = sum(flt(b.total_entrees) for b in brouillards)
        caisse["total_sorties"] = sum(flt(b.total_sorties) for b in brouillards)
        if brouillards:
            # Solde le plus récent (1re ligne car tri date desc)
            caisse["solde_actuel"] = flt(brouillards[0].solde_final)
        for b in brouillards:
            b.date_label = formatdate(b.date_brouillard) if b.date_brouillard else ""
            b.etat_label = b.workflow_state or b.statut or ""
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "comptabilite-dashboard: erreur brouillards")

    # --- Etats Récap Chèques (suivi hebdomadaire des chèques) ---
    recaps = []
    cheques = {"nb": 0, "en_attente": 0, "total_montant": 0, "nombre": 0}
    try:
        recaps = frappe.get_all(
            "Etat Recap Cheques",
            fields=[
                "name", "date_etat", "redacteur_name", "libelle_periode",
                "total_montant", "nombre_cheques", "workflow_state",
                "statut", "modified",
            ],
            order_by="date_etat desc, modified desc",
            limit_page_length=15,
        )
        cheques["nb"] = frappe.db.count("Etat Recap Cheques")
        cheques["en_attente"] = sum(
            1 for r in recaps if "En attente" in (r.workflow_state or ""))
        cheques["total_montant"] = sum(flt(r.total_montant) for r in recaps)
        cheques["nombre"] = sum(int(r.nombre_cheques or 0) for r in recaps)
        for r in recaps:
            r.date_label = formatdate(r.date_etat) if r.date_etat else ""
            r.etat_label = r.workflow_state or r.statut or ""
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "comptabilite-dashboard: erreur recap cheques")

    context.imports = imports
    context.stats = stats
    context.type_counts = type_counts
    context.brouillards = brouillards
    context.caisse = caisse
    context.recaps = recaps
    context.cheques = cheques
    context.no_breadcrumbs = True

    try:
        import json as _json
        context.overview_json = _json.dumps(get_compta_overview(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "comptabilite-dashboard: overview")
    return context


# ════════════════════════════════════════════════════════════════════
#  Vue d'ensemble Comptabilité & Finance (maquette boards/Dashboard
#  Comptabilite) — données réelles, libellés neutres
# ════════════════════════════════════════════════════════════════════
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


@frappe.whitelist()
def get_compta_overview() -> dict:
    """Indicateurs Comptabilité & Finance (trésorerie, brouillards de caisse,
    rapprochements chèques, flux 6 mois). Tout est réel ; défensif si absent."""
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la comptabilité."), frappe.PermissionError)

    from frappe.utils import add_days, today, formatdate, get_first_day, getdate

    month_start = str(get_first_day(today()))
    week_start = str(add_days(today(), -getdate(today()).weekday()))
    six_m = add_days(today(), -185)

    # ── Brouillards de caisse (flux quotidiens de trésorerie) ──
    brs = []
    if _exists("Brouillard Caisse"):
        try:
            brs = frappe.get_all(
                "Brouillard Caisse",
                fields=["name", "date_brouillard", "caissiere_name", "total_entrees",
                        "total_sorties", "solde_final", "workflow_state"],
                order_by="date_brouillard desc, modified desc",
                limit_page_length=400)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "compta-overview: brouillards")

    solde_actuel = flt(brs[0].solde_final) if brs else 0
    caisses = {b.caissiere_name for b in brs if b.caissiere_name}
    entrees_mois = sum(flt(b.total_entrees) for b in brs
                       if str(b.date_brouillard or "") >= month_start)
    sorties_mois = sum(flt(b.total_sorties) for b in brs
                       if str(b.date_brouillard or "") >= month_start)
    br_semaine = sum(1 for b in brs if str(b.date_brouillard or "") >= week_start)
    br_attente = sum(1 for b in brs if "En attente" in (b.workflow_state or ""))
    resultat_net = entrees_mois - sorties_mois

    cheques_attente = _count("Etat Recap Cheques", {"workflow_state": ["like", "%En attente%"]})
    cheques_total = _count("Etat Recap Cheques")

    # ── Hero (6) ──
    net_sign = "+" if resultat_net >= 0 else ""
    hero = [
        {"label": "Trésorerie (solde caisse)", "value": _fmt_m(solde_actuel), "unit": "M FCFA",
         "sub": f"{len(caisses) or 1} caisse(s)", "icon": "coins"},
        {"label": "Entrées du mois", "value": _fmt_m(entrees_mois), "unit": "M FCFA",
         "sub": "encaissements", "icon": "arrowup"},
        {"label": "Sorties du mois", "value": _fmt_m(sorties_mois), "unit": "M FCFA",
         "sub": "décaissements", "icon": "arrowdown"},
        {"label": "Brouillards (semaine)", "value": str(br_semaine),
         "sub": f"{br_attente} à valider", "icon": "receipt"},
        {"label": "Rapprochements chèques", "value": str(cheques_attente),
         "sub": "en attente", "icon": "filecheck"},
        {"label": "Résultat net du mois", "value": net_sign + _fmt_m(resultat_net), "unit": "M FCFA",
         "sub": "entrées − sorties", "icon": "gauge"},
    ]

    # ── Cartes Trésorerie & caisse (5) ──
    treso_cards = [
        {"label": "Solde caisse", "value": _fmt_m(solde_actuel), "unit": "M FCFA",
         "sub": "consolidé", "icon": "coins", "accent": "teal"},
        {"label": "Entrées du mois", "value": _fmt_m(entrees_mois), "unit": "M FCFA",
         "sub": "encaissements", "icon": "arrowup", "accent": "green"},
        {"label": "Sorties du mois", "value": _fmt_m(sorties_mois), "unit": "M FCFA",
         "sub": "décaissements", "icon": "arrowdown", "accent": "orange"},
        {"label": "Brouillards (semaine)", "value": str(br_semaine),
         "sub": f"{br_attente} non validés", "icon": "receipt", "accent": "teal"},
        {"label": "Rapprochements chèques", "value": str(cheques_attente),
         "sub": f"{cheques_total} états au total", "icon": "filecheck", "accent": "teal"},
    ]

    # ── Derniers brouillards (table) ──
    brouillard_rows = []
    for b in brs[:8]:
        brouillard_rows.append({
            "date": formatdate(b.date_brouillard, "dd/MM") if b.date_brouillard else "—",
            "par": b.caissiere_name or "—",
            "entrees": _fmt_m(b.total_entrees) + " M",
            "sorties": _fmt_m(b.total_sorties) + " M",
            "solde": _fmt_m(b.solde_final) + " M",
        })

    # ── Trésorerie 6 mois (entrées / sorties par mois, M FCFA) ──
    flux = {"labels": [], "entrees": [], "sorties": []}
    by_month = {}
    for b in brs:
        d = str(b.date_brouillard or "")
        if not d or d < str(six_m):
            continue
        k = d[:7]
        agg = by_month.setdefault(k, [0.0, 0.0])
        agg[0] += flt(b.total_entrees)
        agg[1] += flt(b.total_sorties)
    for k in sorted(by_month):
        flux["labels"].append(k)
        flux["entrees"].append(round(by_month[k][0] / 1_000_000, 2))
        flux["sorties"].append(round(by_month[k][1] / 1_000_000, 2))

    # ── Documents de caisse par état (doughnut, réel) ──
    etats = {}
    for b in brs:
        st = b.workflow_state or "Brouillon"
        etats[st] = etats.get(st, 0) + 1
    doc_etats = {"labels": list(etats.keys()), "data": list(etats.values())}

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero, "treso_cards": treso_cards, "brouillard_rows": brouillard_rows,
        "flux": flux, "doc_etats": doc_etats,
        "solde_label": _fmt_m(solde_actuel) + " M FCFA",
    }
