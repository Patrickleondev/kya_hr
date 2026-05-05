"""KYA Contracts — API endpoints (token-based, sans création de User Frappe).

Architecture :
- Le signataire accède au contrat via un lien magique : /kya-contrat?name=...&token=<HMAC>
- Aucun compte Frappe n'est créé pour le stagiaire.
- Avant signature : confirmation du téléphone (anti-fuite).
- Signature par sections (case "Lu et approuvé" sur chaque section).
- DG accède via token DG distinct.

Endpoints (allow_guest=True car signataire = Guest) :
- send_to_signataire (RH only)
- verify_phone, update_personal_info, mark_section_signed, sign_contract, get_contract_view (Guest+token)
"""
import frappe
import json
import hmac
import time
from frappe import _
from frappe.utils import now_datetime


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _generate_token():
    return frappe.generate_hash(length=48)


def _verify_token(doc, token, role):
    if not token:
        return False
    field = "access_token_signataire" if role == "employe" else "access_token_dg"
    expected = doc.get(field) or ""
    if not expected:
        return False
    return hmac.compare_digest(str(token), str(expected))


def _load_contract_with_token(contract_id, token, role):
    if not frappe.db.exists("KYA Contrat", contract_id):
        frappe.throw(_("Contrat introuvable"), frappe.DoesNotExistError)
    doc = frappe.get_doc("KYA Contrat", contract_id)
    if not _verify_token(doc, token, role):
        frappe.throw(_("Lien invalide ou expiré"), frappe.PermissionError)
    return doc


def _normalize_phone(p):
    if not p:
        return ""
    return "".join(c for c in str(p) if c.isdigit())[-9:]


# ─── 1. RH envoie le contrat au signataire ───────────────────────────────────

@frappe.whitelist()
def send_to_signataire(contract_id):
    if not any(r in frappe.get_roles() for r in ("HR Manager", "System Manager", "Responsable RH")):
        frappe.throw(_("Permission refusée"), frappe.PermissionError)

    doc = frappe.get_doc("KYA Contrat", contract_id)
    if not doc.employee_email:
        frappe.throw(_("L'employé n'a pas d'email enregistré."))
    if not doc.telephone:
        frappe.throw(_("Le numéro de téléphone du signataire est requis avant l'envoi."))

    if not doc.access_token_signataire:
        doc.access_token_signataire = _generate_token()
    sender = frappe.session.user
    if sender and sender != "Guest" and "@" in sender:
        doc.rh_sender_email = sender

    site = frappe.utils.get_url()
    portail_url = f"{site}/kya-contrat?name={doc.name}&token={doc.access_token_signataire}"
    phone_hint = (doc.telephone or "")[-4:] if doc.telephone else "????"

    message = f"""
    <div style="font-family:Arial,sans-serif; max-width:640px; margin:0 auto; border:1px solid #eee; border-radius:6px; overflow:hidden;">
      <div style="background:linear-gradient(135deg,#f7a800 0%,#e07b00 100%); padding:24px; color:#fff; text-align:center;">
        <h2 style="margin:0;">Bienvenue chez KYA-Energy Group</h2>
        <p style="margin:6px 0 0 0; opacity:0.95;">Votre contrat est prêt à être signé en ligne</p>
      </div>
      <div style="padding:24px 28px;">
        <p>Bonjour <b>{doc.employee_name}</b>,</p>
        <p>Nous avons le plaisir de vous proposer un <b>{doc.contract_type}</b> au sein de KYA-Energy Group.</p>
        <p>Référence : <b>{doc.name}</b></p>

        <div style="background:#fff8e7; border-left:4px solid #e07b00; padding:14px 18px; margin:18px 0;">
          <p style="margin:0;"><b>🔒 Aucun mot de passe à mémoriser.</b><br>
          Le lien ci-dessous vous donne accès direct à votre contrat. Pour des raisons de sécurité,
          il vous sera demandé de <b>confirmer votre numéro de téléphone</b>
          (se terminant par <code style="background:#fff;padding:2px 6px;">…{phone_hint}</code>) avant de signer.</p>
        </div>

        <h3 style="color:#e07b00; margin-top:24px;">Étapes</h3>
        <ol style="line-height:1.8;">
          <li>Cliquez sur le bouton ci-dessous</li>
          <li><b>Confirmez votre numéro de téléphone</b> (les 9 chiffres)</li>
          <li>Complétez vos informations personnelles (Père, Mère, Domicile, Date de naissance)</li>
          <li>Lisez chaque section et cochez <b>« Lu et approuvé »</b> sur chacune</li>
          <li>Apposez votre signature (en la <b>dessinant</b> ou en <b>important une image</b> PNG/JPG)</li>
          <li>Cliquez sur <b>« Signer et Soumettre »</b></li>
        </ol>

        <p style="text-align:center; margin:30px 0;">
          <a href="{portail_url}" style="display:inline-block; background:#e07b00; color:#fff; padding:14px 32px; text-decoration:none; border-radius:6px; font-weight:600;">→ Accéder à mon contrat</a>
        </p>

        <p style="font-size:12px; color:#888; word-break:break-all;">Si le bouton ne fonctionne pas :<br>{portail_url}</p>

        <p style="font-size:13px; color:#666;">Une fois signé, le contrat sera transmis au Directeur Général. Vous recevrez la version finale en PDF par email.</p>
        <p>Pour toute question : <a href="mailto:rh@kya-energy.com">rh@kya-energy.com</a></p>
        <p style="margin-top:30px;">Bien cordialement,<br><b>Le Service des Ressources Humaines</b><br>KYA-Energy Group</p>
      </div>
    </div>
    """
    frappe.sendmail(
        recipients=[doc.employee_email],
        subject=f"Votre contrat {doc.contract_type} — KYA-Energy Group ({doc.name})",
        message=message,
        now=False,
    )

    doc.workflow_state = "En attente Signature Salarié"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"ok": True, "url": portail_url}


