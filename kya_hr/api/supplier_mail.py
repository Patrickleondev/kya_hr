# -*- coding: utf-8 -*-
"""Envoi par email des Bons de Commande et Appels d'Offre aux fournisseurs.

Flux en DEUX temps (revue avant envoi, demandé par l'utilisateur) :
  1. prepare_*  -> renvoie destinataire(s), objet, message pré-remplis +
     indicateur `has_email` (beaucoup de fournisseurs KYA n'ont pas d'email).
  2. send_*     -> envoie réellement (PDF officiel joint), marque l'état.

Le destinataire est éditable côté UI : si le fournisseur n'a pas d'email
enregistré, l'utilisateur le saisit manuellement avant l'envoi ; les
fournisseurs sans email saisi sont simplement ignorés (et listés en retour).
"""
from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import now_datetime, formatdate
from frappe.utils.pdf import get_pdf

from kya_hr.api.print_format import _sanitize_print_html


SEND_ROLES = {
    "Responsable Achats", "Purchase Manager", "Purchase User",
    "DG", "Directeur Général", "DGA", "System Manager", "Administrator",
}


def _check_role():
    if not (set(frappe.get_roles()) & SEND_ROLES):
        frappe.throw(_("Réservé aux Achats / Direction."), frappe.PermissionError)


def _render_pdf(doctype: str, name: str, print_format: str | None = None) -> bytes:
    """Génère un PDF propre (logo inliné, sans appel réseau wkhtmltopdf)."""
    html = frappe.get_print(doctype, name, print_format)
    html = _sanitize_print_html(html)
    return get_pdf(html)


def _supplier_email(supplier: str | None, fallback: str | None = None) -> str:
    fb = (fallback or "").strip()
    if fb:
        return fb
    if supplier and frappe.db.exists("Supplier", supplier):
        return (frappe.db.get_value("Supplier", supplier, "email_id") or "").strip()
    return ""


def _attachment(doctype, name, print_format, prefix):
    try:
        pdf = _render_pdf(doctype, name, print_format)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"supplier_mail PDF {doctype} {name}")
        return None
    fname = f"{prefix}-{name}.pdf".replace("/", "-").replace(" ", "-")
    return {"fname": fname, "fcontent": pdf}


# ─────────────────────────── BON DE COMMANDE ────────────────────────────────

@frappe.whitelist()
def prepare_bc(name: str) -> dict:
    _check_role()
    doc = frappe.get_doc("Bon Commande KYA", name)
    email = _supplier_email(doc.fournisseur, doc.fournisseur_email)
    num = doc.numero_bc or name
    subject = f"Bon de Commande N° {num} — KYA-Energy Group"
    message = (
        f"Bonjour {doc.fournisseur_nom or ''},\n\n"
        f"Veuillez trouver ci-joint notre bon de commande N° {num} "
        f"relatif à : {doc.objet or ''}.\n\n"
        f"Merci de bien vouloir nous confirmer la bonne réception ainsi que "
        f"la disponibilité des articles.\n\n"
        f"Cordialement,\nKYA-Energy Group"
    )
    return {
        "to": email, "has_email": bool(email),
        "supplier_name": doc.fournisseur_nom or "", "numero": num,
        "subject": subject, "message": message, "statut": doc.statut,
    }


@frappe.whitelist()
def send_bc(name: str, to_email: str, subject: str = None, message: str = None, cc: str = None) -> dict:
    _check_role()
    to_email = (to_email or "").strip()
    if not to_email:
        frappe.throw(_("Adresse email du fournisseur requise."))
    doc = frappe.get_doc("Bon Commande KYA", name)
    att = _attachment("Bon Commande KYA", name, "Bon Commande KYA Officiel", "BC")

    frappe.sendmail(
        recipients=[to_email],
        cc=[cc] if cc else None,
        subject=subject or f"Bon de Commande {doc.numero_bc or name}",
        message=(message or "").replace("\n", "<br>"),
        attachments=[att] if att else None,
        reference_doctype="Bon Commande KYA", reference_name=name,
    )
    updates = {}
    if (doc.fournisseur_email or "") != to_email:
        updates["fournisseur_email"] = to_email
    if doc.statut in ("Brouillon", "Émis"):
        updates["statut"] = "Envoyé Fournisseur"
    if updates:
        frappe.db.set_value("Bon Commande KYA", name, updates, update_modified=False)
        frappe.db.commit()
    return {"sent_to": to_email, "attached": bool(att), "statut": updates.get("statut", doc.statut)}


# ─────────────────────────── APPEL D'OFFRE ──────────────────────────────────

@frappe.whitelist()
def prepare_ao(name: str) -> dict:
    _check_role()
    doc = frappe.get_doc("Appel Offre KYA", name)
    rows = []
    for f in doc.fournisseurs:
        email = _supplier_email(f.fournisseur, f.email)
        rows.append({
            "rowname": f.name, "idx": f.idx,
            "fournisseur_nom": f.fournisseur_nom or f.fournisseur or "(sans nom)",
            "email": email, "has_email": bool(email),
            "already_sent": bool(f.envoye),
        })
    num = doc.numero_ao or name
    subject = f"Appel d'Offre N° {num} — KYA-Energy Group"
    limite = formatdate(doc.date_limite) if doc.date_limite else "voir document joint"
    message = (
        f"Bonjour,\n\n"
        f"KYA-Energy Group vous invite à soumissionner à l'appel d'offre "
        f"N° {num} portant sur : {doc.objet or ''}.\n"
        f"Date limite de réponse : {limite}.\n\n"
        f"Veuillez trouver le détail en pièce jointe et nous retourner votre "
        f"meilleure offre.\n\nCordialement,\nKYA-Energy Group"
    )
    return {"fournisseurs": rows, "numero": num, "subject": subject, "message": message}


@frappe.whitelist()
def send_ao(name: str, recipients, subject: str = None, message: str = None) -> dict:
    _check_role()
    recips = json.loads(recipients) if isinstance(recipients, str) else (recipients or [])
    doc = frappe.get_doc("Appel Offre KYA", name)
    att = _attachment("Appel Offre KYA", name, None, "AO")

    sent, skipped = [], []
    for r in recips:
        email = (r.get("email") or "").strip()
        rowname = r.get("rowname")
        label = (r.get("fournisseur_nom")
                 or (frappe.db.get_value("Appel Offre KYA Fournisseur", rowname, "fournisseur_nom") if rowname else None)
                 or email or rowname)
        if not email:
            skipped.append(label)
            continue
        frappe.sendmail(
            recipients=[email],
            subject=subject or f"Appel d'Offre {doc.numero_ao or name}",
            message=(message or "").replace("\n", "<br>"),
            attachments=[att] if att else None,
            reference_doctype="Appel Offre KYA", reference_name=name,
        )
        if rowname and frappe.db.exists("Appel Offre KYA Fournisseur", rowname):
            frappe.db.set_value("Appel Offre KYA Fournisseur", rowname,
                                {"envoye": 1, "date_envoi": now_datetime()},
                                update_modified=False)
        sent.append(email)

    if sent and doc.statut in ("Brouillon", "Validé"):
        frappe.db.set_value("Appel Offre KYA", name, "statut", "Envoyé", update_modified=False)
    frappe.db.commit()
    return {"sent": sent, "skipped": skipped,
            "count_sent": len(sent), "count_skipped": len(skipped), "attached": bool(att)}
