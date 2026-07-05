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
    # Fiches stock sans champ Employee -> destinataire = créateur (repli owner).
    "PV Entree Materiel": {
        "label": "PV d'Entrée de Matériel",
        "route": "pv-entree-materiel",
        "employee_field": "employee",
        "icon": "📥",
    },
    "Retour Materiel KYA": {
        "label": "Bon de Retour de Matériel",
        "route": "retour-materiel",
        "employee_field": "employee",
        "icon": "↩️",
    },
    "Inventaire KYA": {
        "label": "Fiche d'Inventaire",
        "route": "inventaire-kya",
        "employee_field": "employee",
        "icon": "📊",
    },
}


def _logo_inline_attachment():
    """Logo KYA en pièce jointe INLINE (CID) pour les emails.

    Les <img src="http://.../logo.png"> cassent souvent dans les clients mail
    (Gmail/Outlook) : l'URL dépend de get_url()/host_name et n'est pas toujours
    publique (le site interne s'appelle 'frontend' -> http://frontend/...).
    Un logo embarqué via Content-ID (cid:) s'affiche TOUJOURS, sans dépendre
    d'un fetch externe. Référencer ensuite <img src="cid:kyalogo">.
    """
    for fname in ("kya_logo.png", "logo_kya.png"):
        try:
            path = frappe.get_app_path("kya_hr", "public", "images", fname)
            with open(path, "rb") as f:
                content = f.read()
            return {"fname": "kya_logo.png", "fcontent": content, "content_id": "kyalogo"}
        except Exception:
            continue
    return None


def _official_print_format(config):
    """Print format OFFICIEL d'un doctype, lu depuis son Web Form (source de
    verite : c'est le meme format que le bouton Imprimer). Retourne None si
    aucun n'est configure (Frappe retombe alors sur le format auto)."""
    route = config.get("route")
    if not route:
        return None
    try:
        pf = frappe.db.get_value("Web Form", route, "print_format")
        if pf and frappe.db.exists("Print Format", pf):
            return pf
    except Exception:
        pass
    return None


def _get_employee_email(doc, config):
    """Retourne l'email du destinataire de la confirmation.

    1) l'employé lié (config['employee_field']) s'il existe ;
    2) sinon repli sur le CRÉATEUR du document (utilisateur ayant soumis le
       web form) — utile pour les fiches sans champ Employee (PV Entrée,
       Retour, Inventaire) et plus robuste partout.
    """
    emp_id = getattr(doc, config.get("employee_field", "employee"), None)
    if emp_id:
        row = frappe.db.get_value(
            "Employee", emp_id,
            ["company_email", "personal_email", "user_id", "employee_name"],
            as_dict=True,
        )
        if row:
            return row
    owner = getattr(doc, "owner", None)
    if owner and owner not in ("Administrator", "Guest"):
        u = frappe.db.get_value("User", owner, ["email", "full_name"], as_dict=True)
        if u and u.get("email"):
            return {"company_email": None, "personal_email": u.get("email"),
                    "user_id": owner, "employee_name": u.get("full_name") or owner}
    return None


