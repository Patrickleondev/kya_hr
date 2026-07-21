"""Réconcilie les rôles en doublon pour que personne ne soit bloqué.

L'organisation KYA a accumulé plusieurs libellés pour un même métier :
« Chef d'Équipe », « Chef Equipe » (sans accent) et « Responsable Equipe »
désignent le même chef ; « DG » et « Directeur Général » la même personne ;
« DAAF » et « DFC » la même direction financière.

Le problème concret (constaté en prod) : les circuits de validation et les
permissions sont câblés sur UN libellé précis — « Chef d'Équipe » avec accent.
Or certains utilisateurs ne portent que « Responsable Equipe » (yves.lawson,
stock.manager, info1.stage) : à une étape « chef », ils sont bloqués, sans
message clair. Quand la RH crée un compte et choisit l'un des doublons, elle
n'a aucun moyen de deviner lequel le système attend.

Correctif : pour chaque groupe de synonymes, tout utilisateur qui détient AU
MOINS un libellé reçoit aussi les autres. Ainsi, quel que soit le doublon
choisi par la RH, l'accès est complet.

Règles de sûreté :
- **Purement additif** : on n'enlève jamais un rôle. Aucun accès n'est retiré.
- **Idempotent** : relançable sans effet de bord.
- On ne touche QUE des libellés qui existent réellement comme Role.
- On ne fusionne PAS des rôles hiérarchiquement différents (DGA ≠ DG ;
  Comptable n'est PAS remonté au niveau DAAF/DFC).
"""
import frappe

# Groupes de rôles STRICTEMENT équivalents (même fonction, libellés multiples).
# Ne jamais y mêler un rôle de niveau différent.
GROUPES_SYNONYMES: list[list[str]] = [
    ["Chef d'Équipe", "Chef Equipe", "Responsable Equipe", "Responsable d'Équipe"],
    ["Directeur Général", "DG"],
    ["DAAF", "DFC"],
    ["Responsable des Stagiaires", "Responsable Stagiaires", "Resp. Stagiaires"],
]

_IGNORER = {"Administrator", "Guest"}


def _groupes_reels() -> list[list[str]]:
    """Ne garde que les libellés existant réellement comme Role, et les groupes
    d'au moins deux membres (sinon rien à réconcilier)."""
    out = []
    for grp in GROUPES_SYNONYMES:
        reels = [r for r in grp if frappe.db.exists("Role", r)]
        if len(reels) >= 2:
            out.append(reels)
    return out


def reconcilier_utilisateur(user: str, groupes=None, dry_run: bool = False) -> list[str]:
    """Complète les rôles d'UN utilisateur. Retourne les rôles ajoutés."""
    if not user or user in _IGNORER:
        return []
    groupes = groupes or _groupes_reels()
    actuels = set(frappe.get_roles(user))
    a_ajouter = []
    for grp in groupes:
        presents = [r for r in grp if r in actuels]
        if not presents:
            continue  # l'utilisateur n'appartient pas à ce métier
        for r in grp:
            if r not in actuels:
                a_ajouter.append(r)
    if a_ajouter and not dry_run:
        doc = frappe.get_doc("User", user)
        for r in a_ajouter:
            doc.append("roles", {"role": r})
        doc.flags.ignore_permissions = True
        # save() suffit ; on évite add_roles qui recharge tout le doc à chaque rôle.
        doc.save(ignore_permissions=True)
    return a_ajouter


def execute(dry_run: int = 0) -> dict:
    """Réconcilie tous les utilisateurs. Branché sur after_migrate."""
    dry_run = int(dry_run or 0)
    groupes = _groupes_reels()
    res = {"groupes": groupes, "modifies": [], "total_utilisateurs": 0, "dry_run": bool(dry_run)}
    if not groupes:
        return res

    # Utilisateurs concernés = ceux qui portent au moins un libellé d'un groupe.
    tous = {r for grp in groupes for r in grp}
    users = frappe.get_all("Has Role",
                           filters={"role": ["in", list(tous)], "parenttype": "User"},
                           pluck="parent", distinct=True) or []
    res["total_utilisateurs"] = len(set(users))
    for user in sorted(set(users)):
        if user in _IGNORER:
            continue
        try:
            ajouts = reconcilier_utilisateur(user, groupes, dry_run=bool(dry_run))
            if ajouts:
                res["modifies"].append({"user": user, "ajoutes": ajouts})
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             "reconcile_duplicate_roles: %s" % user)
    if not dry_run:
        frappe.db.commit()
    return res


@frappe.whitelist()
def apercu() -> dict:
    """Simulation lisible depuis le desk (ne modifie rien)."""
    if "System Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw("Réservé aux administrateurs.")
    return execute(dry_run=1)
