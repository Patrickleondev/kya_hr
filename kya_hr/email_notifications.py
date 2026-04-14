"""
KYA HR — Email notifications automatiques pour les web forms.
- Email récap à la soumission (avec PDF + lien Mon Espace)
- Email au workflow state change (avec signatures progressives)
- Email attribution de tâches
"""
import frappe
from frappe.utils import get_url, get_fullname

# ── Mapping DocType → nom lisible + route web form ──────────
DOCTYPE_CONFIG = {
    "Permission Sortie Employe": {
        "label": "Permission de Sortie",
        "route": "permission-sortie-employe",
        "employee_field": "employee",
        "icon": "🚪",
    },
    "Permission Sortie Stagiaire": {
        "label": "Permission de Sortie Stagiaire",
        "route": "permission-sortie-stagiaire",
        "employee_field": "employee",
        "icon": "🎓",
    },
    "PV Sortie Materiel": {
        "label": "PV Sortie de Matériel",
        "route": "pv-sortie-materiel",
        "employee_field": "employee",
        "icon": "📦",
    },
    "Demande Achat KYA": {
        "label": "Demande d'Achat",
        "route": "demande-achat",
        "employee_field": "employee",
        "icon": "🛒",
    },
    "Planning Conge": {
        "label": "Planning de Congé",
        "route": "planning-conge",
        "employee_field": "employee",
        "icon": "🏖️",
    },
    "Leave Application": {
        "label": "Demande de Congé",
        "route": "demande-conge",
        "employee_field": "employee",
        "icon": "✈️",
    },
    "Bilan Fin de Stage": {
        "label": "Bilan de Fin de Stage",
        "route": "bilan-fin-de-stage",
        "employee_field": "employee",
        "icon": "📋",
    },
}


def _get_employee_email(doc, config):
    """Retourne l'email de l'employé lié au document."""
    emp_id = getattr(doc, config.get("employee_field", "employee"), None)
    if not emp_id:
        return None
    return frappe.db.get_value(
        "Employee", emp_id,
        ["company_email", "personal_email", "employee_name"],
        as_dict=True,
    )


def _build_recap_body(doc, config, emp_name, is_update=False):
    """Construit le corps HTML de l'email récap."""
    base_url = get_url()
    form_url = "{}/{}".format(base_url, config["route"])
    doc_url = "{}/{}?name={}".format(form_url, doc.name, doc.name)
    espace_url = "{}/mon-espace".format(base_url)
    desk_url = "{}/app/{}/{}".format(base_url, doc.doctype.lower().replace(" ", "-"), doc.name)

    state = getattr(doc, "workflow_state", None) or "Brouillon"
    state_color = "#009688" if "Approuv" in state else (
        "#e53935" if "Rejet" in state else (
            "#f59e0b" if "attente" in state.lower() else "#546e7a"
        )
    )

    title = "Mise à jour" if is_update else "Confirmation de soumission"
    subject_prefix = "📌" if is_update else "✅"

    return """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #009688; padding: 24px; border-radius: 12px 12px 0 0; text-align:center;">
        <img src="{logo_url}"
             alt="KYA-Energy Group" width="60" height="60" border="0" style="margin-bottom:8px;display:block;margin:0 auto;">
        <h2 style="color:white; margin:0;">{icon} {label}</h2>
        <p style="color:rgba(255,255,255,0.8); margin:4px 0 0;">{title}</p>
      </div>
      <div style="background: #ffffff; padding: 24px; border: 1px solid #e0e0e0;">
        <p>Bonjour <b>{emp_name}</b>,</p>
        <p>{message}</p>
        <table style="width:100%; border-collapse:collapse; margin:16px 0;">
          <tr>
            <td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Référence</td>
            <td style="padding:8px; border:1px solid #e0e0e0;">{doc_name}</td>
          </tr>
          <tr>
            <td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Type</td>
            <td style="padding:8px; border:1px solid #e0e0e0;">{label}</td>
          </tr>
          <tr>
            <td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Statut</td>
            <td style="padding:8px; border:1px solid #e0e0e0;">
              <span style="background:{state_color}; color:white; padding:3px 12px; border-radius:12px; font-size:13px;">{state}</span>
            </td>
          </tr>
        </table>
        <div style="text-align:center; margin:24px 0;">
          <a href="{doc_url}" style="display:inline-block; padding:12px 28px; background:#009688;
             color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:14px;">
            📱 Voir ma fiche
          </a>
          <a href="{espace_url}" style="display:inline-block; padding:12px 28px; background:#0054A6;
             color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:14px; margin-left:8px;">
            🏠 Mon Espace
          </a>
        </div>
        <p style="font-size:12px; color:#999; text-align:center;">
          Vous pouvez suivre l'avancement de votre demande depuis votre espace personnel.
          <br>Les notifications email vous informeront à chaque étape du workflow.
        </p>
      </div>
      {footer}
    </div>
    """.format(
        logo_url="{}/assets/kya_hr/images/kya_logo.png".format(get_url()),
        icon=config["icon"],
        label=config["label"],
        title=title,
        emp_name=emp_name,
        message=(
            "Votre {} <b>{}</b> a changé de statut.".format(config["label"], doc.name) if is_update
            else "Votre {} a bien été soumise. Voici le récapitulatif :".format(config["label"])
        ),
        doc_name=doc.name,
        state=state,
        state_color=state_color,
        doc_url=doc_url,
        espace_url=espace_url,
        footer=frappe.get_attr("kya_hr.utils.get_kya_email_footer")(),
    )


