# -*- coding: utf-8 -*-
"""Portail de signature en ligne du Contrat Stage Immersion KYA (sans compte).

Mirroir du flux KYA Contrat (api/kya_contracts.py) mais à 3 signataires
externes/internes avant le DG : stagiaire -> maître de stage -> garant
(tuteur légal ou établissement, optionnel) -> DG (inchangé, toujours signé
depuis le Desk).

Circuit :
  Brouillon
  --RH "Envoyer au stagiaire"--> Envoyé Stagiaire
  --stagiaire signe--> Envoyé Maître Stage
  --maître signe--> Envoyé Garant (si garant_email renseigné) sinon En attente DG
  --garant signe--> En attente DG
  --DG signe (Desk, inchangé)--> Signé

Chemin manuel inchangé : si la RH n'utilise pas "Envoyer au stagiaire" (élève
sans e-mail, cas "sans_email"), elle continue d'utiliser "Soumettre au DG"
directement depuis Brouillon, comme avant — le circuit digital est un ajout,
pas un remplacement obligatoire.
"""
import hmac
import json
import time
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import now_datetime

_ROLE_TOKEN_FIELD = {
    "stagiaire": "access_token_stagiaire",
    "maitre": "access_token_maitre",
    "garant": "access_token_garant",
}
_ROLE_SIGNATURE_FIELD = {
    "stagiaire": "signature_stagiaire",
    "maitre": "signature_maitre",
    "garant": "signature_garant",
}
_ROLE_STATE = {
    "stagiaire": "Envoyé Stagiaire",
    "maitre": "Envoyé Maître Stage",
    "garant": "Envoyé Garant",
}
_PHONE_MIN_COMMUN = 8


def _generate_token():
    return frappe.generate_hash(length=48)


def _phone_digits(p):
    if not p:
        return ""
    d = "".join(c for c in str(p) if c.isdigit())
    if d.startswith("00"):
        d = d[2:]
    return d.lstrip("0")


def _phone_matches(stocke, saisi):
    a, b = _phone_digits(stocke), _phone_digits(saisi)
    if not a or not b:
        return False
    if a == b:
        return True
    court, long_ = (a, b) if len(a) <= len(b) else (b, a)
    seuil = min(_PHONE_MIN_COMMUN, len(a))
    return len(court) >= seuil and long_.endswith(court)


def _verify_token(doc, token, role):
    field = _ROLE_TOKEN_FIELD.get(role)
    if not field or not token:
        return False
    expected = doc.get(field) or ""
    if not expected:
        return False
    return hmac.compare_digest(str(token), str(expected))


def _load_with_token(contract_id, token, role):
    if not frappe.db.exists("Contrat Stage Immersion KYA", contract_id):
        frappe.throw(_("Contrat introuvable"), frappe.DoesNotExistError)
    doc = frappe.get_doc("Contrat Stage Immersion KYA", contract_id)
    if not _verify_token(doc, token, role):
        frappe.throw(_("Lien invalide ou expiré"), frappe.PermissionError)
    return doc


def _rh_emails():
    seen, out = set(), []
    for role in ("Responsable RH", "HR Manager", "HR User"):
        for user in frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"):
            d = frappe.db.get_value("User", user, ["email", "enabled"], as_dict=True)
            if d and d.enabled and d.email and d.email not in seen:
                seen.add(d.email)
                out.append(d.email)
    return out


def _pangolin_note():
    return (
        "<div style='background:#fff8e7;border-left:4px solid #e07b00;padding:12px 16px;"
        "margin:16px 0;font-size:13px;color:#333;'>"
        "🔒 <b>Aucun compte à créer.</b> Ouvrez simplement le lien ci-dessous. "
        "<b>Si une page (souvent sombre) vous demande un « code » à 6 chiffres</b>, "
        "tapez <b>1 1 1 1 1 1</b> (le chiffre 1, six fois) puis continuez."
        "</div>"
    )


def _portal_link(name, token):
    return f"{frappe.utils.get_url()}/contrat-immersion?name={quote(name)}&token={quote(token)}"


def _send(recipients, subject, body_html, doc_name=None):
    recipients = [r for r in dict.fromkeys(recipients) if r]
    if not recipients:
        return
    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=body_html,
                         reference_doctype="Contrat Stage Immersion KYA", reference_name=doc_name, now=False)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "contrat_immersion_signature: notif")


# ── 1. RH démarre le circuit digital ────────────────────────────────────────