# ─── 2. Confirmation téléphone ────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def verify_phone(contract_id, token, phone):
    doc = _load_contract_with_token(contract_id, token, "employe")
    expected = _normalize_phone(doc.telephone)
    given = _normalize_phone(phone)
    if not expected or not given or expected != given:
        time.sleep(1.5)  # anti-bruteforce léger
        frappe.throw(_("Numéro de téléphone incorrect."))
    doc.db_set("phone_confirmed", 1, update_modified=False)
    frappe.db.commit()
    return {"ok": True}


# ─── 3. Mise à jour infos perso ───────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def update_personal_info(contract_id, token, data):
    doc = _load_contract_with_token(contract_id, token, "employe")
    if not doc.phone_confirmed:
        frappe.throw(_("Confirmez d'abord votre numéro de téléphone."))
    if doc.workflow_state not in ("En attente Signature Salarié", "Brouillon"):
        frappe.throw(_("Le contrat n'est plus modifiable."))
    if isinstance(data, str):
        data = json.loads(data)
    allowed = {"telephone", "date_naissance", "domicile", "filiation_pere", "filiation_mere"}
    for k, v in (data or {}).items():
        if k in allowed:
            doc.set(k, v or None)
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"ok": True}


# ─── 4. Marquer une section comme lue/approuvée ───────────────────────────────

@frappe.whitelist(allow_guest=True)
def mark_section_signed(contract_id, token, section_id, role="employe"):
    doc = _load_contract_with_token(contract_id, token, role)
    if role == "employe" and not doc.phone_confirmed:
        frappe.throw(_("Confirmez d'abord votre numéro de téléphone."))
    sections = json.loads(doc.sections_signees or "{}")
    sections.setdefault(role, [])
    if section_id not in sections[role]:
        sections[role].append(section_id)
    doc.db_set("sections_signees", json.dumps(sections), update_modified=False)
    frappe.db.commit()
    return {"ok": True, "sections": sections.get(role, [])}


