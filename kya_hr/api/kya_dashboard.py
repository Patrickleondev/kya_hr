# -*- coding: utf-8 -*-
"""
Tableau de Bord Global KYA-Energy — API
Fournit les stats agrégées de TOUS les web forms pour la vue DG.
Route : /kya-tableau-de-bord
"""
import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, add_days, today, nowdate, now_datetime
import json
import hashlib
from urllib.parse import quote


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
    "reunions": {
        "label": "Réunions & Émargements",
        "icon": "🗓️",
        "color": "#00838f",
        "doctypes": [
            {
                "name": "KYA Reunion Meeting",
                "label": "Réunions synchronisées",
                "status_field": "status",
                "date_field": "start_at",
                "amount_field": None,
                "list_url": "/app/kya-reunion-meeting",
                "form_url": "",
            },
        ],
    },
}

# Statuts classés comme "approuvé", "en attente", "rejeté"
APPROVED_STATES = {"Approuvé", "Approuvée", "Clôturé", "Livré", "Validé", "Terminé"}
REJECTED_STATES = {"Rejeté", "Rejetée", "Annulé", "Annulée"}
DRAFT_STATES = {"Brouillon", "Draft"}
CORE_WEB_FORM_MODULES = {"Core", "Website", "Utilities", "Contacts", "Support", "HR", "Projects"}


def _normalize_route(route):
    route = (route or "").strip()
    if not route:
        return ""
    return "/" + route.strip("/")


def _route_key(route):
    return _normalize_route(route).strip("/")


def _classify(state):
    if state in (0, "0"):
        return "draft"
    if state in (1, "1"):
        return "approved"
    if state in (2, "2"):
        return "rejected"
    if not state:
        return "other"
    s = str(state).strip()
    if s in APPROVED_STATES:
        return "approved"
    if s in REJECTED_STATES:
        return "rejected"
    if s in DRAFT_STATES:
        return "draft"
    return "pending"


def _has_field(doctype, fieldname):
    if not fieldname:
        return False
    if fieldname in {"docstatus", "creation", "modified", "owner", "name"}:
        return True
    try:
        return bool(frappe.get_meta(doctype).has_field(fieldname))
    except Exception:
        return False


def _default_print_format(doctype):
    if not doctype:
        return None
    try:
        preferred = frappe.db.get_value(
            "Print Format",
            {"doc_type": doctype, "name": ["like", "%KYA%"]},
            "name",
        )
        return preferred or frappe.db.get_value("Print Format", {"doc_type": doctype, "standard": "Yes"}, "name")
    except Exception:
        return None


def _pdf_url(doctype, name, print_format=None):
    if not doctype or not name:
        return ""
    params = f"doctype={quote(doctype)}&name={quote(name)}&no_letterhead=0"
    if print_format:
        params += f"&format={quote(print_format)}"
    return "/api/method/frappe.utils.print_format.download_pdf?" + params


def _desk_url(doctype, name=None):
    route = f"/app/{frappe.scrub(doctype).replace('_', '-')}"
    return route + (f"/{quote(name)}" if name else "")


