# -*- coding: utf-8 -*-
"""Cockpit RH de la campagne annuelle de planning des congés.

Point d'entrée RH du process : la RH **définit** la campagne d'une année
(période de saisie + échéance + message), l'**ouvre** (génère un brouillon
pré-rempli par équipe et envoie/donne le lien à chaque chef), puis **suit**
qui a soumis. S'appuie sur l'infrastructure existante :
- `Planning Conge Equipe` (le doctype rempli par les chefs, flux Chef→RH→DG) ;
- `kya_hr.planning_equipe_scheduler.ouvrir_campagne` (création des brouillons) ;
- `Campagne Conge KYA` (persistance de la définition côté RH).
"""
import frappe
from frappe import _
from frappe.utils import getdate, today

from kya_hr import planning_equipe_scheduler as sched

RH_ROLES = {"Responsable RH", "HR Manager", "HR User", "System Manager",
            "Directeur Général", "DGA", "DAAF"}

# États du planning d'équipe considérés « soumis » (le chef a fait sa part).
_SOUMIS = ("En attente RH", "En attente DG", "Approuvé")


def _guard():
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter."), frappe.AuthenticationError)
    if not (RH_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw(_("Accès réservé à la RH et à la Direction."), frappe.PermissionError)


def _campagne_doc(annee, create=False):
    name = frappe.db.get_value("Campagne Conge KYA", {"annee": int(annee)})
    if name:
        return frappe.get_doc("Campagne Conge KYA", name)
    if not create:
        return None
    doc = frappe.new_doc("Campagne Conge KYA")
    doc.annee = int(annee)
    doc.statut = "Préparée"
    return doc


def _teams():
    return frappe.get_all(
        "Equipe KYA",
        filters={"chef_equipe": ["is", "set"]},
        fields=["name", "nom_equipe", "chef_equipe", "chef_equipe_name", "departement"],
        order_by="nom_equipe asc",
    )


def _chef_email(chef_emp):
    if not chef_emp:
        return None
    return (frappe.db.get_value("Employee", chef_emp, "user_id")
            or frappe.db.get_value("Employee", chef_emp, "personal_email"))


@frappe.whitelist()
def get_campagne(annee=None):
    """Vue d'ensemble d'une campagne : définition + statut par équipe + KPI."""
    _guard()
    annee = int(annee or getdate(today()).year)
    doc = _campagne_doc(annee)
    definition = {
        "existe": bool(doc),
        "annee": annee,
        "statut": (doc.statut if doc else "Non définie"),
        "date_ouverture": (str(doc.date_ouverture) if doc and doc.date_ouverture else ""),
        "date_limite": (str(doc.date_limite) if doc and doc.date_limite else ""),
        "message_chef": (doc.message_chef if doc else "") or "",
    }

    equipes = []
    kpi = {"total": 0, "lances": 0, "soumis": 0, "approuves": 0, "en_attente": 0, "non_lances": 0}
    for t in _teams():
        kpi["total"] += 1
        plan = frappe.get_all(
            "Planning Conge Equipe",
            filters={"equipe": t["name"], "annee": annee, "docstatus": ["<", 2]},
            fields=["name", "workflow_state", "statut", "nb_employes", "total_jours", "modified"],
            order_by="creation desc", limit=1,
        )
        chef_mail = _chef_email(t["chef_equipe"])
        row = {
            "equipe": t["name"], "nom_equipe": t["nom_equipe"] or t["name"],
            "departement": t["departement"] or "",
            "chef": t["chef_equipe"], "chef_nom": t["chef_equipe_name"] or "—",
            "a_email": bool(chef_mail),
            "lien": sched._planning_equipe_url(t["name"], annee),
            "planning": None, "etat": "Pas lancé",
            "nb_employes": 0, "total_jours": 0, "maj": "",
        }
        if plan:
            p = plan[0]
            etat = p.workflow_state or p.statut or "Brouillon"
            row.update({
                "planning": p.name, "etat": etat,
                "nb_employes": p.nb_employes or 0, "total_jours": p.total_jours or 0,
                "maj": str(p.modified)[:10] if p.modified else "",
            })
            kpi["lances"] += 1
            if etat in _SOUMIS:
                kpi["soumis"] += 1
                if etat == "Approuvé":
                    kpi["approuves"] += 1
            else:
                kpi["en_attente"] += 1  # brouillon lancé mais pas encore soumis
        else:
            kpi["non_lances"] += 1
        equipes.append(row)

    return {"definition": definition, "equipes": equipes, "kpi": kpi,
            "annee": annee, "annees": list(range(annee - 2, annee + 3))}


@frappe.whitelist()
def definir_campagne(annee, date_ouverture=None, date_limite=None, message_chef=None):
    """Crée ou met à jour la définition de campagne (période + message)."""
    _guard()
    doc = _campagne_doc(annee, create=True)
    doc.date_ouverture = date_ouverture or doc.date_ouverture
    doc.date_limite = date_limite or doc.date_limite
    doc.message_chef = message_chef if message_chef is not None else doc.message_chef
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"name": doc.name, "annee": doc.annee, "statut": doc.statut}


