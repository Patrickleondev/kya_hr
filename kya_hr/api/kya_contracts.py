"""KYA Contracts — API endpoints whitelistés.

Endpoints:
- send_to_signataire: création/maj user + envoi email bienvenue
- sign_contract: appelé depuis le portail web pour signer
- get_contract_for_signing: récupère un contrat avec contrôle d'accès
"""
import frappe
import secrets
import string
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.password import update_password


SIGNATAIRE_ROLE = "KYA Signataire Contrat"


def _ensure_signataire_role():
    if not frappe.db.exists("Role", SIGNATAIRE_ROLE):
        r = frappe.new_doc("Role")
        r.role_name = SIGNATAIRE_ROLE
        r.desk_access = 0  # Web only
        r.insert(ignore_permissions=True)


def _gen_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _ensure_user(email, full_name):
    """Crée l'utilisateur si inexistant, ajoute le rôle signataire, retourne (user, temp_pwd|None)."""
    _ensure_signataire_role()
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
        if not any(r.role == SIGNATAIRE_ROLE for r in user.roles):
            user.append("roles", {"role": SIGNATAIRE_ROLE})
            user.save(ignore_permissions=True)
        return user, None
    pwd = _gen_password()
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": full_name or email.split("@")[0],
        "send_welcome_email": 0,
        "user_type": "Website User",
        "enabled": 1,
        "roles": [{"role": SIGNATAIRE_ROLE}],
    }).insert(ignore_permissions=True)
    update_password(user.name, pwd)
    return user, pwd


@frappe.whitelist()
def send_to_signataire(contract_id):
    """Étape 3 — RH envoie le contrat au signataire."""
    if not any(r in frappe.get_roles() for r in ("HR Manager", "System Manager", "Responsable RH")):
        frappe.throw(_("Permission refusée"), frappe.PermissionError)

    doc = frappe.get_doc("KYA Contrat", contract_id)
    if not doc.employee_email:
        frappe.throw(_("L'employé n'a pas d'email enregistré."))

    user, temp_pwd = _ensure_user(doc.employee_email, doc.employee_name)

    # User Permission : restreindre l'accès au seul contrat concerné
    if not frappe.db.exists("User Permission", {
        "user": user.name, "allow": "KYA Contrat", "for_value": doc.name
    }):
        frappe.get_doc({
            "doctype": "User Permission",
            "user": user.name,
            "allow": "KYA Contrat",
            "for_value": doc.name,
            "apply_to_all_doctypes": 0,
        }).insert(ignore_permissions=True)

    site = frappe.utils.get_url()
    portail_url = f"{site}/kya-contrat?name={doc.name}"

    creds_block = ""
    if temp_pwd:
        creds_block = f"""
        <div style="background:#f5f5f5; padding:12px; border-left:4px solid #e07b00;">
        <p><b>Vos identifiants de connexion :</b></p>
        <p>Plateforme : <a href="{site}">{site}</a><br>
        Identifiant : <code>{doc.employee_email}</code><br>
        Mot de passe temporaire : <code>{temp_pwd}</code></p>
        <p><i>Vous serez invité(e) à le changer dès la première connexion.</i></p>
        </div>
        """

    message = f"""
    <p>Bonjour <b>{doc.employee_name}</b>,</p>
    <p>Nous sommes ravis de vous accueillir au sein de <b>KYA-Energy Group</b>.</p>
    <p>Un contrat de <b>{doc.contract_type}</b> a été préparé à votre attention.
    Merci de le lire attentivement et de le signer en ligne.</p>
    {creds_block}
    <p><b>→ Accéder à votre contrat :</b><br>
    <a href="{portail_url}">{portail_url}</a></p>
    <p>Démarche :<br>
    1. Connectez-vous à la plateforme<br>
    2. Lisez votre contrat en entier<br>
    3. Cochez « J'ai lu et approuvé »<br>
    4. Signez dans le champ de signature<br>
    5. Cliquez sur « Signer et Soumettre »</p>
    <p>Pour toute question : <a href="mailto:rh@kya-energy.com">rh@kya-energy.com</a></p>
    <p>Cordialement,<br>Le Service des Ressources Humaines<br>KYA-Energy Group</p>
    """
    frappe.sendmail(
        recipients=[doc.employee_email],
        subject=f"Bienvenue chez KYA-Energy Group — Votre contrat {doc.name}",
        message=message,
        now=False,
    )

    # Workflow → Envoyé Signataire
    doc.workflow_state = "Envoyé Signataire"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "user": user.name, "url": portail_url}