def _guess_module_from_web_form(web_form):
    title = f"{web_form.get('title') or ''} {web_form.get('route') or ''} {web_form.get('doc_type') or ''}".lower()
    if any(k in title for k in ("achat", "commande", "offre")):
        return "achats", "Achats", "Achats", "🛒", "#e65100"
    if any(k in title for k in ("stock", "materiel", "matériel", "inventaire")):
        return "stock", "Stock", "Stock", "📦", "#2e7d32"
    if any(k in title for k in ("conge", "congé", "permission", "stage", "rh")):
        return "rh", "Ressources Humaines", "RH", "👥", "#1565c0"
    if any(k in title for k in ("caisse", "cheque", "chèque", "compta", "finance")):
        return "comptabilite", "Comptabilité", "Comptabilité", "💰", "#6a1b9a"
    if any(k in title for k in ("vehicule", "véhicule", "logistique")):
        return "logistique", "Logistique", "Logistique", "🚚", "#455a64"
    return "autre", "Autres Services", web_form.get("module") or "Autre", "📋", "#607d8b"


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
                    "department": getattr(e, "department", None),
                    "service_label": getattr(e, "service_label", None),
                    "team_label": getattr(e, "team_label", None),
                }
            config[mk]["doctypes"].append({
                "name": e.doctype_name,
                "label": e.dt_label,
                "status_field": e.status_field or "workflow_state",
                "date_field": e.date_field or "creation",
                "amount_field": e.amount_field or None,
                "list_url": e.list_url or f"/app/{frappe.scrub(e.doctype_name).replace('_', '-')}",
                "form_url": _normalize_route(e.web_form_route),
                "web_form": getattr(e, "web_form_name", None),
                "web_form_route": _normalize_route(e.web_form_route),
                "print_format": getattr(e, "print_format", None) or _default_print_format(e.doctype_name),
                "department": getattr(e, "department", None),
                "service_label": getattr(e, "service_label", None),
                "team_label": getattr(e, "team_label", None),
            })
        for module_key, module_cfg in MODULE_MAP.items():
            if module_key not in config:
                config[module_key] = module_cfg
        return config
    except Exception:
        return MODULE_MAP  # fallback si le DocType n'existe pas encore


_ACTIVE_WF_CACHE = {}


def _has_active_workflow(doctype):
    """True si un Workflow actif existe pour ce doctype (=> workflow_state fait foi)."""
    if doctype not in _ACTIVE_WF_CACHE:
        try:
            _ACTIVE_WF_CACHE[doctype] = bool(
                frappe.db.exists("Workflow", {"document_type": doctype, "is_active": 1})
            )
        except Exception:
            _ACTIVE_WF_CACHE[doctype] = False
    return _ACTIVE_WF_CACHE[doctype]


def _effective_status_field(dt_name, configured):
    """Champ de statut RÉEL à lire.

    Bug terrain : certains doctypes ont un champ `statut` obsolète (jamais mis à
    jour) ET un `workflow_state` piloté par un workflow actif. Le dashboard
    affichait alors 0 approuvé. Règle : si un workflow est actif et que
    `workflow_state` existe, c'est LUI la source de vérité, quel que soit le
    `status_field` configuré.
    """
    if _has_field(dt_name, "workflow_state") and _has_active_workflow(dt_name):
        return "workflow_state"
    return configured or "workflow_state"