def _build_recap_body(doc, config, emp_name, is_update=False):
    """Construit le corps HTML de l'email récap."""
    base_url = get_url()
    form_url = "{}/{}".format(base_url, config["route"])
    doc_url = "{}/{}?name={}".format(form_url, doc.name, doc.name)
    espace_url = "{}/mon-espace".format(base_url)
    desk_url = "{}/app/{}/{}".format(base_url, doc.doctype.lower().replace(" ", "-"), doc.name)

    state = getattr(doc, "workflow_state", None) or "Brouillon"
    state_color = "#2e7d32" if "Approuv" in state else (
        "#e53935" if "Rejet" in state else (
            "#f59e0b" if "attente" in state.lower() else "#546e7a"
        )
    )

    title = "Mise à jour" if is_update else "Confirmation de soumission"
    subject_prefix = "📌" if is_update else "✅"

    return """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <div style="background: linear-gradient(135deg,#f7a800 0%,#e07b00 100%); padding: 24px; border-radius: 12px 12px 0 0; text-align:center;">
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
          <a href="{doc_url}" style="display:inline-block; padding:12px 28px; background:#f7a800;
             color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:14px;">
            📱 Voir ma fiche
          </a>
          <a href="{espace_url}" style="display:inline-block; padding:12px 28px; background:#1a5276;
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

    email = emp_info.get("company_email") or emp_info.get("personal_email") or emp_info.get("user_id")
    if not email:
        return

    emp_name = emp_info.get("employee_name") or "Employé"

    body = _build_recap_body(doc, config, emp_name, is_update=False)

    # Générer le PDF avec le print format OFFICIEL (fiche KYA), pas le format
    # auto generique. Le DG/DGA exigent que le PDF ressemble exactement a la
    # fiche. On prend le format configure sur le Web Form (source de verite),
    # et on rend SANS Letter Head : la fiche officielle est auto-suffisante
    # (sinon le Letter Head par defaut, avec ses placeholders XXXX, pollue le bas).
    attachments = []
    try:
        official_pf = _official_print_format(config)
        pdf_content = frappe.get_print(
            dt, doc.name,
            print_format=official_pf,  # fiche officielle (ex: Ticket Sortie Stagiaire)
            as_pdf=True,
            no_letterhead=1,
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

    # Pas de logo dans les emails : sous Outlook (client de l'entreprise) les
    # images inline (cid:) se cassent. On envoie les notifs SANS logo.

    frappe.sendmail(
        recipients=[email],
        subject="[KYA] {} {} — Confirmation".format(config["icon"], config["label"]),
        message=body,
        attachments=attachments or None,
        now=False,  # file dans la queue email, ne bloque pas le save
    )


def send_workflow_update(doc, method=None):
    """Publie le changement workflow sans email intermédiaire au demandeur.

    Déclenché par doc_events → on_update.
    Le demandeur reçoit la confirmation à la soumission et les états finaux
    via les Notifications Frappe ciblées. Les étapes intermédiaires sont
    réservées aux approbateurs pour éviter les mails peu pertinents.
    """
    dt = doc.doctype
    config = DOCTYPE_CONFIG.get(dt)
    if not config:
        return

    # Ne pas envoyer si c'est le premier save (after_insert s'en charge)
    if doc.is_new():
        return

    # Les états finaux (Approuvé/Rejeté) sont couverts par les Frappe native
    # Notifications (notification.json) — pas de doublon
    _FINAL_STATES = frozenset({
        "Approuvé", "Approuvée", "Rejeté", "Rejetée",
        "Approuvé(e)", "Rejeté(e)", "Terminé", "Clôturé",
    })
    curr_ws = getattr(doc, "workflow_state", None)
    if curr_ws in _FINAL_STATES:
        return

    # Ne pas envoyer si workflow_state n'a pas changé
    old_state = doc.get_doc_before_save()
    if old_state:
        prev_ws = getattr(old_state, "workflow_state", None)
        if prev_ws == curr_ws:
            return
    else:
        # get_doc_before_save() absent = save sans before_save (ex: submit/cancel)
        # on ne peut pas déterminer le changement → on laisse passer prudemment
        pass

    # Le demandeur reçoit déjà la confirmation à la soumission et les états
    # finaux via les Notifications Frappe ciblées. Les états intermédiaires
    # doivent rester pour les approbateurs, pas spammer le demandeur.
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
    """Notifie chaque employé attributaire d'une Tache Equipe.

    - À l'insertion : email à tous les attributaires.
    - À l'update : email uniquement aux NOUVEAUX attributaires (diff avant/après).

    Wiré via doc_events → after_insert + on_update sur Tache Equipe.
    """
    attributions = doc.get("attributions") or []
    if not attributions:
        return

    # Calcul du delta sur on_update : attributaires ajoutés depuis le précédent état.
    new_employees = set()
    if method == "on_update":
        try:
            previous = frappe.get_doc(doc.doctype, doc.name)
            previous_emps = {(a.get("employe") or "") for a in (previous.get("attributions") or [])}
            for row in attributions:
                emp = row.get("employe")
                if emp and emp not in previous_emps:
                    new_employees.add(emp)
            if not new_employees:
                return
        except Exception:
            # Si on n'arrive pas à diff, on évite de spammer : pas d'email sur on_update
            return
    else:
        for row in attributions:
            if row.get("employe"):
                new_employees.add(row["employe"])

    if not new_employees:
        return

    base_url = get_url()
    espace_url = "{}/mon-espace#sec-tasks".format(base_url)
    libelle = (getattr(doc, "libelle", "") or "")
    resultat = (getattr(doc, "resultat_libelle", "") or "")
    kpi = (getattr(doc, "kpi", "") or "Non défini")
    taux = getattr(doc, "taux_estime", 0) or 0
    frequence = getattr(doc, "frequence", "") or ""

    for emp_id in new_employees:
        emp = frappe.db.get_value(
            "Employee", emp_id,
            ["employee_name", "company_email", "personal_email"],
            as_dict=True,
        )
        if not emp:
            continue
        email = emp.get("company_email") or emp.get("personal_email")
        if not email:
            continue

        # Trouver le rôle attribué à cet employé sur cette tâche
        role = "Contributeur"
        for row in attributions:
            if row.get("employe") == emp_id:
                role = row.get("role_attribution") or "Contributeur"
                break

        body = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <div style="background: #1565c0; padding: 24px; border-radius: 12px 12px 0 0; text-align:center;">
            <h2 style="color:white; margin:0;">Nouvelle tâche assignée</h2>
          </div>
          <div style="background: #ffffff; padding: 24px; border: 1px solid #e0e0e0;">
            <p>Bonjour <b>{emp_name}</b>,</p>
            <p>Une nouvelle tâche vous a été assignée en tant que <b>{role}</b> :</p>
            <table style="width:100%; border-collapse:collapse; margin:16px 0;">
              <tr><td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Tâche</td>
                  <td style="padding:8px; border:1px solid #e0e0e0;">{libelle}</td></tr>
              <tr><td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Résultat attendu</td>
                  <td style="padding:8px; border:1px solid #e0e0e0;">{resultat}</td></tr>
              <tr><td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">KPI</td>
                  <td style="padding:8px; border:1px solid #e0e0e0;">{kpi}</td></tr>
              <tr><td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Fréquence</td>
                  <td style="padding:8px; border:1px solid #e0e0e0;">{frequence}</td></tr>
              <tr><td style="padding:8px; background:#f5f5f5; border:1px solid #e0e0e0; font-weight:600;">Taux estimé</td>
                  <td style="padding:8px; border:1px solid #e0e0e0;">{taux}%</td></tr>
            </table>
            <div style="text-align:center; margin:24px 0;">
              <a href="{espace_url}" style="display:inline-block; padding:14px 32px; background:#1565c0;
                 color:#fff; text-decoration:none; border-radius:8px; font-weight:700; font-size:15px;">
                📋 Voir mes tâches
              </a>
            </div>
            <p style="font-size:12px; color:#999; text-align:center;">
              Mettez à jour votre progression depuis Mon Espace.
            </p>
          </div>
          {footer}
        </div>
        """.format(
            emp_name=emp.get("employee_name") or emp_id,
            role=role,
            libelle=libelle,
            resultat=resultat,
            kpi=kpi,
            frequence=frequence,
            taux=taux,
            espace_url=espace_url,
            footer=frappe.get_attr("kya_hr.utils.get_kya_email_footer")(),
        )

        frappe.sendmail(
            recipients=[email],
            subject="[KYA] Nouvelle tâche : {}".format(libelle[:60] or doc.name),
            message=body,
            now=False,
        )
