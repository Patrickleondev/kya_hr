import frappe


def _get_user_equipes(user):
    """Retourne les équipes dont l'utilisateur est chef (via Equipe KYA.chef_equipe)."""
    emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    if not emp:
        return []
    return frappe.get_all("Equipe KYA", filters={"chef_equipe": emp, "est_active": 1}, pluck="name")


def _is_admin(user):
    """Vérifie si l'utilisateur a un rôle admin (HR Manager, System Manager, etc.)."""
    roles = frappe.get_roles(user)
    return bool({"System Manager", "HR Manager", "HR User", "Directeur Général", "DAAF"}.intersection(set(roles)))


# ── Plan Trimestriel ──

def plan_trimestriel_query(user):
    """Permission Query: filtre la liste Plan Trimestriel par équipe du chef."""
    if _is_admin(user):
        return ""

    equipes = _get_user_equipes(user)
    if not equipes:
        # Employé simple : voir les plans de son équipe (membre)
        emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
        if emp:
            mon_equipe = frappe.db.get_value("Employee", emp, "custom_kya_equipe")
            if mon_equipe:
                return f"`tabPlan Trimestriel`.equipe = {frappe.db.escape(mon_equipe)}"
        return "1=0"

    escaped = ", ".join(frappe.db.escape(e) for e in equipes)
    return f"`tabPlan Trimestriel`.equipe IN ({escaped})"


def plan_trimestriel_has_permission(doc, ptype, user):
    """Has Permission: vérifie l'accès à un Plan Trimestriel spécifique."""
    if _is_admin(user):
        return True

    equipes = _get_user_equipes(user)
    if doc.equipe in equipes:
        return True

    # Membre de l'équipe peut lire
    emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    if emp:
        mon_equipe = frappe.db.get_value("Employee", emp, "custom_kya_equipe")
        if mon_equipe == doc.equipe and ptype == "read":
            return True

    return False


# ── Tache Equipe ──

def tache_equipe_query(user):
    """Permission Query: filtre les tâches par équipe ou attribution."""
    if _is_admin(user):
        return ""

    emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    if not emp:
        return "1=0"

    equipes = _get_user_equipes(user)
    conditions = []

    # Chef d'équipe : voit toutes les tâches de ses équipes
    if equipes:
        escaped = ", ".join(frappe.db.escape(e) for e in equipes)
        conditions.append(f"`tabTache Equipe`.equipe IN ({escaped})")

    # Employé attribué : voit ses propres tâches
    conditions.append(
        f"`tabTache Equipe`.name IN "
        f"(SELECT parent FROM `tabTache Equipe Attribution` WHERE employe = {frappe.db.escape(emp)})"
    )

    return "(" + " OR ".join(conditions) + ")"


def tache_equipe_has_permission(doc, ptype, user):
    """Has Permission: vérifie l'accès à une Tache Equipe spécifique."""
    if _is_admin(user):
        return True

    emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    if not emp:
        return False

    # Chef d'équipe
    equipes = _get_user_equipes(user)
    if doc.equipe in equipes:
        return True

    # Employé attribué (lecture + mise à jour taux)
    is_assigned = frappe.db.exists("Tache Equipe Attribution", {
        "parent": doc.name, "employe": emp,
    })
    if is_assigned and ptype in ("read", "write"):
        return True

    return False
