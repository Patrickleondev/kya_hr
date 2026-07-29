# -*- coding: utf-8 -*-
"""API de la page /fiches-poste (self-service).

Réutilise le print format « Fiche de Poste KYA ». Règles d'accès :
- RH / Direction : voient et signent toutes les fiches ;
- l'employé (titulaire) : voit et signe SA fiche ;
- le chef d'équipe : voit les fiches des membres de son équipe (et peut viser en N+1).
La RH remplit le contenu dans le desk ; la page sert surtout à consulter, signer en
ligne (pad) et imprimer.

Circuit de signature (28-29/07/2026) : titulaire -> N+1 (supérieur hiérarchique)
-> DRH, dans cet ordre STRICT, et VERROUILLÉ (une fois une étape signée, elle ne
peut plus être re-signée/écrasée). Chaque étape franchie notifie par e-mail
l'étape suivante (lien direct vers SA fiche) ainsi que la RH (qui suit ainsi
chaque changement d'état sans avoir à chercher). Étape DRH : DGA ET l'assistante
RH (Hanna) reçoivent tous les deux l'invitation ; le premier des deux qui signe
clôt le circuit (pas de double-signature possible, cf. verrouillage ci-dessus).
"""
from urllib.parse import quote

import frappe
from frappe import _
from frappe.translate import print_language

_RH_ROLES = {"Responsable RH", "HR Manager", "HR User", "System Manager",
             "Directeur Général", "DGA"}
_DRH_INVITE_ROLES = ("DGA", "Responsable RH", "HR Manager", "HR User")
_ROLE_FIELD = {"titulaire": "signature_titulaire", "n1": "signature_n1", "drh": "signature_drh"}
_ROLE_LABEL = {"titulaire": "le titulaire", "n1": "le supérieur hiérarchique (N+1)", "drh": "la DRH"}
_ORDER = ("titulaire", "n1", "drh")


def _me():
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


def _is_rh():
    return bool(_RH_ROLES & set(frappe.get_roles(frappe.session.user)))


def _teams_led(me=None):
    me = me or _me()
    if not me:
        return []
    return frappe.get_all("Equipe KYA", filters={"chef_equipe": me}, pluck="name")


def _guard():
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)


def _can_view(employee):
    if _is_rh():
        return True
    me = _me()
    if employee and employee == me:
        return True
    teams = set(_teams_led(me))
    if teams and employee:
        return frappe.db.get_value("Employee", employee, "custom_kya_equipe") in teams
    return False


# ── Résolution des destinataires ────────────────────────────────────────────
def _user_email(user):
    if not user or user in ("Administrator", "Guest"):
        return None
    d = frappe.db.get_value("User", user, ["email", "enabled"], as_dict=True)
    return d.email if d and d.enabled and d.email else None


def _employee_email(employee):
    if not employee:
        return None
    emp = frappe.db.get_value("Employee", employee,
                               ["user_id", "company_email", "personal_email"], as_dict=True)
    if not emp:
        return None
    return _user_email(emp.user_id) or emp.company_email or emp.personal_email


def _emails_for_roles(roles):
    seen, out = set(), []
    for role in roles:
        for user in frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"):
            em = _user_email(user)
            if em and em not in seen:
                seen.add(em)
                out.append(em)
    return out


def _dg_emails():
    return _emails_for_roles(("Directeur Général",))


def _n1_recipient(employee):
    """(nom, email) du N+1 réel (Employee.reports_to). À défaut (chef d'équipe
    sans supérieur renseigné, cas fréquent) : le DG par défaut."""
    reports_to = frappe.db.get_value("Employee", employee, "reports_to") if employee else None
    if reports_to:
        nom, email = frappe.db.get_value("Employee", reports_to, "employee_name"), _employee_email(reports_to)
        if email:
            return nom, email
    dg = _dg_emails()
    return ("le Directeur Général", dg[0]) if dg else (None, None)


