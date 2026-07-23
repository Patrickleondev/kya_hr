# -*- coding: utf-8 -*-
"""Effectifs d'équipe — le chef d'équipe met à jour les informations de ses
membres (rôle dans l'équipe, compétences, notes), la Direction visualise le
détail par équipe/employé, l'employé est notifié et suit les changements.

Champs éditables par le chef : ceux dont il a la meilleure connaissance de
terrain. Les mutations « lourdes » (poste, équipe, département) restent du
ressort RH/Direction et sont tracées par le hook Employee.on_update
(`journaliser_mutation`).
"""
import frappe
from frappe import _
from frappe.utils import now_datetime

# Champs de la fiche Employee que le chef d'équipe peut éditer.
CHEF_FIELDS = [
    {"fieldname": "custom_role_equipe", "label": "Rôle dans l'équipe", "type": "Data"},
    {"fieldname": "custom_competences", "label": "Compétences", "type": "Small Text"},
    {"fieldname": "custom_notes_chef", "label": "Notes du chef", "type": "Small Text"},
]
_CHEF_FIELDNAMES = [f["fieldname"] for f in CHEF_FIELDS]
_LABELS = {f["fieldname"]: f["label"] for f in CHEF_FIELDS}

# Champs suivis comme « mutation » (changement structurant) — tracés partout.
MUTATION_FIELDS = {
    "designation": "Poste / Fonction",
    "custom_kya_equipe": "Équipe",
    "department": "Département",
    "custom_kya_categorie": "Catégorie",
    "custom_kya_classe": "Classe",
}

_RH_ROLES = {"Responsable RH", "HR Manager", "HR User", "System Manager"}
_DG_ROLES = {"Directeur Général", "DGA", "DG"}


def _current_employee():
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


def _roles():
    return set(frappe.get_roles(frappe.session.user))


def _is_rh():
    return bool((_RH_ROLES | _DG_ROLES).intersection(_roles()))


def _teams_led_by(employee):
    if not employee:
        return []
    return frappe.get_all("Equipe KYA", filters={"chef_equipe": employee},
                          pluck="name")


def _chef_of_employee(target_emp, me_emp):
    """me_emp est-il le chef d'une équipe contenant target_emp ?"""
    if not (target_emp and me_emp):
        return False
    teams = set(_teams_led_by(me_emp))
    if not teams:
        return False
    eq = frappe.db.get_value("Employee", target_emp, "custom_kya_equipe")
    return eq in teams


# ── Lecture ───────────────────────────────────────────────────────────────────
@frappe.whitelist()
def chef_editable_fields():
    """Schéma des champs éditables par le chef (pour construire le formulaire)."""
    return CHEF_FIELDS


@frappe.whitelist()
def get_board(equipe=None):
    """Tableau de bord des effectifs.

    - Chef d'équipe : ses équipes uniquement.
    - RH / Direction : toutes les équipes (vue détaillée DG).
    Renvoie, par équipe, la liste des membres avec leurs champs éditables +
    contexte RH en lecture seule, et le résumé des dernières modifications.
    """
    me = _current_employee()
    is_rh = _is_rh()
    if is_rh:
        teams = frappe.get_all("Equipe KYA",
                               fields=["name", "nom_equipe", "departement", "chef_equipe_name"],
                               order_by="nom_equipe asc")
    else:
        my_team_names = _teams_led_by(me)
        if not my_team_names:
            return {"is_rh": False, "is_chef": False, "teams": []}
        teams = frappe.get_all("Equipe KYA", filters={"name": ["in", my_team_names]},
                               fields=["name", "nom_equipe", "departement", "chef_equipe_name"],
                               order_by="nom_equipe asc")
    if equipe:
        teams = [t for t in teams if t["name"] == equipe]

    fields = ["name", "employee_name", "designation", "department", "image",
              "employment_type", "custom_matricule_kya"] + _CHEF_FIELDNAMES
    out_teams = []
    for t in teams:
        membres = frappe.get_all("Employee",
                                 filters={"custom_kya_equipe": t["name"], "status": "Active"},
                                 fields=fields, order_by="employee_name asc")
        out_teams.append({"equipe": t, "membres": membres})
    return {"is_rh": is_rh, "is_chef": bool(_teams_led_by(me)),
            "employee": me, "teams": out_teams,
            "champs": CHEF_FIELDS}


