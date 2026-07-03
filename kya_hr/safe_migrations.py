# -*- coding: utf-8 -*-
"""Wrapper robuste pour after_migrate / after_install.

Problème historique : un script de migration qui plante (DocType manquant
sur une fresh install, bug Frappe v16 "'list' object is not callable", etc.)
faisait avorter toute la suite, laissant l'instance dans un état partiel
(icônes manquantes, workspaces non publiés, branding non posé).

Solution : on appelle chaque script dans son propre try/except. L'échec
d'un script est loggé via frappe.log_error mais N'INTERROMPT PAS les
suivants. La migration globale réussit toujours ; les erreurs sont
visibles dans Desk > Settings > Error Log.

Pour un re-run ciblé : `bench --site <site> execute
kya_hr.safe_migrations.retry_failed`.
"""
from __future__ import annotations

import traceback

import frappe


# Ordre exact des migrations historiques (cf. hooks.py:after_migrate).
# Une entrée = (chemin d'attribut, label humain pour le log).
AFTER_MIGRATE: list[tuple[str, str]] = [
    ("kya_hr.runtime_overrides.execute", "Runtime overrides (timeout gunicorn + disable demo setup)"),
    ("kya_hr.setup_locale.execute", "Setup locale (timezone, fuseau)"),
    ("kya_hr.setup_translations.execute", "Override traductions KYA (Type d'emploi: Stage/Intern/etc.)"),
    ("kya_hr.setup_employment_types.execute", "Normalise Employment Types (FR: Stage/CDD/CDI/Prestataire/Apprentissage)"),
    ("kya_hr.setup_leave_types.execute", "Setup leave types HRMS"),
    ("kya_hr.setup_leave_extension.execute", "Setup champs prolongation exceptionnelle DG sur Leave Application"),
    ("kya_hr.setup_planning_equipe.execute", "Workflow Planning de Congé d'Équipe (Chef -> RH -> DG -> Approuvé)"),
    ("kya_hr.force_sync_workspaces.execute", "Force sync workspaces"),
    ("kya_hr.setup_native_workspaces.execute", "Restaure workspaces natifs vides (HR/Accounting/Stock/Buying/Selling/Payroll)"),
    ("kya_hr.force_publish_webforms.execute", "Force publish web forms"),
    ("kya_hr.ensure_webform_perms.execute", "Ensure DocPerm Employee+Stagiaire sur DocTypes des Web Forms KYA"),
    ("kya_hr.ensure_webform_print_formats.execute", "Associe chaque Web Form a son Print Format officiel (impression complete avec lignes de table)"),
    ("kya_hr.ensure_webform_table_columns.execute", "Tables web forms <= 10 colonnes (BC/PV/Inventaire/Retour/Demande Achat) : plus de scroll horizontal"),
    ("kya_hr.fix_phantom_workflow_roles.execute", "Remap rôles fantômes des transitions (Responsable Comptable -> Comptable)"),
    ("kya_hr.ensure_workflow_states.execute", "Cree tout Workflow State manquant (fix 'État introuvable' : En attente Validation DFC, En attente Maitre de Stage...)"),
    ("kya_hr.ensure_workflow_perms.execute", "Ensure perms approbateurs workflow (write sans if_owner: Chef/Audit/DG/RH...)"),
    ("kya_hr.force_resync_webform_fields.execute", "Force resync web form fields (Frappe v16 bug workaround)"),
    ("kya_hr.notification_fixes.execute", "Notification fixes"),
    ("kya_hr.setup_branding.execute", "Branding KYA (logos, couleurs)"),
    ("kya_hr.fix_all_workspaces.execute", "Fix all workspaces"),
    ("kya_hr.setup_fleet.run", "Setup fleet (DocType véhicule, etc.)"),
    ("kya_hr.setup_fleet_workspace.run", "Setup fleet workspace"),
    ("kya_hr.setup_fleet_dashboard.run", "Setup fleet dashboard"),
    ("kya_hr.setup_pv_extensions.run", "Setup PV extensions"),
    ("kya_hr.setup_retour_materiel.run", "Setup Retour Matériel + fournisseurs KYA"),
    ("kya_hr.setup_kya_stocks.execute", "Setup stock KYA (5 groupes + 36 items + opening 2026-06-05)"),
    ("kya_hr.setup_inventaire_dashboard.run", "Setup inventaire dashboard"),
    ("kya_hr.setup_rh_dashboard.run", "Setup dashboard RH"),
    ("kya_hr.setup_attendance_fields.execute", "Setup custom fields Attendance (KYA marked_by, lateness, etc.)"),
    ("kya_hr.normalize_departments.execute", "Arbre Department en français sous 4 macro-départements (DG/Supports/Techniques/Commerciaux) ; rename_doc propage les références"),
    ("kya_hr.fix_naming_series.execute", "Resync compteurs tabSeries (corrige l'ID employé en double : compteur en retard sur le max réel)"),
    ("kya_hr.desktop_icons.execute", "Desktop icons (workaround Frappe v16)"),
    ("kya_hr.coherence_fixes.execute", "Coherence fixes (champs orphelins)"),
    ("kya_hr.fix_sidebar_equipe_kya.execute", "Fix sidebar : Equipe KYA -> Espace Stagiaires (mauvais link_to)"),
    ("kya_hr.fix_mes_approbations_scope.execute", "Purge 'Mes Approbations' des espaces metier mutualises"),
    ("kya_hr.ensure_visibility.execute", "Ensure workspaces visibility"),
    ("kya_hr.ensure_workspace_roles.execute", "Visibilite workspaces par role (Espace Employes<-Employee, Stagiaires<-Stagiaire, etc.)"),
    ("kya_hr.setup_logistique_access.execute", "Sortie Vehicule visible Direction (DG/DGA) + roles logistiques sur espace Logistique"),
    ("kya_hr.equipe_member_sync.recompute_all", "Recalcule nombre_membres des Equipes KYA (corrige compteurs perimes apres assignation employes)"),
    ("kya_hr.ensure_chef_capabilities.execute", "Aligne capacites chef (Chef Service=Chef Equipe=Chef d'Equipe : approbation + assignation taches)"),
    ("kya_hr.link_employees_users.link_by_email", "Lie Employees aux Users par email (racine 'Nom du Demandeur vide')"),
    ("kya_hr.ensure_employee_roles.execute", "Ensure Employee/Stagiaire roles on linked Users"),
    ("kya_hr.setup_native_parents.execute", "Cree workspaces parents Frappe HR + Comptabilite (groupent natifs v16)"),
    ("kya_hr.fix_duplicate_desktop_icons.execute", "Purge icones/links dupliques (Direction Generale x3, etc.)"),
    ("kya_hr.fix_workspace_labels_fr.execute", "Labels FR avec accents (Comptabilite, Employes, Generale)"),
    ("kya_hr.setup_kya_redirects.execute", "Website redirects /desk/people, /desk/hrms, etc."),
    ("kya_hr.assign_orphan_workspaces.execute", "Donne un workspace d'accueil aux DocTypes orphelins (Visites/Réunions->Direction, Formation/Équipes->RH, Retours->Stock) : sortent du fallback Espace Stagiaires"),
    ("kya_hr.maintenance.fix_workflow_self_approval.execute", "Self-approval=1 sur les transitions de soumission (l'auteur owner doit pouvoir soumettre sa propre fiche : caissier/comptable/employé)"),
    ("kya_hr.maintenance.ensure_direction_oversight.execute", "Direction (DG/DGA) : main complète (read/write/create/delete/export) sur récaps compta/marchés/SoP des dashboards Direction"),
    ("kya_hr.maintenance.sync_workspace_shortcuts.execute", "Rend VISIBLES tous les raccourcis des espaces KYA (bug v16 : shortcut absent du content JSON = non affiché → dashboards Direction invisibles)"),
    ("kya_hr.maintenance.fix_leave_workflow_conditions.execute", "Conditions workflow congés safe-eval (frappe.get_roles indisponible → crash 'Congé pris' ; remplacé par frappe.db.get_list Has Role)"),
    ("kya_hr.maintenance.ensure_link_shortcuts.execute", "Chaque lien d'espace a un raccourci (Department/Designation/Formation/Equipe/Templates… + dashboards RH/Stocks/Achats) ; enchaîne sync_workspace_shortcuts"),
    ("kya_hr.maintenance.setup_supplier_mail_buttons.execute", "Boutons desk « Envoyer au fournisseur » sur Bon Commande KYA + Appel Offre KYA (revue avant envoi, PDF joint, gestion sans email)"),
    ("kya_hr.maintenance.fix_formation_equipe.execute", "Besoin de Formation : champ équipe = Equipe KYA (pas Département) ; département + chef déduits de l'équipe"),
    ("kya_hr.maintenance.ensure_formation_v2.execute", "Formation v2 : réconcilie coût total ligne (direct+accessoire) + compteurs bénéficiaires (suivi par employé) sur plans existants"),
    ("kya_hr.maintenance.fix_workspace_anomalies.execute", "Workspaces : parent_page NULL->'' (icônes qui plantent au clic) + Gestion Équipe accent/emoji"),
    ("kya_hr.maintenance.relabel_native_stock.execute", "Articles : écran ERPNext natif relabellisé en français (Code article/Nom/Groupe/Type/UdM) + droit create Item aux rôles stock (perms standard préservées)"),
    ("kya_hr.maintenance.ensure_pdf_branding.execute", "En-tête KYA (logo + coordonnées) sur les PDF qui en manquaient (Demande Achat/PV Sortie/PV Entrée/Brouillard/Inventaire)"),
    ("kya_hr.maintenance.fix_user_permission_links.execute", "ignore_user_permissions sur les liens Employee/Company des fiches à workflow (User Permission 'ma fiche employé' bloquait les approbateurs : Comptable/DFC/Chef… ne pouvaient plus viser un doc d'autrui)"),
    ("kya_hr.maintenance.backfill_clients_projets.execute", "Client KYA / Projet KYA (répertoires maison) créés depuis les PV Sortie existants — les Links repointés du Customer/Project natif gardent des valeurs valides"),
    ("kya_hr.maintenance.seed_categories_typologie.execute", "14 catégories (typologies d'équipement) de la fiche AEA-ENG-13 semées pour le picker de saisie/import (idempotent, n'écrase pas les catégories libres existantes)"),
]

