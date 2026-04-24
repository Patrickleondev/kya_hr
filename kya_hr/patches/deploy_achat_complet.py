# -*- coding: utf-8 -*-
"""
Deployment script: Appel Offre KYA + Bon Commande KYA
- Workflow States
- Workflows
- Notifications emails (one per state transition)
- Workspace shortcuts
- Demo data (Items, Suppliers, Warehouse) for testing stock flows

Run: bench --site frontend execute kya_hr.patches.deploy_achat_complet.run
"""
import frappe
from frappe.utils import cint, now_datetime

# ---------------------------------------------------------------------------
# KYA email footer partial (reused across notifications)
# ---------------------------------------------------------------------------
KYA_LOGO_URL = "https://www.kya-energy.com/wp-content/uploads/2024/02/Logo-10-ans-KYA.png"


def _email_body(header_title, paragraphs_html, btn_label, btn_url_tpl, accent="#f57c00"):
    """Return a branded HTML email body (KYA orange accent for Achats)."""
    return f"""
<div style='font-family:Arial,sans-serif;max-width:620px;margin:0 auto;'>
  <div style='background:linear-gradient(135deg,{accent},#ff9800);padding:22px;border-radius:12px 12px 0 0;text-align:center;'>
    <img src='{KYA_LOGO_URL}' width='60' style='margin-bottom:6px;'>
    <h2 style='color:white;margin:0;font-size:20px;'>{header_title}</h2>
  </div>
  <div style='background:white;padding:24px;border:1px solid #e0e0e0;border-radius:0 0 12px 12px;'>
    {paragraphs_html}
    <div style='text-align:center;margin:22px 0;'>
      <a href='{btn_url_tpl}' style='display:inline-block;padding:12px 32px;background:{accent};color:white;text-decoration:none;border-radius:8px;font-weight:700;font-size:15px;'>{btn_label}</a>
    </div>
  </div>
  <div style='text-align:center;color:#777;font-size:11px;margin-top:12px;'>
    KYA-Energy Group · <i>Move beyond the sky!</i> · 228 70 45 34 81 · www.kya-energy.com
  </div>
</div>
""".strip()


# ---------------------------------------------------------------------------
# 1. Ensure Workflow States exist
# ---------------------------------------------------------------------------
def ensure_workflow_states():
    states = [
        ("Validé DAAF", "Success"),
        ("Validé DG", "Success"),
        ("Envoyé", "Info"),
        ("Réponses Reçues", "Info"),
        ("Attribué", "Success"),
        ("Clôturé", "Success"),
        ("Annulé", "Danger"),
        ("Émis", "Success"),
    ]
    created = 0
    for name, style in states:
        if not frappe.db.exists("Workflow State", name):
            doc = frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": name,
                "style": style,
            })
            doc.insert(ignore_permissions=True)
            created += 1
    print(f"  [Workflow States] {created} créés")


# ---------------------------------------------------------------------------
# 2. Workflow Actions (Valider, Envoyer, Réception, Attribuer, Clôturer, Annuler, Émettre)
# ---------------------------------------------------------------------------
def ensure_workflow_actions():
    actions = [
        "Valider DAAF", "Valider DG", "Envoyer", "Marquer Réponses Reçues",
        "Attribuer", "Clôturer", "Annuler", "Émettre",
    ]
    created = 0
    for a in actions:
        if not frappe.db.exists("Workflow Action Master", a):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": a}).insert(ignore_permissions=True)
            created += 1
    print(f"  [Workflow Actions] {created} créées")


