import frappe
from frappe import _
from frappe.utils import flt, formatdate, today, add_days

no_cache = 1

_ALLOWED_ROLES = {
    "Directeur Général", "DGA", "DAAF", "DFC",
    "Auditeur Interne", "System Manager",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not _ALLOWED_ROLES.intersection(user_roles):
        frappe.throw(_("Accès réservé à la Direction Générale."), frappe.PermissionError)

    stats = {
        "demandes_dg": 0,
        "brouillards_semaine": 0,
        "effectif_actif": 0,
        "plannings_attente": 0,
        "permissions_attente": 0,
        "montant_demandes_dg": 0,
    }
    demandes_dg = []
    brouillards = []
    plannings_attente = []

    week_ago = add_days(today(), -7)

    try:
        # Demandes Achat en attente DG (palier 3, ≥ 2M XOF)
        demandes_dg = frappe.get_all(
            "Demande Achat KYA",
            filters=[["workflow_state", "in", ("En attente DG", "En attente Direction")]],
            fields=["name", "objet", "montant_total", "demandeur_nom", "modified", "workflow_state"],
            order_by="modified desc",
            limit_page_length=15,
        )
        stats["demandes_dg"] = len(demandes_dg)
        stats["montant_demandes_dg"] = sum(flt(d.montant_total) for d in demandes_dg)
        for d in demandes_dg:
            d.date_label = formatdate(d.modified) if d.modified else ""
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: demandes DG")

    try:
        # Brouillards caisse de la semaine
        brouillards = frappe.get_all(
            "Brouillard Caisse",
            filters=[["creation", ">=", week_ago]],
            fields=["name", "date_brouillard", "caissiere", "total_entrees",
                    "total_sorties", "solde_final", "workflow_state"],
            order_by="date_brouillard desc",
            limit_page_length=15,
        )
        stats["brouillards_semaine"] = len(brouillards)
        for b in brouillards:
            b.date_label = formatdate(b.date_brouillard) if b.date_brouillard else ""
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: brouillards")

    try:
        # Effectif actif
        stats["effectif_actif"] = frappe.db.count("Employee", {"status": "Active"})
    except Exception:
        pass

    try:
        # Plannings congé en attente Direction
        plannings_attente = frappe.get_all(
            "Planning Conge",
            filters=[["workflow_state", "in", ("En attente Direction", "En attente DG")]],
            fields=["name", "employee_name", "date_debut", "date_fin", "nb_jours",
                    "workflow_state", "modified"],
            order_by="modified desc",
            limit_page_length=10,
        )
        stats["plannings_attente"] = len(plannings_attente)
        for p in plannings_attente:
            p.date_label = formatdate(p.date_debut) if p.date_debut else ""
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: plannings")

    try:
        # Permissions de sortie en attente DG (rare mais possible si palier élevé)
        stats["permissions_attente"] = frappe.db.count(
            "Permission Sortie Employe",
            {"workflow_state": ["in", ("En attente DG", "En attente Direction")]},
        )
    except Exception:
        pass

    # ── 5.1 Synthèse par DÉPARTEMENT (toutes les équipes en un écran) ──
    departements = []
    try:
        rows = frappe.db.sql(
            """
            SELECT
                COALESCE(e.department, '(Sans département)') AS dept,
                COUNT(DISTINCT e.name) AS effectif,
                SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS presents,
                SUM(CASE WHEN a.late_entry=1 THEN 1 ELSE 0 END) AS retards,
                SUM(CASE WHEN a.status IN ('On Leave','Half Day') THEN 1 ELSE 0 END) AS conges,
                SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absents
            FROM `tabEmployee` e
            LEFT JOIN `tabAttendance` a
                ON a.employee = e.name AND a.attendance_date = CURDATE()
            WHERE e.status='Active'
            GROUP BY dept
            ORDER BY effectif DESC
            """,
            as_dict=True,
        )
        departements = rows
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: departements")

    # ── 5.1 Synthèse par ÉQUIPE (Employee.custom_kya_equipe -> Equipe KYA) ──
    # En prod, chaque employé est rattaché à une équipe : cette vue se peuple
    # automatiquement. Sur une instance sans équipes, la liste reste vide.
    equipes = []
    try:
        rows = frappe.db.sql(
            """
            SELECT
                eq.name AS equipe,
                eq.nom_equipe AS nom,
                eq.departement AS departement,
                eq.chef_equipe_name AS chef,
                COUNT(DISTINCT e.name) AS effectif,
                SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS presents,
                SUM(CASE WHEN a.late_entry=1 THEN 1 ELSE 0 END) AS retards,
                SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absents
            FROM `tabEquipe KYA` eq
            LEFT JOIN `tabEmployee` e
                ON e.custom_kya_equipe = eq.name AND e.status='Active'
            LEFT JOIN `tabAttendance` a
                ON a.employee = e.name AND a.attendance_date = CURDATE()
            GROUP BY eq.name, eq.nom_equipe, eq.departement, eq.chef_equipe_name
            HAVING effectif > 0
            ORDER BY effectif DESC
            """,
            as_dict=True,
        )
        equipes = rows
    except Exception:
        frappe.log_error(frappe.get_traceback(), "direction-dashboard: equipes")

    # ── 5.1 Bandeau MULTI-MODULES : tout ce qui est "en attente" partout ──
    def _count_waiting(doctype, states):
        try:
            return frappe.db.count(doctype, {"workflow_state": ["in", states]})
        except Exception:
            return 0

    waiting_states = ("En attente Chef", "En attente DAAF", "En attente DG",
                      "En attente Direction", "En attente RH", "En attente Audit",
                      "En attente Magasin", "En attente Comptable", "En attente DFC",
                      "En attente Achats & Stock", "En attente Signature Salarié",
                      "En attente Resp. Stagiaires", "En attente Chef de Service",
                      "En attente du Supérieur Immédiat")
    modules = {
        "Demandes d'achat": _count_waiting("Demande Achat KYA", waiting_states),
        "Permissions sortie": (_count_waiting("Permission Sortie Employe", waiting_states)
                                + _count_waiting("Permission Sortie Stagiaire", waiting_states)),
        "Plannings congé": _count_waiting("Planning Conge", waiting_states),
        "PV matériel": (_count_waiting("PV Sortie Materiel", waiting_states)
                        + _count_waiting("PV Entree Materiel", waiting_states)),
        "Inventaires": _count_waiting("Inventaire KYA", waiting_states),
        "Brouillards caisse": _count_waiting("Brouillard Caisse", waiting_states),
        "Contrats": _count_waiting("KYA Contrat", waiting_states),
    }
    modules_total = sum(modules.values())

    # ── Graphes Chart.js (toutes données réelles) ──
    import json as _json

    # 1. Présence par département (barres empilées)
    presence_chart = {
        "labels": [d.get("dept") or "—" for d in departements],
        "presents": [int(d.get("presents") or 0) for d in departements],
        "absents": [int(d.get("absents") or 0) for d in departements],
        "conges": [int(d.get("conges") or 0) for d in departements],
    }

    # 2. Workflows par statut (camembert) : agrège les états sur les doctypes clés
    wf_doctypes = ["Demande Achat KYA", "Permission Sortie Employe",
                   "Permission Sortie Stagiaire", "Planning Conge",
                   "PV Sortie Materiel", "PV Entree Materiel", "Inventaire KYA",
                   "Brouillard Caisse", "Leave Application", "KYA Contrat"]
    wf_counts = {"En attente": 0, "Approuvé": 0, "Rejeté": 0, "Brouillon": 0}
    for dt in wf_doctypes:
        if not frappe.db.exists("DocType", dt):
            continue
        try:
            rows = frappe.db.sql(
                f"SELECT workflow_state, COUNT(*) n FROM `tab{dt}` GROUP BY workflow_state",
                as_dict=True)
            for r in rows:
                st = (r.workflow_state or "").lower()
                if "attente" in st:
                    wf_counts["En attente"] += r.n
                elif "approuv" in st or "valid" in st or "archiv" in st:
                    wf_counts["Approuvé"] += r.n
                elif "rejet" in st or "annul" in st:
                    wf_counts["Rejeté"] += r.n
                else:
                    wf_counts["Brouillon"] += r.n
        except Exception:
            pass

    # 3. Évolution caisse 6 derniers mois (entrées vs sorties) — réel
    caisse_chart = {"labels": [], "entrees": [], "sorties": []}
    try:
        rows = frappe.db.sql(
            """
            SELECT CONCAT(YEAR(date_brouillard), '-', LPAD(MONTH(date_brouillard), 2, '0')) AS mois,
                   SUM(total_entrees) AS ent, SUM(total_sorties) AS sor
            FROM `tabBrouillard Caisse`
            WHERE date_brouillard >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY mois ORDER BY mois
            """, as_dict=True)
        for r in rows:
            caisse_chart["labels"].append(r.mois or "")
            caisse_chart["entrees"].append(float(r.ent or 0))
            caisse_chart["sorties"].append(float(r.sor or 0))
    except Exception:
        pass

    context.stats = stats
    context.demandes_dg = demandes_dg
    context.brouillards = brouillards
    context.plannings_attente = plannings_attente
    context.departements = departements
    context.equipes = equipes
    context.modules = modules
    context.modules_total = modules_total
    context.presence_chart_json = _json.dumps(presence_chart)
    context.wf_chart_json = _json.dumps(wf_counts)
    context.caisse_chart_json = _json.dumps(caisse_chart)
    context.no_breadcrumbs = True
