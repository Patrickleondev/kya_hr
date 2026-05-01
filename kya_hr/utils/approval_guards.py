# -*- coding: utf-8 -*-
"""
KYA-HR — Garde anti auto-approbation pour tous les workflows.

Le but : empêcher qu'un demandeur/créateur fasse passer sa propre demande
à l'étape suivante (chef → RH → DG, etc.). Frappe contrôle déjà côté workflow
via `allow_self_approval=0`, mais cette garde côté Python ferme tout
contournement (db_set direct, scripts serveur, manipulation Desk par un
utilisateur ayant plusieurs rôles, etc.).

Usage dans un controller :

    from kya_hr.utils.approval_guards import block_self_approval

    class DemandeAchatKya(Document):
        def validate(self):
            block_self_approval(self)
            ...
"""
import frappe

# États où le demandeur n'a PAS le droit de pousser sa propre demande.
# (Les états initiaux comme "Brouillon", "En attente Chef" sont autorisés
#  car c'est le créateur lui-même qui soumet).
_FORBIDDEN_STATES = (
    "En attente Chef",          # le demandeur ne peut pas s'auto-passer Chef
    "En attente Chef Service",
    "En attente Chef d'Equipe",
    "En attente RH",
    "En attente Audit",
    "En attente Auditeur",
    "En attente DAAF",
    "En attente DGA",
    "En attente DG",
    "En attente Direction",
    "En attente Magasin",
    "En attente Comptabilité",
    "Approuvé",
    "Validé",
)

# Profils privilégiés autorisés à valider à la place d'autrui (délégation RH).
_PRIVILEGED_ROLES = {"System Manager", "HR Manager", "Responsable RH"}

# Champs Link Employee couramment utilisés pour identifier le demandeur.
# Ordre d'évaluation : on prend le premier champ trouvé sur le doc.
_EMPLOYEE_LINK_FIELDS = (
    "employee",
    "demandeur",
    "redacteur",
    "caissiere",
    "caissier",
    "stagiaire",
    "responsable",
    "operateur",
)


def _get_requester_user(doc):
    """Retourne l'identifiant utilisateur (email) du demandeur du document.

    On regarde d'abord les champs Link Employee connus pour récupérer le
    `user_id` lié, sinon on retombe sur `doc.owner` (le créateur).
    """
    for fieldname in _EMPLOYEE_LINK_FIELDS:
        emp = doc.get(fieldname)
        if emp:
            user_id = frappe.db.get_value("Employee", emp, "user_id")
            if user_id:
                return user_id
            break  # champ employee trouvé mais sans user_id → fallback owner
    return doc.owner


def block_self_approval(doc):
    """Bloque toute transition d'état effectuée par le demandeur lui-même.

    À appeler depuis `validate()` du controller :
        block_self_approval(self)

    - Ne fait rien si le doc est nouveau ou si `workflow_state` n'a pas changé.
    - Ne fait rien pour Administrator ou les profils privilégiés (HR, etc.).
    - Lève frappe.ValidationError si l'utilisateur courant est le demandeur
      et que l'état cible est dans la liste des états d'approbation interdits.
    """
    # Pas de workflow_state sur ce DocType ? Rien à faire.
    if not hasattr(doc, "workflow_state") or not doc.meta.has_field("workflow_state"):
        return

    if doc.is_new() or not doc.has_value_changed("workflow_state"):
        return

    user = frappe.session.user
    if user == "Administrator":
        return

    roles = set(frappe.get_roles(user))
    if _PRIVILEGED_ROLES & roles:
        return

    requester = _get_requester_user(doc)
    if not requester or user != requester:
        return  # ce n'est pas le demandeur qui agit → laisser passer

    target_state = doc.workflow_state or ""
    if target_state in _FORBIDDEN_STATES:
        frappe.throw(
            "Vous ne pouvez pas valider votre propre demande. "
            "Cette action est réservée à votre supérieur hiérarchique "
            "(Chef de Service, RH, Direction).",
            title="Auto-approbation interdite",
        )