# ---------------------------------------------------------------------------
# 3. Workflow Appel Offre KYA
# ---------------------------------------------------------------------------
def create_workflow_appel_offre():
    name = "Flux Appel Offre KYA"
    if frappe.db.exists("Workflow", name):
        frappe.delete_doc("Workflow", name, force=True)

    wf = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": name,
        "document_type": "Appel Offre KYA",
        "is_active": 1,
        "send_email_alert": 1,
        "workflow_state_field": "workflow_state",
        "states": [
            {"state": "Brouillon", "doc_status": "0", "allow_edit": "Employee"},
            {"state": "Validé DAAF", "doc_status": "0", "allow_edit": "DAAF"},
            {"state": "Validé DG", "doc_status": "1", "allow_edit": "DG"},
            {"state": "Envoyé", "doc_status": "1", "allow_edit": "Purchase Manager", "update_field": "statut", "update_value": "Envoyé"},
            {"state": "Réponses Reçues", "doc_status": "1", "allow_edit": "Purchase Manager", "update_field": "statut", "update_value": "Réponses reçues"},
            {"state": "Attribué", "doc_status": "1", "allow_edit": "DG", "update_field": "statut", "update_value": "Attribué"},
            {"state": "Clôturé", "doc_status": "1", "allow_edit": "Purchase Manager", "update_field": "statut", "update_value": "Clôturé"},
            {"state": "Annulé", "doc_status": "2", "allow_edit": "Purchase Manager", "update_field": "statut", "update_value": "Annulé"},
        ],
        "transitions": [
            {"state": "Brouillon", "action": "Valider DAAF", "next_state": "Validé DAAF", "allowed": "DAAF", "allow_self_approval": 1},
            {"state": "Validé DAAF", "action": "Valider DG", "next_state": "Validé DG", "allowed": "DG", "allow_self_approval": 1},
            {"state": "Validé DG", "action": "Envoyer", "next_state": "Envoyé", "allowed": "Purchase Manager", "allow_self_approval": 1},
            {"state": "Envoyé", "action": "Marquer Réponses Reçues", "next_state": "Réponses Reçues", "allowed": "Purchase Manager", "allow_self_approval": 1},
            {"state": "Réponses Reçues", "action": "Attribuer", "next_state": "Attribué", "allowed": "DG", "allow_self_approval": 1},
            {"state": "Attribué", "action": "Clôturer", "next_state": "Clôturé", "allowed": "Purchase Manager", "allow_self_approval": 1},
            {"state": "Validé DG", "action": "Annuler", "next_state": "Annulé", "allowed": "DG", "allow_self_approval": 1},
            {"state": "Envoyé", "action": "Annuler", "next_state": "Annulé", "allowed": "Purchase Manager", "allow_self_approval": 1},
        ],
    })
    wf.insert(ignore_permissions=True)
    print(f"  [Workflow] {name} créé (8 états, 8 transitions)")


# ---------------------------------------------------------------------------
# 4. Workflow Bon Commande KYA
# ---------------------------------------------------------------------------
def create_workflow_bon_commande():
    name = "Flux Bon Commande KYA"
    if frappe.db.exists("Workflow", name):
        frappe.delete_doc("Workflow", name, force=True)

    wf = frappe.get_doc({
        "doctype": "Workflow",
        "workflow_name": name,
        "document_type": "Bon Commande KYA",
        "is_active": 1,
        "send_email_alert": 1,
        "workflow_state_field": "workflow_state",
        "states": [
            {"state": "Brouillon", "doc_status": "0", "allow_edit": "Purchase User"},
            {"state": "Validé DG", "doc_status": "1", "allow_edit": "DG"},
            {"state": "Émis", "doc_status": "1", "allow_edit": "Purchase Manager", "update_field": "statut", "update_value": "Émis"},
            {"state": "Annulé", "doc_status": "2", "allow_edit": "Purchase Manager", "update_field": "statut", "update_value": "Annulé"},
        ],
        "transitions": [
            {"state": "Brouillon", "action": "Valider DG", "next_state": "Validé DG", "allowed": "DG", "allow_self_approval": 1},
            {"state": "Validé DG", "action": "Émettre", "next_state": "Émis", "allowed": "Purchase Manager", "allow_self_approval": 1},
            {"state": "Validé DG", "action": "Annuler", "next_state": "Annulé", "allowed": "DG", "allow_self_approval": 1},
            {"state": "Émis", "action": "Annuler", "next_state": "Annulé", "allowed": "Purchase Manager", "allow_self_approval": 1},
        ],
    })
    wf.insert(ignore_permissions=True)
    print(f"  [Workflow] {name} créé (4 états, 3 transitions)")