@frappe.whitelist()
def ouvrir(annee, envoyer_mails=1):
    """Ouvre la campagne : génère les brouillons par équipe et (option) notifie
    les chefs. Passe la campagne au statut « Ouverte »."""
    _guard()
    annee = int(annee)
    envoyer = str(envoyer_mails) not in ("0", "false", "False", "")
    doc = _campagne_doc(annee, create=True)
    if not doc.date_ouverture:
        doc.date_ouverture = today()
    doc.statut = "Ouverte"
    doc.flags.ignore_permissions = True
    doc.save()

    deadline_label = frappe.utils.formatdate(doc.date_limite) if doc.date_limite else None
    res = sched.ouvrir_campagne(annee, envoyer_mails=envoyer,
                                deadline_label=deadline_label, message_chef=doc.message_chef)
    frappe.db.commit()
    return res


@frappe.whitelist()
def relancer_equipe(equipe, annee):
    """(Re)envoie l'invitation au chef d'UNE équipe (bouton « Envoyer par mail »)."""
    _guard()
    annee = int(annee)
    t = frappe.db.get_value(
        "Equipe KYA", equipe,
        ["name", "nom_equipe", "chef_equipe", "chef_equipe_name", "departement"],
        as_dict=True,
    )
    if not t:
        frappe.throw(_("Équipe introuvable."))
    if not _chef_email(t["chef_equipe"]):
        frappe.throw(_("Le chef de cette équipe n'a pas d'adresse e-mail connue. "
                       "Utilisez « Copier le lien »."))
    plan = frappe.get_all(
        "Planning Conge Equipe",
        filters={"equipe": equipe, "annee": annee, "docstatus": ["<", 2]},
        fields=["name"], order_by="creation desc", limit=1,
    )
    if plan:
        doc = frappe.get_doc("Planning Conge Equipe", plan[0]["name"])
    else:
        # Pas encore de brouillon : on en crée un à la volée pour cette équipe.
        doc = frappe.new_doc("Planning Conge Equipe")
        doc.equipe = equipe
        doc.annee = annee
        sched._prefill_lignes(doc, equipe, annee)
        if not doc.lignes:
            doc.append("lignes", {"type_conge": "Congé Annuel"})
        doc.flags.ignore_permissions = True
        doc.insert()
    campagne = _campagne_doc(annee)
    deadline_label = (frappe.utils.formatdate(campagne.date_limite)
                      if campagne and campagne.date_limite else None)
    message_chef = campagne.message_chef if campagne else None
    ok = sched._email_chef_invitation(doc, t, deadline_label, message_chef)
    frappe.db.commit()
    if not ok:
        frappe.throw(_("L'envoi du mail a échoué (voir Error Log)."))
    return {"ok": True, "equipe": equipe}


@frappe.whitelist()
def cloturer(annee):
    """Clôture la campagne (informatif : les plannings restent modifiables)."""
    _guard()
    doc = _campagne_doc(annee)
    if not doc:
        frappe.throw(_("Aucune campagne définie pour {0}.").format(annee))
    doc.statut = "Clôturée"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"name": doc.name, "statut": doc.statut}