@frappe.whitelist()
def envoyer_stagiaire(contract_id):
    """Bouton RH : envoie le lien de lecture/signature au stagiaire et bascule
    le contrat dans le circuit digital."""
    if not any(r in frappe.get_roles() for r in
               ("Responsable RH", "HR Manager", "HR User", "System Manager")):
        frappe.throw(_("Permission refusée"), frappe.PermissionError)

    doc = frappe.get_doc("Contrat Stage Immersion KYA", contract_id)
    if doc.sans_email:
        frappe.throw(_("Ce/cette stagiaire est marqué(e) « sans e-mail » — utilisez le circuit papier (Soumettre au DG)."))
    if not doc.email:
        frappe.throw(_("L'e-mail du/de la stagiaire est requis pour l'envoi en ligne."))
    if (doc.workflow_state or "Brouillon") != "Brouillon":
        frappe.throw(_("Ce contrat n'est plus au stade brouillon."))

    if not doc.access_token_stagiaire:
        doc.access_token_stagiaire = _generate_token()
    doc.workflow_state = "Envoyé Stagiaire"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()

    link = _portal_link(doc.name, doc.access_token_stagiaire)
    subject = f"[KYA] Votre contrat de stage d'immersion — à lire et signer ({doc.name})"
    body = (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
        "<div style='background:linear-gradient(135deg,#0e7c4a,#16a34a);padding:20px;"
        "border-radius:8px 8px 0 0;color:#fff;'><h2 style='margin:0;'>Votre contrat de stage d'immersion</h2></div>"
        "<div style='padding:20px 24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;'>"
        f"<p>Bonjour <b>{doc.beneficiaire_nom or ''}</b>,</p>"
        "<p>Votre contrat de stage d'immersion (découverte) chez KYA-Energy Group est prêt. "
        "Ouvrez le lien ci-dessous, lisez chaque partie du contrat, puis apposez votre signature.</p>"
        f"<p style='text-align:center;margin:24px 0;'><a href='{link}' style='background:#0e7c4a;"
        "color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:700;'>"
        "→ Lire et signer mon contrat</a></p>"
        f"{_pangolin_note()}"
        "<p style='font-size:13px;color:#666;'>Une fois signé, votre maître de stage puis, le cas échéant, "
        "votre établissement/tuteur seront invités à leur tour, avant la signature du Directeur Général.</p>"
        f"<p style='font-size:12px;color:#888;'>Référence : {doc.name}</p></div></div>"
    )
    _send([doc.email], subject, body, doc.name)
    return {"ok": True, "workflow_state": doc.workflow_state}


# ── 2. Confirmation téléphone (stagiaire uniquement) ────────────────────────

@frappe.whitelist(allow_guest=True)
def verify_phone(contract_id, token, phone):
    doc = _load_with_token(contract_id, token, "stagiaire")
    if not _phone_matches(doc.telephone, phone):
        time.sleep(1.5)
        frappe.throw(_("Numéro de téléphone incorrect. Saisissez le numéro communiqué aux Ressources Humaines."))
    doc.db_set("phone_confirmed_stagiaire", 1, update_modified=False)
    frappe.db.commit()
    return {"ok": True}


# ── 3. Sections lues/approuvées ──────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def mark_section_signed(contract_id, token, role, section_id):
    if role not in _ROLE_TOKEN_FIELD:
        frappe.throw(_("Rôle invalide."))
    doc = _load_with_token(contract_id, token, role)
    if role == "stagiaire" and not doc.phone_confirmed_stagiaire:
        frappe.throw(_("Confirmez d'abord votre numéro de téléphone."))
    sections = json.loads(doc.sections_signees or "{}")
    sections.setdefault(role, [])
    if section_id not in sections[role]:
        sections[role].append(section_id)
    doc.db_set("sections_signees", json.dumps(sections), update_modified=False)
    frappe.db.commit()
    return {"ok": True, "sections": sections.get(role, [])}


# ── 4. Garant (tuteur légal) : saisie de ses propres informations ──────────

@frappe.whitelist(allow_guest=True)
def update_garant_info(contract_id, token, data):
    doc = _load_with_token(contract_id, token, "garant")
    if doc.workflow_state != "Envoyé Garant":
        frappe.throw(_("Cette étape n'est plus modifiable."))
    if isinstance(data, str):
        data = json.loads(data)
    allowed = {"garant_nom", "garant_qualite"}
    for k, v in (data or {}).items():
        if k in allowed:
            doc.set(k, v or None)
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"ok": True}


