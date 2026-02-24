# Guide d'Assignation des Rôles — Workflows KYA Énergie

## Introduction

Ce document explique comment configurer correctement les **utilisateurs** dans ERPNext pour que les deux workflows de gestion des congés et sorties fonctionnent de bout en bout.

Les deux workflows actifs dans `kya_hr` sont :
- **Flux Congés et Sortie Employés** — pour les employés permanents
- **Flux Autorisation de Sortie Stagiaires** — pour les stagiaires

---

## 1. Les Rôles Impliqués dans les Workflows

| Rôle ERPNext | Qui reçoit ce rôle ? | Responsabilité dans le flux |
|---|---|---|
| `Employee` | Tout employé/stagiaire | Soumet la demande de congé |
| `Supérieur Immédiat` | Chef d'équipe / Responsable direct | 1ère approbation (pour employés non-Chef d'équipe) |
| `Responsable RH` | Gestionnaire RH | 2ème approbation (validation RH) |
| `Directeur Général` | Directeur de l'entreprise | Approbation finale |
| `Responsable des Stagiaires` | Responsable interne des stagiaires | 2ème approbation flux stagiaires |
| `Maître de Stage` | Tuteur du stagiaire | (Rôle informatif, non intégré au flux principal) |
| `Stagiaire` | Tout stagiaire | Rôle d'identification (complète `Employee`) |

---

## 2. Flux Employés — « Flux Congés et Sortie Employés »

### Diagramme du flux

```
Employé soumet
      │
      ▼
[Brouillon]
      │
      ├── Si designation == "Chef d'équipe" ──────────────────────┐
      │                                                             │
      ▼                                                             ▼
[En attente du Supérieur Immédiat]              [En attente RH]
      │                                                             │
      ▼                                                             ▼
[En attente RH] ──────────────────────────► [En attente du DG]
                                                             │
                             ┌───────────────┴───────────────┐
                             ▼                               ▼
                        [Approuvé ✅]                 [Rejeté ❌]
```

### Qui fait quoi ?

