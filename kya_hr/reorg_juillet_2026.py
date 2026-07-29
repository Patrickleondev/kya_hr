# -*- coding: utf-8 -*-
"""Reorganisation KYA-Energy Group — Decision n°2026-010/DG/KEG (23/07/2026,
nouvel organigramme) + Decision n°2026-011/DG/KEG (24/07/2026, nominations).

CE SCRIPT EST MANUEL — NE PAS l'ajouter a safe_migrations/AFTER_MIGRATE.
Contrairement a normalize_departments.py (generique, idempotent, rejoue a
chaque migrate), celui-ci fige un evenement RH precis et date (des personnes
nommees a des postes precis a une date precise). Il doit etre execute UNE
SEULE FOIS, quand la Direction confirme le go-live de la reorganisation, puis
laisse de cote (le referentiel Department/Equipe KYA qu'il cree devient
ensuite la base normale que la RH edite au fil de l'eau).

Structure ciblee : root > Direction Generale (DG/DGA) + 5 Directions
d'activites (chacune avec ses Services) + services transversaux rattaches
directement au DG (Audit Interne & Risques, QHSE, Informatique & Logiciel-IT,
KYA-Energy Laboratory, KYA-Institute of Technology, Fondation KYA,
Prospection & developpement du reseau d'agences) + Agence KYA-Energy Group
Niger (creee vide, cf. Article 5 decision-010 ; la future cheffe d'agence
Noelie EKLOU-ADEGNOH reste dans son equipe actuelle jusqu'a sa prise de
fonction effective a Niamey, ~sept. 2026 — NE PAS la deplacer avant cette
date).

USAGE :
  - Web/prod (pas d'acces bench) : ce fichier est aussi un script autonome.
    Lancer directement avec python (necessite `requests` + un fichier
    .mcp.json accessible avec les creds ERPNEXT_URL/API_KEY/API_SECRET/
    PROXY_TOKEN*, cf. le bloc `if __name__ == "__main__"` en bas).
  - DRY_RUN=True (defaut) : n'envoie AUCUNE requete d'ecriture, se contente
    d'imprimer/loguer les operations prevues (une lecture Company seule pour
    resoudre le nom de la societe).
  - DRY_RUN=False : ecrit reellement. Coupe-circuit sur le premier 403 recu
    (n'insiste jamais sur un blocage proxy/rate-limit).

POINT A VERIFIER PAR LA RH AVANT/APRES EXECUTION :
  - La decision 2026-011 nomme "Bénédicte Kossiwa AMEOGNO" cheffe Achats &
    Approvisionnements. Il existe DEUX employees "AMEOGNO" en base :
    HR-EMP-00047 "Kossiwavi AMEOGNO" (equipe Fabrication/Production) et
    HR-EMP-00059 "Akossiwa AMEOGNO" (designation deja "RESP. ACHAT & APPROV",
    deja rattachee a M. FOUSSENI, deja cheffe de fait de Mme GUEDOPE). Ce
    script retient HR-EMP-00059 (correspondance la plus forte). A confirmer.
  - Employes actifs sans placement determinable (laisses tels quels, a
    completer par la RH) : HR-EMP-00019, 00038, 00039, 00055.
  - Mme Sylvie SHIPKE (en charge de "Prospection & developpement du reseau
    d'agences", Article 1 decision-010) n'a pas ete retrouvee dans la table
    Employee active : creer/lier sa fiche cote RH puis rattacher au
    departement "Prospection & developpement du reseau d'agences - KYA".
"""
from __future__ import annotations

import json
import sys
import time

DRY_RUN = True
SLEEP = 0.25
ROOT = "Tous les départements"
ABBR = "KYA"

DGE = "HR-EMP-00001"  # Directeur General


class Blocked(Exception):
    pass


