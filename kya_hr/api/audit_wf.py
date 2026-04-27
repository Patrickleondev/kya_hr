import frappe

@frappe.whitelist()
def audit_workflow_notifs():
    targets = ["Demande Conge", "Permission Sortie Stagiaire", "Permission Sortie Employe",
               "PV Sortie Materiel", "PV Entree Materiel", "Demande Achat KYA", "Bon Commande KYA",
               "Appel Offre KYA", "Etat Recap Cheques", "Brouillard Caisse", "Inventaire KYA"]
    out = []
    for dt in targets:
        if not frappe.db.exists("DocType", dt):
            out.append({"doctype": dt, "skipped": "doctype not found"}); continue
        wfs = frappe.get_all("Workflow", filters={"document_type": dt, "is_active": 1}, pluck="name")
        trans_roles = set()
        for wf in wfs:
            for r in frappe.get_all("Workflow Transition", filters={"parent": wf}, fields=["allowed"]):
                if r.allowed: trans_roles.add(r.allowed)
        notifs = frappe.get_all("Notification", filters={"document_type": dt, "enabled": 1}, pluck="name")
        notif_roles = set()
        for n in notifs:
            for r in frappe.get_all("Notification Recipient", filters={"parent": n}, fields=["receiver_by_role"]):
                if r.receiver_by_role: notif_roles.add(r.receiver_by_role)
        out.append({
            "doctype": dt, "workflows": wfs,
            "trans_roles": sorted(trans_roles),
            "notif_roles": sorted(notif_roles),
            "orphan_notif": sorted(notif_roles - trans_roles),
            "missing_notif": sorted(trans_roles - notif_roles),
        })
    return out


@frappe.whitelist()
def fix_dg_role_notifs():
    """Fix notification recipients using 'Directeur General' (no accent) vs 'Directeur Général'."""
    wrong = "Directeur General"
    right = "Directeur Général"
    if not frappe.db.exists("Role", right):
        r = frappe.new_doc("Role"); r.role_name = right; r.desk_access = 1
        r.insert(ignore_permissions=True)
    recs = frappe.get_all("Notification Recipient",
                          filters={"receiver_by_role": wrong},
                          fields=["name", "parent"])
    for rec in recs:
        frappe.db.set_value("Notification Recipient", rec.name, "receiver_by_role", right)
    frappe.db.commit()
    return {"fixed_count": len(recs), "notifications": sorted({r.parent for r in recs})}