AFTER_INSTALL: list[tuple[str, str]] = [
    ("kya_hr.runtime_overrides.execute", "Runtime overrides (timeout gunicorn + disable demo setup)"),
    ("kya_hr.desktop_icons.execute", "Desktop icons (install)"),
    ("kya_hr.coherence_fixes.execute", "Coherence fixes (install)"),
    ("kya_hr.ensure_visibility.execute", "Ensure visibility (install)"),
]


def _run_one(path: str, label: str) -> dict:
    """Exécute une migration, attrape toute exception, retourne un résumé."""
    result = {"label": label, "path": path, "ok": False, "error": None}
    try:
        fn = frappe.get_attr(path)
    except Exception as exc:
        result["error"] = f"Cannot import {path}: {exc}"
        _log(label, result["error"])
        return result

    if not callable(fn):
        result["error"] = f"{path} is not callable (type={type(fn).__name__})"
        _log(label, result["error"])
        return result

    try:
        fn()
        result["ok"] = True
    except Exception:
        tb = traceback.format_exc()
        result["error"] = tb
        _log(label, tb)
    return result


def _log(label: str, message: str) -> None:
    """Logue dans Error Log + console pour visibilité immédiate au bench migrate."""
    try:
        frappe.log_error(title=f"[safe_migrations] {label}", message=message[:140000])
    except Exception:
        pass
    # Affiche aussi dans le shell pour que le devops voie l'erreur dans le run de migrate.
    print(f"[kya_hr.safe_migrations] FAILED : {label}\n{message}")


