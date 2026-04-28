"""Smoke tests à exécuter sur preprod après déploiement.

Usage:
    docker exec -it <container> bench --site frontend execute kya_hr.smoke_tests.run

Vérifie que tous les éléments critiques sont en place et fonctionnels:
- Web Forms publiés
- DocTypes accessibles avec permissions correctes
- Workflows actifs
- Print formats existants
- Notifications configurées
- Scheduler events enregistrés
- Pages web accessibles
"""
import frappe


def run():
    """Lance tous les checks et imprime un rapport."""
    print("\n" + "=" * 80)
    print("  KYA HR — SMOKE TESTS PREPROD")
    print("=" * 80 + "\n")

    results = {"OK": 0, "WARN": 0, "FAIL": 0}

    def check(name, condition, fail_msg="", warn=False):
        if condition:
            print(f"  ✅ {name}")
            results["OK"] += 1
            return True
        else:
            level = "⚠️ " if warn else "❌"
            print(f"  {level} {name}{(' — ' + fail_msg) if fail_msg else ''}")
            results["WARN" if warn else "FAIL"] += 1
            return False

    # ─── 1. Web Forms ───────────────────────────────────────────────────
    print("\n[1] WEB FORMS")
    expected_published = [
        "permission-sortie-employe", "permission-sortie-stagiaire",
        "pv-sortie-materiel", "pv-entree-materiel",
        "demande-achat", "appel-offre", "bon-commande",
        "inventaire-kya", "brouillard-caisse", "etat-recap",
        "demande-conge", "planning-conge",
    ]
    for route in expected_published:
        wf = frappe.db.get_value(
            "Web Form", {"route": route},
            ["name", "published", "doc_type", "login_required"], as_dict=True
        )
        if not wf:
            check(f"Web Form '{route}' existe", False, "Introuvable")
            continue
        check(f"Web Form '{route}' publié (DocType: {wf.doc_type})", wf.published == 1,
              f"published={wf.published}")

    check("Bilan fin de stage DÉPUBLIÉ",
          frappe.db.get_value("Web Form", {"route": "bilan-fin-de-stage"}, "published") == 0,
          warn=True)

    # ─── 2. DocTypes custom ─────────────────────────────────────────────
    print("\n[2] DOCTYPES CUSTOM")
    custom_dts = [
        "Demande Achat KYA", "Bon Commande KYA", "Appel Offre KYA",
        "PV Sortie Matériel", "PV Entree Materiel", "Inventaire KYA",
        "Brouillard Caisse", "Etat Recap Cheques",
        "Permission de Sortie Employé", "Permission Sortie Stagiaire",
        "Demande Conge Stagiaire", "Planning Conge",
        "KYA Contrat", "Equipe KYA", "Plan Trimestriel", "Tache Equipe",
        "Sortie Vehicule", "Document Vehicule",
    ]
    for dt in custom_dts:
        exists = frappe.db.exists("DocType", dt)
        check(f"DocType '{dt}' existe", bool(exists))
        if exists:
            # Check System Manager perms
            sm_perm = frappe.db.get_value(
                "DocPerm", {"parent": dt, "role": "System Manager"},
                ["read", "write", "create", "delete"], as_dict=True
            )
            if not sm_perm:
                # Try Custom DocPerm
                sm_perm = frappe.db.get_value(
                    "Custom DocPerm", {"parent": dt, "role": "System Manager"},
                    ["read", "write", "create", "delete"], as_dict=True
                )
            check(f"  System Manager perms sur '{dt}'",
                  bool(sm_perm) and sm_perm.read and sm_perm.write,
                  f"perms={sm_perm}", warn=True)

    # ─── 3. Workflows actifs ────────────────────────────────────────────
    print("\n[3] WORKFLOWS")
    workflows = [
        "Flux RH Unifié", "Flux Permission Sortie Stagiaire",
        "Flux PV Sortie Matériel", "Flux PV Entrée Matériel",
        "Flux Permission Sortie Employé", "Flux Planning Congé",
        "Flux Demande Achat KYA", "Flux Inventaire KYA",
        "Flux Contrat KYA",
    ]
    for wf_name in workflows:
        wf = frappe.db.get_value("Workflow", wf_name, ["is_active", "document_type"], as_dict=True)
        if not wf:
            check(f"Workflow '{wf_name}'", False, "Introuvable")
            continue
        check(f"Workflow '{wf_name}' actif (DocType: {wf.document_type})", wf.is_active == 1)

    # ─── 4. Print formats avec en-tête KYA ──────────────────────────────
    print("\n[4] PRINT FORMATS")
    pfs = [
        "Demande Achat KYA Officiel", "Bon Commande KYA Officiel",
        "PV Sortie Matériel Officiel", "Ticket Sortie Employe",
        "Ticket Sortie Stagiaire", "Ticket Sortie Materiel",
        "Ticket Entree Materiel", "Brouillard Caisse KYA Officiel",
        "Demande Conge KYA", "Bilan de Stage KYA",
        "Fiche Inventaire KYA", "KYA Contrat PDF",
    ]
    for pf in pfs:
        check(f"Print Format '{pf}' existe", bool(frappe.db.exists("Print Format", pf)))

    # ─── 5. Notifications ───────────────────────────────────────────────
    print("\n[5] NOTIFICATIONS")
    notifs = frappe.db.count("Notification", {"enabled": 1})
    check(f"Notifications actives: {notifs}", notifs > 0)
    # Check pour roles inexistants
    bad_role_notifs = frappe.db.sql("""
        SELECT n.name, n.subject FROM `tabNotification` n
        WHERE n.enabled=1 AND n.recipients LIKE '%receiver_by_role%'
    """, as_dict=True)
    if bad_role_notifs:
        print(f"    ℹ {len(bad_role_notifs)} notifications avec receiver_by_role à vérifier manuellement")

    # ─── 6. Scheduler ───────────────────────────────────────────────────
    print("\n[6] SCHEDULER EVENTS")
    from frappe.utils.scheduler import is_scheduler_inactive
    check("Scheduler actif", not is_scheduler_inactive(), warn=True)

    # ─── 7. Pages web ───────────────────────────────────────────────────
    print("\n[7] PAGES WEB")
    pages = ["mon-espace", "recap-brouillards", "kya-tableau-de-bord",
             "kya-contrat", "inventaire-dashboard", "stock-projet-client"]
    import os
    base = os.path.join(frappe.get_app_path("kya_hr"), "www")
    for page in pages:
        py_exists = os.path.exists(os.path.join(base, f"{page}.py")) or \
                    os.path.exists(os.path.join(base, f"{page.replace('-', '_')}.py"))
        html_exists = os.path.exists(os.path.join(base, f"{page}.html")) or \
                      os.path.exists(os.path.join(base, f"{page.replace('-', '_')}.html"))
        check(f"Page /{page}", py_exists and html_exists,
              f"py={py_exists} html={html_exists}")

    # ─── 8. Roles canoniques ────────────────────────────────────────────
    print("\n[8] RÔLES CANONIQUES")
    expected_roles = [
        "DAAF", "Responsable Achats", "Guérite", "Chef Service",
        "Chargé des Stocks", "Auditeur Interne", "Maître de Stage",
        "Responsable des Stagiaires", "Supérieur Immédiat", "Stagiaire",
        "Responsable RH", "Directeur Général", "DGA", "Comptable",
        "Caissière", "KYA Signataire Contrat",
        "Gestionnaire de Flotte",
    ]
    for r in expected_roles:
        check(f"Rôle '{r}' existe", bool(frappe.db.exists("Role", r)),
              warn=True)

    # ─── 9. Workspaces ──────────────────────────────────────────────────
    print("\n[9] WORKSPACES")
    workspaces = ["Espace Stagiaires", "KYA Services",
                  "Espace Achats", "Espace Stock", "Espace Comptabilité",
                  "Espace Employés", "Espace RH", "Logistique"]
    for ws in workspaces:
        check(f"Workspace '{ws}'", bool(frappe.db.exists("Workspace", ws)),
              warn=True)

    # ─── 10. Items / Suppliers / Customers / Warehouses (ERPNext) ──────
    print("\n[10] BASE ERPNEXT (Items/Fournisseurs/Clients/Entrepôts)")
    counts = {
        "Item": frappe.db.count("Item"),
        "Supplier": frappe.db.count("Supplier"),
        "Customer": frappe.db.count("Customer"),
        "Warehouse": frappe.db.count("Warehouse"),
    }
    for k, v in counts.items():
        check(f"{k}: {v} enregistrement(s)", v >= 0)

    # ─── BILAN ──────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"  BILAN: ✅ {results['OK']}  ⚠️  {results['WARN']}  ❌ {results['FAIL']}")
    print("=" * 80 + "\n")
    if results["FAIL"]:
        print("⚠️  Des tests ont échoué. Vérifier les ❌ ci-dessus.\n")
    else:
        print("🎉 Tous les tests critiques passent.\n")
    return results
