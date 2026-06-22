# -*- coding: utf-8 -*-
"""API Expression de Besoins de Formation.

- get_equipes_chef     : équipes dont l'utilisateur courant est le chef
- get_besoin_existant  : brouillon existant pour une équipe/année
- save_besoin          : crée ou met à jour un Besoin de Formation
- soumettre_besoin     : passe en "Soumis à la RH"
"""
import json

import frappe
from frappe import _

_RH_ROLES = {"Responsable RH", "HR Manager", "HR User", "System Manager"}


def _emp():
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")


def _is_rh():
    return bool(_RH_ROLES.intersection(set(frappe.get_roles(frappe.session.user))))


@frappe.whitelist()
def get_equipes_chef():
    emp = _emp()
    is_rh = _is_rh()
    # La RH voit TOUJOURS toutes les équipes (même si elle est aussi chef d'une équipe).
    # Un chef (non-RH) ne voit que les équipes dont il est responsable.
    if is_rh:
        teams = frappe.get_all(
            "Equipe KYA",
            fields=["name", "nom_equipe", "departement", "chef_equipe", "chef_equipe_name"],
            order_by="nom_equipe asc",
        )
    else:
        teams = frappe.get_all(
            "Equipe KYA",
            filters={"chef_equipe": emp},
            fields=["name", "nom_equipe", "departement", "chef_equipe", "chef_equipe_name"],
        )
    return {"teams": teams, "employee": emp, "is_rh": is_rh}


@frappe.whitelist()
def get_besoin_existant(equipe, annee):
    """Brouillon éditable pour équipe/année, ou signalement si déjà soumis."""
    rec = frappe.get_all(
        "Besoin de Formation",
        filters={"equipe": equipe, "annee": int(annee), "docstatus": ["<", 2]},
        fields=["name", "statut", "trimestre", "workflow_state"],
        order_by="creation desc", limit=1,
    )
    if not rec:
        return {"existe": False}
    r = rec[0]
    state = r.workflow_state or r.statut or "Brouillon"
    editable = state == "Brouillon"
    lignes = []
    if editable:
        doc = frappe.get_doc("Besoin de Formation", r.name)
        lignes = [{
            "intitule": l.intitule or "",
            "besoin_exprime": l.besoin_exprime or "",
            "objectif": l.objectif or "",
            "competence": l.competence or "",
            "priorite": l.priorite or "Moyenne",
            "employes_concernes": l.employes_concernes or "",
            "nb_participants": l.nb_participants or 1,
            "justification": l.justification or "",
        } for l in doc.lignes]
    return {
        "existe": True, "name": r.name, "statut": state,
        "editable": editable, "lignes": lignes,
        "trimestre": r.trimestre or "",
    }


@frappe.whitelist()
def save_besoin(equipe, annee, trimestre, lignes, doc_name=None):
    """Crée ou met à jour un Besoin de Formation (état Brouillon)."""
    if isinstance(lignes, str):
        lignes = json.loads(lignes)

    emp = _emp()
    chef = frappe.db.get_value("Equipe KYA", equipe, "chef_equipe")
    if not _is_rh() and emp != chef:
        frappe.throw(_("Seul le chef de cette équipe peut saisir un besoin de formation."),
                     frappe.PermissionError)

    if doc_name and frappe.db.exists("Besoin de Formation", doc_name):
        doc = frappe.get_doc("Besoin de Formation", doc_name)
        doc.set("lignes", [])
    else:
        doc = frappe.new_doc("Besoin de Formation")
        doc.equipe = equipe
        doc.chef_equipe = chef

    doc.annee = int(annee)
    doc.trimestre = trimestre or ""

    for l in lignes:
        doc.append("lignes", {
            "intitule": (l.get("intitule") or "").strip(),
            "besoin_exprime": (l.get("besoin_exprime") or "").strip(),
            "objectif": (l.get("objectif") or "").strip(),
            "competence": (l.get("competence") or "").strip(),
            "priorite": l.get("priorite") or "Moyenne",
            "employes_concernes": (l.get("employes_concernes") or "").strip(),
            "nb_participants": int(l.get("nb_participants") or 1),
            "justification": (l.get("justification") or "").strip(),
        })

    if not doc.lignes:
        frappe.throw(_("Ajoutez au moins une formation avant d'enregistrer."))

    doc.flags.ignore_permissions = True
    if doc_name and frappe.db.exists("Besoin de Formation", doc_name):
        doc.save()
    else:
        doc.insert()
    frappe.db.commit()
    return {"name": doc.name, "statut": doc.statut or "Brouillon"}


@frappe.whitelist()
def soumettre_besoin(doc_name):
    """Passe le besoin de Brouillon à 'Soumis à la RH'."""
    doc = frappe.get_doc("Besoin de Formation", doc_name)
    emp = _emp()
    chef = frappe.db.get_value("Equipe KYA", doc.equipe, "chef_equipe")
    if not _is_rh() and emp != chef:
        frappe.throw(_("Seul le chef peut soumettre."), frappe.PermissionError)

    doc.db_set("workflow_state", "Soumis à la RH", update_modified=False)
    doc.db_set("statut", "Soumis à la RH", update_modified=False)
    frappe.db.commit()
    return {"name": doc.name, "statut": "Soumis à la RH"}
