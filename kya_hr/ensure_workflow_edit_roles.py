"""Grants DIRECTIONNELS pour que les acteurs des circuits puissent ÉDITER
(et donc signer) la fiche à leur étape de workflow.

Constat prod (26/07/2026, matrice complète scratchpad wf_matrix.json) : chaque
état de workflow Frappe n'autorise l'édition qu'à UN rôle (`allow_edit`). Or
plusieurs signataires légitimes ne portaient pas ce rôle précis :
- « En attente Chef » (Demande Achat, PV Sortie) exige « Chef Service » ;
  seuls 6 chefs sur 10 le portaient — les 4 autres voyaient TOUTE la fiche en
  lecture seule → pad de signature grisé → ils abandonnaient et appelaient.
- « En attente du Supérieur Immédiat » (Congés) / « En attente Chef de
  Service » (Planning) exigent « Supérieur Immédiat » ; 5 chefs sur 10.

Métier confirmé (cf. ensure_chef_capabilities) : Chef Service / Chef d'Équipe /
Chef Equipe / Responsable Equipe désignent LE MÊME chef. Un chef est par
définition le supérieur immédiat de ses membres. On complète donc les rôles.

À la différence de reconcile_duplicate_roles (groupes SYNONYMES bidirectionnels),
les grants sont ICI À SENS UNIQUE : porter « Supérieur Immédiat » seul ne fait
PAS de vous un Chef Service.

Purement additif, idempotent. Wrappé dans safe_migrations.AFTER_MIGRATE.
"""
from __future__ import annotations

import frappe

# rôle(s) détenu(s) -> rôles complémentaires à garantir (sens unique)
GRANTS: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("Chef d'Équipe", "Chef Equipe", "Responsable Equipe", "Responsable d'Équipe"),
     ("Chef Service", "Supérieur Immédiat")),
]

_IGNORER = {"Administrator", "Guest"}


def execute() -> dict:
    ajouts = 0
    detail = []
    for sources, cibles in GRANTS:
        sources = [r for r in sources if frappe.db.exists("Role", r)]
        cibles = [r for r in cibles if frappe.db.exists("Role", r)]
        if not sources or not cibles:
            continue
        porteurs = set(frappe.get_all(
            "Has Role",
            filters={"role": ["in", sources], "parenttype": "User"},
            pluck="parent"))
        for user in sorted(porteurs - _IGNORER):
            if not frappe.db.get_value("User", user, "enabled"):
                continue
            actuels = set(frappe.get_roles(user))
            for role in cibles:
                if role in actuels:
                    continue
                u = frappe.get_doc("User", user)
                u.append("roles", {"role": role})
                u.flags.ignore_permissions = True
                u.save(ignore_permissions=True)
                ajouts += 1
                detail.append(f"{user} += {role}")
    if detail:
        print("  [WF-EDIT] " + " ; ".join(detail))
    return {"ajouts": ajouts, "detail": detail}