def _get_doctype_stats(dt_cfg, date_from, date_to):
    """Retourne les stats agrégées pour un DocType donné."""
    dt_name = dt_cfg["name"]
    sf = _effective_status_field(dt_name, dt_cfg.get("status_field"))
    df = dt_cfg.get("date_field") or "creation"
    af = dt_cfg.get("amount_field")
    print_format = dt_cfg.get("print_format") or _default_print_format(dt_name)

    # Vérifier que le DocType existe
    try:
        if not frappe.db.table_exists(dt_name):
            return None
    except Exception:
        return None

    if not _has_field(dt_name, df):
        df = "creation"
    status_expr = f"`{sf}`" if _has_field(dt_name, sf) and sf != "docstatus" else "CASE docstatus WHEN 0 THEN 'Brouillon' WHEN 1 THEN 'Approuvé' ELSE 'Rejeté' END"
    amount_expr = f"`{af}`" if af and _has_field(dt_name, af) else "NULL"
    amount_sum_expr = f"COALESCE(SUM(`{af}`), 0)" if af and _has_field(dt_name, af) else "0"

    try:
        # Compte par statut
        rows = frappe.db.sql(
            f"""
                        SELECT {status_expr} AS status, COUNT(*) AS cnt
            FROM `tab{dt_name}`
            WHERE docstatus < 2
              AND `{df}` >= %(df)s AND `{df}` <= %(dt)s
                        GROUP BY status
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
    if af and _has_field(dt_name, af):
        try:
            res = frappe.db.sql(
                f"""
                SELECT {amount_sum_expr} AS s
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
                 SELECT name, {status_expr} AS status,
                   `{df}` AS record_date,
                     {amount_expr} AS amount,
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

    extra = {}
    if dt_name == "KYA Reunion Meeting":
        try:
            extra["reunion_summary"] = frappe.get_attr("kya_hr.api.kya_reunion.get_summary_for_dashboard")(date_from, date_to)
        except Exception:
            extra["reunion_summary"] = {}

    return {
        "name": dt_name,
        "label": dt_cfg["label"],
        "total": total,
        "by_status": by_status,
        "classified": classified,
        "total_amount": total_amount,
        "list_url": dt_cfg["list_url"],
        "form_url": dt_cfg.get("form_url") or dt_cfg.get("web_form_route") or "",
        "web_form": dt_cfg.get("web_form"),
        "web_form_route": dt_cfg.get("web_form_route") or dt_cfg.get("form_url") or "",
        "department": dt_cfg.get("department"),
        "service_label": dt_cfg.get("service_label"),
        "team_label": dt_cfg.get("team_label"),
        "print_format": print_format,
        "recents": [
            {
                "name": r.name,
                "status": r.status or "—",
                "date": str(r.record_date or "")[:10],
                "amount": flt(r.amount) if r.amount else None,
                "class": _classify(r.status or ""),
                "desk_url": _desk_url(dt_name, r.name),
                "pdf_url": _pdf_url(dt_name, r.name, print_format),
                "print_format": print_format,
            }
            for r in recents
        ],
        **extra,
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

    result = {
        "modules": {},
        "totals": {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "draft": 0},
        "filters": {"modules": []},
        "generated_on": str(now_datetime()),
    }

    active_config = _get_config()
    modules_to_process = {module: active_config[module]} if module and module in active_config else active_config

    for mod_key, mod_cfg in modules_to_process.items():
        mod_result = {
            "label": mod_cfg["label"],
            "icon": mod_cfg["icon"],
            "color": mod_cfg["color"],
            "department": mod_cfg.get("department"),
            "service_label": mod_cfg.get("service_label"),
            "team_label": mod_cfg.get("team_label"),
            "doctypes": [],
            "services": {},
            "totals": {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "draft": 0, "amount": 0},
        }
        for dt_cfg in mod_cfg["doctypes"]:
            stats = _get_doctype_stats(dt_cfg, date_from, date_to)
            if stats is None:
                continue
            mod_result["doctypes"].append(stats)
            service_key = stats.get("service_label") or mod_cfg.get("service_label") or mod_cfg["label"]
            service = mod_result["services"].setdefault(
                service_key,
                {"label": service_key, "total": 0, "pending": 0, "approved": 0, "rejected": 0, "draft": 0, "teams": {}},
            )
            service["total"] += stats["total"]
            for k in ("pending", "approved", "rejected", "draft"):
                mod_result["totals"][k] += stats["classified"][k]
                service[k] += stats["classified"][k]
            mod_result["totals"]["total"] += stats["total"]
            mod_result["totals"]["amount"] += stats["total_amount"]
            team_key = stats.get("team_label") or "Non classé"
            service["teams"][team_key] = service["teams"].get(team_key, 0) + stats["total"]

        result["modules"][mod_key] = mod_result
        result["filters"]["modules"].append({"key": mod_key, "label": mod_cfg["label"]})
        for k in ("total", "pending", "approved", "rejected", "draft"):
            result["totals"][k] += mod_result["totals"][k]

    return result


@frappe.whitelist()
def get_grouped_stats(period="30", group_by="department"):
    """Vue transversale du tableau de bord : agrège TOUTES les fiches par
    département et par équipe (Equipe KYA), via l'auteur de chaque fiche
    (owner → Employee.user_id → department / custom_kya_equipe).

    Retourne les deux regroupements (by_department, by_team) en un appel ;
    `group_by` n'est qu'indicatif côté front (bascule sans re-fetch)."""
    allowed = {"DG", "Directeur Général", "DGA", "System Manager", "Administrator"}
    if not set(frappe.get_roles()).intersection(allowed):
        frappe.throw(_("Accès refusé"), frappe.PermissionError)

    period = int(period or 30)
    date_from = add_days(today(), -period)
    date_to = today()

    # owner (User) -> Employee {department, custom_kya_equipe}
    user_to_emp = {}
    for e in frappe.get_all(
        "Employee", filters={"status": "Active"},
        fields=["employee_name", "user_id", "department", "custom_kya_equipe"],
    ):
        if e.user_id:
            user_to_emp[e.user_id] = e
    # Equipe KYA name -> libellé lisible
    eq_label = {q.name: (q.nom_equipe or q.name)
                for q in frappe.get_all("Equipe KYA", fields=["name", "nom_equipe"])}

    def _blank():
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "draft": 0}

    by_dept, by_team = {}, {}

    for mod_cfg in _get_config().values():
        for dt_cfg in mod_cfg["doctypes"]:
            dt_name = dt_cfg["name"]
            try:
                if not frappe.db.table_exists(dt_name):
                    continue
            except Exception:
                continue
            sf = _effective_status_field(dt_name, dt_cfg.get("status_field"))
            df = dt_cfg.get("date_field") or "creation"
            if not _has_field(dt_name, df):
                df = "creation"
            status_expr = (f"`{sf}`" if _has_field(dt_name, sf) and sf != "docstatus"
                           else "CASE docstatus WHEN 0 THEN 'Brouillon' WHEN 1 THEN 'Approuvé' ELSE 'Rejeté' END")
            try:
                rows = frappe.db.sql(
                    f"""SELECT owner, {status_expr} AS status
                        FROM `tab{dt_name}`
                        WHERE docstatus < 2 AND `{df}` >= %(df)s AND `{df}` <= %(dt)s""",
                    {"df": date_from, "dt": date_to}, as_dict=True,
                )
            except Exception:
                rows = []
            for r in rows:
                emp = user_to_emp.get(r.owner)
                dept = (emp.department if emp and emp.department else None) or "Non défini"
                team = (eq_label.get(emp.custom_kya_equipe) if emp and emp.custom_kya_equipe else None) or "Non affecté"
                cls = _classify(r.status or "")
                for key, bucket in ((dept, by_dept), (team, by_team)):
                    b = bucket.setdefault(key, _blank())
                    b["total"] += 1
                    if cls in b:
                        b[cls] += 1

    def _as_list(d):
        out = [dict(label=k, **v) for k, v in d.items()]
        out.sort(key=lambda x: (-x["total"], x["label"]))
        return out

    return {
        "by_department": _as_list(by_dept),
        "by_team": _as_list(by_team),
        "period": period,
        "generated_on": str(now_datetime()),
    }


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
    if not _has_field(doctype, df):
        df = "creation"
    status_expr = f"`{sf}`" if _has_field(doctype, sf) and sf != "docstatus" else "CASE docstatus WHEN 0 THEN 'Brouillon' WHEN 1 THEN 'Approuvé' ELSE 'Rejeté' END"
    amount_expr = f"`{af}`" if af and _has_field(doctype, af) else "NULL"

    conditions = "docstatus < 2"
    if filters:
        try:
            f = json.loads(filters) if isinstance(filters, str) else filters
            if f.get("status"):
                if _has_field(doctype, sf) and sf != "docstatus":
                    conditions += f" AND `{sf}` = {frappe.db.escape(f['status'])}"
            if f.get("date_from"):
                conditions += f" AND `{df}` >= {frappe.db.escape(f['date_from'])}"
            if f.get("date_to"):
                conditions += f" AND `{df}` <= {frappe.db.escape(f['date_to'])}"
            if f.get("search"):
                s = frappe.db.escape(f"%" + f["search"] + "%")
                if _has_field(doctype, sf) and sf != "docstatus":
                    conditions += f" AND (name LIKE {s} OR `{sf}` LIKE {s})"
                else:
                    conditions += f" AND name LIKE {s}"
        except Exception:
            pass

    try:
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tab{doctype}` WHERE {conditions}"
        )[0][0] or 0

        rows = frappe.db.sql(
            f"""
             SELECT name, {status_expr} AS status,
                   `{df}` AS record_date,
                 {amount_expr} AS amount,
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
                "desk_url": _desk_url(doctype, r.name),
                "pdf_url": _pdf_url(doctype, r.name, dt_cfg.get("print_format") or _default_print_format(doctype)),
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
    lines = ["Module,Service,Equipe,Fiche,Web Form,Print Format,Total,En attente,Approuvé,Rejeté,Brouillon,Montant (XOF)"]
    for mod_key, mod in data.get("modules", {}).items():
        for dt in mod.get("doctypes", []):
            c = dt["classified"]
            lines.append(
                ",".join(str(x) for x in [
                    mod["label"],
                    dt.get("service_label") or "",
                    dt.get("team_label") or "",
                    dt["label"],
                    dt.get("web_form_route") or "",
                    dt.get("print_format") or "",
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
                "print_format": dt.get("print_format") or _default_print_format(dt["name"]),
                "service_label": dt.get("service_label") or mod_cfg["label"],
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


@frappe.whitelist()
def get_syncable_modules():
    """Retourne la liste des modules Frappe qui ont au moins un Web Form publié.

    Why: appeler frappe.client.get_list via fetch() peut etre rejete par Frappe
    selon la configuration. Cet endpoint custom whitelisted est plus propre
    pour alimenter le dialog "Sync par module".
    """
    if not _can_manage_dashboard():
        frappe.throw(_("Réservé aux gestionnaires du tableau de bord."), frappe.PermissionError)
    rows = frappe.get_all("Web Form", filters={"published": 1}, fields=["module"], limit_page_length=0)
    modules = sorted({(r.get("module") or "").strip() for r in rows if r.get("module")})
    return {"modules": modules}


@frappe.whitelist()
def get_fresh_csrf():
    """Retourne un CSRF token frais pour la session courante.

    Why: le token injecte dans le HTML via {{ csrf_token }} peut etre invalide
    apres un changement de session ou un certain delai. Recuperer un token
    frais avant chaque POST evite les erreurs CSRFTokenError / Invalid Request.
    """
    from frappe.sessions import get_csrf_token
    return {"csrf_token": get_csrf_token()}


@frappe.whitelist()
def whoami_dashboard():
    """Endpoint de diagnostic : retourne user + roles + can_manage.

    Permet au frontend de comprendre pourquoi un 403 arrive (Guest vs role manquant).
    """
    user = frappe.session.user
    roles = frappe.get_roles(user) if user != "Guest" else []
    return {
        "user": user,
        "is_guest": user == "Guest",
        "roles": roles,
        "can_manage_dashboard": _can_manage_dashboard(),
    }


def _can_manage_dashboard():
    """Rôles autorisés à synchroniser le tableau de bord depuis les Web Forms.

    Why: la page /kya-tableau-de-bord autorise DG / Directeur Général à ouvrir
    le tableau, donc on doit leur permettre le bouton "Synchroniser Web Forms"
    sinon ils voient le bouton mais ne peuvent pas l'utiliser (rejet PermissionError).
    On élargit aussi aux managers de modules (HR Manager, DAAF, DFC) pour
    rendre la sync modulaire — chacun synchronise les Web Forms de son module.
    """
    allowed = {
        "System Manager", "Dashboard Manager", "Administrator",
        "DG", "Directeur Général", "DGA",
        "DAAF", "DFC",
        "HR Manager", "Responsable RH",
        "Auditeur Interne",
    }
    return bool(set(frappe.get_roles()).intersection(allowed))


def _pick_field(doctype, candidates, fallback="creation"):
    for fieldname in candidates:
        if _has_field(doctype, fieldname):
            return fieldname
    return fallback


def _entry_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def _entry_from_web_form(web_form, overrides=None):
    overrides = overrides or {}
    module_key, module_label, service_label, icon, color = _guess_module_from_web_form(web_form)
    doctype = web_form.get("doc_type")
    status_field = _pick_field(doctype, ["workflow_state", "statut", "status", "docstatus"], "docstatus")
    date_field = _pick_field(
        doctype,
        ["date_sortie", "date_entree", "date_demande", "date_bc", "date_ao", "date_brouillard", "date_etat", "date_inventaire", "posting_date", "creation"],
        "creation",
    )
    amount_field = _pick_field(
        doctype,
        ["montant_total", "total_montant", "budget_estime", "valeur_ecart_total", "grand_total", "amount"],
        "",
    )
    if amount_field == "creation":
        amount_field = ""

    route = _normalize_route(web_form.get("route"))
    print_format = web_form.get("print_format") or _default_print_format(doctype)
    payload = {
        "doctype": "KYA Dashboard Entry",
        "module_key": overrides.get("module_key") or module_key,
        "module_label": overrides.get("module_label") or module_label,
        "icon": overrides.get("icon") or icon,
        "color": overrides.get("color") or color,
        "department": overrides.get("department"),
        "service_label": overrides.get("service_label") or service_label,
        "team_label": overrides.get("team_label"),
        "doctype_name": doctype,
        "web_form_name": web_form.get("name"),
        "dt_label": overrides.get("dt_label") or web_form.get("title") or doctype,
        "status_field": overrides.get("status_field") or status_field,
        "date_field": overrides.get("date_field") or date_field,
        "amount_field": overrides.get("amount_field") or amount_field,
        "list_url": overrides.get("list_url") or _desk_url(doctype),
        "web_form_route": route,
        "print_format": overrides.get("print_format") or print_format,
        "sync_mode": overrides.get("sync_mode") or "Synchronisé depuis Web Form",
        "last_synced_on": now_datetime(),
        "is_active": cint(overrides.get("is_active", 1)),
    }
    payload["sync_fingerprint"] = _entry_hash(payload)
    return payload


def _find_dashboard_entry(settings, web_form_name=None, route=None, doctype=None):
    normalized = _normalize_route(route)
    for row in settings.entries or []:
        if web_form_name and getattr(row, "web_form_name", None) == web_form_name:
            return row
        if normalized and _normalize_route(getattr(row, "web_form_route", None)) == normalized:
            return row
        if doctype and getattr(row, "doctype_name", None) == doctype and not normalized:
            return row
    return None


def _apply_entry_payload(row, payload):
    for key, value in payload.items():
        if key == "doctype":
            continue
        setattr(row, key, value)


@frappe.whitelist()
def register_web_form_route(route, module_key=None, module_label=None, service_label=None, team_label=None, department=None):
    """Ajoute ou met à jour une entrée dashboard à partir d'un chemin Web Form collé."""
    if not _can_manage_dashboard():
        frappe.throw(_("Réservé aux gestionnaires du tableau de bord."), frappe.PermissionError)

    route_key = _route_key(route)
    if not route_key:
        frappe.throw(_("Route Web Form requise."))

    web_form = frappe.db.get_value(
        "Web Form",
        {"route": route_key},
        ["name", "title", "route", "doc_type", "module", "print_format", "published"],
        as_dict=True,
    )
    if not web_form:
        frappe.throw(_("Aucun Web Form trouvé pour la route {0}").format(_normalize_route(route)))
    if not web_form.doc_type or not frappe.db.exists("DocType", web_form.doc_type):
        frappe.throw(_("Le Web Form {0} n'est pas relié à un DocType valide.").format(web_form.name))

    settings = frappe.get_single("KYA Dashboard Settings")
    payload = _entry_from_web_form(
        web_form,
        {
            "module_key": module_key,
            "module_label": module_label,
            "service_label": service_label,
            "team_label": team_label,
            "department": department,
        },
    )
    row = _find_dashboard_entry(settings, web_form_name=web_form.name, route=route_key, doctype=web_form.doc_type)
    if row:
        _apply_entry_payload(row, payload)
        action = "updated"
    else:
        settings.append("entries", payload)
        action = "created"

    settings.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": action, "route": payload["web_form_route"], "doctype": payload["doctype_name"], "print_format": payload.get("print_format")}


@frappe.whitelist(allow_guest=True)
def sync_dashboard_entries_from_web_forms(published_only=1, include_core=0, module=None):
    """Synchronise le registre DG depuis les Web Forms publiées.

    Note securite : allow_guest=True desactive le CSRF check (sinon Frappe v16
    rejette le POST avec CSRFTokenError sur les pages web publiques ou le
    bundle frappe.js n'est pas charge). On verifie l'authentification +
    le role manuellement au debut de la fonction.

    Les statistiques restent calculées en temps réel depuis les DocTypes ; cette méthode ne crée
    que la cartographie contrôlée entre route Web Form, DocType, service et Print Format.

    Args:
        published_only: si truthy, ne synchronise que les Web Forms `published=1`.
        include_core: si truthy, inclut les modules core Frappe (sinon ignorés).
        module: si renseigné, ne synchronise que les Web Forms de ce module
                (ex. "KYA HR", "KYA Services") — permet une sync modulaire par équipe.
    """
    # Verification auth manuelle (allow_guest=True desactive le check Frappe natif)
    if frappe.session.user == "Guest":
        frappe.throw(_("Authentification requise."), frappe.AuthenticationError)
    if not _can_manage_dashboard():
        frappe.throw(_("Réservé aux gestionnaires du tableau de bord."), frappe.PermissionError)

    filters = {}
    if cint(published_only):
        filters["published"] = 1
    if module:
        filters["module"] = module
    web_forms = frappe.get_all(
        "Web Form",
        filters=filters,
        fields=["name", "title", "route", "doc_type", "module", "print_format", "published", "is_standard"],
        order_by="modified desc",
    )

    settings = frappe.get_single("KYA Dashboard Settings")
    created = 0
    updated = 0
    skipped = []

    for web_form in web_forms:
        if not web_form.get("route") or not web_form.get("doc_type"):
            skipped.append({"web_form": web_form.name, "reason": "route/doc_type manquant"})
            continue
        if not cint(include_core) and web_form.get("module") in CORE_WEB_FORM_MODULES:
            skipped.append({"web_form": web_form.name, "reason": "module standard ignoré"})
            continue
        if not frappe.db.exists("DocType", web_form.doc_type):
            skipped.append({"web_form": web_form.name, "reason": "DocType introuvable"})
            continue

        payload = _entry_from_web_form(web_form)
        row = _find_dashboard_entry(settings, web_form_name=web_form.name, route=web_form.route, doctype=web_form.doc_type)
        if row:
            if (getattr(row, "sync_mode", None) or "Synchronisé depuis Web Form") != "Manuel verrouillé":
                _apply_entry_payload(row, payload)
                updated += 1
        else:
            settings.append("entries", payload)
            created += 1

    settings.save(ignore_permissions=True)
    frappe.db.commit()
    return {"created": created, "updated": updated, "skipped": skipped, "total_scanned": len(web_forms)}
