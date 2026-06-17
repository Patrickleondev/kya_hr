# -*- coding: utf-8 -*-
"""API Dashboard Formation KYA — pilotage RH du circuit de formation.

Fournit à /formation-dashboard : KPIs + tables (besoins à revoir, plans par
statut, suivi des formations, coûts). Rôles : RH, DG/DGA, System Manager.
"""
from __future__ import annotations

import frappe
from frappe.utils import flt


FORMATION_ROLES = {
    "System Manager", "Responsable RH", "HR Manager",
    "Directeur Général", "DG", "DGA",
}


def _check_role():
    if not (set(frappe.get_roles(frappe.session.user)) & FORMATION_ROLES):
        frappe.throw("Accès réservé (RH / Direction).", frappe.PermissionError)


def _exists(dt):
    return bool(frappe.db.exists("DocType", dt))


@frappe.whitelist()
def get_overview() -> dict:
    _check_role()
    out = {
        "besoins_a_revoir": 0, "besoins_total": 0,
        "plans_en_cours": 0, "formations_en_suivi": 0,
        "formations_terminees": 0, "cout_total_valide": 0.0,
    }
    if _exists("Besoin de Formation"):
        out["besoins_total"] = frappe.db.count("Besoin de Formation")
        out["besoins_a_revoir"] = frappe.db.count(
            "Besoin de Formation", {"statut": ["in", ["Soumis à la RH", "En revue RH"]]})
    if _exists("Plan de Formation"):
        out["plans_en_cours"] = frappe.db.count(
            "Plan de Formation", {"statut": ["not in", ["Clôturé"]]})
        row = frappe.db.sql(
            """SELECT COALESCE(SUM(cout_total),0) FROM `tabPlan de Formation`
               WHERE statut IN ('Validé','En suivi','Clôturé')""")
        out["cout_total_valide"] = flt(row[0][0]) if row else 0.0
    if _exists("Plan Formation Item"):
        out["formations_en_suivi"] = frappe.db.count(
            "Plan Formation Item", {"retenu_dg": 1, "statut_suivi": ["in", ["Planifiée", "En cours"]]})
        out["formations_terminees"] = frappe.db.count(
            "Plan Formation Item", {"retenu_dg": 1, "statut_suivi": "Terminée"})
    return out


@frappe.whitelist()
def get_besoins(limit: int = 50) -> list[dict]:
    _check_role()
    if not _exists("Besoin de Formation"):
        return []
    return frappe.db.sql(
        """SELECT name, equipe, chef_equipe_name AS chef, annee, trimestre,
                  statut, date_soumission,
                  (SELECT COUNT(*) FROM `tabBesoin Formation Item` i WHERE i.parent = b.name) AS nb_lignes,
                  (SELECT COUNT(*) FROM `tabBesoin Formation Item` i WHERE i.parent = b.name AND i.statut_rh='Retenu') AS nb_retenus
           FROM `tabBesoin de Formation` b
           ORDER BY (b.statut='Soumis à la RH') DESC, b.modified DESC
           LIMIT %(l)s""", {"l": int(limit)}, as_dict=True) or []


@frappe.whitelist()
def get_plans(limit: int = 50) -> list[dict]:
    _check_role()
    if not _exists("Plan de Formation"):
        return []
    return frappe.db.sql(
        """SELECT name, titre, annee, statut, nb_formations, nb_retenues_dg,
                  cout_total, date_soumission_dg
           FROM `tabPlan de Formation`
           ORDER BY modified DESC LIMIT %(l)s""", {"l": int(limit)}, as_dict=True) or []


def _rh_only():
    if not (set(frappe.get_roles(frappe.session.user)) & {"System Manager", "Responsable RH", "HR Manager"}):
        frappe.throw("Action réservée à la RH.", frappe.PermissionError)


@frappe.whitelist()
def compile_year(annee, titre=None):
    """1 clic RH : crée/complète le Plan de l'année en important les lignes
    'Retenu' des besoins, puis renvoie le plan + le nombre de lignes ajoutées."""
    _rh_only()
    from frappe.utils import cint
    annee = cint(annee)
    if not annee:
        frappe.throw("Année invalide.")
    plan_name = frappe.db.get_value("Plan de Formation", {"annee": annee}, "name")
    if plan_name:
        plan = frappe.get_doc("Plan de Formation", plan_name)
    else:
        plan = frappe.new_doc("Plan de Formation")
        plan.titre = titre or ("Plan de Formation %s" % annee)
        plan.annee = annee
        plan.statut = "Compilé"
        plan.workflow_state = "Compilé"
        plan.insert(ignore_permissions=True)
    added = plan.compiler_depuis_besoins(annee)
    plan.save(ignore_permissions=True)
    frappe.db.commit()
    return {"plan": plan.name, "added": added, "total": len(plan.lignes or [])}


@frappe.whitelist()
def get_besoins_by_team(annee=None):
    """Vue DG : besoins regroupés PAR ÉQUIPE, avec les lignes retenues par la RH
    (ce que le DG doit arbitrer). Inclut les employés concernés."""
    _check_role()
    if not _exists("Besoin de Formation"):
        return []
    from frappe.utils import cint
    filters = {"statut": ["in", ["En revue RH", "Traité", "Soumis à la RH"]]}
    if annee:
        filters["annee"] = cint(annee)
    besoins = frappe.get_all("Besoin de Formation", filters=filters,
                             fields=["name", "equipe", "chef_equipe_name", "annee", "trimestre", "statut"],
                             order_by="equipe asc")
    out = []
    for b in besoins:
        lignes = frappe.get_all(
            "Besoin Formation Item", filters={"parent": b.name},
            fields=["intitule", "competence", "priorite", "employes_concernes",
                    "nb_participants", "justification", "statut_rh"],
            order_by="idx asc")
        # On présente au DG en priorité les lignes retenues par la RH
        retenues = [l for l in lignes if l.statut_rh == "Retenu"]
        out.append({
            "besoin": b.name, "equipe": b.equipe, "chef": b.chef_equipe_name,
            "annee": b.annee, "trimestre": b.trimestre, "statut": b.statut,
            "nb_total": len(lignes), "nb_retenues": len(retenues),
            "lignes": retenues or lignes,
        })
    return out


