"""Publication d'evenements realtime pour les dashboards KYA.

Quand un Employee / Attendance / Permission / Planning / PV / Demande Achat
est insere ou modifie, on emet l'evenement 'kya_dashboard_updated' via
frappe.publish_realtime. Les dashboards (tableau-bord-employes, kya-tableau-de-bord)
ecoutent cet evenement cote JS et rafraichissent leurs donnees automatiquement.

L'emission est wrappee dans try/except : un push realtime cassé ne doit
jamais bloquer la sauvegarde d'un document.
"""
import frappe


def notify_dashboard_change(doc, method=None):
    """Push realtime aux dashboards : un document du domaine RH/Achat a change."""
    try:
        frappe.publish_realtime(
            event="kya_dashboard_updated",
            message={
                "doctype": doc.doctype,
                "name": doc.name,
                "user": frappe.session.user,
            },
            after_commit=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "kya_dashboard_realtime push failed")
