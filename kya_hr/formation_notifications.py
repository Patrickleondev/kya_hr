# -*- coding: utf-8 -*-
"""Notifications du circuit Formation (email + cloche in-app).

Branché via doc_events (on_update) sur Besoin de Formation et Plan de Formation.
On détecte un changement d'état (statut) et on prévient les bons acteurs :

  • Besoin → "Soumis à la RH"      → la RH
  • Plan   → "Soumis au DG"         → le DG / DGA
  • Plan   → "Sélection DG"         → la RH (le DG a tranché)
  • Plan   → "Validé" / "En suivi"  → la RH

Aucune dépendance au sandbox workflow : tout passe par les hooks Python.
"""
import frappe
from frappe.utils import get_url_to_form


RH_ROLES = ("Responsable RH", "HR Manager")
DG_ROLES = ("Directeur Général", "DG", "DGA")


def _users_with_roles(roles):
    """Users actifs (non Admin/Guest) portant l'un des rôles."""
    if not roles:
        return []
    rows = frappe.get_all(
        "Has Role",
        filters={"role": ["in", list(roles)], "parenttype": "User"},
        fields=["parent"],
        distinct=True,
    )
    users = []
    for r in rows:
        u = r.parent
        if u in ("Administrator", "Guest"):
            continue
        if frappe.db.get_value("User", u, "enabled"):
            users.append(u)
    return list(dict.fromkeys(users))


def _notify(users, subject, message, doc):
    """Email + Notification Log in-app pour chaque destinataire."""
    users = [u for u in (users or []) if u]
    if not users:
        return
    from kya_hr.utils import kya_email_html
    link = get_url_to_form(doc.doctype, doc.name)
    body = ('%s<p style="margin-top:18px;"><a href="%s" '
            'style="background:#00897B;color:#ffffff;text-decoration:none;padding:10px 18px;'
            'font-weight:bold;display:inline-block;font-family:Arial,Helvetica,sans-serif;">'
            'Ouvrir %s</a></p>' % (message, link, doc.name))
    html = kya_email_html("Gestion de Formation", body, subtitle=subject, accent="#00897B")

    # Email (le SMTP prod est configuré ; en dev sans SMTP, on n'échoue pas)
    try:
        frappe.sendmail(recipients=users, subject=subject, message=html,
                        reference_doctype=doc.doctype, reference_name=doc.name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "formation_notifications sendmail")

    # Cloche in-app (Notification Log)
    for u in users:
        try:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": subject,
                "email_content": message,
                "for_user": u,
                "type": "Alert",
                "document_type": doc.doctype,
                "document_name": doc.name,
            }).insert(ignore_permissions=True)
        except Exception:
            pass


def _changed_to(doc, value):
    """True si `statut` vient de passer à `value` lors de ce save."""
    if doc.get("statut") != value:
        return False
    before = doc.get_doc_before_save()
    return (not before) or before.get("statut") != value


def besoin_on_update(doc, method=None):
    if _changed_to(doc, "Soumis à la RH"):
        _notify(
            _users_with_roles(RH_ROLES),
            "Nouveau besoin de formation — %s" % (doc.get("chef_equipe_name") or doc.equipe),
            "<p>Le chef d'équipe <b>%s</b> a soumis les besoins en formation de l'équipe "
            "<b>%s</b> (%s lignes). Merci de planifier l'entretien de revue.</p>"
            % (doc.get("chef_equipe_name") or "?", doc.equipe, len(doc.lignes or [])),
            doc,
        )


def plan_on_update(doc, method=None):
    if _changed_to(doc, "Soumis au DG"):
        _notify(
            _users_with_roles(DG_ROLES),
            "Plan de formation à valider — %s" % doc.titre,
            "<p>La RH a soumis le plan de formation <b>%s</b> (%s formations compilées) "
            "pour votre sélection.</p>" % (doc.titre, doc.nb_formations),
            doc,
        )
    elif _changed_to(doc, "Sélection DG"):
        _notify(
            _users_with_roles(RH_ROLES),
            "Sélection DG reçue — %s" % doc.titre,
            "<p>Le DG a effectué sa sélection sur le plan <b>%s</b> "
            "(%s formation(s) retenue(s)). Merci de procéder au chiffrage.</p>"
            % (doc.titre, doc.nb_retenues_dg),
            doc,
        )
    elif _changed_to(doc, "Validé") or _changed_to(doc, "En suivi"):
        _notify(
            _users_with_roles(RH_ROLES),
            "Plan de formation validé — %s" % doc.titre,
            "<p>Le plan <b>%s</b> est validé (coût total %s FCFA). Le suivi des "
            "formations peut démarrer.</p>" % (doc.titre, doc.cout_total),
            doc,
        )