# ---------------------------------------------------------------------------
# 5. Notifications Appel Offre (6) + Bon Commande (3)
# ---------------------------------------------------------------------------
def create_notifications():
    url_ao = "{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}"
    url_bc = "{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}"

    notifs = [
        # ---- Appel Offre ----
        {
            "name": "KYA - Appel Offre: En attente DAAF",
            "document_type": "Appel Offre KYA",
            "condition": "doc.workflow_state == 'Brouillon'",
            "recipient_role": "DAAF",
            "subject": "Appel d'Offre à valider: {{ doc.objet }}",
            "body_p": "<p>Un appel d'offre <b>{{ doc.name }}</b> (<i>{{ doc.objet }}</i>) a été créé par {{ doc.demandeur_name }} et attend votre validation.</p><p>Date limite fournisseurs : <b>{{ doc.date_limite }}</b></p>",
            "btn": "📋 Valider l'Appel d'Offre",
        },
        {
            "name": "KYA - Appel Offre: En attente DG",
            "document_type": "Appel Offre KYA",
            "condition": "doc.workflow_state == 'Validé DAAF'",
            "recipient_role": "DG",
            "subject": "Appel d'Offre validé DAAF, attend DG: {{ doc.objet }}",
            "body_p": "<p>L'appel d'offre <b>{{ doc.name }}</b> a été validé par le DAAF et attend votre validation avant envoi aux fournisseurs.</p>",
            "btn": "🔍 Examiner",
        },
        {
            "name": "KYA - Appel Offre: Prêt à envoyer",
            "document_type": "Appel Offre KYA",
            "condition": "doc.workflow_state == 'Validé DG'",
            "recipient_role": "Purchase Manager",
            "subject": "Appel d'Offre approuvé: {{ doc.name }} prêt pour envoi",
            "body_p": "<p>L'appel d'offre <b>{{ doc.name }}</b> est approuvé. Vous pouvez maintenant l'envoyer aux fournisseurs via le bouton <b>📧 Envoyer aux fournisseurs</b>.</p>",
            "btn": "📤 Ouvrir et envoyer",
        },
        {
            "name": "KYA - Appel Offre: Réponses reçues",
            "document_type": "Appel Offre KYA",
            "condition": "doc.workflow_state == 'Réponses Reçues'",
            "recipient_role": "DG",
            "subject": "Réponses fournisseurs reçues: {{ doc.name }}",
            "body_p": "<p>Les réponses des fournisseurs pour l'appel d'offre <b>{{ doc.name }}</b> sont arrivées ({{ doc.nombre_reponses }} réponses).</p><p>Vous pouvez désormais sélectionner le fournisseur retenu et passer à <b>Attribué</b>.</p>",
            "btn": "✅ Attribuer",
        },
        {
            "name": "KYA - Appel Offre: Attribué",
            "document_type": "Appel Offre KYA",
            "condition": "doc.workflow_state == 'Attribué'",
            "recipient_role": "Purchase Manager",
            "subject": "Appel d'Offre attribué: {{ doc.name }}",
            "body_p": "<p>L'appel d'offre <b>{{ doc.name }}</b> a été attribué par la direction. Vous pouvez générer le Bon de Commande correspondant.</p>",
            "btn": "📝 Voir le dossier",
        },
        {
            "name": "KYA - Appel Offre: Annulé",
            "document_type": "Appel Offre KYA",
            "condition": "doc.workflow_state == 'Annulé'",
            "recipient_role": "DAAF",
            "subject": "Appel d'Offre annulé: {{ doc.name }}",
            "body_p": "<p>L'appel d'offre <b>{{ doc.name }}</b> (<i>{{ doc.objet }}</i>) a été annulé.</p>",
            "btn": "🔎 Voir",
        },
        # ---- Bon Commande ----
        {
            "name": "KYA - Bon Commande: En attente DG",
            "document_type": "Bon Commande KYA",
            "condition": "doc.workflow_state == 'Brouillon'",
            "recipient_role": "DG",
            "subject": "Bon de Commande à valider: {{ doc.name }}",
            "body_p": "<p>Un bon de commande <b>{{ doc.name }}</b> (<i>{{ doc.objet }}</i>) destiné à <b>{{ doc.fournisseur_nom }}</b> attend votre validation.</p>",
            "btn": "🖋 Valider le BC",
        },
        {
            "name": "KYA - Bon Commande: Prêt à émettre",
            "document_type": "Bon Commande KYA",
            "condition": "doc.workflow_state == 'Validé DG'",
            "recipient_role": "Purchase Manager",
            "subject": "Bon de Commande approuvé: {{ doc.name }} prêt à émettre",
            "body_p": "<p>Le BC <b>{{ doc.name }}</b> a été signé par la Direction. Vous pouvez désormais l'émettre et l'envoyer au fournisseur <b>{{ doc.fournisseur_nom }}</b>.</p>",
            "btn": "📤 Émettre",
        },
        {
            "name": "KYA - Bon Commande: Annulé",
            "document_type": "Bon Commande KYA",
            "condition": "doc.workflow_state == 'Annulé'",
            "recipient_role": "Purchase Manager",
            "subject": "Bon de Commande annulé: {{ doc.name }}",
            "body_p": "<p>Le bon de commande <b>{{ doc.name }}</b> a été annulé.</p>",
            "btn": "🔎 Voir",
        },
    ]

    created = 0
    updated = 0
    for n in notifs:
        exists = frappe.db.exists("Notification", n["name"])
        url_tpl = "{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}"
        body_html = _email_body(
            header_title=n["document_type"].replace(" KYA", "").upper(),
            paragraphs_html=n["body_p"],
            btn_label=n["btn"],
            btn_url_tpl=url_tpl,
        )
        payload = {
            "doctype": "Notification",
            "name": n["name"],
            "subject": n["subject"],
            "document_type": n["document_type"],
            "event": "Value Change",
            "value_changed": "workflow_state",
            "condition": n["condition"],
            "channel": "Email",
            "enabled": 1,
            "message": body_html,
            "recipients": [{"receiver_by_role": n["recipient_role"]}],
        }
        if exists:
            doc = frappe.get_doc("Notification", n["name"])
            doc.update(payload)
            doc.set("recipients", [{"receiver_by_role": n["recipient_role"]}])
            doc.save(ignore_permissions=True)
            updated += 1
        else:
            frappe.get_doc(payload).insert(ignore_permissions=True)
            created += 1
    print(f"  [Notifications] {created} créées, {updated} mises à jour")


