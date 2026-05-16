# Roadmap — Imports RH (next session)

> **Contexte** : à l'issue de la session du 2026-05-16, les fichiers Excel utilisés
> par la RH ont été analysés mais aucun importeur production n'a été codé pour ne
> pas baisser la qualité. Ce document liste la structure réelle de chaque fichier
> et l'architecture cible pour les imports.

## Architecture proposée (unique pour les 5 imports)

```
DocType "KYA Import RH"
  ├── type_import (Select) : Presence / Solde / Planning / Fiche / Equipe
  ├── periode (Data)       : "Novembre 2025" / "2025-11" / "T1 2026"
  ├── fichier_source (Attach)
  ├── statut (Select)      : Brouillon / Parsé / Importé / Erreur
  ├── total_lignes (Int)
  ├── total_inseres (Int)
  ├── total_erreurs (Int)
  ├── log_traces (Long Text)   # JSON ligne-par-ligne
  └── rows_json (Long Text)    # données parsées brutes pour audit

API endpoints :
  POST /api/method/kya_hr.api.rh_imports.upload_and_parse
       → upload + parse + create KYA Import RH (statut=Brouillon)
  POST /api/method/kya_hr.api.rh_imports.commit_import
       → valide et écrit dans les doctypes cibles (Attendance, Leave Allocation...)
  GET  /api/method/kya_hr.api.rh_imports.download_template?type_import=presence
       → retourne un .xlsx pré-rempli (en-tête KYA + colonnes attendues)

Workspace "Espace RH" : ajouter section "📥 Imports RH" avec 5 boutons URL.
```

## Inventaire des fichiers (mesuré 2026-05-16)

### 1. PRESENCE DU PERSONNEL (mensuel)
**Fichier** : `D:\Stage_KYA_Energy\RH\PRESENCE DU PERSONNEL_NOVEMBRE_2025XXX.xlsx`

**3 feuilles** :
- `Feuil1` (145×12) : liste employés (2 tables côte-à-côte cols 1-5 + 9-12). **Pas de présences**.
- `Données` (146×4) : référentiel `N° MLE, NOM, PRENOMS, SECTION`
- **`VENTILATION` (97×16381 mais ~48 cols utiles)** : LA grille mensuelle
  - Rows 1-9 : letterhead KYA (logo, ref `RH-ENG-04-V01`, date, légende)
  - Rows ~10-12 : headers dates (multi-niveau)
  - Rows ~13-80 : data — col 1 matricule, col 2 NOM, col 3 PRENOM, col 4 FONCTION,
    cols 5-25 statuts journaliers, cols 26+ aggregates (P/A/RM/M counts)
  - Codes statuts : `P` Présent, `RM` Repos Médical, `M` Mission, `PC` Permission/Congé,
    `.` ou vide Absent

**Cible** : `tabAttendance` (HRMS standard) — 1 row par employé×jour.

**Parser** :
```python
def parse_ventilation(ws):
    # 1. Trouver la ligne avec les dates en cellule (généralement row 10-12)
    date_row = find_date_header_row(ws)
    # 2. Mapper colonne → date
    cols_to_date = {c: parse_date(ws.cell(row=date_row, column=c).value)
                    for c in range(5, ws.max_column+1)
                    if ws.cell(row=date_row, column=c).value}
    # 3. Trouver la première ligne de données (employé avec matricule en col 1)
    data_start = find_first_data_row(ws)
    # 4. Pour chaque ligne, extraire matricule + boucler sur les cols de date
    for r in range(data_start, ws.max_row+1):
        matricule = ws.cell(row=r, column=1).value
        if not matricule or not isinstance(matricule, (int, float)):
            continue
        employee = find_employee_by_matricule(matricule)
        for col, date in cols_to_date.items():
            status_code = (ws.cell(row=r, column=col).value or "").strip()
            attendance_status = STATUS_MAP.get(status_code, None)
            if attendance_status:
                yield {"employee": employee, "date": date, "status": attendance_status}

STATUS_MAP = {"P": "Present", "RM": "On Leave", "M": "Work From Home",
              "PC": "On Leave", "": None}
```

