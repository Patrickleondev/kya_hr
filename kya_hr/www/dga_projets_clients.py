"""Tableau de bord : Sorties & Destinations — Clients / Projets.

Vue (DGA / Direction / Magasin) du matériel SORTI et de ses DESTINATIONS,
ventilé par client, par projet/chantier et par type de destination
(équipe interne vs client/projet). Source : PV Sortie Matériel.

NB : ce tableau ne suit PLUS l'avancement des projets — il sert à voir les
sorties et où va le matériel. Lecture seule, rendu serveur + refresh JSON.
"""
import frappe
from frappe import _
from frappe.utils import flt, today, add_days, formatdate

no_cache = 1

_ALLOWED_ROLES = {
    "DGA", "Directeur Général", "Directeur General", "DG", "System Manager",
    "Chef Service", "Projects Manager", "Projects User",
    "Chargé des Stocks", "Responsable Stock", "Magasinier", "Stock User", "Stock Manager",
    "Auditeur Interne", "Auditeur",
}

# Exclut brouillons / rejetés (workflow_state OU statut)
_EXCLUDE = ("Rejeté", "Rejete", "Brouillon")


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la Direction / au Magasin."), frappe.PermissionError)

    context.no_breadcrumbs = True
    context.no_cache = 1
    try:
        import json as _json
        context.overview_json = _json.dumps(get_sorties_overview(), default=str)
    except Exception:
        context.overview_json = "null"
        frappe.log_error(frappe.get_traceback(), "dga-projets-clients: overview")
    return context


def _fmt_n(q):
    try:
        return f"{int(round(flt(q))):,}".replace(",", " ")
    except Exception:
        return "0"