# ---------------------------------------------------------------------------
# 6. Demo data: Company/Warehouse/Items/Suppliers
# ---------------------------------------------------------------------------
DEMO_ITEMS = [
    {"item_code": "KYA-FOURN-001", "item_name": "Ramette papier A4 80g", "stock_uom": "Nos", "rate": 3500},
    {"item_code": "KYA-FOURN-002", "item_name": "Stylo bille bleu", "stock_uom": "Nos", "rate": 150},
    {"item_code": "KYA-FOURN-003", "item_name": "Cahier 200 pages", "stock_uom": "Nos", "rate": 1200},
    {"item_code": "KYA-FOURN-004", "item_name": "Classeur A4 levier", "stock_uom": "Nos", "rate": 2500},
    {"item_code": "KYA-IT-001", "item_name": "Câble HDMI 2m", "stock_uom": "Nos", "rate": 4500},
    {"item_code": "KYA-IT-002", "item_name": "Souris sans fil", "stock_uom": "Nos", "rate": 8500},
    {"item_code": "KYA-IT-003", "item_name": "Clavier USB azerty", "stock_uom": "Nos", "rate": 12000},
    {"item_code": "KYA-IT-004", "item_name": "Disque dur externe 1TB", "stock_uom": "Nos", "rate": 55000},
    {"item_code": "KYA-ELEC-001", "item_name": "Câble électrique 2.5mm² (m)", "stock_uom": "Meter", "rate": 850},
    {"item_code": "KYA-ELEC-002", "item_name": "Panneau solaire 100W", "stock_uom": "Nos", "rate": 45000},
    {"item_code": "KYA-ELEC-003", "item_name": "Batterie 12V 100Ah", "stock_uom": "Nos", "rate": 185000},
    {"item_code": "KYA-ELEC-004", "item_name": "Onduleur 1000VA", "stock_uom": "Nos", "rate": 125000},
    {"item_code": "KYA-OUT-001", "item_name": "Multimètre digital", "stock_uom": "Nos", "rate": 22000},
    {"item_code": "KYA-OUT-002", "item_name": "Perceuse sans fil 18V", "stock_uom": "Nos", "rate": 85000},
    {"item_code": "KYA-CONSOM-001", "item_name": "Bouteille d'eau 1.5L", "stock_uom": "Nos", "rate": 350},
    {"item_code": "KYA-CONSOM-002", "item_name": "Café instantané 200g", "stock_uom": "Nos", "rate": 3800},
]

