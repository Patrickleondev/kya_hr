import frappe

from kya_hr.mon_espace_sync import build_mon_espace_context

no_cache = 1


def get_context(context):
    """Mon Espace — portail employé unifié filtré par rôle."""
    if isinstance(context, dict):
        context = frappe._dict(context)

    if frappe.session.user == "Guest":
        frappe.throw("Veuillez vous connecter", frappe.AuthenticationError)

    user = frappe.session.user
    roles = frappe.get_roles(user)
    sync = build_mon_espace_context(user)

    emp = sync.get("employee") or frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "designation", "department", "image", "employment_type"],
        as_dict=True,
    )

    context.emp = emp
    context.roles = roles
    context.base_url = frappe.utils.get_url()
    context.mon_espace_sync = sync
    context.recent_demandes = sync.get("requests") or []
    context.sync_notifications = sync.get("notifications") or []
    context.form_notifications = sync.get("form_notifications") or []
    context.form_progress = sync.get("form_progress") or {
        "pending": [], "completed": [], "total": 0, "done": 0,
        "remaining": 0, "progress_pct": 100, "next_url": "", "next_label": "",
    }
    context.pending_actions = sync.get("pending_actions") or []
    context.notification_count = sync.get("notification_count") or 0

    context.show_fiches = True
    context.show_forms = True
    context.show_tasks = bool(emp) and frappe.db.exists(
        "Tache Equipe Attribution", {"employe": emp.get("name") if emp else ""}
    )

    rh_roles = {"HR Manager", "HR User", "Responsable RH", "System Manager"}
    context.show_rh = bool(rh_roles.intersection(set(roles)))

    stock_roles = {"Stock Manager", "Stock User", "Chargé des Stocks",
                   "Responsable Stock", "Magasinier", "System Manager"}
    context.show_stock = bool(stock_roles.intersection(set(roles)))

    achat_roles = {"Purchase Manager", "Purchase User", "Responsable Achats", "DAAF", "System Manager"}
    context.show_achats = bool(achat_roles.intersection(set(roles)))

    # Comptabilité : comptable, caissier, DFC, DAAF...
    compta_roles = {"Comptable", "Caissier", "DFC", "DAAF",
                    "Accounts Manager", "Accounts User", "System Manager"}
    context.show_compta = bool(compta_roles.intersection(set(roles)))

    # Logistique / flotte
    logistique_roles = {"Gestionnaire de Flotte", "DST - Responsable Logistique",
                        "Responsable Logistique", "Chef Service", "System Manager"}
    context.show_logistique = bool(logistique_roles.intersection(set(roles)))

    direction_roles = {"Directeur Général", "DG", "DGA", "DAAF", "System Manager"}
    context.show_direction = bool(direction_roles.intersection(set(roles)))

    # is_stagiaire = vrai si Employee.employment_type=Stage OU role Stagiaire.
    # Voir kya_services/www/mon_espace.py pour le commentaire detaille.
    context.is_stagiaire = bool(emp) and (
        emp.get("employment_type") == "Stage"
        or "Stagiaire" in roles
    )
    stagiaire_mgmt_roles = {"Responsable des Stagiaires", "Maître de Stage", "HR Manager", "System Manager"}
    context.show_stagiaires_mgmt = bool(stagiaire_mgmt_roles.intersection(set(roles)))

    chef_roles = {"Chef Service", "Supérieur Immédiat", "HR Manager", "System Manager"}
    context.is_chef = bool(chef_roles.intersection(set(roles)))

    context.mes_equipes = []
    context.is_chef_equipe = False
    if emp:
        mes_equipes = frappe.get_all(
            "Equipe KYA",
            filters={"chef_equipe": emp.get("name"), "est_active": 1},
            fields=["name", "nom_equipe", "departement", "nombre_membres"],
        )
        context.mes_equipes = mes_equipes
        context.is_chef_equipe = len(mes_equipes) > 0

        context.mon_equipe = None
        mon_eq = frappe.db.get_value("Employee", emp.get("name"), "custom_kya_equipe")
        if mon_eq:
            context.mon_equipe = frappe.db.get_value(
                "Equipe KYA",
                mon_eq,
                ["name", "nom_equipe", "departement", "chef_equipe_name"],
                as_dict=True,
            )

    context.fiches_disponibles = sync.get("available_forms") or []
    context.stats = sync.get("stats") or {"total": 0, "en_cours": 0, "approuve": 0, "rejete": 0}

    return context