def _pangolin_note():
    return (
        "<div style='background:#fff8e7;border-left:4px solid #e07b00;padding:12px 16px;"
        "margin:16px 0;font-size:13px;color:#333;'>"
        "🔒 <b>Aucun mot de passe supplémentaire à retenir.</b> Connectez-vous simplement avec "
        "votre compte KYA habituel. <b>Si une page (souvent sombre) vous demande un « code » à "
        "6 chiffres</b>, tapez <b>1 1 1 1 1 1</b> (le chiffre 1, six fois) puis continuez."
        "</div>"
    )


def _fiche_link(name):
    return f"{frappe.utils.get_url()}/fiches-poste?name={quote(name)}"


def _send(recipients, subject, body_html):
    recipients = [r for r in dict.fromkeys(recipients) if r]  # dédoublonne, préserve l'ordre
    if not recipients:
        return
    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=body_html,
                         reference_doctype="Fiche de Poste KYA", now=False)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "fiche_poste: notif")


def _notify_after_signature(doc, role):
    """Après une signature réussie : prévient l'étape suivante + la RH (à
    chaque changement d'état, comme demandé)."""
    name = doc["name"]
    titre = doc.get("intitule_poste") or name
    nom_titulaire = doc.get("employee_name") or "—"
    link = _fiche_link(name)
    rh_group = _emails_for_roles(("Responsable RH", "HR Manager", "HR User"))

    if role == "titulaire":
        nom_n1, email_n1 = _n1_recipient(doc.get("employee"))
        subject = f"[KYA] {nom_titulaire} a signé sa fiche de poste — à votre tour"
        body = (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#0e6b58,#16a34a);padding:20px;"
            "border-radius:8px 8px 0 0;color:#fff;'><h2 style='margin:0;'>Fiche de poste — à viser</h2></div>"
            "<div style='padding:20px 24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;'>"
            f"<p>Bonjour,</p><p><b>{nom_titulaire}</b> ({titre}) vient de signer sa fiche de poste. "
            "En tant que <b>supérieur hiérarchique (N+1)</b>, merci de la relire et d'y apposer votre visa.</p>"
            f"<p style='text-align:center;margin:24px 0;'><a href='{link}' style='background:#0e6b58;"
            "color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:700;'>"
            "→ Consulter et viser la fiche</a></p>"
            f"{_pangolin_note()}"
            f"<p style='font-size:12px;color:#888;'>Référence : {name}</p></div></div>"
        )
        _send([email_n1] + rh_group, subject, body)

    elif role == "n1":
        drh_group = _emails_for_roles(_DRH_INVITE_ROLES)
        subject = f"[KYA] Fiche de poste {nom_titulaire} — en attente de validation DRH"
        body = (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#0e6b58,#16a34a);padding:20px;"
            "border-radius:8px 8px 0 0;color:#fff;'><h2 style='margin:0;'>Fiche de poste — validation DRH</h2></div>"
            "<div style='padding:20px 24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;'>"
            f"<p>Bonjour,</p><p>La fiche de poste de <b>{nom_titulaire}</b> ({titre}) a été signée par le "
            "titulaire et visée par le supérieur hiérarchique. Il ne manque plus que la validation DRH.</p>"
            f"<p style='text-align:center;margin:24px 0;'><a href='{link}' style='background:#0e6b58;"
            "color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:700;'>"
            "→ Valider la fiche</a></p>"
            f"{_pangolin_note()}"
            f"<p style='font-size:12px;color:#888;'>Référence : {name}</p></div></div>"
        )
        _send(drh_group, subject, body)

    else:  # drh — clôture du circuit
        nom_n1, email_n1 = _n1_recipient(doc.get("employee"))
        email_titulaire = _employee_email(doc.get("employee"))
        subject = f"[KYA] Fiche de poste {nom_titulaire} — circuit clôturé ✅"
        body = (
            "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
            "<div style='background:linear-gradient(135deg,#2e7d32,#66bb6a);padding:20px;"
            "border-radius:8px 8px 0 0;color:#fff;'><h2 style='margin:0;'>✅ Fiche de poste finalisée</h2></div>"
            "<div style='padding:20px 24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;'>"
            f"<p>Bonjour,</p><p>La fiche de poste de <b>{nom_titulaire}</b> ({titre}) a reçu les trois "
            "signatures (titulaire, N+1, DRH) et est désormais complète.</p>"
            f"<p style='text-align:center;margin:24px 0;'><a href='{link}' style='background:#166534;"
            "color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:700;'>"
            "→ Consulter / télécharger le PDF</a></p>"
            f"{_pangolin_note()}"
            f"<p style='font-size:12px;color:#888;'>Référence : {name}</p></div></div>"
        )
        _send([email_titulaire, email_n1] + rh_group, subject, body)


