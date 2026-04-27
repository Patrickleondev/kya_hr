# Copyright (c) 2025, KYA-Energy Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


# ─── Cache (request-scoped) pour les rôles directifs ─────────────────────────
def _resolve_designated_employee_email(designation_keywords, department=None):
    """Trouve l'employé Active dont la designation matche un des mots-clés.
    Si `department` fourni, filtre dans ce département (ou ses ancêtres).
    Retourne le user_id (= email) ou None.
    """
    filters = {"status": "Active"}
    or_filters = [
        ["designation", "like", f"%{kw}%"] for kw in designation_keywords
    ]
    candidates = frappe.get_all(
        "Employee",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "user_id", "department", "designation"],
        limit=20,
    )
    if not candidates:
        return None

    # Si un département est précisé, on remonte la chaîne parent_department
    # pour trouver le candidat le plus proche dans la hiérarchie.
    if department:
        ancestors = [department]
        cur = department
        # max 6 niveaux de remontée
        for _ in range(6):
            parent = frappe.db.get_value("Department", cur, "parent_department")
            if not parent or parent in ancestors:
                break
            ancestors.append(parent)
            cur = parent
        for anc in ancestors:
            for c in candidates:
                if c.get("department") == anc and c.get("user_id"):
                    return c["user_id"]

    # Fallback : premier candidat avec user_id
    for c in candidates:
        if c.get("user_id"):
            return c["user_id"]
    return None


def _user_id_of_employee(emp_name):
    if not emp_name:
        return None
    return frappe.db.get_value("Employee", emp_name, "user_id") or None


def _resolve_user_by_role(role_name, department=None):
    """Trouve un user actif portant un rôle Frappe donné.
    Si `department` fourni, privilégie l'employé du même département (ou ancêtre).
    """
    users = frappe.get_all(
        "Has Role",
        filters={"role": role_name, "parenttype": "User"},
        fields=["parent"],
    )
    user_ids = [
        u.parent for u in users
        if u.parent and u.parent not in ("Administrator", "Guest")
    ]
    if not user_ids:
        return None

    # Filtre : users actifs
    active = frappe.get_all(
        "User",
        filters={"name": ["in", user_ids], "enabled": 1},
        pluck="name",
    )
    if not active:
        return None

    if department:
        # Trouve l'employé de même département/ancêtre
        ancestors = [department]
        cur = department
        for _ in range(6):
            parent = frappe.db.get_value("Department", cur, "parent_department")
            if not parent or parent in ancestors:
                break
            ancestors.append(parent)
            cur = parent
        for anc in ancestors:
            emp = frappe.db.get_value(
                "Employee",
                {"user_id": ["in", active], "department": anc, "status": "Active"},
                "user_id",
            )
            if emp:
                return emp

    # Fallback : 1er user actif lié à un Employee actif
    for u in active:
        if frappe.db.exists("Employee", {"user_id": u, "status": "Active"}):
            return u
    return active[0]


