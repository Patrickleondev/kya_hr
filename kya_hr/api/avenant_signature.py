# -*- coding: utf-8 -*-
"""Avenant au contrat — signature EN LIGNE (portail token, comme KYA Contrat).

L'employé(e) reçoit un lien magique /kya-avenant?name=...&token=<HMAC>, confirme
son identité (téléphone, 8 chiffres), lit l'avenant et signe « lu et approuvé »
de son côté. La RH le transmet ensuite au DG, qui co-signe (portail ou fiche).
Aucun compte Frappe n'est créé pour le signataire.

Ce module RÉUTILISE délibérément les briques éprouvées de `kya_contracts`
(génération de jeton, rapprochement téléphone par suffixe, nettoyage du HTML
d'impression pour le logo) : une seule source de vérité, pas de divergence.

Endpoints Guest (le signataire est un invité ; le jeton fait foi) :
- verify_phone, sign_avenant, get_avenant_view, download_final_pdf
"""
import base64
import hmac
import json
import re
import time

import frappe
from frappe import _
from frappe.utils import now_datetime

# Briques partagées avec le contrat (source unique).
from kya_hr.api.kya_contracts import (
    _generate_token,
    _normalize_mention,
    _normalize_phone,
    _phone_matches,
    _request_ip,
    _sanitize_contract_pdf_html,
    _contact_rh,
    _mailto,
)

DT = "Avenant Contrat KYA"
PRINT_FORMAT = "Avenant Contrat KYA"
EMPLOYEE_SIGNATURE_STATES = ("En attente Signature Salarié",)
FINAL_STATES = ("Signé",)


# ─── Helpers token ────────────────────────────────────────────────────────────

def _verify_token(doc, token, role):
    if not token:
        return False
    field = "access_token_signataire" if role == "employe" else "access_token_dg"
    expected = doc.get(field) or ""
    if not expected:
        return False
    return hmac.compare_digest(str(token), str(expected))


def _load_with_token(name, token, role):
    if not frappe.db.exists(DT, name):
        frappe.throw(_("Avenant introuvable"), frappe.DoesNotExistError)
    doc = frappe.get_doc(DT, name)
    if not _verify_token(doc, token, role):
        frappe.throw(_("Lien invalide ou expiré"), frappe.PermissionError)
    return doc


# ─── 1. RH envoie l'avenant au signataire (déclenché par le workflow) ─────────

