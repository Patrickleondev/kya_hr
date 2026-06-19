# -*- coding: utf-8 -*-
"""Logique serveur pour « Planning Conge Equipe ».

Le chef d'équipe saisit, en début d'année, les périodes de congé prévues
pour chacun de ses collègues. Le flux est : Chef → RH → DG → Approuvé.
À l'approbation DG, un « Planning Conge » individuel est généré pour chaque
employé concerné, ce qui déclenche la chaîne existante (leave_bridge →
Leave Application HRMS → décompte des soldes).

Câblé via doc_events dans hooks.py (le DocType est custom:1, donc Frappe ne
charge pas la classe controller).
"""
import frappe
from frappe import _
from frappe.utils import date_diff, getdate


# ──────────────────────────────────────────────────────────────────────────
#  Calculs & validations (before_save / validate)
# ──────────────────────────────────────────────────────────────────────────
def compute(doc, method=None):
    _compute_lines(doc)
    _validate_lines(doc)
    _set_synthese(doc)
    _set_titre(doc)


def _compute_lines(doc):
    for row in doc.get("lignes") or []:
        if row.date_debut and row.date_fin:
            days = date_diff(row.date_fin, row.date_debut) + 1
            row.nb_jours = max(days, 0)
        else:
            row.nb_jours = 0


def _validate_lines(doc):
    if not (doc.get("lignes") or []):
        frappe.throw(_("Ajoutez au moins une période de congé pour l'équipe."))
    for row in doc.lignes:
        if row.date_debut and row.date_fin and getdate(row.date_fin) < getdate(row.date_debut):
            frappe.throw(
                _("Ligne {0} ({1}) : la date de fin doit être postérieure à la date de début.")
                .format(row.idx, row.employee_name or row.employee or "")
            )
        if doc.annee and row.date_debut and getdate(row.date_debut).year != int(doc.annee):
            frappe.throw(
                _("Ligne {0} : la période ({1}) n'est pas dans l'année du planning ({2}).")
                .format(row.idx, row.date_debut, doc.annee)
            )


def _set_synthese(doc):
    total = 0
    employes = set()
    for row in doc.get("lignes") or []:
        total += int(row.nb_jours or 0)
        if row.employee:
            employes.add(row.employee)
    doc.total_jours = total
    doc.nb_employes = len(employes)


def _set_titre(doc):
    label = doc.get("chef_equipe_name") or doc.get("equipe") or _("Équipe")
    doc.titre = f"{label} — {doc.get('annee') or ''}".strip(" —")


# ──────────────────────────────────────────────────────────────────────────
#  Synchro du champ Select `statut` avec workflow_state
# ──────────────────────────────────────────────────────────────────────────
def sync_statut(doc, method=None):
    state = getattr(doc, "workflow_state", None)
    if not state:
        return
    try:
        if doc.docstatus == 1:
            doc.db_set("statut", state, update_modified=False)
        else:
            doc.statut = state
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────
#  Génération des plannings individuels à l'approbation DG
# ──────────────────────────────────────────────────────────────────────────
def generate_individual_plannings(doc, method=None):
    """Quand le planning d'équipe est Approuvé, crée un « Planning Conge »
    individuel (déjà approuvé) par employé concerné. Idempotent."""
    if getattr(doc, "workflow_state", None) != "Approuvé":
        return
    if doc.get("generes"):
        return
    if doc.flags.get("plannings_equipe_generated"):
        return

    # Regroupe les lignes par employé
    par_employe = {}
    for row in doc.get("lignes") or []:
        if not (row.employee and row.date_debut and row.date_fin and row.type_conge):
            continue
        par_employe.setdefault(row.employee, []).append(row)

    if not par_employe:
        return

    crees, erreurs = [], []
    for employee, rows in par_employe.items():
        # Évite les doublons si un planning a déjà été généré pour cet employé/année
        deja = frappe.db.exists(
            "Planning Conge",
            {"employee": employee, "annee": doc.annee,
             "commentaire_employe": ["like", f"%{doc.name}%"]},
        )
        if deja:
            crees.append(deja)
            continue
        try:
            # Insertion à l'état Brouillon (le DocType Planning Conge a son
            # propre workflow actif), puis passage direct « Approuvé » via
            # db_set (évite la validation de transition), puis submit.
            pc = frappe.get_doc({
                "doctype": "Planning Conge",
                "employee": employee,
                "annee": doc.annee,
                "commentaire_employe": _("Généré depuis le Planning d'Équipe {0}").format(doc.name),
                "periodes": [{
                    "date_debut": r.date_debut,
                    "date_fin": r.date_fin,
                    "type_conge": r.type_conge,
                    "remarque": r.remarque,
                } for r in rows],
            })
            pc.flags.ignore_permissions = True
            pc.flags.skip_solde_validation = True
            pc.insert()
            pc.db_set("workflow_state", "Approuvé", update_modified=False)
            pc.db_set("statut", "Approuvé", update_modified=False)
            pc.reload()
            pc.flags.ignore_permissions = True
            pc.flags.skip_solde_validation = True
            pc.submit()  # déclenche leave_bridge -> Leave Application + soldes
            crees.append(pc.name)
        except Exception as e:
            erreurs.append(f"{employee}: {e}")
            frappe.log_error(frappe.get_traceback(), "generate_individual_plannings")

    # On ne verrouille (generes=1) que si tout est passé : permet de rejouer
    # une génération partielle sans créer de doublons (garde-fou `deja`).
    if crees and not erreurs:
        doc.flags.plannings_equipe_generated = True
    try:
        if crees and not erreurs:
            doc.db_set("generes", 1, update_modified=False)
        doc.db_set("plannings_generes", ", ".join(crees)[:140000], update_modified=False)
    except Exception:
        pass

    if crees:
        frappe.msgprint(
            _("✅ {0} planning(s) individuel(s) généré(s) : {1}").format(len(crees), ", ".join(crees)),
            alert=True, indicator="green",
        )
    if erreurs:
        frappe.msgprint(
            _("⚠️ Erreurs lors de la génération :<br>") + "<br>".join(erreurs),
            alert=True, indicator="orange",
        )