# ─── 5. Signature finale ──────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def sign_contract(contract_id, token, signature_data, role="employe", total_sections=None):
    doc = _load_contract_with_token(contract_id, token, role)

    if total_sections:
        try:
            total_sections = int(total_sections)
        except Exception:
            total_sections = 0
        signed = json.loads(doc.sections_signees or "{}").get(role, [])
        if total_sections > 0 and len(signed) < total_sections:
            frappe.throw(_("Vous devez cocher 'Lu et approuvé' sur chaque section ({0}/{1}).").format(len(signed), total_sections))

    if role == "employe":
        if not doc.phone_confirmed:
            frappe.throw(_("Confirmez d'abord votre numéro de téléphone."))
        if doc.workflow_state != "En attente Signature Salarié":
            frappe.throw(_("Le contrat n'est pas en attente de votre signature."))
        doc.signature_employe = signature_data
        doc.contrat_lu = 1
        doc.nom_signe_employe = doc.employee_name
        doc.date_signature_employe = now_datetime()
        doc.workflow_state = "Signé Salarié"
        if not doc.access_token_dg:
            doc.access_token_dg = _generate_token()
        doc.flags.ignore_permissions = True
        doc.save()
        _notify_rh_after_signataire(doc)
    elif role == "dg":
        if doc.workflow_state != "En attente DG":
            frappe.throw(_("Le contrat n'est pas en attente de la signature DG."))
        doc.signature_dg = signature_data
        doc.date_signature_dg = now_datetime()
        doc.workflow_state = "Validé"
        doc.flags.ignore_permissions = True
        doc.save()
        try:
            doc.submit()
        except Exception:
            frappe.log_error(frappe.get_traceback(), "KYA Contrat submit")
    else:
        frappe.throw(_("Rôle invalide"))

    frappe.db.commit()
    return {"ok": True, "state": doc.workflow_state}


# ─── 6. Notifications après chaque signature ────────────────────────────────

def _notify_rh_after_signataire(doc):
    """Après signature du salarié/stagiaire : notifier la RH (gateway).
    La RH cliquera ensuite l'action workflow 'Soumettre au DG' qui déclenchera
    `notify_dg_after_rh_gateway` via le hook on_update du controller.
    """
    rh_recipients = []
    if doc.rh_sender_email:
        rh_recipients.append(doc.rh_sender_email)
    try:
        rh_email = frappe.db.get_single_value("KYA Dashboard Settings", "rh_email")
        if rh_email and rh_email not in rh_recipients:
            rh_recipients.append(rh_email)
    except Exception:
        pass
    for u in frappe.get_all("Has Role", filters={"role": "Responsable RH", "parenttype": "User"}, fields=["parent"]):
        em = frappe.db.get_value("User", u.parent, "email")
        if em and em not in rh_recipients:
            rh_recipients.append(em)
    if not rh_recipients:
        return
    site = frappe.utils.get_url()
    desk_url = f"{site}/app/kya-contrat/{doc.name}"
    frappe.sendmail(
        recipients=rh_recipients,
        subject=f"✅ {doc.employee_name} a signé son contrat — À soumettre au DG",
        message=f"""
        <div style="font-family:Arial,sans-serif; max-width:640px; margin:0 auto; border:1px solid #eee; border-radius:6px; overflow:hidden;">
          <div style="background:linear-gradient(135deg,#1a5276 0%,#2980b9 100%); padding:20px; color:#fff;">
            <h2 style="margin:0;">Contrat signé par le salarié</h2>
          </div>
          <div style="padding:24px 28px;">
            <p>Bonjour,</p>
            <p><b>{doc.employee_name}</b> a signé son contrat de <b>{doc.contract_type}</b>
            le {frappe.format_value(doc.date_signature_employe, {'fieldtype':'Datetime'})}.</p>
            <p>Veuillez relire le contrat puis cliquer sur l'action <b>« Soumettre au DG »</b>
            pour déclencher la co-signature du Directeur Général.</p>
            <p style="text-align:center; margin:24px 0;">
              <a href="{desk_url}" style="display:inline-block; background:#1a5276; color:#fff; padding:12px 26px; text-decoration:none; border-radius:5px; font-weight:600;">→ Ouvrir le contrat</a>
            </p>
            <p style="font-size:13px; color:#666;">Référence : <b>{doc.name}</b></p>
          </div>
        </div>
        """,
        now=False,
    )