def send_signataire_email(doc):
    """Envoie au signataire le lien magique. Appelé quand l'avenant ENTRE dans
    'En attente Signature Salarié' (action workflow « Envoyer au salarié » ou
    bouton RH). Ne lève jamais : ne doit pas bloquer le workflow. Retourne l'URL
    du portail, ou None si l'email manque."""
    if not doc.employee_email:
        return None
    if not doc.access_token_signataire:
        token = _generate_token()
        doc.access_token_signataire = token
        try:
            doc.db_set("access_token_signataire", token, update_modified=False)
        except Exception:
            pass

    site = frappe.utils.get_url()
    portail_url = f"{site}/kya-avenant?name={doc.name}&token={doc.access_token_signataire}"
    phone_hint = (_normalize_phone(doc.telephone)[-4:] if doc.telephone else "") or "????"
    _rh_nom, _rh_email = _contact_rh(doc)
    contact_rh_html = _mailto(_rh_nom, _rh_email or "rh@kya-energy.com")
    objet = doc.objet or "avenant à votre contrat de travail"

    message = f"""
    <div style="font-family:Arial,sans-serif; max-width:640px; margin:0 auto; border:1px solid #eee; border-radius:6px; overflow:hidden;">
      <div style="background:linear-gradient(135deg,#f7a800 0%,#e07b00 100%); padding:24px; color:#fff; text-align:center;">
        <h2 style="margin:0;">KYA-Energy Group</h2>
        <p style="margin:6px 0 0 0; opacity:0.95;">Un avenant à votre contrat est prêt à être signé en ligne</p>
      </div>
      <div style="padding:24px 28px;">
        <p>Bonjour <b>{doc.beneficiaire_nom or ''}</b>,</p>
        <p>La Direction des Ressources Humaines vous transmet, pour signature, un
        <b>avenant à votre contrat de travail</b> ({objet}).</p>
        <p>Référence : <b>{doc.name}</b></p>

        <div style="background:#fff8e7; border-left:4px solid #e07b00; padding:14px 18px; margin:18px 0;">
          <p style="margin:0;"><b>🔒 Aucun mot de passe à mémoriser.</b><br>
          Le lien ci-dessous vous donne accès direct au document. Pour des raisons de sécurité,
          il vous sera demandé de <b>confirmer votre numéro de téléphone</b>
          (se terminant par <code style="background:#fff;padding:2px 6px;">…{phone_hint}</code>) avant de signer.</p>
        </div>

        <h3 style="color:#e07b00; margin-top:24px;">Étapes</h3>
        <ol style="line-height:1.8;">
          <li>Cliquez sur le bouton ci-dessous.</li>
          <li><b>Si une page (souvent sombre) vous demande un « code » à 6 chiffres</b>,
              tapez <b><code style="background:#fff;padding:2px 6px;font-size:15px;">1 1 1 1 1 1</code></b>
              (le chiffre 1, six fois) puis continuez.</li>
          <li><b>Confirmez votre numéro de téléphone</b> (celui communiqué aux RH).
              Numéro togolais : vos <b>8 chiffres</b> suffisent (ex.
              <code style="background:#fff;padding:2px 6px;">90123456</code>).</li>
          <li>Lisez l'avenant, saisissez la mention <b>« lu et approuvé »</b>, apposez votre signature.</li>
          <li>Cliquez sur <b>« Signer »</b>.</li>
        </ol>

        <p style="text-align:center; margin:30px 0;">
          <a href="{portail_url}" style="display:inline-block; background:#e07b00; color:#fff; padding:14px 32px; text-decoration:none; border-radius:6px; font-weight:600;">→ Accéder à mon avenant</a>
        </p>

        <p style="font-size:12px; color:#888; word-break:break-all;">Si le bouton ne fonctionne pas :<br>{portail_url}</p>

        <p style="font-size:13px; color:#666;">Une fois signé, l'avenant sera transmis au Directeur Général. Vous recevrez la version finale en PDF par email.</p>

        <div style="background:#f4f6f8; border-left:4px solid #e07b00; padding:12px 16px; margin:18px 0; font-size:13px; color:#333;">
          <b>🙋 Bloqué(e) à une étape ?</b> Contactez le service des Ressources Humaines : {contact_rh_html}.<br>
          <span style="color:#5a6470;">Précisez la référence <b>{doc.name}</b> dans votre message.</span>
        </div>
        <p style="margin-top:30px;">Bien cordialement,<br><b>Le Service des Ressources Humaines</b><br>KYA-Energy Group</p>
      </div>
    </div>
    """
    frappe.sendmail(
        recipients=[doc.employee_email],
        subject=f"Avenant à votre contrat — KYA-Energy Group ({doc.name})",
        message=message,
        reference_doctype=DT,
        reference_name=doc.name,
        now=False,
    )
    return portail_url


@frappe.whitelist()
def send_to_signataire(name):
    """Bouton RH : (ré)envoie le lien au signataire + met l'état à
    'En attente Signature Salarié'. L'envoi passe par send_signataire_email."""
    if not any(r in frappe.get_roles() for r in ("HR Manager", "System Manager", "Responsable RH", "HR User")):
        frappe.throw(_("Permission refusée"), frappe.PermissionError)
    doc = frappe.get_doc(DT, name)
    if not doc.employee_email:
        frappe.throw(_("L'email du/de la signataire est requis avant l'envoi."))
    if not doc.telephone:
        frappe.throw(_("Le numéro de téléphone du/de la signataire est requis avant l'envoi."))

    sender = frappe.session.user
    if sender and sender != "Guest" and "@" in sender:
        doc.rh_sender_email = sender

    portail_url = send_signataire_email(doc)
    doc.flags.signataire_email_sent = True
    doc.workflow_state = "En attente Signature Salarié"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"ok": True, "url": portail_url}


# ─── 2. Confirmation téléphone ────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def verify_phone(name, token, phone):
    doc = _load_with_token(name, token, "employe")
    if not _phone_matches(doc.telephone, phone):
        time.sleep(1.5)
        frappe.throw(_(
            "Numéro de téléphone incorrect. Saisissez le numéro communiqué aux "
            "Ressources Humaines, par exemple 90123456."
        ))
    doc.db_set("phone_confirmed", 1, update_modified=False)
    frappe.db.commit()
    return {"ok": True}


# ─── 3. Signature ─────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def sign_avenant(name, token, signature_data, role="employe", mention_text=None, mention_image=None):
    doc = _load_with_token(name, token, role)
    # Le jeton fait foi. La signature CHANGE le workflow_state → validation
    # workflow (get_transitions/check_permission) qui refuserait le Guest malgré
    # ignore_permissions. On élève au contexte système pour la mutation.
    _prev = frappe.session.user
    frappe.set_user("Administrator")
    try:
        return _sign_body(doc, signature_data, role, mention_text, mention_image)
    finally:
        frappe.set_user(_prev)


