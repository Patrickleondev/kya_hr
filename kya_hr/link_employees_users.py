"""Lie automatiquement les fiches Employee aux comptes User par email.

RACINE DE FRUSTRATION identifiee : un employe se connecte mais sa fiche
Employee n'a pas son compte dans le champ 'user_id'. Consequences :
- Web forms : 'Nom du Demandeur' reste vide (impossible de savoir qui c'est)
- Acces : les permissions basees sur le lien Employee echouent
- Dashboards perso (Mon Espace) ne trouvent pas l'employe

Ce module fournit :
1. audit() : rapport lecture seule. Combien d'Employees sans user_id,
   combien matchables par email, combien orphelins (pas de User).
2. link_by_email() : pour chaque Employee Active sans user_id, cherche
   un User dont l'email correspond (company_email / personal_email /
   prefered_email) et fait le lien. Ne cree PAS de User.
3. create_and_link(send_welcome=False) : pour les Employees sans User
   correspondant, CREE un compte User (role Employee) avec l'email
   company_email et fait le lien. send_welcome=False par defaut (pas
   d'email envoye, mot de passe a definir par la RH).

Idempotent : ne touche jamais un Employee qui a deja un user_id.
Securite : ne lie que si l'email matche exactement (pas de fuzzy).
"""
from __future__ import annotations

import frappe


EMAIL_FIELDS = ["company_email", "personal_email", "prefered_email"]


def _candidate_emails(emp: dict) -> list[str]:
    """Retourne les emails non vides d'un Employee, dans l'ordre de priorite."""
    emails = []
    for f in EMAIL_FIELDS:
        val = (emp.get(f) or "").strip().lower()
        if val and val not in emails:
            emails.append(val)
    return emails


def _find_user_by_email(emails: list[str]) -> str | None:
    """Cherche un User actif dont l'email ou le name matche un des emails."""
    for email in emails:
        # User.name est souvent l'email lui-meme
        if frappe.db.exists("User", email):
            return email
        # Sinon chercher par champ email
        u = frappe.db.get_value("User", {"email": email, "enabled": 1}, "name")
        if u:
            return u
    return None


def on_session_creation(login_manager=None) -> None:
    """Hook on_session_creation : auto-lie l'utilisateur qui se connecte.

    A chaque login, si l'utilisateur a une fiche Employee dont l'email
    correspond mais sans user_id renseigne, on fait le lien automatiquement.
    Resultat : le systeme s'auto-repare. Plus besoin de saisie manuelle
    du user_id par la RH -> 'Nom du Demandeur' se remplit, acces coherents.

    Silencieux et defensif : ne leve jamais (ne doit JAMAIS bloquer un login).
    """
    try:
        user = frappe.session.user
        if not user or user in ("Guest", "Administrator"):
            return

        # Rôles en doublon : si la RH a assigné « Responsable Equipe » là où le
        # système attend « Chef d'Équipe », on complète au login pour que
        # l'utilisateur ne soit bloqué à aucune étape. Purement additif.
        try:
            from kya_hr.reconcile_duplicate_roles import reconcilier_utilisateur
            if reconcilier_utilisateur(user):
                frappe.db.commit()
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             "on_session_creation reconcile_roles")

        # Deja lie a une fiche Employee ? -> on garantit quand meme l'acces
        # (role Employee + module KYA HR non bloque : cf. employee_access).
        already = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if already:
            try:
                from kya_hr.employee_access import ensure_access_for_user
                ensure_access_for_user(user)
                frappe.db.commit()
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 "on_session_creation ensure_access")
            return

        # Chercher une fiche Employee active dont un email == user (ou son email)
        user_email = (frappe.db.get_value("User", user, "email") or user).strip().lower()
        candidates = frappe.db.sql(
            """
            SELECT name FROM `tabEmployee`
            WHERE status = 'Active'
              AND (user_id IS NULL OR user_id = '')
              AND (
                LOWER(company_email) = %(e)s
                OR LOWER(personal_email) = %(e)s
                OR LOWER(prefered_email) = %(e)s
              )
            LIMIT 1
            """,
            {"e": user_email},
        )
        if candidates:
            frappe.db.set_value("Employee", candidates[0][0], "user_id", user,
                                update_modified=False)
            frappe.db.commit()
            # Nouveau lien -> poser role + debloquer les modules KYA
            try:
                from kya_hr.employee_access import ensure_access_for_user
                ensure_access_for_user(user)
                frappe.db.commit()
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 "on_session_creation ensure_access (new link)")
    except Exception:
        # Ne jamais bloquer le login
        try:
            frappe.log_error(frappe.get_traceback(), "link_employees_users.on_session_creation")
        except Exception:
            pass


