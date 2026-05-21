"""Synchronisation automatique role <-> employment_type sur Employee.

Frappe distingue 2 notions qui peuvent deriver :
- `Employee.employment_type` : donnee metier RH (Stage, CDI, CDD, etc.)
- `User.roles` (table 'Has Role') : permission technique Frappe

Quand l'admin modifie l'un OU l'autre, on veut que l'autre suive
automatiquement, sinon /mon-espace, les workflows et les redirects de
webform divergent (un user marque 'Stagiaire' en role mais
'employment_type=CDI' va recevoir le mauvais traitement partout).

Branche `before_save` (et `on_update`) sur Employee :
- Si employment_type == 'Stage' -> ajoute role 'Stagiaire' au User lie
- Si employment_type != 'Stage' (changement) -> retire role 'Stagiaire'
- Garantit toujours le role 'Employee' (cf ensure_employee_roles.py)

Idempotent et silencieux : echec d'ecriture sur Has Role ne bloque jamais
le save de l'Employee.
"""
import frappe


def _has_user_role(user: str, role: str) -> bool:
    if not user or not role:
        return False
    return bool(frappe.db.exists(
        "Has Role",
        {"parent": user, "parenttype": "User", "role": role},
    ))


def _add_user_role(user: str, role: str) -> bool:
    if not user or not role:
        return False
    if user in ("Administrator", "Guest"):
        return False
    if not frappe.db.exists("User", user):
        return False
    if not frappe.db.exists("Role", role):
        return False
    if _has_user_role(user, role):
        return False
    try:
        frappe.get_doc({
            "doctype": "Has Role",
            "parent": user,
            "parenttype": "User",
            "parentfield": "roles",
            "role": role,
        }).insert(ignore_permissions=True, ignore_if_duplicate=True)
        return True
    except Exception as exc:
        if "Duplicate" not in str(exc):
            try:
                frappe.log_error(frappe.get_traceback(), f"role_sync add {user}/{role}")
            except Exception:
                pass
        return False


def _remove_user_role(user: str, role: str) -> bool:
    if not user or not role:
        return False
    if user in ("Administrator", "Guest"):
        return False
    try:
        rows = frappe.get_all(
            "Has Role",
            filters={"parent": user, "parenttype": "User", "role": role},
            pluck="name",
        )
        for name in rows:
            frappe.delete_doc("Has Role", name, force=True, ignore_missing=True)
        return bool(rows)
    except Exception:
        try:
            frappe.log_error(frappe.get_traceback(), f"role_sync remove {user}/{role}")
        except Exception:
            pass
        return False


def sync_employee_role(doc, method=None):
    """Aligne les roles User sur Employee.employment_type."""
    try:
        user = getattr(doc, "user_id", None)
        if not user or user in ("Administrator", "Guest"):
            return

        emp_type = (getattr(doc, "employment_type", None) or "").strip()

        # Tout employe actif doit avoir 'Employee' (defense en profondeur ;
        # ensure_employee_roles.py fait la version batch en after_migrate).
        if getattr(doc, "status", "Active") == "Active":
            _add_user_role(user, "Employee")

        # Stagiaire <-> employment_type = Stage
        if emp_type == "Stage":
            _add_user_role(user, "Stagiaire")
        else:
            # employment_type a change vers autre chose (CDI, CDD, ...)
            # ou est vide -> retire le role Stagiaire pour eviter la
            # divergence (sauf si admin l'a explicitement laisse).
            if _has_user_role(user, "Stagiaire"):
                _remove_user_role(user, "Stagiaire")
    except Exception:
        # Ne JAMAIS bloquer le save de l'Employee.
        try:
            frappe.log_error(frappe.get_traceback(), "role_sync.sync_employee_role")
        except Exception:
            pass