@frappe.whitelist()
def get_sorties_overview(period: int = 180) -> dict:
    """Sorties matériel & destinations (par client, projet, type). Défensif."""
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé."), frappe.PermissionError)
    if not frappe.db.exists("DocType", "PV Sortie Materiel"):
        return {"date_str": formatdate(today(), "EEEE d MMMM y"), "hero": [],
                "par_projet": [], "par_client": [], "sorties": [],
                "dest_split": {"labels": [], "data": []}, "top_clients": {"labels": [], "data": []}}

    period = int(period or 180)
    date_from = add_days(today(), -period)
    args = {"d": date_from}
    excl = "', '".join(_EXCLUDE)
    cond = (f"pv.date_sortie >= %(d)s AND COALESCE(NULLIF(pv.workflow_state,''), "
            f"pv.statut, '') NOT IN ('{excl}')")
    # libellés normalisés
    CLIENT = "COALESCE(NULLIF(pv.client_name,''), NULLIF(pv.customer_manuel,''), NULLIF(pv.client,''), NULLIF(pv.customer,''))"
    PROJ = "COALESCE(NULLIF(pv.projet,''), NULLIF(pv.project,''), NULLIF(pv.chantier_libre,''))"

    def q(sql):
        try:
            return frappe.db.sql(sql, args, as_dict=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "dga-projets-clients: query")
            return []

    # ── KPIs ──
    k = q(f"""SELECT COUNT(DISTINCT pv.name) nb_pv,
                     SUM(CASE WHEN pv.destination_type='Équipe interne' THEN 1 ELSE 0 END) AS dummy
              FROM `tabPV Sortie Materiel` pv WHERE {cond}""")
    nb_pv = int(k[0].nb_pv or 0) if k else 0
    qte = q(f"""SELECT COALESCE(SUM(pvi.qte_reellement_sortie),0) qte
                FROM `tabPV Sortie Materiel` pv JOIN `tabPV Sortie Materiel Item` pvi
                ON pvi.parent=pv.name WHERE {cond}""")
    qte_totale = flt(qte[0].qte) if qte else 0
    nbc = q(f"SELECT COUNT(DISTINCT {CLIENT}) n FROM `tabPV Sortie Materiel` pv WHERE {cond} AND {CLIENT} IS NOT NULL")
    nb_clients = int(nbc[0].n or 0) if nbc else 0
    nbp = q(f"SELECT COUNT(DISTINCT {PROJ}) n FROM `tabPV Sortie Materiel` pv WHERE {cond} AND {PROJ} IS NOT NULL")
    nb_projets = int(nbp[0].n or 0) if nbp else 0
    nbi = q(f"SELECT COUNT(DISTINCT pv.name) n FROM `tabPV Sortie Materiel` pv WHERE {cond} AND pv.destination_type='Équipe interne'")
    nb_internes = int(nbi[0].n or 0) if nbi else 0

    hero = [
        {"label": "Sorties (PV)", "value": str(nb_pv), "sub": f"{period} derniers jours", "icon": "arrowup"},
        {"label": "Quantité sortie", "value": _fmt_n(qte_totale), "sub": "articles", "icon": "box"},
        {"label": "Clients / projets servis", "value": str(nb_clients), "sub": f"{nb_projets} projets/chantiers", "icon": "users"},
        {"label": "Sorties internes", "value": str(nb_internes), "sub": "équipes KYA", "icon": "truck"},
    ]

    # ── Par projet / chantier ──
    par_projet = q(f"""SELECT {PROJ} AS projet, MAX({CLIENT}) AS client,
                              COUNT(DISTINCT pv.name) nb,
                              COALESCE(SUM(pvi.qte_reellement_sortie),0) qte
                       FROM `tabPV Sortie Materiel` pv
                       LEFT JOIN `tabPV Sortie Materiel Item` pvi ON pvi.parent=pv.name
                       WHERE {cond} AND {PROJ} IS NOT NULL
                       GROUP BY projet ORDER BY qte DESC LIMIT 15""")

    # ── Par client / destination ──
    par_client = q(f"""SELECT COALESCE({CLIENT},
                              CASE WHEN pv.destination_type='Équipe interne' THEN 'Équipe interne' ELSE '—' END) AS dest,
                              pv.destination_type AS type,
                              COUNT(DISTINCT pv.name) nb,
                              COALESCE(SUM(pvi.qte_reellement_sortie),0) qte
                       FROM `tabPV Sortie Materiel` pv
                       LEFT JOIN `tabPV Sortie Materiel Item` pvi ON pvi.parent=pv.name
                       WHERE {cond}
                       GROUP BY dest, type ORDER BY qte DESC LIMIT 15""")

    # ── Dernières sorties ──
    sorties = q(f"""SELECT pv.name, pv.date_sortie, pv.destination_type AS type,
                           {PROJ} AS projet, {CLIENT} AS client, pv.objet,
                           COALESCE(SUM(pvi.qte_reellement_sortie),0) qte,
                           COALESCE(NULLIF(pv.workflow_state,''), pv.statut, '') AS etat
                    FROM `tabPV Sortie Materiel` pv
                    LEFT JOIN `tabPV Sortie Materiel Item` pvi ON pvi.parent=pv.name
                    WHERE {cond}
                    GROUP BY pv.name ORDER BY pv.date_sortie DESC LIMIT 14""")
    sorties_rows = []
    for s in sorties:
        sorties_rows.append({
            "ref": s.name, "date": formatdate(s.date_sortie, "dd/MM/y") if s.date_sortie else "—",
            "type": s.type or "—",
            "destination": s.client or (("Équipe interne") if s.type == "Équipe interne" else "—"),
            "projet": s.projet or "—", "objet": s.objet or "",
            "qte": _fmt_n(s.qte),
            "etat": s.etat or "—",
            "accent": "ok" if "approuv" in (s.etat or "").lower() else ("bad" if "rejet" in (s.etat or "").lower() else "wait"),
        })

    par_projet_rows = [{"projet": r.projet or "—", "client": r.client or "—",
                        "nb": int(r.nb or 0), "qte": _fmt_n(r.qte)} for r in par_projet]
    par_client_rows = [{"dest": r.dest or "—", "type": r.type or "—",
                        "nb": int(r.nb or 0), "qte": _fmt_n(r.qte)} for r in par_client]

    # ── Charts ──
    split = q(f"""SELECT COALESCE(NULLIF(pv.destination_type,''),'Autre') t, COUNT(DISTINCT pv.name) n
                  FROM `tabPV Sortie Materiel` pv WHERE {cond} GROUP BY t""")
    dest_split = {"labels": [r.t for r in split], "data": [int(r.n or 0) for r in split]}
    top = par_client[:6]
    top_clients = {"labels": [(r.dest or "—") for r in top],
                   "data": [int(round(flt(r.qte))) for r in top]}

    return {
        "date_str": formatdate(today(), "EEEE d MMMM y"),
        "hero": hero, "par_projet": par_projet_rows, "par_client": par_client_rows,
        "sorties": sorties_rows, "dest_split": dest_split, "top_clients": top_clients,
        "periode_label": f"{period} jours",
    }