@frappe.whitelist()
def get_membre_fiche(employee):
    """Fiche éditable d'un membre + son historique de modifications."""
    if not employee or not frappe.db.exists("Employee", employee):
        frappe.throw(_("Employé introuvable."))
    me = _current_employee()
    if not (_is_rh() or _chef_of_employee(employee, me)):
        frappe.throw(_("Vous ne pouvez consulter que les membres de votre équipe."),
                     frappe.PermissionError)
    emp = frappe.db.get_value("Employee", employee,
                              ["employee_name", "designation", "department",
                               "custom_kya_equipe"] + _CHEF_FIELDNAMES, as_dict=True)
    histo = frappe.get_all("Modification Info Employe KYA",
                           filters={"employee": employee},
                           fields=["champ", "ancienne_valeur", "nouvelle_valeur",
                                   "type_modif", "modifie_par_nom", "date_modif"],
                           order_by="date_modif desc", limit=20)
    return {"employee": employee, "valeurs": emp, "champs": CHEF_FIELDS, "historique": histo}


# ── Écriture (chef) ───────────────────────────────────────────────────────────
@frappe.whitelist()
def update_membre_info(employee, values):
    """Enregistre les champs éditables d'un membre (chef ou RH), journalise
    chaque changement et notifie l'employé."""
    import json
    if isinstance(values, str):
        values = json.loads(values)
    if not employee or not frappe.db.exists("Employee", employee):
        frappe.throw(_("Employé introuvable."))
    me = _current_employee()
    if not (_is_rh() or _chef_of_employee(employee, me)):
        frappe.throw(_("Seul le chef de l'équipe (ou la RH) peut modifier cette fiche."),
                     frappe.PermissionError)

    doc = frappe.get_doc("Employee", employee)
    equipe = doc.get("custom_kya_equipe")
    changements = []
    for fn in _CHEF_FIELDNAMES:
        if fn not in values:
            continue
        new = (values.get(fn) or "").strip() if isinstance(values.get(fn), str) else values.get(fn)
        old = doc.get(fn) or ""
        if (new or "") == (old or ""):
            continue
        doc.set(fn, new)
        changements.append((fn, old, new))

    if not changements:
        return {"updated": 0}

    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True
    doc.save()

    for fn, old, new in changements:
        _journaliser(employee, doc.employee_name, equipe, _LABELS.get(fn, fn),
                     old, new, "Info")
    _notifier_employe(employee, doc.employee_name,
                      [(_LABELS.get(fn, fn), new) for fn, _o, new in changements], "Info")
    frappe.db.commit()
    return {"updated": len(changements),
            "champs": [_LABELS.get(fn, fn) for fn, _o, _n in changements]}


# ── Journalisation & notifications ────────────────────────────────────────────
def _journaliser(employee, employee_name, equipe, champ, old, new, type_modif):
    try:
        m = frappe.new_doc("Modification Info Employe KYA")
        m.employee = employee
        m.employee_name = employee_name
        m.equipe = equipe
        m.champ = champ
        m.ancienne_valeur = str(old or "")
        m.nouvelle_valeur = str(new or "")
        m.type_modif = type_modif
        m.date_modif = now_datetime()
        m.flags.ignore_permissions = True
        m.insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "equipe_membres._journaliser")


def _notifier_employe(employee, employee_name, champs_values, type_modif):
    """Mail à l'employé résumant la mise à jour de sa fiche (Phase 3)."""
    try:
        user = frappe.db.get_value("Employee", employee, "user_id")
        if not user or user in ("Administrator", "Guest"):
            return
        lignes = "".join(
            "<li><b>{0}</b> : {1}</li>".format(frappe.utils.escape_html(c),
                                               frappe.utils.escape_html(str(v or "—")))
            for c, v in champs_values)
        titre = ("Votre fiche a été mise à jour" if type_modif == "Info"
                 else "Mise à jour de votre situation (mutation)")
        frappe.sendmail(
            recipients=[user],
            subject="[KYA] {0}".format(titre),
            message=(
                "<p>Bonjour {nom},</p>"
                "<p>Les informations suivantes de votre fiche viennent d'être mises à jour :</p>"
                "<ul>{lignes}</ul>"
                "<p>Vous pouvez les consulter depuis <a href='{url}'>Mon Espace</a>.</p>"
                "<p>— Ressources Humaines, KYA-Energy Group</p>"
            ).format(nom=employee_name or "", lignes=lignes,
                     url=frappe.utils.get_url("/mon-espace")),
            reference_doctype="Employee", reference_name=employee,
            now=False,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "equipe_membres._notifier_employe")


