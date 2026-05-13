"""Patch workflow.json: update PV Entree Materiel to use Achats & Stock instead of Magasin."""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
WF_PATH = os.path.join(BASE, "fixtures", "workflow.json")

with open(WF_PATH, encoding="utf-8") as f:
    workflows = json.load(f)

for wf in workflows:
    if wf.get("document_type") == "PV Entree Materiel":
        wf["states"] = [
            {"state": "Brouillon",                "doc_status": "0", "allow_edit": "Employee",             "update_field": "statut", "update_value": "Brouillon",                "is_optional_state": 0, "send_email": 0},
            {"state": "En attente Achats & Stock", "doc_status": "0", "allow_edit": "Chargé des Stocks",  "update_field": "statut", "update_value": "En attente Achats & Stock", "is_optional_state": 0, "send_email": 1},
            {"state": "En attente Comptable",      "doc_status": "0", "allow_edit": "Responsable Comptable","update_field": "statut","update_value": "En attente Comptable",      "is_optional_state": 0, "send_email": 1},
            {"state": "En attente Audit",           "doc_status": "0", "allow_edit": "Auditeur Interne",   "update_field": "statut", "update_value": "En attente Audit",           "is_optional_state": 0, "send_email": 1},
            {"state": "Approuvé",                   "doc_status": "1", "allow_edit": "Auditeur Interne",   "update_field": "statut", "update_value": "Approuvé",                   "is_optional_state": 0, "send_email": 1},
            {"state": "Rejeté",                     "doc_status": "1", "allow_edit": "Chargé des Stocks",  "update_field": "statut", "update_value": "Rejeté",                     "is_optional_state": 0, "send_email": 1},
        ]
        wf["transitions"] = [
            {"state": "Brouillon",                "action": "Déclarer la Réception",   "next_state": "En attente Achats & Stock", "allowed": "Employee",             "allow_self_approval": 1, "condition": None},
            {"state": "En attente Achats & Stock", "action": "Valider Réception Stock","next_state": "En attente Comptable",      "allowed": "Chargé des Stocks",    "allow_self_approval": 0, "condition": None},
            {"state": "En attente Achats & Stock", "action": "Valider Réception Stock","next_state": "En attente Comptable",      "allowed": "Responsable Achats",   "allow_self_approval": 0, "condition": None},
            {"state": "En attente Achats & Stock", "action": "Valider Réception Stock","next_state": "En attente Comptable",      "allowed": "Stock Manager",        "allow_self_approval": 0, "condition": None},
            {"state": "En attente Achats & Stock", "action": "Valider Réception Stock","next_state": "En attente Comptable",      "allowed": "System Manager",       "allow_self_approval": 0, "condition": None},
            {"state": "En attente Achats & Stock", "action": "Rejeter",                "next_state": "Rejeté",                   "allowed": "Chargé des Stocks",    "allow_self_approval": 0, "condition": None},
            {"state": "En attente Comptable",      "action": "Valider Comptabilité",   "next_state": "En attente Audit",          "allowed": "Responsable Comptable","allow_self_approval": 0, "condition": None},
            {"state": "En attente Comptable",      "action": "Valider Comptabilité",   "next_state": "En attente Audit",          "allowed": "Accounts Manager",     "allow_self_approval": 0, "condition": None},
            {"state": "En attente Comptable",      "action": "Valider Comptabilité",   "next_state": "En attente Audit",          "allowed": "System Manager",       "allow_self_approval": 0, "condition": None},
            {"state": "En attente Comptable",      "action": "Rejeter",                "next_state": "Rejeté",                   "allowed": "Responsable Comptable","allow_self_approval": 0, "condition": None},
            {"state": "En attente Audit",           "action": "Approuver",              "next_state": "Approuvé",                 "allowed": "Auditeur Interne",     "allow_self_approval": 0, "condition": None},
            {"state": "En attente Audit",           "action": "Approuver",              "next_state": "Approuvé",                 "allowed": "System Manager",       "allow_self_approval": 0, "condition": None},
            {"state": "En attente Audit",           "action": "Rejeter",                "next_state": "Rejeté",                   "allowed": "Auditeur Interne",     "allow_self_approval": 0, "condition": None},
        ]
        print("OK: PV Entree Materiel workflow updated to Achats & Stock flow")
        break

with open(WF_PATH, "w", encoding="utf-8") as f:
    json.dump(workflows, f, ensure_ascii=False, indent=1)
print("Done.")