def execute(dry_run: bool = True, mcp_json_path: str = "d:/Stage_KYA_Energy/.mcp.json") -> dict:
    """Point d'entree unique. Lit les identifiants prod depuis .mcp.json et
    applique (ou simule si dry_run) la reorganisation complete."""
    import requests
    from requests.adapters import HTTPAdapter, Retry

    env = json.load(open(mcp_json_path, encoding="utf-8"))["mcpServers"]["erpnext-prod"]["env"]
    base = env["ERPNEXT_URL"].rstrip("/")
    sess = requests.Session()
    sess.headers.update({
        "Authorization": f"token {env['ERPNEXT_API_KEY']}:{env['ERPNEXT_API_SECRET']}",
        "P-Access-Token-Id": env["PROXY_TOKEN_ID"], "P-Access-Token": env["PROXY_TOKEN"],
        "Content-Type": "application/json",
    })
    sess.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=2,
                                                         status_forcelist=[502, 503, 504])))

    report = {"depts_created": [], "depts_renamed": [], "teams_created": [], "teams_updated": [],
              "emp_updated": [], "errors": [], "dry_run": dry_run}
    company = {"name": None}

    def _check(r, label):
        if r.status_code == 403:
            print(f"\n!!! 403 sur [{label}] -- ARRET IMMEDIAT (pas d'insistance sur un throttle proxy).")
            raise Blocked(label)
        if r.status_code >= 400:
            report["errors"].append(f"{label}: {r.status_code} {r.text[:200]}")
        time.sleep(SLEEP)
        return r

    def full(label):
        return f"{label} - {ABBR}"

    def create_dept(label, parent, is_group=1):
        target = full(label)
        if dry_run:
            report["depts_created"].append(f"{target} (sous {parent}) [SIMULE]")
            return target
        payload = {"department_name": label, "parent_department": parent, "is_group": is_group}
        if company["name"]:
            payload["company"] = company["name"]
        r = sess.post(f"{base}/api/resource/Department", data=json.dumps(payload), timeout=60)
        _check(r, f"create_dept {label}")
        if r.status_code < 400:
            report["depts_created"].append(target)
        return target

    def rename_dept(old, new_label, new_parent=None):
        new_full = full(new_label)
        if dry_run:
            report["depts_renamed"].append(f"{old} -> {new_full} [SIMULE]")
            return new_full
        if old != new_full:
            r = sess.post(f"{base}/api/method/frappe.client.rename_doc", data=json.dumps({
                "doctype": "Department", "old_name": old, "new_name": new_full}), timeout=90)
            _check(r, f"rename_doc Department {old}->{new_full}")
        fields = {"department_name": new_label}
        if new_parent:
            fields["parent_department"] = new_parent
        r = sess.put(f"{base}/api/resource/Department/{requests.utils.quote(new_full)}",
                     data=json.dumps(fields), timeout=60)
        _check(r, f"set Department {new_full}")
        report["depts_renamed"].append(f"{old} -> {new_full}")
        return new_full

    def rename_team(old, new_name):
        if old == new_name:
            return old
        if dry_run:
            report["teams_updated"].append(f"RENAME {old} -> {new_name} [SIMULE]")
            return new_name
        r = sess.post(f"{base}/api/method/frappe.client.rename_doc", data=json.dumps({
            "doctype": "Equipe KYA", "old_name": old, "new_name": new_name}), timeout=90)
        _check(r, f"rename_doc Equipe KYA {old}->{new_name}")
        report["teams_updated"].append(f"RENAME {old} -> {new_name}")
        return new_name

    def update_team(name, **fields):
        if dry_run:
            report["teams_updated"].append(f"{name}: {fields} [SIMULE]")
            return
        r = sess.put(f"{base}/api/resource/Equipe KYA/{requests.utils.quote(name)}",
                     data=json.dumps(fields), timeout=60)
        _check(r, f"update_team {name}")
        report["teams_updated"].append(f"{name}: {fields}")

    def create_team(name, departement, chef_equipe=None):
        if dry_run:
            report["teams_created"].append(f"{name} -> {departement} (chef={chef_equipe}) [SIMULE]")
            return
        payload = {"nom_equipe": name, "departement": departement, "est_active": 1}
        if chef_equipe:
            payload["chef_equipe"] = chef_equipe
        r = sess.post(f"{base}/api/resource/Equipe KYA", data=json.dumps(payload), timeout=60)
        _check(r, f"create_team {name}")
        report["teams_created"].append(f"{name} -> {departement} (chef={chef_equipe})")

    def update_emp(name, **fields):
        if dry_run:
            report["emp_updated"].append(f"{name}: {fields} [SIMULE]")
            return
        r = sess.put(f"{base}/api/resource/Employee/{requests.utils.quote(name)}",
                     data=json.dumps(fields), timeout=60)
        _check(r, f"update_emp {name}")
        report["emp_updated"].append(f"{name}: {fields}")

    try:
        if not dry_run:
            comp = sess.get(f"{base}/api/resource/Company", params={
                "fields": '["name","abbr"]', "limit_page_length": 1}, timeout=60)
            _check(comp, "get Company")
            cdata = comp.json().get("data") or []
            if cdata:
                company["name"] = cdata[0]["name"]

        # ── 1) Department : renames ──
        dir_technique = rename_dept("Services Technique - KYA", "Direction Technique & Projets")
        dir_commercial = rename_dept("Services Commerciaux - KYA", "Direction du Développement Commercial")
        dir_daf = rename_dept("Services Supports - KYA", "Direction Administrative & Financière (DAF)")
        svc_it = rename_dept("EQUIPE INFORMATIQUE - KYA", "Informatique & Logiciel (IT)", new_parent=ROOT)

        # ── 2) Department : creations ──
        dir_industrielle = create_dept("Direction Industrielle", ROOT)
        dir_rh = create_dept("Direction des Ressources Humaines (DRH)", ROOT)
        svc_audit = create_dept("Audit Interne & Risques", ROOT, is_group=0)
        create_dept("QHSE", ROOT, is_group=0)
        create_dept("KYA-Energy Laboratory", ROOT, is_group=0)
        create_dept("KYA-Institute of Technology", ROOT, is_group=0)
        create_dept("Fondation KYA", ROOT, is_group=0)
        create_dept("Prospection & développement du réseau d'agences", ROOT, is_group=0)
        create_dept("Agence KYA-Energy Group Niger", ROOT, is_group=0)

        svc_offres = create_dept("Bureau d'études & Appels d'offres", dir_technique, is_group=0)
        svc_installations = create_dept("Installations & Chantiers", dir_technique, is_group=0)
        svc_sav = create_dept("SAV & Maintenance", dir_technique, is_group=0)
        svc_controle_sup = create_dept("Contrôle & Supervision", dir_technique, is_group=0)

        svc_production = create_dept("Production & Assemblage", dir_industrielle, is_group=0)
        create_dept("Méthodes & Industrialisation", dir_industrielle, is_group=0)
        create_dept("Qualité Produit", dir_industrielle, is_group=0)
        svc_supplychain = create_dept("Supply Chain & Magasins", dir_industrielle, is_group=0)

        create_dept("Grands Comptes", dir_commercial, is_group=0)
        svc_ventes = create_dept("Ventes & Distribution", dir_commercial, is_group=0)
        svc_marketing = create_dept("Marketing & Communication", dir_commercial, is_group=0)
        create_dept("Animation des agences", dir_commercial, is_group=0)

        create_dept("Recrutement & GPEC", dir_rh, is_group=0)
        create_dept("Administration & Paie", dir_rh, is_group=0)
        create_dept("Formation & Développement", dir_rh, is_group=0)
        create_dept("Relations Sociales", dir_rh, is_group=0)

        svc_compta = create_dept("Comptabilité & Fiscalité", dir_daf, is_group=0)
        create_dept("Contrôle de Gestion", dir_daf, is_group=0)
        create_dept("Trésorerie & Financements", dir_daf, is_group=0)
        svc_achats = create_dept("Achats & Approvisionnements", dir_daf, is_group=0)
        svc_moyens_gx = create_dept("Juridique & PI - Moyens Généraux", dir_daf, is_group=0)

        dg = full("Direction Générale")

        # ── 3) Equipe KYA ──
        rename_team("Equipe Offres", "Equipe Bureau d'Études & Appels d'Offres")
        update_team("Equipe Bureau d'Études & Appels d'Offres", departement=svc_offres, chef_equipe="HR-EMP-00030")
        create_team("Equipe Contrôle & Supervision", svc_controle_sup, chef_equipe="HR-EMP-00061")

        rename_team("Equipe Installation", "Equipe Installations & Chantiers")
        update_team("Equipe Installations & Chantiers", departement=svc_installations, chef_equipe="HR-EMP-00070")

        rename_team("Equipe Maintenance et SAV", "Equipe SAV & Maintenance")
        update_team("Equipe SAV & Maintenance", departement=svc_sav, chef_equipe="HR-EMP-00028")

        rename_team("Equipe Audit Interne", "Equipe Audit Interne & Risques")
        update_team("Equipe Audit Interne & Risques", departement=svc_audit, chef_equipe="")

        update_team("Equipe Assemblage", departement=svc_production, chef_equipe="HR-EMP-00063")
        rename_team("Equipe Fabrication", "Equipe Production")
        update_team("Equipe Production", departement=svc_production, chef_equipe="HR-EMP-00020")

        rename_team("Equipe Commercial", "Equipe Ventes & Distribution")
        update_team("Equipe Ventes & Distribution", departement=svc_ventes, chef_equipe="HR-EMP-00040")

        rename_team("Equipe Communication", "Equipe Marketing & Communication")
        update_team("Equipe Marketing & Communication", departement=svc_marketing, chef_equipe="HR-EMP-00025")

        rename_team("Equipe Compabilité et Finance", "Equipe Comptabilité & Fiscalité")
        update_team("Equipe Comptabilité & Fiscalité", departement=svc_compta, chef_equipe="")

        rename_team("Equipe Achats et Stocks", "Equipe Achats & Approvisionnements")
        update_team("Equipe Achats & Approvisionnements", departement=svc_achats, chef_equipe="HR-EMP-00059")
        create_team("Equipe Supply Chain & Magasins", svc_supplychain, chef_equipe=None)

        update_team("Equipe RH", departement=dir_rh, chef_equipe="HR-EMP-00003")

        rename_team("Logistique", "Equipe Moyens Généraux")
        update_team("Equipe Moyens Généraux", departement=svc_moyens_gx, chef_equipe="HR-EMP-00018")

        rename_team("Equipe Informatique", "Equipe Informatique & Logiciels (IT)")
        update_team("Equipe Informatique & Logiciels (IT)", departement=svc_it, chef_equipe="HR-EMP-00002")

        # ── 4) Employees : departement / superieur / designation ──
        emp_updates = [
            ("HR-EMP-00021", dg, DGE, "DIRECTEUR TECHNIQUE & PROJETS"),
            ("HR-EMP-00032", dg, DGE, "DIRECTEUR ADMINISTRATIF & FINANCIER"),
            ("HR-EMP-00067", dg, DGE, "DIRECTRICE DEV. COMMERCIAL (INTÉRIM)"),

            ("HR-EMP-00030", svc_offres, "HR-EMP-00021", "CHEF EQUIPE OFFRES"),
            ("HR-EMP-00033", svc_offres, "HR-EMP-00030", None),
            ("HR-EMP-00061", svc_controle_sup, "HR-EMP-00021", "CHEF EQUIPE CONTROLE & SUPERVISION"),
            ("HR-EMP-00070", svc_installations, "HR-EMP-00021", "CHEF EQUIPE INSTALLATIONS & CHANTIERS"),
            ("HR-EMP-00022", svc_installations, "HR-EMP-00070", None),
            ("HR-EMP-00027", svc_installations, "HR-EMP-00070", None),
            ("HR-EMP-00034", svc_installations, "HR-EMP-00070", None),
            ("HR-EMP-00035", svc_installations, "HR-EMP-00070", None),
            ("HR-EMP-00057", svc_installations, "HR-EMP-00070", None),
            ("HR-EMP-00062", svc_installations, None, None),
            ("HR-EMP-00028", svc_sav, "HR-EMP-00021", "CHEF EQUIPE SAV & MAINTENANCE"),
            ("HR-EMP-00023", svc_sav, "HR-EMP-00028", None),
            ("HR-EMP-00036", svc_sav, "HR-EMP-00028", None),
            ("HR-EMP-00041", svc_sav, "HR-EMP-00028", None),
            ("HR-EMP-00046", svc_sav, "HR-EMP-00028", None),

            ("HR-EMP-00024", svc_audit, DGE, None),

            ("HR-EMP-00063", svc_production, DGE, "CHEF EQUIPE ASSEMBLAGE"),
            ("HR-EMP-00031", svc_production, "HR-EMP-00063", None),
            ("HR-EMP-00052", svc_production, "HR-EMP-00063", None),
            ("HR-EMP-00053", svc_production, "HR-EMP-00063", None),
            ("HR-EMP-00020", svc_production, DGE, "CHEF EQUIPE PRODUCTION"),
            ("HR-EMP-00042", svc_production, "HR-EMP-00020", None),
            ("HR-EMP-00047", svc_production, "HR-EMP-00020", None),
            ("HR-EMP-00049", svc_production, "HR-EMP-00020", None),
            ("HR-EMP-00004", svc_supplychain, DGE, None),

            ("HR-EMP-00040", svc_ventes, "HR-EMP-00067", "CHEF EQUIPE VENTE & DISTRIBUTION"),
            ("HR-EMP-00025", svc_marketing, "HR-EMP-00067", "CHEF EQUIPE MARKETING & COMM."),
            ("HR-EMP-00044", svc_marketing, "HR-EMP-00025", None),
            ("HR-EMP-00054", svc_marketing, "HR-EMP-00025", None),

            ("HR-EMP-00003", dir_rh, "HR-EMP-00066", None),
            ("HR-EMP-00043", dir_rh, "HR-EMP-00003", None),
            ("HR-EMP-00048", dir_rh, "HR-EMP-00003", None),
            ("HR-EMP-00069", dir_rh, "HR-EMP-00003", None),

            ("HR-EMP-00037", svc_compta, DGE, None),
            ("HR-EMP-00064", svc_compta, DGE, None),
            ("HR-EMP-00017", svc_compta, "HR-EMP-00032", None),
            ("KEG-STG-00001", svc_compta, "HR-EMP-00032", None),
            ("HR-EMP-00059", svc_achats, "HR-EMP-00032", None),
            ("HR-EMP-00026", svc_achats, "HR-EMP-00059", None),
            ("HR-EMP-00018", svc_moyens_gx, "HR-EMP-00032", "CHEF EQUIPE MOYENS GENERAUX"),
            ("HR-EMP-00058", svc_moyens_gx, "HR-EMP-00018", None),
            ("HR-EMP-00060", svc_moyens_gx, "HR-EMP-00018", None),
            ("HR-EMP-00065", svc_moyens_gx, "HR-EMP-00018", None),

            ("HR-EMP-00002", svc_it, DGE, "CHEF SERVICE INFORMATIQUE & LOGICIELS - IT"),
            ("HR-EMP-00006", svc_it, "HR-EMP-00002", None),
            ("HR-EMP-00007", svc_it, "HR-EMP-00002", None),
            ("HR-EMP-00010", svc_it, "HR-EMP-00002", None),
            ("HR-EMP-00014", svc_it, "HR-EMP-00002", None),
            ("HR-EMP-00015", svc_it, "HR-EMP-00002", None),
            ("HR-EMP-00029", svc_it, "HR-EMP-00002", None),
            ("HR-EMP-00050", svc_it, "HR-EMP-00002", None),

            ("HR-EMP-00056", dg, DGE, None),
            ("HR-EMP-00068", dg, DGE, None),
        ]
        for emp, dept, rt, desig in emp_updates:
            fields = {"department": dept}
            if rt is not None:
                fields["reports_to"] = rt
            if desig:
                fields["designation"] = desig
            update_emp(emp, **fields)

        # reassignations d'equipe pour les 2 personnes qui quittent leur ancienne equipe
        update_emp("HR-EMP-00061", custom_kya_equipe="Equipe Contrôle & Supervision")
        update_emp("HR-EMP-00004", custom_kya_equipe="Equipe Supply Chain & Magasins")

    except Blocked as e:
        report["errors"].append(f"ARRET (403) pendant [{e}] — progres partiel seulement.")

    print(f"\n=== RAPPORT reorg_juillet_2026 (dry_run={dry_run}) ===")
    for k, v in report.items():
        if k == "dry_run":
            continue
        print(f"\n-- {k} ({len(v)}) --")
        for line in v:
            print(f"  {line}")
    return report


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dry = "--apply" not in sys.argv
    if dry:
        print("[dry-run] Ajouter --apply en argument pour ecrire reellement en prod.\n")
    execute(dry_run=dry)