def _sign_body(doc, signature_data, role, mention_text, mention_image):
    if role == "employe":
        if not doc.phone_confirmed:
            frappe.throw(_("Confirmez d'abord votre numéro de téléphone."))
        if doc.workflow_state not in EMPLOYEE_SIGNATURE_STATES:
            frappe.throw(_("L'avenant n'est pas en attente de votre signature."))
        normalized = _normalize_mention(mention_text)
        if "lu" not in normalized or "approuv" not in normalized:
            frappe.throw(_("Veuillez saisir la mention « lu et approuvé » avant de signer."))
        doc.mention_lu_approuve_text = mention_text
        if mention_image:
            doc.mention_lu_approuve_image = mention_image
        doc.date_mention = now_datetime()
        doc.signature_employe = signature_data
        doc.nom_signe_employe = doc.beneficiaire_nom
        doc.date_signature_employe = now_datetime()
        doc.signature_employe_ip = _request_ip()
        doc.workflow_state = "Signé Salarié"
        if not doc.access_token_dg:
            doc.access_token_dg = _generate_token()
        doc.flags.ignore_permissions = True
        doc.save()
        _notify_rh_after_signataire(doc)
    elif role == "dg":
        if doc.workflow_state != "En attente DG":
            frappe.throw(_("L'avenant n'est pas en attente de la signature du DG."))
        # Le DG dessine sa signature dans le portail : on l'utilise telle quelle
        # (et non l'estampille enregistrée).
        doc.signature_dg = signature_data
        doc.utiliser_signature_enregistree = 0
        doc.date_signature_dg = now_datetime()
        doc.signature_dg_ip = _request_ip()
        doc.workflow_state = "Signé"
        doc.flags.ignore_permissions = True
        doc.save()
        try:
            doc.submit()
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Avenant KYA submit (portail DG)")
    else:
        frappe.throw(_("Rôle invalide"))

    frappe.db.commit()
    return {"ok": True, "state": doc.workflow_state}


# ─── 4. Notifications ─────────────────────────────────────────────────────────

def _notify_rh_after_signataire(doc):
    """Après signature du salarié : notifier la RH (elle cliquera « Soumettre au DG »)."""
    recipients = []
    if doc.rh_sender_email:
        recipients.append(doc.rh_sender_email)
    try:
        rh_email = frappe.db.get_single_value("KYA Dashboard Settings", "rh_email")
        if rh_email and rh_email not in recipients:
            recipients.append(rh_email)
    except Exception:
        pass
    for u in frappe.get_all("Has Role", filters={"role": "Responsable RH", "parenttype": "User"}, fields=["parent"]):
        em = frappe.db.get_value("User", u.parent, "email")
        if em and em not in recipients:
            recipients.append(em)
    if not recipients:
        return
    site = frappe.utils.get_url()
    desk_url = f"{site}/app/avenant-contrat-kya/{doc.name}"
    frappe.sendmail(
        recipients=recipients,
        subject=f"✅ {doc.beneficiaire_nom} a signé son avenant — À soumettre au DG",
        message=f"""
        <div style="font-family:Arial,sans-serif; max-width:640px; margin:0 auto; border:1px solid #eee; border-radius:6px; overflow:hidden;">
          <div style="background:linear-gradient(135deg,#1a5276 0%,#2980b9 100%); padding:20px; color:#fff;">
            <h2 style="margin:0;">Avenant signé par le salarié</h2>
          </div>
          <div style="padding:24px 28px;">
            <p>Bonjour,</p>
            <p><b>{doc.beneficiaire_nom}</b> a signé son avenant
            le {frappe.format_value(doc.date_signature_employe, {'fieldtype':'Datetime'})}.</p>
            <p>Veuillez relire l'avenant puis cliquer sur l'action <b>« Soumettre au DG »</b>
            pour déclencher la co-signature du Directeur Général.</p>
            <p style="text-align:center; margin:24px 0;">
              <a href="{desk_url}" style="display:inline-block; background:#1a5276; color:#fff; padding:12px 26px; text-decoration:none; border-radius:5px; font-weight:600;">→ Ouvrir l'avenant</a>
            </p>
            <p style="font-size:13px; color:#666;">Référence : <b>{doc.name}</b></p>
          </div>
        </div>
        """,
        reference_doctype=DT, reference_name=doc.name, now=False,
    )


