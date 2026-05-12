# Guides d'import — KYA Energy ERPNext

Documentation à destination des équipes **RH** et **Chefs d'Équipe**.  
Chaque section détaille le format du fichier Excel attendu, les colonnes obligatoires et la procédure étape par étape.

---

## 1. Import des Employés (RH)

### Quand l'utiliser
Lors de l'arrivée de nouveaux employés ou d'une migration initiale. À utiliser **avant** l'import des présences.

### Format attendu
Fichier : `IMPORT-Employé.xlsx` (modèle disponible dans `D:\Stage_KYA_Energy\RH\`)

| Colonne | Champ ERPNext | Obligatoire | Exemple |
|---|---|---|---|
| Matricule | `custom_matricule_kya` | Oui | `KYA-00042` |
| Nom | `last_name` | Oui | `AZOUMAH` |
| Prénom | `first_name` | Oui | `Yao Ketowoglo` |
| Email professionnel | `company_email` | Recommandé | `y.azoumah@kya-energy.com` |
| Téléphone | `cell_number` | Non | `+228 90 00 00 00` |
| Département | `department` | Oui | `DST` |
| Désignation/Poste | `designation` | Oui | `Directeur Général` |
| Type d'emploi | `employment_type` | Oui | `CDI` / `CDD` / `Stage` / `Prestataire` |
| Date d'entrée | `date_of_joining` | Oui | `01/01/2024` (JJ/MM/AAAA) |
| Genre | `gender` | Recommandé | `Masculin` / `Féminin` |

### Procédure
1. Préparer le fichier Excel (colonne Matricule obligatoire — unicité).
2. Dans Frappe Desk → **Human Resources > Import > Import d'Employés**.
3. Téléverser le fichier → Mapper les colonnes → Lancer l'import.
4. Vérifier les doublons via le rapport **Employee List** (filtre par matricule).

> **Règle anti-doublon** : si le matricule existe déjà, Frappe mettra à jour la fiche (pas de doublon).

---

## 2. Import des Présences Mensuelles (RH)

### Quand l'utiliser
Chaque fin de mois après validation de la feuille de présence par les chefs de service.  
L'import crée les enregistrements `Attendance` dans HRMS, ce qui alimente le **Dashboard RH** (`/kya-rh-dashboard`).

### Format attendu — Onglet VENTILATION
Fichier : `PRESENCE DU PERSONNEL_MMMM_AAAA.xlsx`

Le script lit l'onglet **VENTILATION** avec la structure suivante :

```
Lignes d'en-tête :
  - Ligne dates : colonnes 6+ = dates au format datetime Excel
  - Ligne header : NOM (col 2), PRENOMS (col 3), POSTE (col 4), DEPARTEMENT (col 5)

Lignes de données (une ligne par employé) :
  col 1 = N° Ord. | col 2 = NOM | col 3 = PRENOMS | col 4 = Poste | col 5 = Dépt
  col 6+ = codes journaliers selon la légende
```

### Codes de présence acceptés

| Code | Signification | Status Frappe |
|---|---|---|
| `P` | Présent | `Present` |
| `R` | Retard | `Present` (late_entry=1) |
| `M` | Mission terrain | `Work From Home` |
| `C` | Congé annuel | `On Leave` |
| `PC` | Permission convenance | `On Leave` |
| `CM` | Congé maternité/paternité | `On Leave` |
| `RM` | Repos médical | `On Leave` |
| `CF` | Congé formation | `On Leave` |
| `PE` | Permission exceptionnelle | `On Leave` |
| `MP` | Mis à pied (sanction) | `Absent` |
| `CG` | Congé général | `On Leave` |
| `F` | Jour férié | *ignoré — géré par Holiday List* |
| *vide* | Non renseigné | *ignoré par défaut* |

### Algorithme de matching Employé ↔ Ligne Excel

Le script utilise un matching en **3 passes** pour éviter les erreurs d'homonymie :

1. **Match exact normalisé** : `NOM PRENOMS` (Excel) ↔ toutes les variantes du nom en base (employee_name, last_name + first_name, first_name + last_name). Insensible aux accents et à la casse.
2. **Match inversé** : `PRENOMS NOM` ↔ idem.
3. **Déambiguïsation par NOM + préfixe prénom** : si deux employés ont le même NOM, le premier dont le prénom commence par les mêmes lettres gagne. Si ambiguïté non résolue → l'employé est mis dans la liste `unmatched` pour correction manuelle.

### Procédure

```bash
# Test d'abord en dry_run (ne crée rien) :
bench --site frontend execute kya_hr.maintenance.import_attendance.run \
    --kwargs "{'path': '/chemin/vers/PRESENCE_NOVEMBRE_2025.xlsx', 'dry_run': True}"

# Résultat attendu : {"ok": true, "rows_excel": 72, "matched_employees": 70, "unmatched": [...], "attendance_records": 1500}

# Une fois le dry_run validé, import réel :
bench --site frontend execute kya_hr.maintenance.import_attendance.run \
    --kwargs "{'path': '/chemin/vers/PRESENCE_NOVEMBRE_2025.xlsx', 'dry_run': False}"
```

> **Important** : les doublons (même employé + même date) sont automatiquement ignorés (skip). L'import peut être relancé sans risque.

### Que faire avec les non-matchés ?
Après dry_run, consulter la liste `unmatched` dans le résultat. Pour chaque nom non trouvé :
- Vérifier l'orthographe dans Frappe (fiche Employee → Nom + Prénom).
- Si l'employé n'existe pas encore, l'importer d'abord (cf. §1).
- Relancer le dry_run jusqu'à `unmatched = []`.

---

## 3. Import des Évaluations d'Équipe (Chef d'Équipe)

### Quand l'utiliser
Pour saisir en masse les taux d'avancement des tâches trimestrielles depuis un tableau Excel de l'équipe.

### Format attendu

| Colonne | Champ | Obligatoire | Exemple |
|---|---|---|---|
| Matricule | `custom_matricule_kya` | Oui | `KYA-00042` |
| Libellé tâche | `libelle` | Oui | `Maintenance préventive Q1` |
| Taux estimé | `taux_estime` | Non | `100` |
| Taux effectif | `taux_effectif` | Oui | `85` |
| Commentaire | `commentaire` | Non | `Avancement sur 3 semaines` |

### Procédure
1. Dans **Mon Espace** (`/mon-espace`), section "Gestion de mon Équipe".
2. Bouton **"📥 Importer Excel Évaluation"**.
3. Téléverser le fichier → L'import met à jour les champs `taux_effectif` et `statut` automatiquement.

> Le **statut** est recalculé automatiquement : `taux_effectif ≥ 100` → **Terminé** ; `taux_effectif > 0` → **En cours** ; `0` → **Non démarré**.

---

## 4. Import des Matricules (RH — opération ponctuelle)

### Quand l'utiliser
Pour affecter les matricules KYA (`KYA-XXXXX`) aux employés existants après une migration ou un ajout en masse.

### Procédure via API
```bash
bench --site frontend execute kya_hr.api.matricules_import.run_import \
    --kwargs "{'file_url': '/files/matricules.xlsx'}"
```

### Format du fichier matricules.xlsx

| Colonne A | Colonne B |
|---|---|
| `employee_name` (nom exact dans Frappe) | `matricule` (ex: `KYA-00001`) |

---

## 5. Règles générales anti-doublon

| Type | Clé d'unicité | Comportement si doublon |
|---|---|---|
| Employee | `custom_matricule_kya` | Mise à jour (update) |
| Attendance | `(employee, attendance_date)` | Skip (ignoré) |
| Tache Equipe | `name` (auto-incrémenté) | Pas de doublon possible |
| KYA Form Response | `(formulaire, employe)` | Skip si déjà soumis |

---

## Contacts en cas de problème

- **Support technique** : DSI KYA Energy — ticket interne
- **Données RH** : responsable RH (`rh@kya-energy.com`)
- **Vérification en base** : `bench --site frontend mariadb` puis SQL direct
