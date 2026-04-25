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
    <div style="font-family:Arial,sans-serif; max-width:640px; margin:0 auto; border:1px solid #eee; border-radius:6px; overflow:hidden;">
      <div style="background:linear-gradient(135deg,#f7a800 0%,#e07b00 100%); padding:24px; color:#fff; text-align:center;">
        <h2 style="margin:0;">Bienvenue chez KYA-Energy Group</h2>
        <p style="margin:6px 0 0 0; opacity:0.95;">Votre contrat est prêt à être signé en ligne</p>
      </div>
      <div style="padding:24px 28px;">
        <p>Bonjour <b>{doc.employee_name}</b>,</p>
        <p>Nous avons le plaisir de vous proposer un <b>{doc.contract_type}</b> au sein de KYA-Energy Group.</p>
        <p>Référence du contrat : <b>{doc.name}</b></p>

        {creds_block}

        <h3 style="color:#e07b00; margin-top:24px;">Étapes à suivre</h3>
        <ol style="line-height:1.8;">
          <li>Cliquez sur le lien ci-dessous pour accéder à votre contrat</li>
          <li>Connectez-vous avec les identifiants fournis</li>
          <li><b>Complétez vos informations personnelles</b> :
            <ul>
              <li>Nom du Père et de la Mère (filiation)</li>
              <li>Date de naissance</li>
              <li>Domicile</li>
              <li>Téléphone</li>
            </ul>
          </li>
          <li>Lisez attentivement le contrat dans son intégralité</li>
          <li>Cochez la case <b>« J'ai lu et approuvé »</b></li>
          <li>Apposez votre signature (au choix) :
            <ul>
              <li>en la <b>dessinant</b> à la souris ou au doigt sur tablette/téléphone</li>
              <li>ou en <b>important une image</b> de votre signature scannée (PNG/JPG)</li>
            </ul>
          </li>
          <li>Cliquez sur <b>« Signer et Soumettre »</b></li>
        </ol>

        <p style="text-align:center; margin:30px 0;">
          <a href="{portail_url}" style="display:inline-block; background:#e07b00; color:#fff; padding:14px 32px; text-decoration:none; border-radius:6px; font-weight:600;">→ Accéder à mon contrat</a>
        </p>

        <p style="font-size:13px; color:#666;">Une fois votre signature apposée, le contrat sera transmis au Directeur Général pour co-signature.
        Vous recevrez la version finale signée par email au format PDF.</p>

        <p>Pour toute question, contactez-nous : <a href="mailto:rh@kya-energy.com">rh@kya-energy.com</a></p>
        <p style="margin-top:30px;">Bien cordialement,<br><b>Le Service des Ressources Humaines</b><br>KYA-Energy Group</p>
      </div>
    </div>
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


@frappe.whitelist()
def update_personal_info(contract_id, data):
    """Le signataire complète ses infos perso depuis le portail (avant signature)."""
    import json
    if isinstance(data, str):
        data = json.loads(data)
    doc = frappe.get_doc("KYA Contrat", contract_id)
    if frappe.session.user != doc.employee_email and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Vous n'êtes pas le signataire de ce contrat."), frappe.PermissionError)
    if doc.workflow_state not in ("Envoyé Signataire", "Brouillon"):
        frappe.throw(_("Le contrat n'est plus modifiable."))

    allowed = {"telephone", "date_naissance", "domicile", "filiation_pere", "filiation_mere"}
    for k, v in data.items():
        if k in allowed:
            doc.set(k, v or None)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True}
