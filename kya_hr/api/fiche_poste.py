# -*- coding: utf-8 -*-
"""API de la page /fiches-poste (self-service).

Réutilise le print format « Fiche de Poste KYA ». Règles d'accès :
- RH / Direction : voient et signent toutes les fiches ;
- l'employé (titulaire) : voit et signe SA fiche ;
- le chef d'équipe : voit les fiches des membres de son équipe (et peut viser en N+1).
La RH remplit le contenu dans le desk ; la page sert surtout à consulter, signer en
ligne (pad) et imprimer.
"""
from urllib.parse import quote

import frappe
from frappe import _
from frappe.translate import print_language

_RH_ROLES = {"Responsable RH", "HR Manager", "HR User", "System Manager",
             "Directeur Général", "DGA"}
_ROLE_FIELD = {"titulaire": "signature_titulaire", "n1": "signature_n1", "drh": "signature_drh"}


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
    if not frappe.db.exists("Fiche de Poste KYA", name):
        frappe.throw(_("Fiche introuvable."))
    employee = frappe.db.get_value("Fiche de Poste KYA", name, "employee")
    me, rh = _me(), _is_rh()
    if role == "titulaire":
        ok = rh or (employee and employee == me)
    elif role == "n1":
        ok = rh or _can_view(employee) and bool(_teams_led(me))
    else:  # drh
        ok = rh
    if not ok:
        frappe.throw(_("Vous n'êtes pas autorisé à apposer cette signature."), frappe.PermissionError)
    frappe.db.set_value("Fiche de Poste KYA", name, _ROLE_FIELD[role], signature)
    frappe.db.commit()
    return {"ok": True, "role": role}
