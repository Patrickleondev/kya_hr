# -*- coding: utf-8 -*-
"""API du Planning de Congé d'Équipe.

- get_my_teams      : équipes dont l'utilisateur courant est le chef
- get_membres_equipe: membres actifs d'une équipe (+ le chef)
- soumettre_planning: crée le Planning d'Équipe et l'envoie à la RH
- get_calendrier    : données du calendrier annuel des congés
"""
import json

import frappe
from frappe import _
from frappe.utils import date_diff, getdate

_RH_ROLES = {"Responsable RH", "HR Manager", "HR User", "System Manager",
             "Directeur Général", "DGA"}


def _current_employee():
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


def _user_roles():
    return set(frappe.get_roles(frappe.session.user))


def _teams_for(employee):
    """Équipes dont `employee` est le chef."""
    if not employee:
        return []
    return frappe.get_all(
        "Equipe KYA",
        filters={"chef_equipe": employee},
        fields=["name", "nom_equipe", "departement", "chef_equipe", "chef_equipe_name"],
    )


@frappe.whitelist()
def get_my_teams():
    """Retourne les équipes pilotées par l'utilisateur (chef), ou toutes pour la RH."""
    emp = _current_employee()
    is_rh = bool(_RH_ROLES.intersection(_user_roles()))
    if is_rh and not _teams_for(emp):
        teams = frappe.get_all(
            "Equipe KYA",
            fields=["name", "nom_equipe", "departement", "chef_equipe", "chef_equipe_name"],
            order_by="nom_equipe asc",
        )
    else:
        teams = _teams_for(emp)
    return {"is_rh": is_rh, "employee": emp, "teams": teams}


@frappe.whitelist()
def get_membres_equipe(equipe):
    """Membres actifs d'une équipe (inclut le chef même s'il n'est pas membre)."""
    if not equipe:
        return {"membres": []}
    membres = frappe.get_all(
        "Employee",
        filters={"custom_kya_equipe": equipe, "status": "Active"},
        fields=["name", "employee_name", "designation"],
        order_by="employee_name asc",
    )
    chef = frappe.db.get_value("Equipe KYA", equipe, "chef_equipe")
    if chef and not any(m["name"] == chef for m in membres):
        cn = frappe.db.get_value("Employee", chef, ["employee_name", "designation"], as_dict=True)
        if cn:
            membres.insert(0, {"name": chef, "employee_name": cn.employee_name,
                               "designation": cn.designation})
    return {"membres": membres}


@frappe.whitelist()
def soumettre_planning(equipe, annee, lignes, commentaire_chef=None):
    """Crée le Planning d'Équipe et l'envoie directement à la RH (En attente RH)."""
    if isinstance(lignes, str):
        lignes = json.loads(lignes)
    if not equipe:
        frappe.throw(_("Équipe manquante."))
    if not lignes:
        frappe.throw(_("Aucune période saisie."))

    emp = _current_employee()
    chef = frappe.db.get_value("Equipe KYA", equipe, "chef_equipe")
    is_priv = bool(_RH_ROLES.intersection(_user_roles()))
    if not is_priv and emp != chef:
        frappe.throw(_("Seul le chef de cette équipe (ou la RH) peut soumettre ce planning."),
                     frappe.PermissionError)

    doc = frappe.new_doc("Planning Conge Equipe")
    doc.equipe = equipe
    doc.annee = int(annee)
    doc.commentaire_chef = commentaire_chef
    for l in lignes:
        if not (l.get("employee") and l.get("date_debut") and l.get("date_fin")):
            continue
        doc.append("lignes", {
            "employee": l["employee"],
            "date_debut": l["date_debut"],
            "date_fin": l["date_fin"],
            "type_conge": l.get("type_conge") or "Congé Annuel",
            "remarque": l.get("remarque"),
        })
    if not doc.lignes:
        frappe.throw(_("Aucune période valide (employé + dates) à enregistrer."))

    # Insertion à l'état initial Brouillon (exigé par le moteur de workflow),
    # puis passage direct « En attente RH » via db_set : on évite la validation
    # de transition (le contrôle d'accès est déjà fait ci-dessus : chef ou RH).
    doc.flags.ignore_permissions = True
    doc.insert()
    doc.db_set("workflow_state", "En attente RH", update_modified=False)
    doc.db_set("statut", "En attente RH", update_modified=False)
    frappe.db.commit()

    _notify_rh(doc)
    return {"name": doc.name, "nb_lignes": len(doc.lignes)}


def _notify_rh(doc):
    try:
        recipients = []
        for role in ("Responsable RH", "HR Manager"):
            recipients += frappe.get_all(
                "Has Role",
                filters={"role": role, "parenttype": "User"},
                pluck="parent",
            )
        recipients = [r for r in set(recipients) if r not in ("Administrator", "Guest")]
        if not recipients:
            return
        url = frappe.utils.get_url(f"/app/planning-conge-equipe/{doc.name}")
        frappe.sendmail(
            recipients=recipients,
            subject=_("Planning de congé d'équipe à valider — {0}").format(doc.titre or doc.name),
            message=_(
                "<p>Le chef <b>{chef}</b> a soumis le planning de congé annuel de son équipe "
                "<b>{equipe}</b> ({nb} période(s), {emp} employé(s)).</p>"
                "<p><a href='{url}'>Ouvrir le planning pour validation</a></p>"
            ).format(chef=doc.chef_equipe_name or "", equipe=doc.equipe,
                     nb=len(doc.lignes), emp=doc.nb_employes, url=url),
            reference_doctype=doc.doctype, reference_name=doc.name,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "planning_equipe._notify_rh")


@frappe.whitelist()
def get_calendrier(annee, equipe=None, departement=None):
    """Données du calendrier annuel : 1 entrée par ligne de congé planifiée,
    colorée selon l'état du planning d'équipe."""
    annee = int(annee)
    conditions = ["pe.docstatus < 2", "pce.annee = %(annee)s"]
    params = {"annee": annee}
    if equipe:
        conditions.append("pce.equipe = %(equipe)s")
        params["equipe"] = equipe
    if departement:
        conditions.append("pce.departement = %(dep)s")
        params["dep"] = departement

    rows = frappe.db.sql(
        f"""
        SELECT pe.employee, pe.employee_name, pe.date_debut, pe.date_fin,
               pe.type_conge, pe.nb_jours,
               pce.name AS planning, pce.equipe, pce.departement,
               pce.chef_equipe_name, pce.workflow_state AS etat
        FROM `tabPlanning Conge Equipe Ligne` pe
        JOIN `tabPlanning Conge Equipe` pce ON pce.name = pe.parent
        WHERE {' AND '.join(conditions)}
        ORDER BY pce.equipe, pe.employee_name, pe.date_debut
        """,
        params, as_dict=True,
    )
    equipes = sorted({r.equipe for r in rows if r.equipe})
    return {"annee": annee, "lignes": rows, "equipes": equipes}
