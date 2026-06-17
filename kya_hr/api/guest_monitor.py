# -*- coding: utf-8 -*-
"""API d'intégration — KYA Guest Monitor (app du collègue 'kya-guest').

L'app enregistre des VISITES de visiteurs et les synchronise vers ce serveur
Frappe central. Ces endpoints reçoivent ces visites dans le DocType
« KYA Guest Visit » (idempotent par 'external_id' = champ 'id' de la source).

Authentification : clé API Frappe d'un compte de service dédié
    Authorization: token <api_key>:<api_secret>
Le compte de service doit avoir le rôle « KYA Integration » (ou System
Manager). Voir integration_kya/API_GUEST_MONITOR.md.
"""
from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import get_datetime

DOCTYPE = "KYA Guest Visit"
INTEGRATION_ROLES = {"KYA Integration", "System Manager"}

# Champs acceptés depuis la source -> champ DocType (identiques ici).
_VISIT_FIELDS = (
    "nom", "prenom", "numero_piece", "profession", "service_id",
    "personne_visitee", "motif", "statut", "signature", "signature_depart",
)
_VISIT_DATETIMES = ("check_in", "check_out")


def _require_integration():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Authentification requise (clé API)."), frappe.AuthenticationError)
    if not (INTEGRATION_ROLES & set(frappe.get_roles(user))):
        frappe.throw(
            _("Accès réservé au compte de service d'intégration (rôle 'KYA Integration')."),
            frappe.PermissionError,
        )


def _apply_fields(doc, data):
    for f in _VISIT_FIELDS:
        if f in data and data.get(f) is not None:
            doc.set(f, data.get(f))
    for f in _VISIT_DATETIMES:
        if data.get(f):
            doc.set(f, get_datetime(data.get(f)))


@frappe.whitelist(methods=["POST"])
def record_visit(**data):
    """Crée ou met à jour une visite (upsert par 'id' source -> external_id).

    Corps JSON attendu (au moins) : id, nom, prenom. Les autres champs sont
    facultatifs : numero_piece, profession, service_id, personne_visitee,
    motif, statut, check_in, check_out, signature, signature_depart.
    """
    _require_integration()
    external_id = data.get("external_id") or data.get("id")
    if not external_id:
        frappe.throw(_("Le champ 'id' (identifiant source) est requis."))
    external_id = str(external_id)

    if frappe.db.exists(DOCTYPE, external_id):
        doc = frappe.get_doc(DOCTYPE, external_id)
        _apply_fields(doc, data)
        doc.save(ignore_permissions=True)
        action = "updated"
    else:
        doc = frappe.new_doc(DOCTYPE)
        doc.external_id = external_id
        _apply_fields(doc, data)
        if not doc.statut:
            doc.statut = "En cours"
        if not doc.check_in:
            doc.check_in = frappe.utils.now_datetime()
        doc.insert(ignore_permissions=True)
        action = "created"

    frappe.db.commit()
    return {"ok": True, "action": action, "name": doc.name, "external_id": external_id}


@frappe.whitelist(methods=["POST"])
def checkout_visit(external_id=None, id=None, check_out=None, signature_depart=None):
    """Marque le départ d'un visiteur (statut 'Termine')."""
    _require_integration()
    external_id = str(external_id or id or "")
    if not external_id:
        frappe.throw(_("'id' requis."))
    if not frappe.db.exists(DOCTYPE, external_id):
        frappe.throw(_("Visite introuvable : {0}").format(external_id))
    doc = frappe.get_doc(DOCTYPE, external_id)
    doc.statut = "Termine"
    doc.check_out = get_datetime(check_out) if check_out else frappe.utils.now_datetime()
    if signature_depart:
        doc.signature_depart = signature_depart
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "name": doc.name, "statut": doc.statut,
            "check_out": str(doc.check_out)}


@frappe.whitelist()
def get_visit(external_id=None, id=None):
    """Récupère une visite par son identifiant source."""
    _require_integration()
    external_id = str(external_id or id or "")
    if not frappe.db.exists(DOCTYPE, external_id):
        return {"ok": False, "found": False}
    doc = frappe.get_doc(DOCTYPE, external_id)
    return {"ok": True, "found": True, "visit": doc.as_dict()}