def journaliser_mutation(doc, method=None):
    """Hook Employee.on_update : trace toute mutation structurante (poste,
    équipe, département…) et notifie l'employé, quelle que soit l'origine
    (desk RH, board, import)."""
    try:
        before = doc.get_doc_before_save()
        if not before:
            return
        changements = []
        for fn, label in MUTATION_FIELDS.items():
            old = before.get(fn)
            new = doc.get(fn)
            if (old or "") != (new or ""):
                changements.append((fn, label, old, new))
        if not changements:
            return
        equipe = doc.get("custom_kya_equipe")
        for fn, label, old, new in changements:
            _journaliser(doc.name, doc.employee_name, equipe, label, old, new, "Mutation")
        _notifier_employe(doc.name, doc.employee_name,
                          [(label, new) for _fn, label, _o, new in changements], "Mutation")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "equipe_membres.journaliser_mutation")


# ── Suivi côté employé (Phase 3) ──────────────────────────────────────────────
@frappe.whitelist()
def mes_modifications(limit=15):
    """Historique des mises à jour de la fiche de l'utilisateur courant."""
    emp = _current_employee()
    if not emp:
        return []
    rows = frappe.get_all("Modification Info Employe KYA",
                          filters={"employee": emp},
                          fields=["name", "champ", "nouvelle_valeur", "type_modif",
                                  "modifie_par_nom", "date_modif", "vu_par_employe"],
                          order_by="date_modif desc", limit=int(limit or 15))
    return rows


@frappe.whitelist()
def marquer_vu():
    """L'employé accuse réception : marque ses modifications comme vues."""
    emp = _current_employee()
    if not emp:
        return {"ok": False}
    frappe.db.set_value("Modification Info Employe KYA",
                        {"employee": emp, "vu_par_employe": 0},
                        "vu_par_employe", 1, update_modified=False)
    frappe.db.commit()
    return {"ok": True}


# ── Consignes RH aux chefs ────────────────────────────────────────────────────
@frappe.whitelist()
def envoyer_consignes_chefs(message_perso=None):
    """La RH envoie aux chefs d'équipe le mode d'emploi pour mettre à jour les
    informations de leurs membres."""
    if not _is_rh():
        frappe.throw(_("Réservé à la RH et à la Direction."), frappe.PermissionError)
    chefs = frappe.get_all("Equipe KYA", filters={"chef_equipe": ["is", "set"]},
                           fields=["chef_equipe", "nom_equipe"])
    dests = {}
    for c in chefs:
        u = frappe.db.get_value("Employee", c["chef_equipe"], "user_id")
        if u and u not in ("Administrator", "Guest"):
            dests.setdefault(u, []).append(c["nom_equipe"])
    if not dests:
        return {"envoyes": 0}
    etapes = (
        "<ol>"
        "<li>Ouvrez <a href='{url}'>Effectifs de mon équipe</a> (ou « Mon Espace » → Gestion de mon Équipe).</li>"
        "<li>Sélectionnez votre équipe, puis un membre.</li>"
        "<li>Renseignez son <b>rôle dans l'équipe</b>, ses <b>compétences</b> et vos <b>notes</b>.</li>"
        "<li>Enregistrez : le membre est notifié et la Direction voit la mise à jour.</li>"
        "<li>Pour un changement de poste, d'équipe ou de département (mutation), contactez la RH.</li>"
        "</ol>"
    ).format(url=frappe.utils.get_url("/equipe-effectifs"))
    envoyes = 0
    for user, equipes in dests.items():
        try:
            frappe.sendmail(
                recipients=[user],
                subject="[KYA] Mise à jour des informations de votre équipe",
                message=(
                    "<p>Bonjour,</p>"
                    "<p>Merci de tenir à jour les informations des membres de votre équipe "
                    "({eq}). Voici les étapes :</p>{etapes}"
                    "{perso}"
                    "<p>— Ressources Humaines, KYA-Energy Group</p>"
                ).format(eq=", ".join(equipes), etapes=etapes,
                         perso=("<p><i>{0}</i></p>".format(frappe.utils.escape_html(message_perso))
                                if message_perso else "")),
                now=False,
            )
            envoyes += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), "equipe_membres.envoyer_consignes_chefs")
    return {"envoyes": envoyes}
