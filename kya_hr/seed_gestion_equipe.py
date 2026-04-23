"""
Seed mock data for Gestion Équipe module:
- Plan Trimestriel (quarterly plans per department)
- Tache Equipe (tasks within plans)
- KYA Evaluation (N+1 evaluates N, etc.)

Run: bench --site frontend execute kya_hr.seed_gestion_equipe.execute
"""
import frappe
from frappe.utils import today, add_days, nowdate
import random


def execute():
    frappe.flags.in_import = True
    print("=== SEED GESTION EQUIPE ===")

    company = "KYA-Energy Group"
    abbr = frappe.db.get_value("Company", company, "abbr") or "KG"

    # ── CLEANUP broken records from previous runs ──
    broken = frappe.get_all("Plan Trimestriel", filters={"equipe_abbr": ["in", ["", None]]}, pluck="name")
    for b in broken:
        try:
            frappe.db.sql("DELETE FROM `tabResultat Attendu Item` WHERE parent=%s", b)
            frappe.db.sql("DELETE FROM `tabTache Equipe` WHERE plan=%s", b)
            frappe.db.sql("DELETE FROM `tabPlan Trimestriel` WHERE name=%s", b)
            print(f"  Cleaned broken plan: {b}")
        except Exception:
            pass
    if broken:
        frappe.db.commit()

    # Get employees
    employees = frappe.get_all(
        "Employee",
        filters={"company": company, "status": "Active"},
        fields=["name", "employee_name", "department", "designation", "user_id"],
        order_by="name",
    )
    if not employees:
        print("  ERROR: No employees found!")
        return

    emp_map = {e.name: e for e in employees}
    dept_emps = {}
    for e in employees:
        dept_emps.setdefault(e.department, []).append(e)

    print(f"  Found {len(employees)} employees in {len(dept_emps)} departments")

    # ── 1. PLAN TRIMESTRIEL ──
    print("\n--- 1. PLAN TRIMESTRIEL ---")
    plans_created = 0

    plans_data = [
        {
            "titre": "Plan T3 2025 - Services Technique",
            "equipe": f"Services Technique - {abbr}",
            "equipe_abbr": "ST",
            "trimestre": "T3",
            "annee": 2025,
            "statut": "En cours",
            "resultats": [
                {"numero": "R1", "libelle": "Réduire le taux de pannes récurrentes de 30%", "poids": 40},
                {"numero": "R2", "libelle": "Former 100% des techniciens sur les nouvelles normes", "poids": 30},
                {"numero": "R3", "libelle": "Digitaliser les fiches d'intervention", "poids": 30},
            ],
        },
        {
            "titre": "Plan T3 2025 - Finance et Comptabilité",
            "equipe": f"Finance et Comptabilité - {abbr}",
            "equipe_abbr": "FC",
            "trimestre": "T3",
            "annee": 2025,
            "statut": "En cours",
            "resultats": [
                {"numero": "R1", "libelle": "Clôture mensuelle avant le 5 du mois suivant", "poids": 50},
                {"numero": "R2", "libelle": "Réduction des écarts de caisse à 0%", "poids": 30},
                {"numero": "R3", "libelle": "Mise à jour du plan comptable SYSCOHADA", "poids": 20},
            ],
        },
        {
            "titre": "Plan T3 2025 - Direction Générale",
            "equipe": f"Direction Générale - {abbr}",
            "equipe_abbr": "DG",
            "trimestre": "T3",
            "annee": 2025,
            "statut": "Évaluation",
            "resultats": [
                {"numero": "R1", "libelle": "Augmenter le CA de 15% par rapport au T2", "poids": 40},
                {"numero": "R2", "libelle": "Finaliser le partenariat stratégique avec BOAD", "poids": 35},
                {"numero": "R3", "libelle": "Déployer le système de suivi des KPI digitalisé", "poids": 25},
            ],
        },
        {
            "titre": "Plan T2 2025 - Services Technique",
            "equipe": f"Services Technique - {abbr}",
            "equipe_abbr": "ST",
            "trimestre": "T2",
            "annee": 2025,
            "statut": "Clôturé",
            "resultats": [
                {"numero": "R1", "libelle": "Installation de 5 sites solaires neufs", "poids": 50},
                {"numero": "R2", "libelle": "Maintenance préventive sur 100% du parc existant", "poids": 30},
                {"numero": "R3", "libelle": "Rédaction des procédures techniques normalisées", "poids": 20},
            ],
        },
        {
            "titre": "Plan T4 2025 - EQUIPE INFORMATIQUE",
            "equipe": f"EQUIPE INFORMATIQUE - {abbr}",
            "equipe_abbr": "INFO",
            "trimestre": "T4",
            "annee": 2025,
            "statut": "Brouillon",
            "resultats": [
                {"numero": "R1", "libelle": "Déployer ERPNext v16 en production", "poids": 40},
                {"numero": "R2", "libelle": "Former 80% des utilisateurs sur les modules métier", "poids": 35},
                {"numero": "R3", "libelle": "Mettre en place la sauvegarde automatisée", "poids": 25},
            ],
        },
    ]

    plan_names = {}  # key: titre -> name in DB
    for p in plans_data:
        if frappe.db.exists("Plan Trimestriel", {"titre": p["titre"]}):
            existing = frappe.db.get_value("Plan Trimestriel", {"titre": p["titre"]}, "name")
            plan_names[p["titre"]] = existing
            print(f"  Skip (exists): {p['titre']}")
            continue

        # Find chef d'equipe
        dept_name = p["equipe"]
        dept_employees = dept_emps.get(dept_name, [])
        chef = None
        for e in dept_employees:
            if "CHEF" in (e.designation or "").upper() or "DIRECTEUR" in (e.designation or "").upper() or "RESP" in (e.designation or "").upper():
                chef = e
                break
        if not chef and dept_employees:
            chef = dept_employees[0]

        resultats = []
        for r in p["resultats"]:
            resultats.append({
                "numero": r["numero"],
                "libelle": r["libelle"],
                "poids": r["poids"],
                "nombre_taches": 0,
                "score": round(random.uniform(40, 95), 1) if p["statut"] in ("Clôturé", "Évaluation") else 0,
            })

        try:
            doc = frappe.get_doc({
                "doctype": "Plan Trimestriel",
                "titre": p["titre"],
                "equipe": dept_name,
                "equipe_abbr": p["equipe_abbr"],
                "trimestre": p["trimestre"],
                "annee": p["annee"],
                "chef_equipe": chef.name if chef else None,
                "chef_equipe_name": chef.employee_name if chef else None,
                "statut": "Brouillon",
                "resultats": resultats,
                "nombre_taches": 0,
                "taches_attribuees": 0,
                "taches_terminees": 0,
                "score_collectif": round(random.uniform(50, 90), 1) if p["statut"] in ("Clôturé", "Évaluation") else 0,
            })
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            # Set actual statut bypassing workflow via direct SQL
            if p["statut"] != "Brouillon":
                frappe.db.sql(
                    "UPDATE `tabPlan Trimestriel` SET statut=%s WHERE name=%s",
                    (p["statut"], doc.name),
                )
            plan_names[p["titre"]] = doc.name
            plans_created += 1
            print(f"  Created: {doc.name} - {p['titre']} [{p['statut']}]")
        except Exception as e:
            print(f"  ERROR Plan: {p['titre']} → {e}")

    frappe.db.commit()
    print(f"  Total plans created: {plans_created}")

    # ── 2. TACHE EQUIPE ──
    print("\n--- 2. TACHE EQUIPE ---")
    taches_created = 0

    taches_data = [
        # Plan T3 2025 - Services Technique
        {
            "plan_titre": "Plan T3 2025 - Services Technique",
            "taches": [
                {"resultat_numero": "R1", "resultat_libelle": "Réduire le taux de pannes récurrentes de 30%",
                 "libelle": "Audit des installations récurrentes en panne", "frequence": "Mensuelle",
                 "digitalisable": "OUI", "taux_digitalisation": 60,
                 "kpi": "Nombre de sites audités / total sites", "poids": 15,
                 "taux_estime": 80, "taux_effectif": 65, "statut": "En cours"},
                {"resultat_numero": "R1", "resultat_libelle": "Réduire le taux de pannes récurrentes de 30%",
                 "libelle": "Mise en place planning maintenance préventive", "frequence": "Trimestrielle",
                 "digitalisable": "OUI", "taux_digitalisation": 80,
                 "kpi": "Planning validé et diffusé (O/N)", "poids": 15,
                 "taux_estime": 100, "taux_effectif": 90, "statut": "Terminé"},
                {"resultat_numero": "R2", "resultat_libelle": "Former 100% des techniciens sur les nouvelles normes",
                 "libelle": "Session de formation NFC 15-100", "frequence": "Trimestrielle",
                 "digitalisable": "NON", "taux_digitalisation": 0,
                 "kpi": "% techniciens formés", "poids": 15,
                 "taux_estime": 100, "taux_effectif": 50, "statut": "En cours"},
                {"resultat_numero": "R3", "resultat_libelle": "Digitaliser les fiches d'intervention",
                 "libelle": "Numériser les fiches terrain sur ERPNext", "frequence": "Mensuelle",
                 "digitalisable": "OUI", "taux_digitalisation": 100,
                 "kpi": "% fiches digitalisées", "poids": 10,
                 "taux_estime": 90, "taux_effectif": 40, "statut": "En cours"},
            ],
        },
        # Plan T3 2025 - Finance et Comptabilité
        {
            "plan_titre": "Plan T3 2025 - Finance et Comptabilité",
            "taches": [
                {"resultat_numero": "R1", "resultat_libelle": "Clôture mensuelle avant le 5 du mois suivant",
                 "libelle": "Rapprochement bancaire mensuel", "frequence": "Mensuelle",
                 "digitalisable": "OUI", "taux_digitalisation": 90,
                 "kpi": "Date de clôture effective vs J+5", "poids": 25,
                 "taux_estime": 95, "taux_effectif": 80, "statut": "En cours"},
                {"resultat_numero": "R1", "resultat_libelle": "Clôture mensuelle avant le 5 du mois suivant",
                 "libelle": "Validation des écritures comptables", "frequence": "Mensuelle",
                 "digitalisable": "OUI", "taux_digitalisation": 100,
                 "kpi": "% écritures validées avant deadline", "poids": 25,
                 "taux_estime": 100, "taux_effectif": 95, "statut": "En cours"},
                {"resultat_numero": "R2", "resultat_libelle": "Réduction des écarts de caisse à 0%",
                 "libelle": "Inventaire-caisse hebdomadaire", "frequence": "Hebdomadaire",
                 "digitalisable": "NON", "taux_digitalisation": 0,
                 "kpi": "Écart en XOF", "poids": 20,
                 "taux_estime": 100, "taux_effectif": 85, "statut": "En cours"},
            ],
        },
        # Plan T3 2025 - Direction Générale
        {
            "plan_titre": "Plan T3 2025 - Direction Générale",
            "taches": [
                {"resultat_numero": "R1", "resultat_libelle": "Augmenter le CA de 15% par rapport au T2",
                 "libelle": "Revue commerciale mensuelle", "frequence": "Mensuelle",
                 "digitalisable": "OUI", "taux_digitalisation": 70,
                 "kpi": "CA cumulé vs objectif", "poids": 20,
                 "taux_estime": 100, "taux_effectif": 75, "statut": "En cours"},
                {"resultat_numero": "R2", "resultat_libelle": "Finaliser le partenariat stratégique avec BOAD",
                 "libelle": "Rédaction du protocole d'accord", "frequence": "Trimestrielle",
                 "digitalisable": "OUI", "taux_digitalisation": 100,
                 "kpi": "Document signé (O/N)", "poids": 20,
                 "taux_estime": 100, "taux_effectif": 60, "statut": "En cours"},
            ],
        },
        # Plan T2 2025 - Services Technique (clôturé)
        {
            "plan_titre": "Plan T2 2025 - Services Technique",
            "taches": [
                {"resultat_numero": "R1", "resultat_libelle": "Installation de 5 sites solaires neufs",
                 "libelle": "Installation site Kpalimé (20 kWc)", "frequence": "Trimestrielle",
                 "digitalisable": "NON", "taux_digitalisation": 0,
                 "kpi": "Site opérationnel (O/N)", "poids": 10,
                 "taux_estime": 100, "taux_effectif": 100, "statut": "Terminé"},
                {"resultat_numero": "R1", "resultat_libelle": "Installation de 5 sites solaires neufs",
                 "libelle": "Installation site Atakpamé (15 kWc)", "frequence": "Trimestrielle",
                 "digitalisable": "NON", "taux_digitalisation": 0,
                 "kpi": "Site opérationnel (O/N)", "poids": 10,
                 "taux_estime": 100, "taux_effectif": 100, "statut": "Terminé"},
                {"resultat_numero": "R2", "resultat_libelle": "Maintenance préventive sur 100% du parc existant",
                 "libelle": "Tournée maintenance Région Maritime", "frequence": "Mensuelle",
                 "digitalisable": "OUI", "taux_digitalisation": 50,
                 "kpi": "% sites visités", "poids": 15,
                 "taux_estime": 100, "taux_effectif": 90, "statut": "Terminé"},
            ],
        },
    ]

    for td in taches_data:
        plan_name = plan_names.get(td["plan_titre"])
        if not plan_name:
            print(f"  Skip taches: plan '{td['plan_titre']}' not found")
            continue

        plan_doc = frappe.get_doc("Plan Trimestriel", plan_name)
        dept_name = plan_doc.equipe
        dept_employees = dept_emps.get(dept_name, [])

        for t in td["taches"]:
            if frappe.db.exists("Tache Equipe", {"plan": plan_name, "libelle": t["libelle"]}):
                print(f"  Skip (exists): {t['libelle'][:50]}")
                continue

            # Attribution: assign 1-2 employees from the department
            attributions = []
            available = dept_employees[:] if dept_employees else employees[:3]
            random.shuffle(available)
            for i, emp in enumerate(available[:min(2, len(available))]):
                attributions.append({
                    "employe": emp.name,
                    "nom_employe": emp.employee_name,
                    "role_attribution": "Responsable" if i == 0 else "Contributeur",
                })

            try:
                doc = frappe.get_doc({
                    "doctype": "Tache Equipe",
                    "plan": plan_name,
                    "equipe": dept_name,
                    "resultat_numero": t["resultat_numero"],
                    "resultat_libelle": t["resultat_libelle"],
                    "libelle": t["libelle"],
                    "frequence": t["frequence"],
                    "digitalisable": t["digitalisable"],
                    "taux_digitalisation": t["taux_digitalisation"],
                    "attributions": attributions,
                    "kpi": t["kpi"],
                    "poids": t["poids"],
                    "taux_estime": t["taux_estime"],
                    "taux_effectif": t["taux_effectif"],
                    "statut": t["statut"],
                    "commentaire": "",
                })
                doc.flags.ignore_permissions = True
                doc.flags.ignore_validate = True
                doc.flags.ignore_mandatory = True
                doc.insert(ignore_permissions=True)
                taches_created += 1
                print(f"  Created: {doc.name} - {t['libelle'][:50]}")
            except Exception as e:
                print(f"  ERROR Tache: {t['libelle'][:40]} → {e}")

    frappe.db.commit()

    # Update task counts on plans
    for titre, pn in plan_names.items():
        try:
            total = frappe.db.count("Tache Equipe", {"plan": pn})
            attrib = frappe.db.count("Tache Equipe", {"plan": pn, "statut": ["!=", "Non démarré"]})
            done = frappe.db.count("Tache Equipe", {"plan": pn, "statut": "Terminé"})
            frappe.db.set_value("Plan Trimestriel", pn, {
                "nombre_taches": total,
                "taches_attribuees": attrib,
                "taches_terminees": done,
            }, update_modified=False)
        except Exception:
            pass
    frappe.db.commit()
    print(f"  Total taches created: {taches_created}")

    # ── 3. KYA EVALUATION ──
    print("\n--- 3. KYA EVALUATION ---")
    evals_created = 0

    criteres_n1_evalue_n = [
        "Qualité du travail fourni",
        "Respect des délais",
        "Esprit d'initiative et proactivité",
        "Travail en équipe et collaboration",
        "Communication et reporting",
        "Assiduité et ponctualité",
        "Respect des procédures internes",
        "Capacité d'apprentissage",
    ]

    criteres_n_evalue_n1 = [
        "Clarté des objectifs fixés",
        "Disponibilité et écoute",
        "Feedback constructif et régulier",
        "Soutien au développement professionnel",
        "Gestion des conflits dans l'équipe",
        "Équité dans la répartition du travail",
    ]

    criteres_stage = [
        "Adaptation au milieu professionnel",
        "Maîtrise des tâches confiées",
        "Ponctualité et assiduité",
        "Initiative et autonomie",
        "Qualité des livrables",
        "Intégration dans l'équipe",
    ]

    # Build evaluation pairs
    eval_entries = []

    # N+1 evaluates N (managers evaluate their team)
    # Find managers/chefs
    managers = [e for e in employees if any(x in (e.designation or "").upper()
        for x in ("DIRECTEUR", "CHEF", "RESP"))]
    subordinates = [e for e in employees if not any(x in (e.designation or "").upper()
        for x in ("DIRECTEUR", "CHEF", "RESP")) and "STAGE" not in (e.designation or "").upper()]
    stagiaires = [e for e in employees if "STAGE" in (e.designation or "").upper()]

    # N+1 → N evaluations
    for mgr in managers[:3]:
        dept_subs = [e for e in subordinates if e.department == mgr.department]
        if not dept_subs:
            dept_subs = subordinates[:2]
        for sub in dept_subs[:2]:
            eval_entries.append({
                "type_evaluation": "N+1 évalue N",
                "trimestre": "T3 (Jul-Sep)",
                "annee": 2025,
                "evaluateur": mgr.name,
                "evaluateur_name": mgr.employee_name,
                "evalue": sub.name,
                "evalue_name": sub.employee_name,
                "titre_evaluation": f"Évaluation T3 2025 - {sub.employee_name}",
                "criteres_list": criteres_n1_evalue_n,
                "statut": random.choice(["Brouillon", "Soumis", "Validé"]),
                "points_forts": f"Bonne maîtrise de ses responsabilités. {sub.employee_name} montre un engagement constant.",
                "ameliorations": "Améliorer la communication écrite et le suivi des indicateurs.",
            })

    # N → N+1 evaluations
    for sub in subordinates[:3]:
        dept_mgrs = [e for e in managers if e.department == sub.department]
        if not dept_mgrs:
            dept_mgrs = managers[:1]
        for mgr in dept_mgrs[:1]:
            eval_entries.append({
                "type_evaluation": "N évalue N+1",
                "trimestre": "T3 (Jul-Sep)",
                "annee": 2025,
                "evaluateur": sub.name,
                "evaluateur_name": sub.employee_name,
                "evalue": mgr.name,
                "evalue_name": mgr.employee_name,
                "titre_evaluation": f"Évaluation ascendante T3 2025 - {mgr.employee_name}",
                "criteres_list": criteres_n_evalue_n1,
                "statut": random.choice(["Brouillon", "Soumis"]),
                "points_forts": f"{mgr.employee_name} fait preuve de leadership et d'écoute envers son équipe.",
                "ameliorations": "Renforcer la fréquence des réunions d'équipe.",
            })

    # Maître de stage évalue Stagiaire
    for stag in stagiaires[:3]:
        dept_mgrs = [e for e in managers if e.department == stag.department]
        if not dept_mgrs:
            dept_mgrs = managers[:1]
        for mgr in dept_mgrs[:1]:
            eval_entries.append({
                "type_evaluation": "Maître de stage évalue Stagiaire",
                "trimestre": "T3 (Jul-Sep)",
                "annee": 2025,
                "evaluateur": mgr.name,
                "evaluateur_name": mgr.employee_name,
                "evalue": stag.name,
                "evalue_name": stag.employee_name,
                "titre_evaluation": f"Éval. stage T3 2025 - {stag.employee_name}",
                "criteres_list": criteres_stage,
                "statut": random.choice(["Brouillon", "Soumis", "Validé"]),
                "points_forts": f"{stag.employee_name} montre une bonne volonté d'apprentissage.",
                "ameliorations": "Développer plus d'autonomie dans l'exécution des tâches.",
            })

    # Create evaluations
    for ev in eval_entries:
        if frappe.db.exists("KYA Evaluation", {
            "evaluateur": ev["evaluateur"],
            "evalue": ev["evalue"],
            "trimestre": ev["trimestre"],
        }):
            print(f"  Skip (exists): {ev['titre_evaluation'][:50]}")
            continue

        criteres = []
        for c in ev["criteres_list"]:
            note = str(random.randint(2, 5)) if ev["statut"] != "Brouillon" else "3"
            criteres.append({"libelle": c, "note": note})

        # Calculate average
        notes = [int(c["note"]) for c in criteres]
        taux_moyen = round(sum(notes) / len(notes) * 20, 1) if notes else 0  # Scale to 100

        try:
            doc = frappe.get_doc({
                "doctype": "KYA Evaluation",
                "type_evaluation": ev["type_evaluation"],
                "trimestre": ev["trimestre"],
                "annee": ev["annee"],
                "evaluateur": ev["evaluateur"],
                "evaluateur_name": ev["evaluateur_name"],
                "evalue": ev["evalue"],
                "evalue_name": ev["evalue_name"],
                "titre_evaluation": ev["titre_evaluation"],
                "criteres": criteres,
                "taux_moyen": taux_moyen,
                "statut": ev["statut"],
                "points_forts": ev["points_forts"],
                "ameliorations": ev["ameliorations"],
                "soumis_le": add_days(today(), -random.randint(1, 30)) if ev["statut"] != "Brouillon" else None,
            })
            doc.flags.ignore_permissions = True
            doc.flags.ignore_validate = True
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            evals_created += 1
            print(f"  Created: {doc.name} - {ev['titre_evaluation'][:50]} [{ev['statut']}]")
        except Exception as e:
            print(f"  ERROR Eval: {ev['titre_evaluation'][:40]} → {e}")

    frappe.db.commit()
    print(f"  Total evaluations created: {evals_created}")

    # ── SUMMARY ──
    print("\n" + "=" * 50)
    print("SEED GESTION EQUIPE COMPLETE!")
    print(f"  Plans Trimestriels: {plans_created}")
    print(f"  Taches Equipe: {taches_created}")
    print(f"  KYA Evaluations: {evals_created}")
    print("=" * 50)

    frappe.flags.in_import = False
