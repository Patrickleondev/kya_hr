# -*- coding: utf-8 -*-
"""Campagne annuelle automatique du Planning de Congé d'Équipe.

Déclenché par le scheduler (cf. hooks.scheduler_events) :
- `lancer_campagne_annuelle`  : 1er décembre → prépare l'année SUIVANTE.
    Pour chaque équipe ayant un chef : crée un BROUILLON de Planning d'Équipe
    pré-rempli (membres chargés ; périodes reconduites de l'an N-1 si dispo)
    puis envoie un email d'invitation au chef.
- `relancer_campagne`         : ~28 décembre → relance les chefs en retard et
    transmet la liste des équipes sans planning soumis à la RH / DG.

Tout est idempotent : aucune création en double, relances filtrées.
"""
import frappe
from frappe import _
from frappe.utils import getdate


# ── Paramètres (modifiables) ───────────────────────────────────────────────
DEADLINE_LABEL = "31 décembre"   # juste pour les messages


def _target_year():
    """Année préparée par la campagne = année suivante (lancement en décembre)."""
    return getdate().year + 1


def _shift_year(d, year):
    """Décale une date à l'année cible en gardant jour/mois (gère le 29/02)."""
    d = getdate(d)
    try:
        return d.replace(year=year)
    except ValueError:
        return d.replace(year=year, day=28)  # 29/02 -> 28/02 si année non bissextile


def _teams_with_chef():
    return frappe.get_all(
        "Equipe KYA",
        filters={"chef_equipe": ["is", "set"]},
        fields=["name", "nom_equipe", "chef_equipe", "chef_equipe_name", "departement"],
    )


def _members(equipe):
    return frappe.get_all(
        "Employee",
        filters={"custom_kya_equipe": equipe, "status": "Active"},
        fields=["name", "employee_name"],
        order_by="employee_name asc",
    )


def _chef_email(chef_emp):
    if not chef_emp:
        return None
    return (frappe.db.get_value("Employee", chef_emp, "user_id")
            or frappe.db.get_value("Employee", chef_emp, "personal_email"))


def _role_users(*roles):
    out = []
    for r in roles:
        out += frappe.get_all("Has Role", filters={"role": r, "parenttype": "User"}, pluck="parent")
    return [u for u in set(out) if u not in ("Administrator", "Guest")]


# ── Lancement de campagne (1er décembre) ───────────────────────────────────
def lancer_campagne_annuelle():
    annee = _target_year()
    cree, ignore = 0, 0
    for t in _teams_with_chef():
        equipe = t["name"]
        if frappe.db.exists("Planning Conge Equipe", {"equipe": equipe, "annee": annee}):
            ignore += 1
            continue
        try:
            doc = frappe.new_doc("Planning Conge Equipe")
            doc.equipe = equipe
            doc.annee = annee
            doc.commentaire_chef = _("Brouillon généré automatiquement — campagne {0}.").format(annee)
            _prefill_lignes(doc, equipe, annee)
            if not doc.lignes:
                ignore += 1
                continue
            doc.flags.ignore_permissions = True
            doc.insert()
            cree += 1
            _email_chef_invitation(doc, t)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "planning_equipe.lancer_campagne_annuelle")
    frappe.db.commit()
    print(f"[planning_equipe_scheduler] campagne {annee} : {cree} brouillon(s) créé(s), {ignore} ignoré(s).")
    return {"annee": annee, "crees": cree, "ignores": ignore}


def _prefill_lignes(doc, equipe, annee):
    """Reconduit les périodes de l'an N-1 (dates décalées) ; sinon charge juste
    les membres (sans dates) pour que le chef complète."""
    prev = frappe.get_all(
        "Planning Conge Equipe",
        filters={"equipe": equipe, "annee": annee - 1, "docstatus": ["<", 2]},
        fields=["name"], order_by="creation desc", limit=1,
    )
    if prev:
        prev_doc = frappe.get_doc("Planning Conge Equipe", prev[0]["name"])
        for r in prev_doc.lignes:
            if not (r.employee and r.date_debut and r.date_fin):
                continue
            # ne reconduire que les employés encore actifs dans l'équipe
            if frappe.db.get_value("Employee", r.employee, "status") != "Active":
                continue
            doc.append("lignes", {
                "employee": r.employee,
                "date_debut": _shift_year(r.date_debut, annee),
                "date_fin": _shift_year(r.date_fin, annee),
                "type_conge": r.type_conge or "Congé Annuel",
                "remarque": r.remarque,
            })
        if doc.lignes:
            return
    # pas de N-1 exploitable : pré-charge les membres sans dates
    for m in _members(equipe):
        doc.append("lignes", {"employee": m["name"], "type_conge": "Congé Annuel"})