def notify_dg_after_rh_gateway(doc, method=None):
    """Hook : quand l'état passe à 'En attente DG' (RH a cliqué « Soumettre au
    DG »), envoyer le lien magique du portail au DG."""
    if doc.workflow_state != "En attente DG":
        return
    if not doc.access_token_dg:
        doc.access_token_dg = _generate_token()
        doc.db_set("access_token_dg", doc.access_token_dg, update_modified=False)
    site = frappe.utils.get_url()
    url = f"{site}/kya-avenant?name={doc.name}&token={doc.access_token_dg}"
    desk_url = f"{site}/app/avenant-contrat-kya/{doc.name}"
    dg_emails = []
    for u in frappe.get_all("Has Role", filters={"role": "Directeur Général", "parenttype": "User"}, fields=["parent"]):
        em = frappe.db.get_value("User", u.parent, "email")
        if em:
            dg_emails.append(em)
    if not dg_emails:
        return
    signe_le = frappe.format_value(doc.date_signature_employe, {'fieldtype': 'Datetime'}) if doc.date_signature_employe else ""
    frappe.sendmail(
        recipients=dg_emails,
        subject=f"✍️ Co-signature requise — Avenant de {doc.beneficiaire_nom}",
        message=f"""
        <div style="font-family:Arial,sans-serif; max-width:640px; margin:0 auto; border:1px solid #eee; border-radius:6px; overflow:hidden;">
          <div style="background:linear-gradient(135deg,#1a5276 0%,#2980b9 100%); padding:20px; color:#fff;">
            <h2 style="margin:0;">Co-signature DG requise</h2>
          </div>
          <div style="padding:24px 28px;">
            <p>Monsieur le Directeur Général,</p>
            <p>La RH a transmis pour co-signature l'avenant au contrat de
            <b>{doc.beneficiaire_nom}</b>{f' (signé par le salarié le {signe_le})' if signe_le else ''}.</p>
            <p>Vous pouvez co-signer <b>en ligne</b> via le lien ci-dessous, ou depuis la fiche.</p>
            <p style="text-align:center; margin:24px 0;">
              <a href="{url}" style="display:inline-block; background:#1a5276; color:#fff; padding:12px 26px; text-decoration:none; border-radius:5px; font-weight:600;">→ Co-signer en ligne</a>
            </p>
            <p style="font-size:12px; color:#888;">Ou depuis le bureau : <a href="{desk_url}">{desk_url}</a></p>
            <p style="font-size:13px; color:#666;">Référence : <b>{doc.name}</b></p>
          </div>
        </div>
        """,
        reference_doctype=DT, reference_name=doc.name, now=False,
    )


# ─── 5. Vue portail + téléchargement PDF ─────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_avenant_view(name, token):
    if not frappe.db.exists(DT, name):
        frappe.throw(_("Avenant introuvable"), frappe.DoesNotExistError)
    doc = frappe.get_doc(DT, name)
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
        "can_sign": (role == "employe" and doc.workflow_state in EMPLOYEE_SIGNATURE_STATES) or
                    (role == "dg" and doc.workflow_state == "En attente DG"),
        "is_finalized": doc.workflow_state in FINAL_STATES,
    }


@frappe.whitelist(allow_guest=True)
def download_final_pdf(name, token):
    if not frappe.db.exists(DT, name):
        frappe.throw(_("Avenant introuvable"), frappe.DoesNotExistError)
    doc = frappe.get_doc(DT, name)
    if not (_verify_token(doc, token, "employe") or _verify_token(doc, token, "dg")):
        frappe.throw(_("Lien invalide ou expiré"), frappe.PermissionError)
    if doc.workflow_state not in FINAL_STATES:
        frappe.throw(_("Le PDF final sera disponible après la co-signature du DG."))

    if not doc.pdf_final:
        try:
            doc._generate_and_attach_pdf()
            frappe.db.commit()
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Avenant KYA — PDF à la demande")
    if not doc.pdf_final:
        frappe.throw(_("PDF final introuvable."))

    file_name = frappe.db.get_value("File", {"file_url": doc.pdf_final}, "name")
    if not file_name:
        frappe.throw(_("Fichier PDF introuvable."))
    file_doc = frappe.get_doc("File", file_name)
    frappe.local.response.filename = file_doc.file_name or f"Avenant_{doc.name}.pdf"
    frappe.local.response.filecontent = file_doc.get_content()
    frappe.local.response.type = "download"


def render_avenant_pdf_html(doc):
    """HTML d'impression prêt pour wkhtmltopdf (logo inline, chrome retiré)."""
    _prev = frappe.session.user
    try:
        frappe.set_user("Administrator")
        html = frappe.get_print(DT, doc.name, print_format=PRINT_FORMAT, no_letterhead=1)
    finally:
        frappe.set_user(_prev)
    return _sanitize_contract_pdf_html(html)
