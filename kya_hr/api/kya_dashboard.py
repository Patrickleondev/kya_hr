# -*- coding: utf-8 -*-
"""
Tableau de Bord Global KYA-Energy — API
Fournit les stats agrégées de TOUS les web forms pour la vue DG.
Route : /kya-tableau-de-bord
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, today, nowdate
import json


# ─── Cartographie des modules → DocTypes (valeurs par défaut / fallback) ──
MODULE_MAP = {
    "rh": {
        "label": "Ressources Humaines",
        "icon": "👥",
        "color": "#1565c0",
        "doctypes": [
            {
                "name": "Permission Sortie Employe",
                "label": "Permissions Sortie Employé",
                "status_field": "workflow_state",
                "date_field": "creation",
                "amount_field": None,
                "list_url": "/app/permission-sortie-employe",
                "form_url": "/permission-sortie-employe",
            },
            {
                "name": "Permission Sortie Stagiaire",
                "label": "Permissions Sortie Stagiaire",
                "status_field": "workflow_state",
                "date_field": "creation",
                "amount_field": None,
                "list_url": "/app/permission-sortie-stagiaire",
                "form_url": "/permission-sortie-stagiaire",
            },
            {
                "name": "Bilan Fin de Stage",
                "label": "Bilans de Fin de Stage",
                "status_field": "workflow_state",
                "date_field": "creation",
                "amount_field": None,
                "list_url": "/app/bilan-fin-de-stage",
                "form_url": "/bilan-fin-de-stage",
            },
            {
                "name": "Planning Conge",
                "label": "Plannings de Congé",
                "status_field": "workflow_state",
                "date_field": "creation",
                "amount_field": None,
                "list_url": "/app/planning-conge",
                "form_url": "/planning-conge",
            },
        ],
    },
    "achats": {
        "label": "Achats",
        "icon": "🛒",
        "color": "#e65100",
        "doctypes": [
            {
                "name": "Demande Achat KYA",
                "label": "Demandes d'Achat",
                "status_field": "workflow_state",
                "date_field": "creation",
                "amount_field": "montant_total",
                "list_url": "/app/demande-achat-kya",
                "form_url": "/demande-achat",
            },
            {
                "name": "Bon Commande KYA",
                "label": "Bons de Commande",
                "status_field": "statut",
                "date_field": "date_bc",
                "amount_field": "montant_total",
                "list_url": "/app/bon-commande-kya",
                "form_url": "/bon-commande",
            },
            {
                "name": "Appel Offre KYA",
                "label": "Appels d'Offre",
                "status_field": "statut",
                "date_field": "date_ao",
                "amount_field": "budget_estime",
                "list_url": "/app/appel-offre-kya",
                "form_url": "/appel-offre",
            },
        ],
    },
    "stock": {
        "label": "Stocks",
        "icon": "📦",
        "color": "#2e7d32",
        "doctypes": [
            {
                "name": "PV Sortie Materiel",
                "label": "PV Sorties Matériel",
                "status_field": "workflow_state",
                "date_field": "date_sortie",
                "amount_field": None,
                "list_url": "/app/pv-sortie-materiel",
                "form_url": "/pv-sortie-materiel",
            },
            {
                "name": "PV Entree Materiel",
                "label": "PV Entrées Matériel",
                "status_field": "statut",
                "date_field": "date_entree",
                "amount_field": None,
                "list_url": "/app/pv-entree-materiel",
                "form_url": "/pv-entree-materiel",
            },
            {
                "name": "Inventaire KYA",
                "label": "Inventaires",
                "status_field": "statut",
                "date_field": "date_inventaire",
                "amount_field": "valeur_ecart_total",
                "list_url": "/app/inventaire-kya",
                "form_url": "/inventaire-kya",
            },
        ],
    },
    "compta": {
        "label": "Comptabilité & Finance",
        "icon": "💰",
        "color": "#6a1b9a",
        "doctypes": [
            {
                "name": "Brouillard Caisse",
                "label": "Brouillards de Caisse",
                "status_field": "statut",
                "date_field": "date_brouillard",
                "amount_field": "total_montant",
                "list_url": "/app/brouillard-caisse",
                "form_url": "/brouillard-caisse",
            },
            {
                "name": "Etat Recap Cheques",
                "label": "États Récap. Chèques",
                "status_field": "statut",
                "date_field": "date_etat",
                "amount_field": "total_montant",
                "list_url": "/app/etat-recap-cheques",
                "form_url": "/etat-recap",
            },
        ],
    },
}

# Statuts classés comme "approuvé", "en attente", "rejeté"
APPROVED_STATES = {"Approuvé", "Approuvée", "Clôturé", "Livré", "Validé", "Terminé"}
REJECTED_STATES = {"Rejeté", "Rejetée", "Annulé", "Annulée"}
DRAFT_STATES = {"Brouillon", "Draft"}


def _get_config():
    """
    Charge la config depuis KYA Dashboard Settings (DocType Single).
    Si le tableau est vide → fallback sur MODULE_MAP intégré.
    """
    try:
        settings = frappe.get_single("KYA Dashboard Settings")
        entries = [e for e in (settings.entries or []) if e.is_active]
        if not entries:
            return MODULE_MAP  # pas encore configuré → valeurs par défaut

        config = {}
        for e in entries:
            mk = (e.module_key or "autre").strip()
            if mk not in config:
                config[mk] = {
                    "label": e.module_label or mk.title(),
                    "icon": e.icon or "📋",
                    "color": e.color or "#607d8b",
                    "doctypes": [],
                }
            config[mk]["doctypes"].append({
                "name": e.doctype_name,
                "label": e.dt_label,
                "status_field": e.status_field or "workflow_state",
                "date_field": e.date_field or "creation",
                "amount_field": e.amount_field or None,
                "list_url": e.list_url or f"/app/{frappe.scrub(e.doctype_name).replace('_', '-')}",
                "form_url": e.web_form_route or "",
            })
        return config
    except Exception:
        return MODULE_MAP  # fallback si le DocType n'existe pas encore



    if not state:
        return "other"
    s = str(state).strip()
    if s in APPROVED_STATES:
        return "approved"
    if s in REJECTED_STATES:
        return "rejected"
    if s in DRAFT_STATES:
        return "draft"
    return "pending"  # En attente Chef, En attente DAAF, etc.


def _get_doctype_stats(dt_cfg, date_from, date_to):
    """Retourne les stats agrégées pour un DocType donné."""
    dt_name = dt_cfg["name"]
    sf = dt_cfg["status_field"]
    df = dt_cfg["date_field"]
    af = dt_cfg.get("amount_field")

    # Vérifier que le DocType existe
    try:
        if not frappe.db.table_exists(f"tab{dt_name}"):
            return None
    except Exception:
        return None

    try:
        # Compte par statut
        rows = frappe.db.sql(
            f"""
            SELECT `{sf}` AS status, COUNT(*) AS cnt
            FROM `tab{dt_name}`
            WHERE docstatus < 2
              AND `{df}` >= %(df)s AND `{df}` <= %(dt)s
            GROUP BY `{sf}`
            """,
            {"df": date_from, "dt": date_to},
            as_dict=True,
        )
    except Exception:
        rows = []

    by_status = {}
    classified = {"pending": 0, "approved": 0, "rejected": 0, "draft": 0, "other": 0}
    total = 0
    for r in rows:
        label = r.status or "Brouillon"
        by_status[label] = r.cnt
        classified[_classify(label)] += r.cnt
        total += r.cnt

    # Montant total si applicable
    total_amount = 0
    if af:
        try:
            res = frappe.db.sql(
                f"""
                SELECT COALESCE(SUM(`{af}`), 0) AS s
                FROM `tab{dt_name}`
                WHERE docstatus < 2 AND `{df}` >= %(df)s AND `{df}` <= %(dt)s
                """,
                {"df": date_from, "dt": date_to},
            )
            total_amount = flt(res[0][0]) if res else 0
        except Exception:
            pass

    # 5 derniers enregistrements
    try:
        recents = frappe.db.sql(
            f"""
            SELECT name, `{sf}` AS status,
                   `{df}` AS record_date,
                   {('`' + af + '`') if af else 'NULL'} AS amount,
                   creation, modified_by
            FROM `tab{dt_name}`
            WHERE docstatus < 2
            ORDER BY modified DESC
            LIMIT 5
            """,
            as_dict=True,
        )
    except Exception:
        recents = []

    return {
        "name": dt_name,
        "label": dt_cfg["label"],
        "total": total,
        "by_status": by_status,
        "classified": classified,
        "total_amount": total_amount,
        "list_url": dt_cfg["list_url"],
        "form_url": dt_cfg["form_url"],
        "recents": [
            {
                "name": r.name,
                "status": r.status or "—",
                "date": str(r.record_date or "")[:10],
                "amount": flt(r.amount) if r.amount else None,
                "class": _classify(r.status or ""),
            }
            for r in recents
        ],
    }


@frappe.whitelist()
def get_global_stats(period="30", module=None):
    """
    Retourne les stats agrégées de tous les web forms.
    period : nombre de jours (30, 90, 180, 365)
    module : optionnel, filtre sur un module (rh, achats, stock, compta)
    """
    # Seuls DG, System Manager, Administrator ont accès
    allowed = {"DG", "Directeur Général", "System Manager", "Administrator"}
    user_roles = set(frappe.get_roles())
    if not user_roles.intersection(allowed):
        frappe.throw(_("Accès refusé"), frappe.PermissionError)

    period = int(period or 30)
    date_from = add_days(today(), -period)
    date_to = today()

    result = {"modules": {}, "totals": {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "draft": 0}}

    active_config = _get_config()
    modules_to_process = {module: active_config[module]} if module and module in active_config else active_config

    for mod_key, mod_cfg in modules_to_process.items():
        mod_result = {
            "label": mod_cfg["label"],
            "icon": mod_cfg["icon"],
            "color": mod_cfg["color"],
            "doctypes": [],
            "totals": {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "draft": 0, "amount": 0},
        }
        for dt_cfg in mod_cfg["doctypes"]:
            stats = _get_doctype_stats(dt_cfg, date_from, date_to)
            if stats is None:
                continue
            mod_result["doctypes"].append(stats)
            for k in ("pending", "approved", "rejected", "draft"):
                mod_result["totals"][k] += stats["classified"][k]
            mod_result["totals"]["total"] += stats["total"]
            mod_result["totals"]["amount"] += stats["total_amount"]

        result["modules"][mod_key] = mod_result
        for k in ("total", "pending", "approved", "rejected", "draft"):
            result["totals"][k] += mod_result["totals"][k]

    return result


@frappe.whitelist()
def get_module_records(doctype, filters=None, limit=50, offset=0):
    """
    Retourne la liste paginée des enregistrements d'un DocType (vue liste par module).
    Accessible depuis les espaces RH, Achats, Stock, Comptabilité.
    """
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("Accès refusé"), frappe.PermissionError)

    # Trouver la config (dynamique ou fallback MODULE_MAP)
    dt_cfg = None
    for mod in _get_config().values():
        for d in mod["doctypes"]:
            if d["name"] == doctype:
                dt_cfg = d
                break

    if not dt_cfg:
        frappe.throw(_("DocType non reconnu dans le tableau de bord KYA"))

    sf = dt_cfg["status_field"]
    df = dt_cfg["date_field"]
    af = dt_cfg.get("amount_field")

    conditions = "docstatus < 2"
    if filters:
        try:
            f = json.loads(filters) if isinstance(filters, str) else filters
            if f.get("status"):
                conditions += f" AND `{sf}` = {frappe.db.escape(f['status'])}"
            if f.get("date_from"):
                conditions += f" AND `{df}` >= {frappe.db.escape(f['date_from'])}"
            if f.get("date_to"):
                conditions += f" AND `{df}` <= {frappe.db.escape(f['date_to'])}"
            if f.get("search"):
                s = frappe.db.escape(f"%" + f["search"] + "%")
                conditions += f" AND (name LIKE {s} OR `{sf}` LIKE {s})"
        except Exception:
            pass

    try:
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tab{doctype}` WHERE {conditions}"
        )[0][0] or 0

        rows = frappe.db.sql(
            f"""
            SELECT name, `{sf}` AS status,
                   `{df}` AS record_date,
                   {('`' + af + '`') if af else 'NULL'} AS amount,
                   owner, creation, modified
            FROM `tab{doctype}`
            WHERE {conditions}
            ORDER BY modified DESC
            LIMIT {int(limit)} OFFSET {int(offset)}
            """,
            as_dict=True,
        )
    except Exception as e:
        return {"records": [], "total": 0, "error": str(e)}

    return {
        "records": [
            {
                "name": r.name,
                "status": r.status or "Brouillon",
                "class": _classify(r.status or ""),
                "date": str(r.record_date or "")[:10],
                "amount": flt(r.amount) if r.amount else None,
                "owner": r.owner,
                "modified": str(r.modified or "")[:16],
                "form_url": dt_cfg["form_url"] + "/" + r.name,
                "desk_url": dt_cfg["list_url"].replace("/app/", "/app/") + "/" + r.name,
            }
            for r in rows
        ],
        "total": total,
        "doctype": doctype,
        "label": dt_cfg["label"],
    }


@frappe.whitelist()
def export_stats_csv(period="30"):
    """Exporte toutes les stats en CSV pour Excel."""
    allowed = {"DG", "Directeur Général", "System Manager", "Administrator"}
    if not set(frappe.get_roles()).intersection(allowed):
        frappe.throw(_("Accès refusé"), frappe.PermissionError)

    data = get_global_stats(period=period)
    lines = ["Module,Fiche,Total,En attente,Approuvé,Rejeté,Brouillon,Montant (XOF)"]
    for mod_key, mod in data.get("modules", {}).items():
        for dt in mod.get("doctypes", []):
            c = dt["classified"]
            lines.append(
                ",".join(str(x) for x in [
                    mod["label"],
                    dt["label"],
                    dt["total"],
                    c["pending"],
                    c["approved"],
                    c["rejected"],
                    c["draft"],
                    int(dt["total_amount"]),
                ])
            )
    return "\n".join(lines)


@frappe.whitelist()
def seed_dashboard_config():
    """
    Initialise KYA Dashboard Settings avec les valeurs par défaut (MODULE_MAP).
    Accessible via le bouton 'Initialiser' depuis le tableau de bord.
    Réservé aux System Manager.
    """
    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("Réservé aux System Manager"), frappe.PermissionError)

    settings = frappe.get_single("KYA Dashboard Settings")
    if settings.entries:
        # Déjà configuré — on retourne le nombre d'entrées
        return {"status": "already_configured", "count": len(settings.entries)}

    rows = []
    for mod_key, mod_cfg in MODULE_MAP.items():
        for dt in mod_cfg["doctypes"]:
            rows.append({
                "doctype": "KYA Dashboard Entry",
                "module_key": mod_key,
                "module_label": mod_cfg["label"],
                "icon": mod_cfg["icon"],
                "color": mod_cfg["color"],
                "doctype_name": dt["name"],
                "dt_label": dt["label"],
                "status_field": dt.get("status_field") or "workflow_state",
                "date_field": dt.get("date_field") or "creation",
                "amount_field": dt.get("amount_field") or "",
                "list_url": dt.get("list_url") or "",
                "web_form_route": dt.get("form_url") or "",
                "is_active": 1,
            })

    settings.entries = rows
    settings.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "seeded", "count": len(rows)}


@frappe.whitelist()
def reset_dashboard_config():
    """
    Réinitialise KYA Dashboard Settings avec les valeurs par défaut.
    ATTENTION : efface la configuration actuelle.
    Réservé aux System Manager.
    """
    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("Réservé aux System Manager"), frappe.PermissionError)

    settings = frappe.get_single("KYA Dashboard Settings")
    settings.entries = []
    settings.save(ignore_permissions=True)
    frappe.db.commit()
    # Re-seed
    return seed_dashboard_config()