def send_submission_recap(doc, method=None):
    """Envoie un email récap à l'employé après la soumission d'un web form.

    Déclenché par doc_events → after_insert.
    Inclut le PDF en pièce jointe si le print format existe.
    """
    dt = doc.doctype
    config = DOCTYPE_CONFIG.get(dt)
    if not config:
        return

    emp_info = _get_employee_email(doc, config)
    if not emp_info:
        return

    email = emp_info.get("company_email") or emp_info.get("personal_email")
    if not email:
        return

    emp_name = emp_info.get("employee_name") or "Employé"

    body = _build_recap_body(doc, config, emp_name, is_update=False)

    # Générer le PDF si possible
    attachments = []
    try:
        pdf_content = frappe.get_print(
            dt, doc.name,
            print_format=None,  # utilise le format par défaut
            as_pdf=True,
        )
        if pdf_content:
            filename = "{}-{}.pdf".format(
                config["route"],
                doc.name.replace("/", "-"),
            )
            attachments.append({
                "fname": filename,
                "fcontent": pdf_content,
            })
    except Exception:
        pass  # pas de print format disponible, on envoie sans PDF

    frappe.sendmail(
        recipients=[email],
        subject="[KYA] {} {} — Confirmation".format(config["icon"], config["label"]),
        message=body,
        attachments=attachments or None,
        now=True,
    )


def send_workflow_update(doc, method=None):
    """Envoie un email à l'employé quand le workflow change.

    Déclenché par doc_events → on_update.
    Le document reste le même, seul le statut change.
    Inclut le PDF mis à jour (avec signatures progressives).
    """
    dt = doc.doctype
    config = DOCTYPE_CONFIG.get(dt)
    if not config:
        return

    # Ne pas envoyer si c'est le premier save (after_insert s'en charge)
    if doc.is_new():
        return

    # Ne pas envoyer si workflow_state n'a pas changé
    old_state = doc.get_doc_before_save()
    if old_state:
        prev_ws = getattr(old_state, "workflow_state", None)
        curr_ws = getattr(doc, "workflow_state", None)
        if prev_ws == curr_ws:
            return
    else:
        return

    emp_info = _get_employee_email(doc, config)
    if not emp_info:
        return

    email = emp_info.get("company_email") or emp_info.get("personal_email")
    if not email:
        return

    emp_name = emp_info.get("employee_name") or "Employé"
    body = _build_recap_body(doc, config, emp_name, is_update=True)

    # PDF avec signatures mises à jour
    attachments = []
    try:
        pdf_content = frappe.get_print(dt, doc.name, as_pdf=True)
        if pdf_content:
            filename = "{}-{}.pdf".format(
                config["route"],
                doc.name.replace("/", "-"),
            )
            attachments.append({"fname": filename, "fcontent": pdf_content})
    except Exception:
        pass

    frappe.sendmail(
        recipients=[email],
        subject="[KYA] {} {} — {}".format(
            config["icon"], config["label"],
            getattr(doc, "workflow_state", "Mis à jour"),
        ),
        message=body,
        attachments=attachments or None,
        now=True,
    )

    # Diffusion temps réel → les fiches ouvertes dans l'interface se rafraîchissent
    try:
        frappe.publish_realtime(
            event="workflow_state_change",
            message={
                "doctype": dt,
                "docname": doc.name,
                "workflow_state": getattr(doc, "workflow_state", ""),
            },
            doctype=dt,
            docname=doc.name,
            after_commit=True,
        )
    except Exception:
        pass


