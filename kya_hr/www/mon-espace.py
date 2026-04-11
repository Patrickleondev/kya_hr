import frappe

no_cache = 1

def get_context(context):
    """Mon Espace — portail employé unifié filtré par rôle."""
    if frappe.session.user == "Guest":
        frappe.throw("Veuillez vous connecter", frappe.AuthenticationError)

    user = frappe.session.user
    roles = frappe.get_roles(user)

    # Identifier l'employé connecté
    emp = frappe.db.get_value("Employee",
        {"user_id": user, "status": "Active"},
        ["name", "employee_name", "designation", "department", "image", "employment_type"],
        as_dict=True
    )

    context.emp = emp
    context.roles = roles
    context.base_url = frappe.utils.get_url()

    # ── Sections visibles par rôle ──
    # Toutes les fiches que l'employé peut voir
    context.show_fiches = True  # Tout employé voit ses propres fiches

    # Formulaires/Enquêtes KYA (tout le monde)
    context.show_forms = True

    # Tâches (si l'employé est attribué dans au moins une Tache Equipe)
    context.show_tasks = bool(emp) and frappe.db.exists(
        "Tache Equipe Attribution", {"employe": emp.get("name") if emp else ""}
    )

    # Section RH (HR User, HR Manager, Responsable RH seulement)
    rh_roles = {"HR Manager", "HR User", "Responsable RH", "System Manager"}
    context.show_rh = bool(rh_roles.intersection(set(roles)))

    # Section Stock (Stock Manager, Stock User, Chargé des Stocks)
    stock_roles = {"Stock Manager", "Stock User", "Chargé des Stocks", "System Manager"}
    context.show_stock = bool(stock_roles.intersection(set(roles)))

    # Section Achats (Purchase Manager, Responsable Achats, DAAF)
    achat_roles = {"Purchase Manager", "Purchase User", "Responsable Achats", "DAAF", "System Manager"}
    context.show_achats = bool(achat_roles.intersection(set(roles)))

    # Section Direction (DG, DAAF)
    direction_roles = {"Directeur Général", "DAAF", "System Manager"}
    context.show_direction = bool(direction_roles.intersection(set(roles)))

    # Section Stagiaires
    context.is_stagiaire = bool(emp) and emp.get("employment_type") == "Stage"
    stagiaire_mgmt_roles = {"Responsable des Stagiaires", "Maître de Stage", "HR Manager", "System Manager"}
    context.show_stagiaires_mgmt = bool(stagiaire_mgmt_roles.intersection(set(roles)))

    # Section Chef Service/Supérieur
    chef_roles = {"Chef Service", "Supérieur Immédiat", "HR Manager", "System Manager"}
    context.is_chef = bool(chef_roles.intersection(set(roles)))

    # ── Section Équipe (Chef d'Équipe) ──
    context.mes_equipes = []
    context.is_chef_equipe = False
    if emp:
        mes_equipes = frappe.get_all("Equipe KYA",
            filters={"chef_equipe": emp.get("name"), "est_active": 1},
            fields=["name", "nom_equipe", "departement", "nombre_membres"],
        )
        context.mes_equipes = mes_equipes
        context.is_chef_equipe = len(mes_equipes) > 0

        # Équipe dont je suis membre
        context.mon_equipe = None
        mon_eq = frappe.db.get_value("Employee", emp.get("name"), "custom_kya_equipe")
        if mon_eq:
            context.mon_equipe = frappe.db.get_value("Equipe KYA", mon_eq,
                ["name", "nom_equipe", "departement", "chef_equipe_name"], as_dict=True)

    # Fiches disponibles pour cet employé (type de web forms accessibles)
    context.fiches_disponibles = []
    if emp:
        fiches_config = [
            {"label": "Permission de Sortie", "route": "permission-sortie-employe", "icon": "🚪",
             "roles": None},  # tous les employés
            {"label": "PV Sortie Matériel", "route": "pv-sortie-materiel", "icon": "📦",
             "roles": None},
            {"label": "Demande d'Achat", "route": "demande-achat", "icon": "🛒",
             "roles": None},
            {"label": "Planning de Congé", "route": "planning-conge", "icon": "🏖️",
             "roles": None},
            {"label": "Demande de Congé", "route": "demande-conge", "icon": "✈️",
             "roles": None},
        ]
        if context.is_stagiaire:
            fiches_config.insert(0, {
                "label": "Permission de Sortie Stagiaire", "route": "permission-sortie-stagiaire",
                "icon": "🎓", "roles": None
            })
            fiches_config.append({
                "label": "Bilan de Fin de Stage", "route": "bilan-fin-de-stage",
                "icon": "📋", "roles": None
            })

        for f in fiches_config:
            if f["roles"] is None or any(r in roles for r in f["roles"]):
                context.fiches_disponibles.append(f)

    # Compteurs de demandes en cours
    context.stats = {"total": 0, "en_cours": 0, "approuve": 0, "rejete": 0}
    if emp:
        for dt in ["Permission Sortie Employe", "PV Sortie Materiel", "Demande Achat KYA",
                    "Planning Conge", "Leave Application", "Permission Sortie Stagiaire", "Bilan Fin de Stage"]:
            try:
                emp_field = "employee"
                total = frappe.db.count(dt, {emp_field: emp.name})
                en_cours = frappe.db.count(dt, {emp_field: emp.name, "workflow_state": ["like", "%attente%"]})
                approuve = frappe.db.count(dt, {emp_field: emp.name, "workflow_state": ["like", "%Approuv%"]})
                rejete = frappe.db.count(dt, {emp_field: emp.name, "workflow_state": ["like", "%Rejet%"]})
                context.stats["total"] += total
                context.stats["en_cours"] += en_cours
                context.stats["approuve"] += approuve
                context.stats["rejete"] += rejete
            except Exception:
                pass

    return context