@frappe.whitelist()
def sign_contract(contract_id, signature_data, role="employe"):
    """Signature depuis le portail. role='employe' ou 'dg'."""
    doc = frappe.get_doc("KYA Contrat", contract_id)
    user = frappe.session.user

    if role == "employe":
        if user != doc.employee_email and "System Manager" not in frappe.get_roles():
            frappe.throw(_("Vous n'êtes pas le signataire de ce contrat."), frappe.PermissionError)
        if doc.workflow_state != "Envoyé Signataire":
            frappe.throw(_("Le contrat n'est pas en attente de votre signature."))
        doc.signature_employe = signature_data
        doc.contrat_lu = 1
        doc.nom_signe_employe = doc.employee_name
        doc.date_signature_employe = now_datetime()
        doc.workflow_state = "Signé Employé"
        doc.save(ignore_permissions=True)
        # Notif DG
        _notify_dg(doc)
    elif role == "dg":
        if not any(r in frappe.get_roles() for r in ("Directeur Général", "DG", "System Manager")):
            frappe.throw(_("Seul le Directeur Général peut co-signer."), frappe.PermissionError)
        if doc.workflow_state != "Signé Employé":
            frappe.throw(_("Le contrat n'est pas en attente de la signature DG."))
        doc.signature_dg = signature_data
        doc.date_signature_dg = now_datetime()
        doc.workflow_state = "Finalisé"
        doc.save(ignore_permissions=True)
        # Submit + génération PDF (déclenchée par on_update)
        try:
            doc.submit()
        except Exception:
            frappe.log_error(frappe.get_traceback(), "KYA Contrat submit")
    else:
        frappe.throw(_("Rôle de signature invalide"))

    frappe.db.commit()
    return {"ok": True, "state": doc.workflow_state}


def _notify_dg(doc):
    site = frappe.utils.get_url()
    url = f"{site}/kya-contrat?name={doc.name}"
    dg_emails = []
    for u in frappe.get_all("Has Role", filters={"role": "Directeur Général", "parenttype": "User"}, fields=["parent"]):
        em = frappe.db.get_value("User", u.parent, "email")
        if em:
            dg_emails.append(em)
    if not dg_emails:
        return
    frappe.sendmail(
        recipients=dg_emails,
        subject=f"✅ {doc.employee_name} a signé son contrat — Action requise (DG)",
        message=f"""
        <p>Bonjour,</p>
        <p>M/Mme <b>{doc.employee_name}</b> a signé son contrat de <b>{doc.contract_type}</b>
        le {frappe.format_value(doc.date_signature_employe, {'fieldtype':'Datetime'})}.</p>
        <p>Le contrat est en attente de votre co-signature.</p>
        <p><a href="{url}">→ Accéder au contrat</a></p>
        <p>Référence : <b>{doc.name}</b></p>
        """,
        now=False,
    )


@frappe.whitelist()
def get_contract_for_signing(contract_id):
    """Récupère un contrat pour le portail web avec contrôle d'accès."""
    doc = frappe.get_doc("KYA Contrat", contract_id)
    user = frappe.session.user
    roles = set(frappe.get_roles())
    is_signataire = (user == doc.employee_email)
    is_dg = bool(roles & {"Directeur Général", "DG", "System Manager"})
    is_rh = bool(roles & {"HR Manager", "Responsable RH", "System Manager"})

    if not (is_signataire or is_dg or is_rh):
        frappe.throw(_("Accès refusé"), frappe.PermissionError)

    return {
        "doc": doc.as_dict(),
        "can_sign_employe": is_signataire and doc.workflow_state == "Envoyé Signataire",
        "can_sign_dg": is_dg and doc.workflow_state == "Signé Employé",
        "is_finalized": doc.workflow_state == "Finalisé",
    }
