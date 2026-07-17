# -*- coding: utf-8 -*-
"""Gestion de l'absence du comptable dans le circuit Brouillard de Caisse.

Symétrique du « chef absent » des permissions de sortie (cf.
[[kya_hr.chef_routing]]). Quand la case `comptable_absent` est cochée, le
brouillard saute l'étape « visa Comptable » et part directement au DFC (règle
métier : le comptable peut être en congé). Le comptable reçoit alors un simple
mail d'information — aucune action n'est requise de sa part.
"""
import frappe


def notify_comptable_absent(doc, method=None):
    """Mail d'info aux comptables quand un brouillard saute leur visa.

    Envoyé UNE fois, à l'entrée dans « En attente DFC » avec comptable_absent.
    Défensif : ne lève jamais (ne doit pas bloquer le save)."""
    try:
        if not getattr(doc, "comptable_absent", 0):
            return
        if doc.get("workflow_state") != "En attente DFC":
            return
        before = doc.get_doc_before_save()
        if before and before.get("workflow_state") == "En attente DFC":
            return  # déjà notifié, pas une transition

        # Destinataires : tous les utilisateurs actifs ayant le rôle Comptable,
        # sauf l'auteur de la fiche (souvent la caissière qui a coché la case).
        emails = frappe.db.sql_list(
            """SELECT DISTINCT u.email
               FROM `tabUser` u
               JOIN `tabHas Role` r ON r.parent = u.name
               WHERE r.role = 'Comptable' AND u.enabled = 1
                 AND IFNULL(u.email, '') != ''
                 AND u.name NOT IN ('Administrator', 'Guest')""",
        )
        emails = [e for e in emails if e and e != doc.get("owner")]
        if not emails:
            return

        note = doc.get("comptable_absent_note") or ""
        extra = ("<br>Intérim / précision : <i>%s</i>."
                 % frappe.utils.escape_html(note)) if note else ""
        caissiere = doc.get("caissiere_name") or doc.get("caissiere") or ""
        frappe.sendmail(
            recipients=emails,
            subject="Brouillard de caisse traité sans votre visa (absence signalée) — %s" % doc.name,
            message=(
                "<p>Le brouillard de caisse <b>%s</b>%s a été soumis.</p>"
                "<p>Vous ayant été signalé <b>absent(e)</b>, il est transmis "
                "<b>directement au DFC</b> — <b>aucune action n'est requise de "
                "votre part</b>.%s</p>"
                % (doc.name,
                   (" (caissière : %s)" % frappe.utils.escape_html(caissiere)) if caissiere else "",
                   extra)
            ),
            reference_doctype=doc.doctype, reference_name=doc.name,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "notify_comptable_absent")