# ── 5. Signature ─────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def signer(contract_id, token, role, signature_data, total_sections=None):
    if role not in _ROLE_TOKEN_FIELD:
        frappe.throw(_("Rôle invalide."))
    doc = _load_with_token(contract_id, token, role)
    _prev_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        return _signer_body(doc, role, signature_data, total_sections)
    finally:
        frappe.set_user(_prev_user)


def _signer_body(doc, role, signature_data, total_sections):
    if role == "stagiaire" and not doc.phone_confirmed_stagiaire:
        frappe.throw(_("Confirmez d'abord votre numéro de téléphone."))
    if doc.workflow_state != _ROLE_STATE[role]:
        frappe.throw(_("Ce contrat n'est pas en attente de votre signature."))
    if total_sections:
        try:
            total_sections = int(total_sections)
        except Exception:
            total_sections = 0
        signed = json.loads(doc.sections_signees or "{}").get(role, [])
        if total_sections > 0 and len(signed) < total_sections:
            frappe.throw(_("Veuillez cocher « Lu et approuvé » sur chaque section ({0}/{1}).").format(len(signed), total_sections))

    doc.set(_ROLE_SIGNATURE_FIELD[role], signature_data)

    if role == "stagiaire":
        if not doc.access_token_maitre:
            doc.access_token_maitre = _generate_token()
        doc.workflow_state = "Envoyé Maître Stage"
    elif role == "maitre":
        if doc.garant_email:
            if not doc.access_token_garant:
                doc.access_token_garant = _generate_token()
            doc.workflow_state = "Envoyé Garant"
        else:
            doc.workflow_state = "En attente DG"
    else:  # garant
        doc.workflow_state = "En attente DG"

    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"ok": True, "state": doc.workflow_state}


# ── 6. Notifications à la transition (appelées par le controller) ──────────

def notifier_transition(doc, before_state):
    """Appelé depuis le hook on_update du controller : envoie l'invitation à
    l'étape qui vient de s'ouvrir + informe la RH, UNE SEULE FOIS (au moment
    exact de la transition, pas à chaque sauvegarde dans le même état)."""
    state = doc.workflow_state or ""
    if state == before_state:
        return
    if state == "Envoyé Maître Stage":
        _notifier_maitre(doc)
    elif state == "Envoyé Garant":
        _notifier_garant(doc)
    elif state == "En attente DG":
        _notifier_rh_pret_pour_dg(doc)


def _notifier_maitre(doc):
    email = doc.maitre_stage_email
    if not email and doc.maitre_stage_employee:
        email = frappe.db.get_value("Employee", doc.maitre_stage_employee, "user_id")
        if email:
            u = frappe.db.get_value("User", email, ["email", "enabled"], as_dict=True)
            email = u.email if u and u.enabled else None
    rh = _rh_emails()
    if not email:
        # Pas d'e-mail renseigné pour le maître de stage : on ne bloque pas le
        # circuit, mais on prévient la RH qu'il faudra le faire signer autrement.
        _send(rh, f"[KYA] {doc.beneficiaire_nom} — maître de stage sans e-mail",
              f"<p>Le/la stagiaire <b>{doc.beneficiaire_nom}</b> ({doc.name}) a signé son contrat, "
              "mais aucun e-mail n'est renseigné pour le maître de stage : merci de le/la faire "
              "signer manuellement (fiche desk) ou de renseigner son e-mail puis de relancer l'envoi.",
              doc.name)
        return
    link = _portal_link(doc.name, doc.access_token_maitre)
    subject = f"[KYA] {doc.beneficiaire_nom} a signé son contrat de stage — à votre tour"
    body = (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
        "<div style='background:linear-gradient(135deg,#0e7c4a,#16a34a);padding:20px;"
        "border-radius:8px 8px 0 0;color:#fff;'><h2 style='margin:0;'>Contrat de stage — votre part</h2></div>"
        "<div style='padding:20px 24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;'>"
        f"<p>Bonjour,</p><p>Vous êtes désigné(e) <b>maître de stage</b> de "
        f"<b>{doc.beneficiaire_nom}</b>. {('Il' if not doc.gender or doc.gender=='Male' else 'Elle')} vient de "
        "signer son contrat de stage d'immersion. Merci de le relire et d'y apposer votre signature.</p>"
        f"<p style='text-align:center;margin:24px 0;'><a href='{link}' style='background:#0e7c4a;"
        "color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:700;'>"
        "→ Consulter et signer</a></p>"
        f"{_pangolin_note()}"
        f"<p style='font-size:12px;color:#888;'>Référence : {doc.name}</p></div></div>"
    )
    _send([email] + _rh_emails(), subject, body, doc.name)