**Calcul d'heures par mois** : agréger les `Present` × 8h (standard contrat) pour chaque employé sur la période. Stocker dans un nouveau doctype `Bilan Mensuel Presence` (à créer) ou comme champ calculé sur `Employee Monthly Salary`.

### 2. SOLDE CONGES PERSONNEL
**Fichier** : `D:\Stage_KYA_Energy\RH\SOLDE CONGES PERSONNEL 2025XXX.xlsx`

**1 feuille `Feuil1` (62×17)** :
- Row 1 : titre "ETAT DU SOLDE DE..."
- Row 2 : headers principaux : `N° Ord., Nom & Prénoms, Date d'embauche, Date de référence, Ancienneté à date, Nombre total de jours, Nombre de jours pris, Solde initial, Périodes de jouissance`
- Row 3 : sub-headers : `2023, 2024, CONGE ANTICIPE C, CONGE INDIVIDUEL`
- Row 4+ : data (1 ligne par employé)

**Cible** : `tabLeave Allocation` (HRMS) + nouveau doctype `Solde Conge Annuel KYA`
(pour stocker l'ancienneté et le solde calculé spécifique au Togo).

**Parser** : skip 3 lignes, mapper colonnes, créer Leave Allocation par employé.

### 3. PLANNING DES CONGES ANNUELS
**Fichier** : `D:\Stage_KYA_Energy\RH\PLANNING DES CONGÉS ANNUELS 2025XXXX.xlsx`

**2 feuilles** :
- `PLANNING GLOBAL` (144×9)
  - Rows 1-13 : letterhead KYA (`RH-ENG-21-V01`, date, signatures Rédigé/Vérifié/Validé)
  - **Row 14 : headers** `NOM, PRENOMS, FONCTION, PROPOSITIONS VALIDÉES, Dates, NBRE DE JOURS PRIS`
  - Row 15+ : data
- `AUTRES ABSENCES` (10×6) : suivi des autres absences (maladie etc.)

**Cible** : `tabPlanning Conge` (custom KYA existant) — coexiste avec le système actuel.

**Parser** : skip 13 lignes, parser à partir de R15, écrire des Planning Conge avec
`workflow_state="Validé"` (puisque c'est un planning déjà validé).

### 4. FICHE DE GESTION DES CONGES ANNUELS
**Fichier(s)** :
- `D:\Stage_KYA_Energy\RH\FICHE DE GESTION DES CONGES ANNUELS 2025XXXX.xlsx`
- `D:\Stage_KYA_Energy\RH\Système de planning de congé\FICHE DE GESTION DES CONGES ANNUELS 2026.xlsx`

**Structure** (`Feuil1` ~55×30) :
- Row 2 : titre "FICHE DE GESTION..."
- Row 3 : headers ligne 1 : `Nbre Jours Acquis, Congés anticipés, Nbre Jours Restants, Durée congé général, Solde en fin janvier, Premier départ, ..., Deuxième départ`
- Row 4 : headers ligne 2 (sub) : `N° Ord, Nom, Prénoms, [vides], Date départ 1, Date reprise 1, Nbre jours jouis, Solde 1, ...`
- Row 5+ : data, 1 ligne par employé avec PLUSIEURS dates de départ (jusqu'à 3 ou 4)

**Cible** : nouveau doctype `Fiche Gestion Conge KYA` qui rassemble :
- Employee (Link)
- Année (Int)
- Nbre jours acquis (Int) - calculé selon ancienneté
- Congés anticipés (Int)
- Solde initial (Int)
- Multiples départs (child table avec date_depart, date_reprise, nb_jours)
- Solde final calculé

**Parser** : multi-row headers (2 lignes), mapper colonnes en fusion.

### 5. PROPOSITION DE PLANIFICATION 2026 CODIR
**Fichier** : `D:\Stage_KYA_Energy\RH\Système de planning de congé\Proposition_de_planification_des_congés_annuels_2026_CODIR_KYA.xlsx`

**Structure** (`Planning prévis-congé2026` 65×29) :
- Row 1 : headers ligne 1 : `N° Ord, Nom, Prénoms, Nbre jours rest, Nbre Jours Acquis, Congés obligatoires, Durée congé général, Solde en fin jan, Congés obligat, ...`
- Row 2 : headers ligne 2 : `Date départ 1, Date reprise 1, [Nbre jours], Date de départ, Date de reprise`
- Row 3 : ligne de section "DIRECTION GENERALE"
- Row 4+ : data (avec **formules `#REF!`** parfois — fichier de proposition, pas final)

Le fichier contient des `#REF!` (formules cassées) → le parser doit **gérer les valeurs d'erreur** Excel (les ignorer ou les remplacer par null).

**Cible** : même que Planning ci-dessus, mais avec `workflow_state="En attente"` (proposition).

### 6. GESTION D'ÉQUIPE (mentionné par user mais pas de fichier fourni)
Le user a parlé d'un import "pour gestion d'équipe (pour gestion d'équipe aussi tu te
bases sur le template que je t'ai lié pour faire un modèle d'import que les chefs
d'équipe peuvent download et renseigner avec les IDs des personnel)".

**Cible** : `tabEquipe KYA` + `tabTache Equipe` (existants).

**Modèle à créer** (downloadable Excel template) :
- Sheet 1 "Équipe" : nom_équipe, chef_équipe (matricule), date_creation
- Sheet 2 "Membres" : nom_équipe, matricule_membre, rôle
- Sheet 3 "Tâches" : nom_équipe, titre_tache, description, date_debut, date_fin, taux_effectif

## Codes statuts standard à mapper (Présences)

| Code XLS | Attendance Status | Comment |
|---|---|---|
| `P` | `Present` | Présent normal |
| `RM` | `On Leave` + Leave Type=Sick Leave | Repos médical |
| `M` | `Work From Home` | Mission externe (à confirmer avec user) |
| `PC` | `On Leave` + Leave Type=Annual Leave | Permission/Congé |
| `A` | `Absent` | Absence non-justifiée |
| (vide ou `.`) | skip (jour férié ou weekend) | |

## Ordre d'implémentation recommandé pour next session

1. **DocType `KYA Import RH`** + workspace shortcuts (1h)
2. **Endpoint `download_template`** générique avec sous-routines par type (1h)
3. **Parser Presence VENTILATION** + écriture Attendance + Bilan Mensuel (2h)
4. **Parser Solde Congés** + écriture Leave Allocation + Solde Conge Annuel KYA (1h30)
5. **Parser Planning** + écriture Planning Conge (1h)
6. **Parser Fiche Gestion** + écriture Fiche Gestion Conge KYA (1h30)
7. **Parser + template Gestion Équipe** (1h)

**Total estimé : 9h de travail focus** (1 journée de dev).

## Edge cases à ne pas oublier

- Letterhead KYA en haut → toujours skip les lignes jusqu'à trouver la ligne avec
  les headers attendus
- Multi-row headers → fusionner les 2 lignes en 1 dict pour le mapping colonne→champ
- Cellules `#REF!`, `#N/A`, `#DIV/0!` → traiter comme `None`
- Noms d'employés avec espaces de trailing → `str.strip()` partout
- Matricules en `int` parfois, `str` parfois → normaliser via `_find_employee()`
- Le code existant `kya_hr.api.attendance_import` couvre déjà un FORMAT SIMPLE
  (1 ligne par jour) — utile à garder en parallèle pour les imports manuels.

## Lien avec le système existant

- `Planning Conge` (custom) : on garde, l'import alimente les états validés.
- `Leave Application` (HRMS) : pas de change, c'est la demande individuelle.
- `Attendance` (HRMS) : alimenté par l'import + import simple existant.
- `Equipe KYA` / `Tache Equipe` : alimenté par l'import Gestion Équipe.
- Tous les workflows existants (chef_routing, signatures, notifications) restent
  inchangés — l'import écrit en état "Validé/Approuvé" directement.