def _email_chef_invitation(doc, team):
    email = _chef_email(team["chef_equipe"])
    if not email:
        return
    url = frappe.utils.get_url("/planning-equipe")
    try:
        frappe.sendmail(
            recipients=[email],
            subject=_("Planning de congé {0} — à compléter pour votre équipe").format(doc.annee),
            message=_(
                "<p>Bonjour {chef},</p>"
                "<p>La campagne de planification des congés <b>{annee}</b> est ouverte. "
                "Un brouillon a été préparé pour votre équipe <b>{equipe}</b> "
                "(membres déjà chargés{recond}).</p>"
                "<p>Merci de <b>renseigner les périodes</b> et de soumettre avant le <b>{deadline}</b> :</p>"
                "<p><a href='{url}'>➡️ Compléter le planning de mon équipe</a></p>"
            ).format(chef=team["chef_equipe_name"] or "", annee=doc.annee, equipe=team["nom_equipe"] or doc.equipe,
                     recond=_(", périodes de l'an passé reconduites") if any(l.date_debut for l in doc.lignes) else "",
                     deadline=DEADLINE_LABEL, url=url),
            reference_doctype=doc.doctype, reference_name=doc.name,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "planning_equipe._email_chef_invitation")


# ── Relance + escalade (~28 décembre) ──────────────────────────────────────
def relancer_campagne():
    annee = _target_year()
    en_retard = []
    for t in _teams_with_chef():
        equipe = t["name"]
        soumis = frappe.db.exists("Planning Conge Equipe", {
            "equipe": equipe, "annee": annee,
            "workflow_state": ["in", ["En attente RH", "En attente DG", "Approuvé"]],
        })
        if soumis:
            continue
        en_retard.append(t)
        _relance_chef(t, annee)
    if en_retard:
        _escalade_rh_dg(en_retard, annee)
    frappe.db.commit()
    print(f"[planning_equipe_scheduler] relance {annee} : {len(en_retard)} équipe(s) en retard.")
    return {"annee": annee, "en_retard": len(en_retard)}


def _relance_chef(team, annee):
    email = _chef_email(team["chef_equipe"])
    if not email:
        return
    url = frappe.utils.get_url("/planning-equipe")
    try:
        frappe.sendmail(
            recipients=[email],
            subject=_("Rappel : planning de congé {0} de votre équipe non soumis").format(annee),
            message=_(
                "<p>Bonjour {chef},</p>"
                "<p>Le planning de congé <b>{annee}</b> de votre équipe <b>{equipe}</b> "
                "n'a pas encore été soumis. Merci de le compléter rapidement "
                "(échéance : <b>{deadline}</b>).</p>"
                "<p><a href='{url}'>➡️ Compléter maintenant</a></p>"
            ).format(chef=team["chef_equipe_name"] or "", annee=annee,
                     equipe=team["nom_equipe"] or team["name"], deadline=DEADLINE_LABEL, url=url),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "planning_equipe._relance_chef")


def _escalade_rh_dg(en_retard, annee):
    recipients = _role_users("Responsable RH", "HR Manager", "Directeur Général", "DGA")
    if not recipients:
        return
    rows = "".join(
        f"<li>{t['nom_equipe'] or t['name']} — chef : {t['chef_equipe_name'] or '—'}</li>"
        for t in en_retard
    )
    try:
        frappe.sendmail(
            recipients=recipients,
            subject=_("Plannings de congé {0} non soumis : {1} équipe(s)").format(annee, len(en_retard)),
            message=_(
                "<p>Les équipes suivantes n'ont pas encore soumis leur planning "
                "de congé <b>{annee}</b> (échéance {deadline}) :</p><ul>{rows}</ul>"
            ).format(annee=annee, deadline=DEADLINE_LABEL, rows=rows),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "planning_equipe._escalade_rh_dg")
