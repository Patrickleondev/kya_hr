# -*- coding: utf-8 -*-
"""Poste de garde (Guérite) — registre des permissions de sortie APPROUVÉES.

Sur le terrain, l'agent de guérite recueillait les fiches papier signées avant
de laisser sortir un employé/stagiaire. Ici il retrouve, en lecture seule, les
permissions de sortie DÉFINITIVEMENT approuvées (toutes signatures posées) avec
le PDF officiel signé à télécharger. Aucun bouton d'action : la guérite ne fait
que contrôler.
"""
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, today
from urllib.parse import quote

no_cache = 1

# Rôles autorisés à consulter la guérite : l'agent de guérite + la hiérarchie
# qui supervise les sorties (Direction, RH, Responsable des Stagiaires).
_ALLOWED_ROLES = {
    "Guérite", "Directeur Général", "DG", "DGA", "Responsable RH",
    "HR Manager", "Responsable des Stagiaires", "System Manager",
}

_APPROVED = ("Approuvé", "Approuvée", "Approuve")

_SOURCES = [
    {
        "doctype": "Permission Sortie Employe",
        "titre": "Sorties — Employés",
        "print_format": "Ticket Sortie Employe",
        "badge": "Employé",
    },
    {
        "doctype": "Permission Sortie Stagiaire",
        "titre": "Sorties — Stagiaires",
        "print_format": "Ticket Sortie Stagiaire",
        "badge": "Stagiaire",
    },
]


def _fmt_heure(v):
    if not v:
        return ""
    s = str(v)
    # "08:00:00" -> "08:00"
    return s[:5] if len(s) >= 5 else s


def _collect(source, limit=200):
    dt = source["doctype"]
    if not frappe.db.exists("DocType", dt):
        return []
    fields = ["name", "employee_name", "department", "date_sortie",
              "heure_depart", "heure_retour", "motif", "workflow_state", "modified"]
    meta = frappe.get_meta(dt)
    fields = [f for f in fields if f == "name" or meta.has_field(f)]
    try:
        rows = frappe.get_all(
            dt,
            filters=[["workflow_state", "in", _APPROVED]],
            fields=fields,
            order_by="date_sortie desc, modified desc",
            limit_page_length=limit,
            ignore_permissions=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "guerite: collect " + dt)
        return []

    tj = getdate(today())
    out = []
    for r in rows:
        ds = getdate(r.date_sortie) if r.get("date_sortie") else None
        out.append({
            "doctype": dt,
            "name": r.name,
            "employe": r.get("employee_name") or "—",
            "departement": r.get("department") or "",
            "date_sortie": r.get("date_sortie"),
            "date_label": formatdate(r.date_sortie, "EEE d MMM y") if r.get("date_sortie") else "—",
            "heure_depart": _fmt_heure(r.get("heure_depart")),
            "heure_retour": _fmt_heure(r.get("heure_retour")),
            "motif": r.get("motif") or "",
            "badge": source["badge"],
            "print_format": source["print_format"],
            "pdf_url": (
                "/api/method/frappe.utils.print_format.download_pdf"
                "?doctype=" + quote(dt)
                + "&name=" + quote(r.name)
                + "&format=" + quote(source["print_format"])
                + "&_lang=fr"
            ),
            "is_today": bool(ds and ds == tj),
            "is_past": bool(ds and ds < tj),
        })
    return out


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)
    if not _ALLOWED_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé au poste de garde (Guérite)."), frappe.PermissionError)

    groupes = []
    total = 0
    total_today = 0
    for src in _SOURCES:
        lignes = _collect(src)
        total += len(lignes)
        total_today += sum(1 for l in lignes if l["is_today"])
        groupes.append({"titre": src["titre"], "badge": src["badge"], "lignes": lignes})

    context.groupes = groupes
    context.total = total
    context.total_today = total_today
    context.date_str = formatdate(today(), "EEEE d MMMM y")
    context.no_breadcrumbs = True
    return context
