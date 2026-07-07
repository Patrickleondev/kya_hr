"""Page : Dashboard Commercial & CRM.

Route : /commercial-dashboard

S'appuie sur le CRM natif ERPNext (Lead, Customer) enrichi des champs KYA du
tunnel commercial (demande devis → devis envoyé → accepté → facturé → payé).
Tous les champs custom sont interrogés en DÉFENSIF (présents en prod, absents
en local) : le dashboard dégrade proprement.
"""
from __future__ import annotations

import frappe


ACCESS_ROLES = {
    "System Manager", "Directeur General", "Directeur Général", "DG", "DGA",
    "Responsable Commercial", "Commercial", "Chargé Commercial",
    "Sales Manager", "Sales User", "CRM Manager", "CRM User",
    "Chef Service", "Responsable RH", "HR Manager", "Auditeur Interne", "Auditeur",
}


def get_context(context):
    user = frappe.session.user
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/commercial-dashboard"
        raise frappe.Redirect

    if not (set(frappe.get_roles(user)) & ACCESS_ROLES):
        frappe.throw("Accès refusé - rôle Commercial ou Direction requis.", frappe.PermissionError)

    context.page_title = "Dashboard Commercial & CRM"
    context.no_cache = 1
    context.no_breadcrumbs = True
    try:
        import json as _json
        context.overview_json = _json.dumps(get_commercial_overview(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "commercial-dashboard: overview")
    return context


# ════════════════════════════════════════════════════════════════════
#  Vue d'ensemble Commercial & CRM — données réelles (Lead/Customer)
# ════════════════════════════════════════════════════════════════════
_CLOSED = ("Converted", "Do Not Contact", "Lost Quotation")


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


def _hasf(dt, field):
    try:
        return _exists(dt) and frappe.get_meta(dt).has_field(field)
    except Exception:
        return False


def _count_flag(field, value=1):
    """Compte les Lead où un champ custom (drapeau) vaut `value`, seulement si le
    champ existe (sinon None → carte masquée/—)."""
    if not _hasf("Lead", field):
        return None
    try:
        return frappe.db.count("Lead", {field: value})
    except Exception:
        return None


@frappe.whitelist()
def get_commercial_overview() -> dict:
    if not (set(frappe.get_roles(frappe.session.user)) & ACCESS_ROLES):
        frappe.throw("Accès réservé au commercial et à la Direction.", frappe.PermissionError)

    from frappe.utils import add_days, today, formatdate

    six_m = str(add_days(today(), -185))
    month_start = today()[:8] + "01"

    leads_actifs = 0
    if _exists("Lead"):
        try:
            leads_actifs = frappe.db.count("Lead", {"status": ["not in", _CLOSED]})
        except Exception:
            leads_actifs = _count("Lead")
    leads_total = _count("Lead")
    leads_mois = _count("Lead", {"creation": [">=", month_start]})
    clients = _count("Customer", {"disabled": 0})

    # Tunnel commercial (drapeaux custom KYA, défensif)
    n_demande = _count_flag("custom_demande_devis")
    n_envoye = _count_flag("custom_devis_envoyé")
    n_accepte = _count_flag("custom_devis_accepté_")
    n_facture = _count_flag("custom_facture_envoyé_")
    n_paye = _count_flag("custom_payé")
    n_rappel = _count_flag("custom_rappel_traite_", 0)  # rappels NON traités

    base_conv = n_envoye if n_envoye else leads_actifs
    taux_conv = round((n_accepte or 0) / base_conv * 100) if base_conv else 0

    # ── Hero (6) ──
    def _s(v):
        return str(v) if v is not None else "—"
    hero = [
        {"label": "Leads actifs", "value": str(leads_actifs), "sub": f"{leads_total} au total", "icon": "trending"},
        {"label": "Nouveaux leads (mois)", "value": str(leads_mois), "sub": "ce mois", "icon": "userplus"},
        {"label": "Devis envoyés", "value": _s(n_envoye), "sub": "propositions", "icon": "file"},
        {"label": "Devis acceptés", "value": _s(n_accepte), "sub": "gagnés", "icon": "check"},
        {"label": "Clients", "value": str(clients), "sub": "comptes actifs", "icon": "users"},
        {"label": "Taux de conversion", "value": str(taux_conv), "unit": "%",
         "sub": "devis acceptés / envoyés", "icon": "target"},
    ]

    # ── Tunnel (cartes étapes) — masque les étapes sans champ ──
    funnel = []
    for lbl, val, ic, ac in [
        ("Demandes de devis", n_demande, "inbox", "teal"),
        ("Devis envoyés", n_envoye, "file", "teal"),
        ("Devis acceptés", n_accepte, "check", "green"),
        ("Factures envoyées", n_facture, "receipt", "orange"),
        ("Payés", n_paye, "coins", "green"),
        ("Rappels à traiter", n_rappel, "clock", "orange"),
    ]:
        if val is not None:
            funnel.append({"label": lbl, "value": str(val), "icon": ic, "accent": ac})

    # ── Leads par statut ──
    leads_status = []
    if _exists("Lead"):
        try:
            rows = frappe.db.sql(
                """SELECT COALESCE(NULLIF(status,''),'Lead') s, COUNT(*) n
                   FROM `tabLead` WHERE status NOT IN %(c)s GROUP BY s ORDER BY n DESC LIMIT 10""",
                {"c": _CLOSED}, as_dict=True)
            tot = sum(int(r.n) for r in rows) or 1
            for r in rows:
                leads_status.append({"statut": r.s, "n": int(r.n), "part": round(int(r.n) / tot * 100)})
        except Exception:
            frappe.log_error(frappe.get_traceback(), "commercial-overview: status")

    # ── Leads par type de prospect (champ custom) ──
    leads_type = []
    if _hasf("Lead", "custom_type_de_prospect"):
        try:
            rows = frappe.db.sql(
                """SELECT COALESCE(NULLIF(custom_type_de_prospect,''),'Non précisé') t, COUNT(*) n
                   FROM `tabLead` GROUP BY t ORDER BY n DESC LIMIT 8""", as_dict=True)
            for r in rows:
                leads_type.append({"type": r.t, "n": int(r.n)})
        except Exception:
            pass

    # ── Leads par mois (6 mois) ──
    flux = {"labels": [], "data": []}
    if _exists("Lead"):
        try:
            rows = frappe.db.sql(
                """SELECT CONCAT(YEAR(creation),'-',LPAD(MONTH(creation),2,'0')) mois, COUNT(*) n
                   FROM `tabLead` WHERE creation >= %s GROUP BY mois ORDER BY mois""",
                (six_m,), as_dict=True)
            for r in rows:
                flux["labels"].append(r.mois)
                flux["data"].append(int(r.n))
        except Exception:
            pass

    # ── Leads récents (table) ──
    lead_rows = []
    if _exists("Lead"):
        fields = ["name", "lead_name", "status", "lead_owner", "creation"]
        for f in ("custom_type_de_prospect", "custom_devis_envoyé", "mobile_no"):
            if _hasf("Lead", f):
                fields.append(f)
        try:
            for l in frappe.get_all("Lead", filters={"status": ["not in", _CLOSED]},
                                    fields=fields, order_by="creation desc", limit_page_length=10):
                etape = "Nouveau"
                if l.get("custom_devis_envoyé"):
                    etape = "Devis envoyé"
                lead_rows.append({
                    "nom": l.get("lead_name") or l.name,
                    "type": l.get("custom_type_de_prospect") or "—",
                    "statut": l.get("status") or "Lead",
                    "owner": (l.get("lead_owner") or "").split("@")[0] or "—",
                    "etape": etape,
                    "date": formatdate(l.creation, "dd/MM/y") if l.get("creation") else "—",
                })
        except Exception:
            frappe.log_error(frappe.get_traceback(), "commercial-overview: lead_rows")

    # ── Satisfaction client (enquêtes) ──
    sat_avg, sat_n = 0, 0
    if _exists("EnqueteSatisfactionClient"):
        try:
            enq = frappe.get_all("EnqueteSatisfactionClient",
                fields=["efficacite_sav", "qualite_maintenance", "efficacite_installation"],
                limit_page_length=2000)
            vals = []
            for e in enq:
                for k in ("efficacite_sav", "qualite_maintenance", "efficacite_installation"):
                    try:
                        v = int(e.get(k))
                        if 1 <= v <= 5:
                            vals.append(v)
                    except (TypeError, ValueError):
                        pass
            sat_n = len(enq)
            sat_avg = round(sum(vals) / len(vals), 1) if vals else 0
        except Exception:
            pass

    # ── Équipes commerciales ──
    teams = []
    if _exists("Equipe KYA"):
        try:
            for t in frappe.get_all("Equipe KYA",
                    filters={"est_active": 1},
                    fields=["nom_equipe", "chef_equipe_name", "nombre_membres", "departement"],
                    limit_page_length=200):
                blob = (t.nom_equipe or "") + " " + (t.departement or "")
                if any(k in blob.lower() for k in ("commerc", "communicat", "marketing", "vente")):
                    teams.append({"equipe": t.nom_equipe or "—", "chef": t.chef_equipe_name or "—",
                                  "membres": int(t.nombre_membres or 0)})
        except Exception:
            pass

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero, "funnel": funnel, "leads_status": leads_status,
        "leads_type": leads_type, "flux": flux, "lead_rows": lead_rows,
        "teams": teams, "sat_avg": sat_avg, "sat_n": sat_n,
        "leads_label": f"{leads_actifs} actifs",
        "alertes": {
            # calé sur la répartition réelle des statuts en prod
            "a_relancer": _count("Lead", {"status": "Open"}),
            "opportunites": _count("Lead", {"status": "Opportunity"}),
            "devis": _count("Lead", {"status": "Quotation"}),
            "jamais_qualifies": _count("Lead", {"status": "Lead"}),
        },
        "clients_label": f"{clients} clients",
    }
