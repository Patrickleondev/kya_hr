# -*- coding: utf-8 -*-
"""Mise en place « Effectifs d'équipe » (Phase 2) :
- champs éditables par le chef sur la fiche Employee (rôle/compétences/notes) ;
- le DocType journal existe déjà (reload-doc) ; on garantit juste les droits.
Idempotent — appelé en AFTER_MIGRATE.
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_champs_chef():
    """Ajoute (si absents) les champs éditables par le chef d'équipe, groupés
    juste après le lien « Équipe » de la classification KYA."""
    fields = {
        "Employee": [
            {
                "fieldname": "custom_role_equipe",
                "label": "Rôle dans l'équipe",
                "fieldtype": "Data",
                "insert_after": "custom_kya_equipe",
                "description": "Renseigné par le chef d'équipe.",
            },
            {
                "fieldname": "custom_competences",
                "label": "Compétences",
                "fieldtype": "Small Text",
                "insert_after": "custom_role_equipe",
                "description": "Compétences clés (chef d'équipe).",
            },
            {
                "fieldname": "custom_notes_chef",
                "label": "Notes du chef",
                "fieldtype": "Small Text",
                "insert_after": "custom_competences",
                "description": "Observations du chef d'équipe.",
            },
        ]
    }
    create_custom_fields(fields, update=True)


def execute():
    ensure_champs_chef()
    frappe.db.commit()