class PermissionSortieEmploye(Document):
    def validate(self):
        self.validate_employee_is_not_intern()
        self.set_employee_details()
        self.resolve_notification_recipients()
        self.guard_self_approval()

    def before_insert(self):
        """When HR creates manually via Desk, start workflow at 'En attente RH'
        to skip the Chef step (RH is the creator)."""
        if not self.flags.via_web_form:
            user_roles = frappe.get_roles(frappe.session.user)
            if "HR Manager" in user_roles or "HR User" in user_roles:
                self.workflow_state = "En attente RH"
                # Auto-fill chef bypass
                name = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "employee_name")
                if not name:
                    name = frappe.utils.get_fullname(frappe.session.user)
                self.signataire_chef = (name or "") + " (Créé par RH)"
                self.date_signature_chef = frappe.utils.today()

    def validate_employee_is_not_intern(self):
        if self.employee:
            emp_type = frappe.db.get_value("Employee", self.employee, "employment_type")
            if emp_type and emp_type == "Stage":
                frappe.throw(
                    "Les stagiaires doivent utiliser le formulaire Permission de Sortie Stagiaire."
                )

    def set_employee_details(self):
        if self.employee and not self.employee_name:
            self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")

    def resolve_notification_recipients(self):
        """Auto-remplit notif_chef_email / notif_rh_email / notif_dga_email / notif_dg_email
        à partir de la hiérarchie réelle (Employee.reports_to, Department, designations).

        Permet aux notifications fixtures de cibler le BON destinataire (l'email du
        responsable concerné) au lieu d'une boîte générique rh@kya-energy.com.
        """
        # Chef : reports_to de l'employé
        if self.employee:
            chef_emp = frappe.db.get_value("Employee", self.employee, "reports_to")
            self.notif_chef_email = _user_id_of_employee(chef_emp)

        # Responsable RH : par designation (fallback rôle Frappe "Responsable RH")
        if not self.notif_rh_email:
            self.notif_rh_email = _resolve_designated_employee_email(
                ["DRH", "Responsable RH", "Ressources Humaines", "RESP. RH", "DIR. RH"],
                department=self.department,
            ) or _resolve_user_by_role("Responsable RH", department=self.department) \
              or _resolve_user_by_role("HR Manager", department=self.department)

        # DGA : designation "Directeur Général Adjoint" / "DGA" / "G. ADJOINT" / "Adjoint"
        if not self.notif_dga_email:
            self.notif_dga_email = _resolve_designated_employee_email(
                ["Directeur Général Adjoint", "DGA", "G. ADJOINT", "G ADJOINT", "DIR. ADJOINT"],
            ) or _resolve_user_by_role("DGA")

        # DG : designation "Directeur Général" (mais pas "Adjoint")
        if not self.notif_dg_email:
            dg_email = _resolve_designated_employee_email(["Directeur Général"])
            # Filtre exclusion "Adjoint" : on prend le 1er DG dont la designation
            # ne contient PAS "Adjoint".
            if dg_email:
                desig = frappe.db.get_value(
                    "Employee", {"user_id": dg_email}, "designation"
                ) or ""
                if "Adjoint" in desig:
                    # Cherche un autre DG sans "Adjoint"
                    rows = frappe.get_all(
                        "Employee",
                        filters={"status": "Active"},
                        or_filters=[["designation", "like", "%Directeur Général%"]],
                        fields=["user_id", "designation"],
                        limit=20,
                    )
                    for r in rows:
                        if r.get("user_id") and "Adjoint" not in (r.get("designation") or ""):
                            dg_email = r["user_id"]
                            break
            self.notif_dg_email = dg_email

    def guard_self_approval(self):
        """Empêche le créateur d'approuver/transitioner sa propre demande
        (sauf si HR Manager qui crée pour quelqu'un d'autre, ou System Manager).

        Frappe contrôle déjà via `allow_self_approval=0` au niveau workflow,
        mais cette garde côté Python ferme tout contournement (db_set direct,
        scripts serveur, etc.).
        """
        if self.is_new() or not self.has_value_changed("workflow_state"):
            return
        user = frappe.session.user
        if user == "Administrator":
            return
        roles = set(frappe.get_roles(user))
        # Les profils privilégiés peuvent forcer (ex: HR Manager qui valide pour autrui)
        if {"System Manager", "HR Manager"} & roles:
            return

        # Si le user courant EST le demandeur (owner) ou l'employé concerné
        emp_user = (
            frappe.db.get_value("Employee", self.employee, "user_id") if self.employee else None
        )
        if user == self.owner or (emp_user and user == emp_user):
            current_state = self.workflow_state or ""
            # Le demandeur peut toujours soumettre (Brouillon → En attente Chef)
            if current_state in ("Brouillon", "En attente Chef"):
                # transitions autorisées au demandeur uniquement vers "En attente Chef"
                # rien à bloquer ici (Frappe workflow gère via allow_self_approval=0)
                pass
            if current_state in ("En attente RH", "En attente Direction", "Approuvé"):
                frappe.throw(
                    "Vous ne pouvez pas approuver votre propre demande de permission. "
                    "Cette action est réservée à votre Chef de Service, RH ou Direction."
                )

    def before_submit(self):
        if self.workflow_state == "Approuvé":
            self.statut = "Approuvé"

    def on_update_after_submit(self):
        if self.workflow_state:
            self.db_set("statut", self.workflow_state, update_modified=False)
        self.capture_signature()

    def capture_signature(self):
        """Auto-fill approver name/date when they sign at their workflow level."""
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        name = emp or frappe.utils.get_fullname(user)
        today = frappe.utils.today()
        ws = self.workflow_state

        # Chef signs → state moves to "En attente RH"
        if ws == "En attente RH" and not self.get("signataire_chef"):
            self.db_set("signataire_chef", name, update_modified=False)
            self.db_set("date_signature_chef", today, update_modified=False)

        # RH signs → state moves to "En attente Direction"
        if ws == "En attente Direction" and not self.get("signataire_rh"):
            self.db_set("signataire_rh", name, update_modified=False)
            self.db_set("date_signature_rh", today, update_modified=False)
            # If Chef was bypassed (Absence Chef → En attente RH), mark it
            if not self.get("signataire_chef"):
                self.db_set("signataire_chef", name + " (Absence Chef)", update_modified=False)
                self.db_set("date_signature_chef", today, update_modified=False)

        # DGA signs → state moves to "Approuvé"
        if ws == "Approuvé" and not self.get("signataire_dga"):
            self.db_set("signataire_dga", name, update_modified=False)
            self.db_set("date_signature_dga", today, update_modified=False)
            # If DGA was bypassed (Absence DGA), mark it
            if not self.get("signataire_rh") and self.get("signataire_chef"):
                # RH bypassed to DGA directly — shouldn't happen normally
                pass
            # If Chef was bypassed earlier, keep that mark
            # If DGA absent and someone else validated
            if self.workflow_state == "Approuvé" and not self.get("signature_dga"):
                # Validated via "Valider (Absence DGA)" — no DGA signature drawn
                bypass_action = frappe.db.get_value(
                    "Workflow Action",
                    {"reference_name": self.name, "status": "Completed"},
                    "workflow_action",
                    order_by="creation desc"
                )
                if bypass_action and "Absence DGA" in (bypass_action or ""):
                    self.db_set("signataire_dga", name + " (Absence DGA)", update_modified=False)