@frappe.whitelist()
def audit() -> dict:
    """Rapport lecture seule sur la sante du linkage Employee <-> User."""
    employees = frappe.db.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "user_id"] + EMAIL_FIELDS,
    )

    total = len(employees)
    linked = 0
    matchable = []
    orphans = []  # pas de User correspondant
    no_email = []

    for emp in employees:
        if emp.get("user_id"):
            linked += 1
            continue
        emails = _candidate_emails(emp)
        if not emails:
            no_email.append({"name": emp.name, "employee_name": emp.employee_name})
            continue
        user = _find_user_by_email(emails)
        if user:
            matchable.append({"name": emp.name, "employee_name": emp.employee_name,
                              "user": user})
        else:
            orphans.append({"name": emp.name, "employee_name": emp.employee_name,
                           "emails": emails})

    return {
        "total_active": total,
        "already_linked": linked,
        "matchable_now": len(matchable),
        "orphans_no_user": len(orphans),
        "no_email_at_all": len(no_email),
        "details": {
            "matchable": matchable,
            "orphans": orphans,
            "no_email": no_email,
        },
    }


@frappe.whitelist()
def link_by_email() -> dict:
    """Lie les Employees sans user_id a un User existant par email exact."""
    employees = frappe.db.get_all(
        "Employee",
        filters={"status": "Active", "user_id": ["in", [None, ""]]},
        fields=["name", "employee_name"] + EMAIL_FIELDS,
    )

    stats = {"linked": 0, "no_match": 0, "errors": []}
    for emp in employees:
        emails = _candidate_emails(emp)
        user = _find_user_by_email(emails) if emails else None
        if not user:
            stats["no_match"] += 1
            continue
        try:
            frappe.db.set_value("Employee", emp.name, "user_id", user,
                                update_modified=False)
            stats["linked"] += 1
        except Exception as exc:
            stats["errors"].append({"employee": emp.name, "error": str(exc)})
            frappe.log_error(frappe.get_traceback(), f"link_employees_users: {emp.name}")

    try:
        frappe.db.commit()
    except Exception:
        pass

    print(f"[link_employees_users.link_by_email] {stats}")
    return stats


@frappe.whitelist()
def create_and_link(send_welcome: int = 0) -> dict:
    """Cree un User pour chaque Employee orphelin (avec email) et le lie.

    send_welcome=0 : pas d'email envoye, le compte est cree desactive
    cote notification. La RH definira le mot de passe ensuite.

    ATTENTION : action a faire en connaissance de cause. Ne creer des
    comptes que pour de vrais employes. Necessite role System Manager.
    """
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Reserve au System Manager", frappe.PermissionError)

    send_welcome = int(send_welcome or 0)

    employees = frappe.db.get_all(
        "Employee",
        filters={"status": "Active", "user_id": ["in", [None, ""]]},
        fields=["name", "employee_name", "first_name", "last_name"] + EMAIL_FIELDS,
    )

    stats = {"created": 0, "linked_existing": 0, "skipped_no_email": 0, "errors": []}
    for emp in employees:
        emails = _candidate_emails(emp)
        if not emails:
            stats["skipped_no_email"] += 1
            continue

        # Si un User existe deja -> juste lier
        existing = _find_user_by_email(emails)
        if existing:
            try:
                frappe.db.set_value("Employee", emp.name, "user_id", existing,
                                    update_modified=False)
                stats["linked_existing"] += 1
            except Exception as exc:
                stats["errors"].append({"employee": emp.name, "error": str(exc)})
            continue

        # Creer un nouveau User
        email = emails[0]
        try:
            user = frappe.new_doc("User")
            user.email = email
            user.first_name = emp.get("first_name") or emp.employee_name or email
            if emp.get("last_name"):
                user.last_name = emp.last_name
            user.send_welcome_email = 1 if send_welcome else 0
            user.user_type = "System User"
            user.append("roles", {"role": "Employee"})
            user.insert(ignore_permissions=True)
            frappe.db.set_value("Employee", emp.name, "user_id", user.name,
                                update_modified=False)
            stats["created"] += 1
        except Exception as exc:
            stats["errors"].append({"employee": emp.name, "error": str(exc)})
            frappe.log_error(frappe.get_traceback(), f"create_and_link: {emp.name}")

    try:
        frappe.db.commit()
    except Exception:
        pass

    print(f"[link_employees_users.create_and_link] {stats}")
    return stats