@frappe.whitelist()
def save_dg_selection(plan, decisions):
    """DG : enregistre la sélection (retenu_dg + motif) par ligne du plan.
    `decisions` = JSON [{"idx": 1, "retenu": 1, "motif": "..."}]."""
    if not (set(frappe.get_roles(frappe.session.user)) & {"System Manager", "Directeur Général", "DG", "DGA"}):
        frappe.throw("Sélection réservée à la Direction.", frappe.PermissionError)
    decisions = frappe.parse_json(decisions) if isinstance(decisions, str) else (decisions or [])
    doc = frappe.get_doc("Plan de Formation", plan)
    by_idx = {int(d.get("idx")): d for d in decisions}
    for row in doc.lignes:
        if row.idx in by_idx:
            d = by_idx[row.idx]
            row.retenu_dg = 1 if d.get("retenu") else 0
            if d.get("motif") is not None:
                row.motif_dg = d.get("motif")
    # On NE change PAS le workflow_state ici : la transition d'état (vers
    # « Sélection DG ») reste l'action workflow dédiée du DG. On persiste juste
    # les cases cochées ; validate() recalcule nb_retenues_dg + cout_total.
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"plan": doc.name, "retenues": doc.nb_retenues_dg, "cout_total": doc.cout_total}


def _dg_only():
    if not (set(frappe.get_roles(frappe.session.user)) & {"System Manager", "Directeur Général", "DG", "DGA"}):
        frappe.throw("Action réservée à la Direction.", frappe.PermissionError)


@frappe.whitelist()
def get_plans_for_dg() -> list[dict]:
    """Plans que le DG doit arbitrer (soumis) ou en cours d'arbitrage."""
    _check_role()
    if not _exists("Plan de Formation"):
        return []
    return frappe.db.sql(
        """SELECT name, titre, annee, statut, workflow_state,
                  nb_formations, nb_retenues_dg, cout_total
           FROM `tabPlan de Formation`
           WHERE statut IN ('Soumis au DG', 'Sélection DG')
           ORDER BY (statut='Soumis au DG') DESC, annee DESC, modified DESC""",
        as_dict=True) or []


@frappe.whitelist()
def get_plan_lignes(plan) -> dict:
    """Détail d'un plan pour l'écran de sélection DG : chaque ligne avec son
    idx (clé pour save_dg_selection) + l'état actuel des cases retenu_dg."""
    _check_role()
    doc = frappe.get_doc("Plan de Formation", plan)
    lignes = []
    for row in doc.lignes:
        lignes.append({
            "idx": row.idx,
            "equipe": row.equipe,
            "intitule": row.intitule,
            "priorite": row.priorite,
            "nb_participants": row.nb_participants,
            "justification": row.justification,
            "retenu_dg": 1 if row.retenu_dg else 0,
            "motif_dg": row.motif_dg or "",
        })
    return {
        "plan": doc.name, "titre": doc.titre, "annee": doc.annee,
        "statut": doc.statut, "workflow_state": doc.workflow_state,
        "nb_formations": doc.nb_formations, "nb_retenues_dg": doc.nb_retenues_dg,
        "cout_total": doc.cout_total, "lignes": lignes,
        "can_validate": doc.statut == "Soumis au DG",
    }


@frappe.whitelist()
def submit_dg_selection(plan):
    """DG : applique la transition workflow « Valider la sélection »
    (Soumis au DG -> Sélection DG) après avoir coché les formations retenues.
    On passe par apply_workflow (≠ save) pour respecter le circuit + les perms."""
    _dg_only()
    from frappe.model.workflow import apply_workflow
    doc = frappe.get_doc("Plan de Formation", plan)
    if doc.statut != "Soumis au DG":
        frappe.throw("Ce plan n'est pas en attente de validation DG (statut : %s)." % doc.statut)
    apply_workflow(doc, "Valider la sélection")
    frappe.db.commit()
    return {"plan": doc.name, "statut": doc.statut,
            "retenues": doc.nb_retenues_dg, "cout_total": doc.cout_total}


@frappe.whitelist()
def get_suivi(limit: int = 100) -> list[dict]:
    """Formations retenues par le DG, avec leur statut de suivi."""
    _check_role()
    if not _exists("Plan Formation Item"):
        return []
    return frappe.db.sql(
        """SELECT i.parent AS plan, i.equipe, i.intitule, i.organisme, i.cout,
                  i.date_debut, i.date_fin, i.statut_suivi
           FROM `tabPlan Formation Item` i
           JOIN `tabPlan de Formation` p ON p.name = i.parent
           WHERE i.retenu_dg = 1
           ORDER BY FIELD(i.statut_suivi,'En cours','Planifiée','À planifier','Terminée','Annulée'),
                    i.date_debut ASC
           LIMIT %(l)s""", {"l": int(limit)}, as_dict=True) or []