DEMO_SUPPLIERS = [
    {"supplier_name": "CFAO Technologies Togo", "country": "Togo", "email": "contact@cfao-togo.test", "phone": "+228 22 21 45 00"},
    {"supplier_name": "Bureautique Lomé SARL", "country": "Togo", "email": "", "phone": "+228 90 12 34 56"},
    {"supplier_name": "Solar Africa Distribution", "country": "Togo", "email": "commercial@solar-africa.test", "phone": "+228 70 88 99 11"},
    {"supplier_name": "Quincaillerie du Golfe", "country": "Togo", "email": "", "phone": "+228 22 61 23 44"},
    {"supplier_name": "IT Plus Togo", "country": "Togo", "email": "ventes@itplus.test", "phone": "+228 99 12 88 77"},
]


def ensure_demo_company_warehouse():
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        if not frappe.db.exists("Company", "KYA-Energy Group"):
            c = frappe.get_doc({
                "doctype": "Company",
                "company_name": "KYA-Energy Group",
                "abbr": "KEG",
                "default_currency": "XOF",
                "country": "Togo",
            })
            c.insert(ignore_permissions=True)
        company = "KYA-Energy Group"
        frappe.db.set_single_value("Global Defaults", "default_company", company)

    abbr = frappe.db.get_value("Company", company, "abbr")
    wh_name = f"Magasin Central KYA - {abbr}"
    if not frappe.db.exists("Warehouse", wh_name):
        wh = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": "Magasin Central KYA",
            "company": company,
            "is_group": 0,
        })
        wh.insert(ignore_permissions=True)
        frappe.db.set_single_value("Stock Settings", "default_warehouse", wh.name)
    return company, wh_name


def create_demo_items():
    created = 0
    for it in DEMO_ITEMS:
        if frappe.db.exists("Item", it["item_code"]):
            continue
        doc = frappe.get_doc({
            "doctype": "Item",
            "item_code": it["item_code"],
            "item_name": it["item_name"],
            "item_group": "All Item Groups",
            "stock_uom": it["stock_uom"],
            "is_stock_item": 1,
            "include_item_in_manufacturing": 0,
            "standard_rate": it["rate"],
            "last_purchase_rate": it["rate"],
        })
        doc.insert(ignore_permissions=True)
        created += 1
    print(f"  [Items] {created} items créés (total: {frappe.db.count('Item')})")