def send_task_assignment_email(doc, method=None):
    """Envoie un email quand une tâche est assignée à un employé.

    Déclenché par doc_events → after_insert sur Tache Equipe.
    """
    attribution = getattr(doc, "attribution", None)
    if not attribution:
        return

    emp = frappe.db.get_value(
        "Employee", attribution,
        ["employee_name", "company_email", "personal_email"],
        as_dict=True,
    )
    if not emp:
        return

    email = emp.get("company_email") or emp.get("personal_email")
    if not email:
        return

    base_url = get_url()
    espace_url = "{}/mon-espace#sec-tasks".format(base_url)

    body = """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: #1565c0; padding: 24px; border-radius: 12px 12px 0 0; text-align:center;">
        <img src="{logo_url}"
             alt="KYA-Energy Group" width="60" height="60" border="0" style="margin-bottom:8px;display:block;margin:0 auto;">
        <h2 style="color:white; margin:0;">📌 Nouvelle tâche assignée</h2>
      </div>
      <div style="background: #ffffff; padding: 24px; border: 1px solid #e0e0e0;">
        <p>Bonjour <b>{emp_name}</b>,</p>
        <p>Une nouvelle tâche vous a été assignée dans le cadre du plan trimestriel :</p>
        <table style="width:100%; border-collapse:collapse; margin:16px 0;">
          <tr>
            <td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Tâche</td>
            <td style="padding:8px; border:1px solid #e0e0e0;">{libelle}</td>
          </tr>
          <tr>
            <td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Résultat attendu</td>
            <td style="padding:8px; border:1px solid #e0e0e0;">{resultat}</td>
          </tr>
          <tr>
            <td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">KPI</td>
            <td style="padding:8px; border:1px solid #e0e0e0;">{kpi}</td>
          </tr>
          <tr>
            <td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Taux estimé</td>
            <td style="padding:8px; border:1px solid #e0e0e0;">{taux}%</td>
          </tr>
        </table>
        <div style="text-align:center; margin:24px 0;">
          <a href="{espace_url}" style="display:inline-block; padding:14px 32px; background:#1565c0;
             color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:15px;">
            📋 Voir mes tâches
          </a>
        </div>
        <p style="font-size:12px; color:#999; text-align:center;">
          Vous pouvez mettre à jour votre progression depuis votre espace personnel.
        </p>
      </div>
      {footer}
    </div>
    """.format(
        logo_url="{}/assets/kya_hr/images/kya_logo.png".format(base_url),
        emp_name=emp.get("employee_name"),
        libelle=getattr(doc, "libelle", ""),
        resultat=getattr(doc, "resultat_libelle", ""),
        kpi=getattr(doc, "kpi", "Non défini"),
        taux=getattr(doc, "taux_estime", 0),
        espace_url=espace_url,
        footer=frappe.get_attr("kya_hr.utils.get_kya_email_footer")(),
    )

    frappe.sendmail(
        recipients=[email],
        subject="[KYA] 📌 Nouvelle tâche : {}".format(
            (getattr(doc, "libelle", "") or "")[:60]
        ),
        message=body,
        now=True,
    )