def _notifier_garant(doc):
    link = _portal_link(doc.name, doc.access_token_garant)
    qui = "votre tuteur légal" if doc.type_garant == "Tuteur Légal" else "l'établissement de formation"
    subject = f"[KYA] Contrat de stage {doc.beneficiaire_nom} — signature {('du tuteur légal' if doc.type_garant == 'Tuteur Légal' else 'de l établissement')}"
    body = (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
        "<div style='background:linear-gradient(135deg,#0e7c4a,#16a34a);padding:20px;"
        "border-radius:8px 8px 0 0;color:#fff;'><h2 style='margin:0;'>Contrat de stage — votre signature</h2></div>"
        "<div style='padding:20px 24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;'>"
        f"<p>Bonjour,</p><p>Le contrat de stage d'immersion de <b>{doc.beneficiaire_nom}</b> chez "
        f"KYA-Energy Group a été signé par {qui and 'le/la stagiaire et le maître de stage'}. "
        + ("Merci de renseigner votre nom et votre qualité, de relire le contrat, puis de le signer."
           if doc.type_garant == "Tuteur Légal" else
           "Merci de relire le contrat puis de le signer.") +
        "</p>"
        f"<p style='text-align:center;margin:24px 0;'><a href='{link}' style='background:#0e7c4a;"
        "color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:700;'>"
        "→ Consulter et signer</a></p>"
        f"{_pangolin_note()}"
        f"<p style='font-size:12px;color:#888;'>Référence : {doc.name}</p></div></div>"
    )
    _send([doc.garant_email] + _rh_emails(), subject, body, doc.name)


def _notifier_rh_pret_pour_dg(doc):
    rh = _rh_emails()
    if not rh:
        return
    site = frappe.utils.get_url()
    desk_url = f"{site}/app/contrat-stage-immersion-kya/{doc.name}"
    subject = f"[KYA] {doc.beneficiaire_nom} — contrat prêt pour signature DG"
    body = (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
        "<div style='background:linear-gradient(135deg,#0e7c4a,#16a34a);padding:20px;"
        "border-radius:8px 8px 0 0;color:#fff;'><h2 style='margin:0;'>Prêt pour le DG</h2></div>"
        "<div style='padding:20px 24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;'>"
        f"<p>Bonjour,</p><p>Le contrat de stage d'immersion de <b>{doc.beneficiaire_nom}</b> a recueilli "
        "toutes les signatures préalables (stagiaire, maître de stage"
        + (", garant" if doc.garant_email else "") +
        "). Vous pouvez maintenant le transmettre au Directeur Général pour signature finale "
        "(action « Soumettre au DG » puis signature du DG dans sa fiche).</p>"
        f"<p style='text-align:center;margin:24px 0;'><a href='{desk_url}' style='background:#0e7c4a;"
        "color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:700;'>"
        "→ Ouvrir le contrat</a></p>"
        f"<p style='font-size:12px;color:#888;'>Référence : {doc.name}</p></div></div>"
    )
    _send(rh, subject, body, doc.name)


# ── 7. Vue portail (rôle + progression) ─────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_view(contract_id, token):
    if not frappe.db.exists("Contrat Stage Immersion KYA", contract_id):
        frappe.throw(_("Contrat introuvable"), frappe.DoesNotExistError)
    doc = frappe.get_doc("Contrat Stage Immersion KYA", contract_id)
    role = None
    for r in ("stagiaire", "maitre", "garant"):
        if _verify_token(doc, token, r):
            role = r
            break
    if not role:
        frappe.throw(_("Lien invalide ou expiré"), frappe.PermissionError)

    sections_signed = json.loads(doc.sections_signees or "{}").get(role, [])
    return {
        "doc": doc.as_dict(),
        "role": role,
        "phone_confirmed": bool(doc.phone_confirmed_stagiaire) if role == "stagiaire" else True,
        "sections_signed": sections_signed,
        "can_sign": doc.workflow_state == _ROLE_STATE[role],
        "can_edit_garant_info": (role == "garant" and doc.type_garant == "Tuteur Légal"
                                  and doc.workflow_state == "Envoyé Garant"),
    }
