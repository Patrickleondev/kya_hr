# -*- coding: utf-8 -*-
"""Auto-rempli report_to_user (Email du chef) pour les DocTypes KYA.
Utilise par doc_events.before_save pour assurer que les notifications 'En attente Chef'
trouvent toujours le bon destinataire.
"""
import frappe


# Rôles qui gouvernent l'étape « En attente Chef » du workflow. Un demandeur qui
# porte l'un d'eux EST le chef : il ne peut pas valider sa propre étape chef, donc
# on la saute directement vers la RH. Choix RH du 20/07/2026.
_CHEF_ROLES = {
    "Chef Service",
    "Supérieur Immédiat",
    "Chef Equipe",
    "Chef d'Équipe",
    "Responsable Equipe",
    "Responsable d'Équipe",
}


def route_start_state(doc, method=None):
    """Pré-remplit le visa chef à la CRÉATION quand l'étape chef doit être sautée.

    Ce DocType est custom=1 → sa classe Python n'est pas chargée par Frappe ;
    ce point d'entrée (doc_events before_insert) EST le vrai contrôleur.

    On NE force PAS `workflow_state` ici : Frappe refuse une transition directe
    Brouillon → En attente RH à l'insertion. On pose seulement le SIGNAL
    (`date_signature_chef` + `signataire_chef`) ; c'est une transition dédiée du
    workflow (condition `doc.date_signature_chef`) qui envoie la demande à la RH
    au moment du « Soumettre » — exactement comme le fait la case « chef absent ».

    Cas couverts :
    - RH crée pour autrui via Desk (l'étape chef est couverte par la RH).
    - Le demandeur EST lui-même chef/responsable (il ne peut pas se valider ;
      sinon la demande reste bloquée à « En attente Chef »). Choix RH 20/07/2026.

    On ne touche à rien si « chef absent » est coché (ce chemin a sa propre
    transition) ni si un visa chef est déjà présent.
    """
    if doc.get("chef_absent") or doc.get("date_signature_chef"):
        return
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return
    roles = set(frappe.get_roles(user))
    is_hr = bool({"HR Manager", "HR User"} & roles)
    is_chef = bool(_CHEF_ROLES & roles)

    mention = None
    via_web_form = bool(getattr(doc, "flags", None) and doc.flags.get("via_web_form"))
    if is_hr and not via_web_form:
        mention = "Créé par RH"
    elif is_chef and not is_hr:
        # Un non-RH ne peut créer QUE pour lui-même → un chef qui crée demande
        # pour lui-même : bypass légitime de l'étape chef.
        mention = "Demandeur est chef — étape chef non requise"

    if not mention:
        return

    name = frappe.db.get_value("Employee", {"user_id": user}, "employee_name") \
        or frappe.utils.get_fullname(user)
    doc.signataire_chef = (name or "") + f" ({mention})"
    doc.date_signature_chef = frappe.utils.today()


def populate_chef(doc, method=None):
    """Remplit doc.report_to_user depuis Employee.reports_to.user_id.

    L'employé est résolu depuis `doc.employee` s'il existe, sinon depuis le
    créateur de la fiche (`owner`) — indispensable pour les PV de sortie, dont
    la web form ne renseigne pas de champ `employee` : sans ce repli, la notif
    « En attente Chef » ne trouvait aucun destinataire (le chef n'était jamais
    prévenu)."""
    emp = getattr(doc, "employee", None)
    if not emp:
        creator = doc.get("owner") or frappe.session.user
        if creator and creator not in ("Administrator", "Guest"):
            emp = frappe.db.get_value("Employee", {"user_id": creator}, "name")
    if not emp:
        return
    try:
        chef_emp = frappe.db.get_value("Employee", emp, "reports_to")
        if not chef_emp:
            return
        chef_user = frappe.db.get_value("Employee", chef_emp, "user_id")
        if chef_user and getattr(doc, "report_to_user", None) != chef_user:
            doc.report_to_user = chef_user
    except Exception:
        # Fail silent: ne bloque jamais le save
        pass


# États où la demande arrive APRÈS avoir sauté le chef (chef absent).
_CHEF_ABSENT_INFO_STATES = {"En attente RH", "En attente Resp. Stagiaires"}


def notify_chef_absent(doc, method=None):
    """Si 'chef absent' coché, le chef (report_to) reçoit un simple mail d'info
    et la demande part directement à la RH. Envoyé une seule fois, au passage
    dans l'état RH/Resp. Stagiaires."""
    if not getattr(doc, "chef_absent", 0):
        return
    state = doc.get("workflow_state")
    if state not in _CHEF_ABSENT_INFO_STATES:
        return
    before = doc.get_doc_before_save()
    if before and before.get("workflow_state") == state:
        return  # pas un changement d'état -> déjà notifié

    chef_email = None
    if doc.get("report_to"):
        chef_email = (frappe.db.get_value("Employee", doc.report_to, "user_id")
                      or frappe.db.get_value("Employee", doc.report_to, "personal_email"))
    if not chef_email:
        chef_email = doc.get("report_to_user")
    if not chef_email or chef_email in ("Administrator", "Guest"):
        return

    interim = doc.get("chef_absent_note") or ""
    extra = (" Intérim / précision : <i>%s</i>." % frappe.utils.escape_html(interim)) if interim else ""
    try:
        frappe.sendmail(
            recipients=[chef_email],
            subject="Demande de sortie traitée par la RH (absence signalée) — %s" % doc.name,
            message=(
                "<p>Une demande de permission de sortie de <b>%s</b> a été soumise.</p>"
                "<p>Vous ayant été signalé <b>absent(e)</b>, elle est transmise "
                "<b>directement à la RH</b> pour traitement — <b>aucune action n'est "
                "requise de votre part</b>.%s</p>"
                % (doc.get("employee_name") or "", extra)
            ),
            reference_doctype=doc.doctype, reference_name=doc.name,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "notify_chef_absent")