@frappe.whitelist()
def liste():
    _guard()
    fields = ["name", "employee", "employee_name", "intitule_poste", "departement",
              "signature_titulaire", "signature_n1", "signature_drh", "modified"]
    if _is_rh():
        rows = frappe.get_all("Fiche de Poste KYA", fields=fields, order_by="employee_name asc")
    else:
        me = _me()
        or_filters = []
        if me:
            or_filters.append(["employee", "=", me])
        teams = _teams_led(me)
        if teams:
            membres = frappe.get_all("Employee", filters={"custom_kya_equipe": ["in", teams]}, pluck="name")
            if membres:
                or_filters.append(["employee", "in", membres])
        if not or_filters:
            return []
        rows = frappe.get_all("Fiche de Poste KYA", fields=fields,
                              or_filters=or_filters, order_by="employee_name asc")
    me = _me()
    out = []
    for r in rows:
        r["signed"] = {k: bool(r.get(f)) for k, f in _ROLE_FIELD.items()}
        for f in _ROLE_FIELD.values():
            r.pop(f, None)
        r["is_mine"] = bool(me and r.get("employee") == me)
        r["pdf_url"] = ("/api/method/kya_hr.api.print_format.download_pdf"
                        "?doctype=" + quote("Fiche de Poste KYA") + "&name=" + quote(r["name"])
                        + "&format=" + quote("Fiche de Poste KYA") + "&language=fr")
        out.append(r)
    return out


@frappe.whitelist()
def apercu(name):
    _guard()
    if not frappe.db.exists("Fiche de Poste KYA", name):
        frappe.throw(_("Fiche introuvable."))
    employee = frappe.db.get_value("Fiche de Poste KYA", name, "employee")
    if not _can_view(employee):
        frappe.throw(_("Accès non autorisé à cette fiche."), frappe.PermissionError)
    with print_language("fr"):
        return frappe.get_print("Fiche de Poste KYA", name, "Fiche de Poste KYA")


@frappe.whitelist()
def signer(name, role, signature):
    _guard()
    if role not in _ROLE_FIELD:
        frappe.throw(_("Rôle de signature invalide."))
    if not (signature or "").startswith("data:image"):
        frappe.throw(_("Signature vide."))
    doc = frappe.db.get_value(
        "Fiche de Poste KYA", name,
        ["employee", "employee_name", "intitule_poste", "signature_titulaire", "signature_n1", "signature_drh"],
        as_dict=True)
    if not doc:
        frappe.throw(_("Fiche introuvable."))
    employee = doc.employee
    me, rh = _me(), _is_rh()
    if role == "titulaire":
        ok = rh or (employee and employee == me)
    elif role == "n1":
        ok = rh or (_can_view(employee) and bool(_teams_led(me)))
    else:  # drh
        ok = rh
    if not ok:
        frappe.throw(_("Vous n'êtes pas autorisé à apposer cette signature."), frappe.PermissionError)

    # Circuit STRICT et VERROUILLÉ : titulaire -> N+1 -> DRH.
    idx = _ORDER.index(role)
    if idx > 0:
        prev_role = _ORDER[idx - 1]
        if not doc.get(_ROLE_FIELD[prev_role]):
            frappe.throw(_("{0} doit d'abord signer avant vous.").format(_ROLE_LABEL[prev_role].capitalize()))
    if doc.get(_ROLE_FIELD[role]):
        frappe.throw(_("Cette étape a déjà été signée — impossible de la signer une seconde fois."))

    frappe.db.set_value("Fiche de Poste KYA", name, _ROLE_FIELD[role], signature)
    frappe.db.commit()
    doc["name"] = name
    _notify_after_signature(doc, role)
    return {"ok": True, "role": role}