def create_demo_suppliers():
    created = 0
    for s in DEMO_SUPPLIERS:
        if frappe.db.exists("Supplier", s["supplier_name"]):
            continue
        sup = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": s["supplier_name"],
            "supplier_group": "All Supplier Groups",
            "country": s["country"],
            "supplier_type": "Company",
        })
        sup.insert(ignore_permissions=True)
        # Add contact if email/phone
        if s.get("email") or s.get("phone"):
            name_parts = s["supplier_name"].split()
            first = name_parts[0]
            last = name_parts[-1] if len(name_parts) > 1 else "-"
            contact = frappe.get_doc({
                "doctype": "Contact",
                "first_name": f"Contact {first}",
                "last_name": last,
                "is_primary_contact": 1,
                "links": [{"link_doctype": "Supplier", "link_name": sup.name}],
            })
            if s.get("email"):
                contact.append("email_ids", {"email_id": s["email"], "is_primary": 1})
            if s.get("phone"):
                contact.append("phone_nos", {"phone": s["phone"], "is_primary_mobile_no": 1})
            contact.insert(ignore_permissions=True)
        created += 1
    print(f"  [Suppliers] {created} fournisseurs créés (total: {frappe.db.count('Supplier')})")


# ---------------------------------------------------------------------------
# 7. Workspace shortcuts
# ---------------------------------------------------------------------------
def add_workspace_shortcuts():
    """Ajouter Bon Commande + Appel Offre au workspace Espace Employes (via SQL pour eviter validations)."""
    ws_name = "Espace Employes"
    if not frappe.db.exists("Workspace", ws_name):
        print(f"  [Workspace] {ws_name} introuvable - skip")
        return

    wanted = [
        {"link_to": "Bon Commande KYA", "label": "Bons de Commande", "icon": "receipt", "color": "Orange"},
        {"link_to": "Appel Offre KYA", "label": "Appels d'Offre", "icon": "send", "color": "Orange"},
    ]
    # Current max idx
    max_idx = frappe.db.sql(
        "SELECT COALESCE(MAX(idx),0) FROM `tabWorkspace Shortcut` WHERE parent=%s", ws_name
    )[0][0]
    added = 0
    for w in wanted:
        exists = frappe.db.exists("Workspace Shortcut", {"parent": ws_name, "label": w["label"]})
        if exists:
            continue
        max_idx += 1
        new_name = frappe.generate_hash(length=10)
        frappe.db.sql("""
            INSERT INTO `tabWorkspace Shortcut`
            (name, creation, modified, modified_by, owner, docstatus, idx,
             parent, parenttype, parentfield,
             type, link_to, label, icon, color, doc_view, stats_filter, format, url, report_ref_doctype, restrict_to_domain)
            VALUES (%(n)s, NOW(), NOW(), 'Administrator', 'Administrator', 0, %(idx)s,
                    %(parent)s, 'Workspace', 'shortcuts',
                    'DocType', %(link_to)s, %(label)s, %(icon)s, %(color)s, NULL, NULL, NULL, NULL, NULL, NULL)
        """, {
            "n": new_name, "idx": max_idx, "parent": ws_name,
            "link_to": w["link_to"], "label": w["label"],
            "icon": w["icon"], "color": w["color"],
        })
        added += 1
    if added:
        frappe.db.commit()
    print(f"  [Workspace '{ws_name}'] {added} shortcuts ajoutes")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
def run():
    print("=== DEPLOY ACHAT COMPLET (Appel Offre + Bon Commande) ===")

    print("[1/7] Workflow States...")
    ensure_workflow_states()

    print("[2/7] Workflow Actions...")
    ensure_workflow_actions()

    print("[3/7] Workflow Appel Offre...")
    create_workflow_appel_offre()

    print("[4/7] Workflow Bon Commande...")
    create_workflow_bon_commande()

    print("[5/7] Notifications email...")
    create_notifications()

    print("[6/7] Demo data...")
    company, wh = ensure_demo_company_warehouse()
    print(f"  [Company] {company} · [Warehouse] {wh}")
    create_demo_items()
    create_demo_suppliers()

    print("[7/7] Workspace shortcuts...")
    add_workspace_shortcuts()

    frappe.db.commit()
    frappe.clear_cache()
    print("=== DONE ===")