| Étape | Responsable | Rôle requis | Action |
|---|---|---|---|
| **1.** Création de la demande | L'employé lui-même | `Employee` | Cliquer "Soumettre" |
| **2a.** (Si non-chef d'équipe) | Chef d'équipe / N+1 | `Supérieur Immédiat` | "Approuver" ou "Rejeter" |
| **2b.** (Si Chef d'équipe) | RH directement | `Responsable RH` | Passe directement à l'étape RH |
| **3.** Validation RH | Gestionnaire RH | `Responsable RH` | "Approuver" ou "Rejeter" |
| **4.** Approbation finale | Directeur | `Directeur Général` | "Approuver" ou "Rejeter" |

---

## 3. Flux Stagiaires — « Flux Autorisation de Sortie Stagiaires »

### Diagramme du flux

```
Stagiaire soumet
      │
      ▼
[Brouillon]
      │
      ▼
[En attente du Supérieur Immédiat]
      │
      ├──────────────────────────┐
      ▼                          ▼
[En attente du Responsable   [Rejeté ❌]
     des Stagiaires]
      │
      ├──────────────────────────┐
      ▼                          ▼
[En attente du DG]          [Rejeté ❌]
      │
      ├──────────────────────────┐
      ▼                          ▼
[Approuvé ✅]               [Rejeté ❌]
```

### Qui fait quoi ?

| Étape | Responsable | Rôle requis | Action |
|---|---|---|---|
| **1.** Création de la demande | Le stagiaire | `Employee` (+ `Stagiaire`) | Cliquer "Soumettre" |
| **2.** Approbation N+1 | Tuteur direct / Chef d'équipe | `Supérieur Immédiat` | "Approuver" ou "Rejeter" |
| **3.** Validation responsable | Responsable des stagiaires | `Responsable des Stagiaires` | "Approuver" ou "Rejeter" |
| **4.** Approbation finale | Directeur | `Directeur Général` | "Approuver" ou "Rejeter" |

---

## 4. Configuration Pas-à-Pas dans ERPNext

### Étape 1 : Créer les utilisateurs

Pour chaque personne dans l'entreprise :

1. Aller dans **Settings → Users → New User**
2. Renseigner `Email`, `Prénom`, `Nom`
3. **Important** : cocher `Enabled`
4. Dans l'onglet **Roles**, ajouter les rôles selon le tableau ci-dessous

### Étape 2 : Assigner les rôles par profil

| Profil | Rôles à assigner |
|---|---|
| **Employé standard** | `Employee`, `Employee Self Service` |
| **Chef d'équipe** | `Employee`, `Employee Self Service`, `Supérieur Immédiat` |
| **Stagiaire** | `Employee`, `Employee Self Service`, `Stagiaire` |
| **Responsable des Stagiaires** | `Employee`, `Employee Self Service`, `Responsable des Stagiaires` |
| **Gestionnaire RH** | `Employee`, `HR User`, `HR Manager`, `Responsable RH` |
| **Directeur Général** | `Employee`, `HR Manager`, `Directeur Général`, `System Manager` |
| **Administrateur Système** | `System Manager`, `Administrator` |

### Étape 3 : Lier l'utilisateur à son fiche Employé

1. Ouvrir la fiche **Employee** de la personne
2. Dans le champ **User ID**, sélectionner l'utilisateur ERPNext créé
3. Sauvegarder

> [!IMPORTANT]
> **Sans ce lien, le workflow ne fonctionnera pas.** ERPNext identifie l'employé via son `User ID`. Si ce champ est vide, la personne ne pourra pas soumettre de demande de congé.

### Étape 4 : Vérifier le champ `leave_approver` sur la fiche Employé

Sur la fiche **Employee**, onglet **Leave Details** :
- **Leave Approver** : mettre l'email du chef direct (Supérieur Immédiat)

Cela permet à ERPNext d'identifier automatiquement qui doit approuver en premier.

---

## 5. Cas Particulier : Condition « Chef d'équipe »

Le flux Employés contient cette logique automatique :

```python
# Transition 1 : Si PAS chef d'équipe → passe par Supérieur Immédiat
condition: frappe.db.get_value('Employee', doc.employee, 'designation') != "Chef d'équipe"

# Transition 2 : Si Chef d'équipe → va directement à RH
condition: frappe.db.get_value('Employee', doc.employee, 'designation') == "Chef d'équipe"
```

**Ce que cela implique :**
- La `designation` (désignation) sur la fiche Employé **doit être exactement** `Chef d'équipe` (avec l'apostrophe typographique, respecter la casse).
- Tout autre intitulé de poste passera par l'étape Supérieur Immédiat normalement.

---

## 6. Droits d'Accès (`DocType Permissions`)

Pour que chaque rôle puisse voir et éditer les demandes de congé à son étape, vérifier dans **Setup → DocType → Leave Application → Permissions** :

| Rôle | Lire | Écrire | Soumettre | Annuler |
|---|---|---|---|---|
| `Employee` | ✅ | ✅ | ✅ | ✅ (ses propres) |
| `Supérieur Immédiat` | ✅ | ✅ | ❌ | ❌ |
| `Responsable RH` | ✅ | ✅ | ✅ | ✅ |
| `Responsable des Stagiaires` | ✅ | ✅ | ❌ | ❌ |
| `Directeur Général` | ✅ | ✅ | ✅ | ✅ |
| `HR Manager` | ✅ | ✅ | ✅ | ✅ |

> [!TIP]
> Dans ERPNext, le workflow **surpasse** les permissions standard. Seul le rôle désigné à l'étape courante verra le bouton d'action (Approuver/Rejeter). Vérifier quand même les permissions de lecture pour éviter les pages blanches.

---

## 7. Checklist de Vérification Finale

Avant de tester le flux de bout en bout, vérifier :

- [ ] Chaque utilisateur est **activé** dans Settings → Users
- [ ] Chaque utilisateur a au moins le rôle `Employee`
- [ ] Chaque fiche **Employee** a un **User ID** renseigné
- [ ] La **designation** des Chefs d'équipe est exactement `Chef d'équipe`
- [ ] Le champ **Leave Approver** est renseigné sur chaque fiche Employee
- [ ] Le workflow **Flux Congés et Sortie Employés** a `is_active = 1`
- [ ] Le workflow **Flux Autorisation de Sortie Stagiaires** a `is_active = 1` (si utilisé en parallèle)
- [ ] Les rôles `Supérieur Immédiat`, `Responsable RH`, `Directeur Général`, `Responsable des Stagiaires` ont **`desk_access = 1`** dans leurs définitions de rôle

> [!WARNING]
> **Problème courant** : Dans votre `role.json` actuel, les rôles `Directeur Général`, `Responsable RH`, `Supérieur Immédiat`, `Responsable des Stagiaires`, et `Stagiaire` ont `desk_access: 0`. Cela signifie que ces utilisateurs n'auront pas accès au bureau ERPNext pour voir les demandes. **Il faut passer `desk_access` à `1`** pour tous les rôles qui doivent approuver.

---

## 8. Correction Nécessaire — `desk_access` des Rôles Workflow

Les rôles suivants dans `role.json` doivent avoir `desk_access: 1` :

| Rôle | Valeur actuelle | Valeur correcte |
|---|---|---|
| `Directeur Général` | `0` | **`1`** |
| `Responsable RH` | `0` | **`1`** |
| `Supérieur Immédiat` | `0` | **`1`** |
| `Responsable des Stagiaires` | `0` | **`1`** |
| `Stagiaire` | `0` | `0` ✅ (accès limité souhaitable) |
| `Maître de Stage` | `0` | `0` ✅ (role informatif) |

Pour corriger, soit via l'interface (**Setup → Role → modifier chaque rôle**), soit directement dans `role.json` avant de faire `bench migrate`.
