"""
One-shot script to patch workflow.json:
1. Update "Flux PV Entree Materiel" to add Comptable + Audit steps
2. Add "Flux Retour Materiel KYA" workflow
Run: python patch_workflows.py
"""
import json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
WF_PATH = os.path.join(BASE, "fixtures", "workflow.json")

with open(WF_PATH, encoding="utf-8") as f:
    workflows = json.load(f)

# ── 1. Update PV Entree Materiel workflow ──────────────────────────────────
for wf in workflows:
    if wf.get("document_type") == "PV Entree Materiel":
        wf["states"] = [
            {"state": "Brouillon",           "doc_status": "0", "allow_edit": "Employee",         "update_field": "statut", "update_value": "Brouillon",           "is_optional_state": 0, "send_email": 0},
            {"state": "En attente Magasin",  "doc_status": "0", "allow_edit": "Chargé des Stocks","update_field": "statut", "update_value": "En attente Magasin",  "is_optional_state": 0, "send_email": 1},
            {"state": "En attente Comptable","doc_status": "0", "allow_edit": "Responsable Comptable","update_field": "statut","update_value": "En attente Comptable","is_optional_state": 0,"send_email": 1},
            {"state": "En attente Audit",    "doc_status": "0", "allow_edit": "Auditeur Interne", "update_field": "statut", "update_value": "En attente Audit",    "is_optional_state": 0, "send_email": 1},
            {"state": "Approuvé",            "doc_status": "1", "allow_edit": "Auditeur Interne", "update_field": "statut", "update_value": "Approuvé",            "is_optional_state": 0, "send_email": 1},
            {"state": "Rejeté",              "doc_status": "1", "allow_edit": "Chargé des Stocks","update_field": "statut", "update_value": "Rejeté",              "is_optional_state": 0, "send_email": 1},
        ]
        wf["transitions"] = [
            {"state": "Brouillon",           "action": "Envoyer au Magasin",  "next_state": "En attente Magasin",   "allowed": "Employee",             "allow_self_approval": 1,  "condition": None},
            {"state": "En attente Magasin",  "action": "Réceptionner",        "next_state": "En attente Comptable", "allowed": "Chargé des Stocks",    "allow_self_approval": 0,  "condition": None},
            {"state": "En attente Magasin",  "action": "Réceptionner",        "next_state": "En attente Comptable", "allowed": "Responsable Stock",    "allow_self_approval": 0,  "condition": None},
            {"state": "En attente Magasin",  "action": "Rejeter",             "next_state": "Rejeté",               "allowed": "Chargé des Stocks",    "allow_self_approval": 0,  "condition": None},
            {"state": "En attente Comptable","action": "Valider Comptabilité","next_state": "En attente Audit",     "allowed": "Responsable Comptable","allow_self_approval": 0,  "condition": None},
            {"state": "En attente Comptable","action": "Valider Comptabilité","next_state": "En attente Audit",     "allowed": "Accounts Manager",     "allow_self_approval": 0,  "condition": None},
            {"state": "En attente Comptable","action": "Rejeter",             "next_state": "Rejeté",               "allowed": "Responsable Comptable","allow_self_approval": 0,  "condition": None},
            {"state": "En attente Audit",    "action": "Approuver",           "next_state": "Approuvé",             "allowed": "Auditeur Interne",     "allow_self_approval": 0,  "condition": None},
            {"state": "En attente Audit",    "action": "Approuver",           "next_state": "Approuvé",             "allowed": "System Manager",       "allow_self_approval": 0,  "condition": None},
            {"state": "En attente Audit",    "action": "Rejeter",             "next_state": "Rejeté",               "allowed": "Auditeur Interne",     "allow_self_approval": 0,  "condition": None},
        ]
        print("✓ PV Entree Materiel workflow updated (added Comptable + Audit steps)")
        break

# ── 2. Add Retour Materiel KYA workflow (only if not already there) ────────
existing_names = {wf.get("name", "").lower() for wf in workflows}
if "flux retour matériel kya" not in existing_names and "flux retour materiel kya" not in existing_names:
    retour_wf = {
        "docstatus": 0,
        "doctype": "Workflow",
        "document_type": "Retour Materiel KYA",
        "enable_action_confirmation": 1,
        "is_active": 1,
        "modified": "2026-05-13 00:00:00",
        "name": "Flux Retour Matériel KYA",
        "override_status": 0,
        "send_email_alert": 1,
        "workflow_name": "Flux Retour Matériel KYA",
        "workflow_state_field": "workflow_state",
        "workflow_data": None,
        "states": [
            {"state": "Brouillon",          "doc_status": "0", "allow_edit": "Employee",          "update_field": "statut", "update_value": "Brouillon",          "is_optional_state": 0, "send_email": 0},
            {"state": "En attente Magasin", "doc_status": "0", "allow_edit": "Chargé des Stocks", "update_field": "statut", "update_value": "En attente Magasin", "is_optional_state": 0, "send_email": 1},
            {"state": "Approuvé",           "doc_status": "1", "allow_edit": "Chargé des Stocks", "update_field": "statut", "update_value": "Approuvé",           "is_optional_state": 0, "send_email": 1},
            {"state": "Rejeté",             "doc_status": "1", "allow_edit": "Chargé des Stocks", "update_field": "statut", "update_value": "Rejeté",             "is_optional_state": 0, "send_email": 1},
        ],
        "transitions": [
            {"state": "Brouillon",          "action": "Déclarer le Retour",   "next_state": "En attente Magasin", "allowed": "Employee",             "allow_self_approval": 1, "condition": None},
            {"state": "En attente Magasin", "action": "Réceptionner Retour",  "next_state": "Approuvé",           "allowed": "Chargé des Stocks",    "allow_self_approval": 0, "condition": None},
            {"state": "En attente Magasin", "action": "Réceptionner Retour",  "next_state": "Approuvé",           "allowed": "Responsable Stock",    "allow_self_approval": 0, "condition": None},
            {"state": "En attente Magasin", "action": "Réceptionner Retour",  "next_state": "Approuvé",           "allowed": "System Manager",       "allow_self_approval": 0, "condition": None},
            {"state": "En attente Magasin", "action": "Rejeter",              "next_state": "Rejeté",             "allowed": "Chargé des Stocks",    "allow_self_approval": 0, "condition": None},
            {"state": "En attente Magasin", "action": "Rejeter",              "next_state": "Rejeté",             "allowed": "System Manager",       "allow_self_approval": 0, "condition": None},
        ],
    }
    workflows.append(retour_wf)
    print("✓ Flux Retour Matériel KYA workflow added")
else:
    print("  Retour Materiel KYA workflow already exists, skipping")

# ── Write back ─────────────────────────────────────────────────────────────
with open(WF_PATH, "w", encoding="utf-8") as f:
    json.dump(workflows, f, ensure_ascii=False, indent=1)
print(f"\n✅ workflow.json updated ({len(workflows)} workflows total)")