def _run_all(table: list[tuple[str, str]], phase: str) -> dict:
    print(f"[kya_hr.safe_migrations] === {phase} : {len(table)} étapes ===")
    results = []
    ok_count = 0
    failed = []
    for path, label in table:
        res = _run_one(path, label)
        results.append(res)
        if res["ok"]:
            ok_count += 1
            print(f"  OK   {label}")
        else:
            failed.append(label)
            print(f"  FAIL {label} (voir Error Log)")
    print(
        f"[kya_hr.safe_migrations] {phase} terminé : "
        f"{ok_count}/{len(table)} OK, {len(failed)} en erreur."
    )
    try:
        frappe.db.commit()
    except Exception:
        pass
    return {"phase": phase, "ok": ok_count, "failed": failed, "details": results}


def after_migrate() -> dict:
    """Entrypoint pour hooks.after_migrate. Toujours retourne, ne lève jamais."""
    return _run_all(AFTER_MIGRATE, "after_migrate")


def after_install() -> dict:
    """Entrypoint pour hooks.after_install."""
    return _run_all(AFTER_INSTALL, "after_install")


@frappe.whitelist()
def retry_failed() -> dict:
    """Permet à un admin de re-rejouer la suite after_migrate à la main
    depuis le desk ou un bench execute. Utile après avoir corrigé un bug
    dans un script."""
    return after_migrate()