def notify_dg_after_rh_gateway(doc, method=None):
    """Hook on_update : quand l'état passe à 'En attente DG' (RH a cliqué
    'Soumettre au DG'), envoyer le lien magique du portail au DG.
    """
    if doc.workflow_state != "En attente DG":
        return
    if doc.get("_dg_notified"):
        return
    if not doc.access_token_dg:
        doc.access_token_dg = _generate_token()
        doc.db_set("access_token_dg", doc.access_token_dg, update_modified=False)
    site = frappe.utils.get_url()
    url = f"{site}/kya-contrat?name={doc.name}&token={doc.access_token_dg}"
    dg_emails = []
    for u in frappe.get_all("Has Role", filters={"role": "Directeur Général", "parenttype": "User"}, fields=["parent"]):
        em = frappe.db.get_value("User", u.parent, "email")
        if em:
            dg_emails.append(em)
    if not dg_emails:
        return
    frappe.sendmail(
        recipients=dg_emails,
        subject=f"✍️ Co-signature requise — Contrat {doc.contract_type} de {doc.employee_name}",
        message=f"""
        <div style="font-family:Arial,sans-serif; max-width:640px; margin:0 auto; border:1px solid #eee; border-radius:6px; overflow:hidden;">
          <div style="background:linear-gradient(135deg,#1a5276 0%,#2980b9 100%); padding:20px; color:#fff;">
            <h2 style="margin:0;">Co-signature DG requise</h2>
          </div>
          <div style="padding:24px 28px;">
            <p>Monsieur le Directeur Général,</p>
            <p>La RH a transmis pour co-signature le contrat de <b>{doc.contract_type}</b>
            de <b>{doc.employee_name}</b>.</p>
            <p>Le salarié a déjà signé le {frappe.format_value(doc.date_signature_employe, {'fieldtype':'Datetime'})}.</p>
            <p style="text-align:center; margin:24px 0;">
              <a href="{url}" style="display:inline-block; background:#1a5276; color:#fff; padding:12px 26px; text-decoration:none; border-radius:5px; font-weight:600;">→ Accéder au contrat</a>
            </p>
            <p style="font-size:13px; color:#666;">Référence : <b>{doc.name}</b></p>
          </div>
        </div>
        """,
        now=False,
    )


# ─── 7. Récupération du contrat pour le portail ──────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_contract_view(contract_id, token):
    if not frappe.db.exists("KYA Contrat", contract_id):
        frappe.throw(_("Contrat introuvable"), frappe.DoesNotExistError)
    doc = frappe.get_doc("KYA Contrat", contract_id)
    role = None
    if _verify_token(doc, token, "employe"):
        role = "employe"
    elif _verify_token(doc, token, "dg"):
        role = "dg"
    else:
        frappe.throw(_("Lien invalide ou expiré"), frappe.PermissionError)

    return {
        "doc": doc.as_dict(),
        "role": role,
        "phone_confirmed": bool(doc.phone_confirmed),
        "sections_signees": json.loads(doc.sections_signees or "{}").get(role, []),
        "can_sign": (role == "employe" and doc.workflow_state == "En attente Signature Salarié") or
                    (role == "dg" and doc.workflow_state == "En attente DG"),
        "is_finalized": doc.workflow_state in ("Validé", "RH (revue)", "Archivé"),
    }
