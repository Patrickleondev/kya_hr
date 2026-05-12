# Rôles, flux et notifications — KYA HR

Référence opérationnelle pour la RH : à qui attribuer quel rôle, qui voit quoi sur le bureau Frappe, qui valide à chaque étape, qui reçoit les emails. À tenir à jour à chaque évolution d'un workflow ou d'un rôle.

## 1. Inventaire des rôles

### 1.1 Rôles métier KYA

| Rôle | Pour qui | Portée |
|---|---|---|
| `Directeur Général` | DG | Validation finale tout flux, accès complet, audit |
| `DGA` | DGA | Co-signature DG sur certains flux, accès complet |
| `Responsable Comptable` | Resp. Comptabilité (ex-DAAF / ex-DFC) | Validation finance, audit, accès Compta + Achats |
| `Auditeur Interne` | Audit | Vérification croisée sur Achats, Stock, Compta |
| `Responsable RH` | Chef RH | Validation RH, accès complet RH |
| `HR Manager` / `HR User` | Équipe RH | Gestion fiches employés, congés, contrats |
| `Responsable des Stagiaires` | Coordinateur stagiaires | Validation Stage (permissions, bilans, contrats) |
| `Maître de Stage` | Encadrant de stage | Validation Stagiaire (permissions, bilans) |
| `Chef Service` | Chef de département/service | Validation hiérarchique 1er niveau |
| `Chef Equipe` | Chef d'une équipe opérationnelle | Voit uniquement son équipe (cf. §3) |
| `Supérieur Immédiat` | N+1 direct sur certains flux RH | Validation amont congés/permissions |
| `Responsable Achats` | Resp. Achats | Validation Demande Achat / Bon Commande |
| `Responsable Stock` / `Chargé des Stocks` | Magasin | Réception, sortie matériel, inventaires |
| `Fleet Manager` / `Responsable Logistique` / `Driver` | Logistique | Flotte véhicules, missions terrain |
| `KYA Destinataire Notif` | Comptes "mailbox" sans accès UI | Reçoit notifications, n'ouvre pas Frappe |
| `KYA Survey Admin` | Admin enquêtes/évaluations | Module kya_services |
| `Stagiaire` | Stagiaire actif | Vue limitée à sa propre fiche Employee |
| `Employee` | Tout employé actif | Rôle par défaut Frappe HRMS |

### 1.2 Rôles techniques Frappe / ERPNext

| Rôle | Sert à | À donner à |
|---|---|---|
| `System Manager` | Admin technique | 1-2 personnes IT/DSI uniquement |
| `Accounts Manager` / `Accounts User` | Module Accounting ERPNext | Resp. Comptable + Comptables |
| `Purchase Manager` / `Purchase User` | Module Purchase ERPNext | Resp. Achats + acheteurs |
| `Stock Manager` / `Stock User` | Module Stock ERPNext | Chargé des Stocks + magasiniers |

> **Règle** : ne jamais ajouter `System Manager` à un utilisateur métier. Pour donner les pleins droits sur un module, utiliser le rôle métier (`Responsable Comptable`, `HR Manager`…) — ils sont configurés pour avoir tous les droits dont ils ont besoin.

## 2. Visibilité des icônes de bureau par rôle

Configuré dans `kya_hr/desktop_icons.py` → `RESTRICTED_LAYOUT_ROLES`.

| Espace de bureau | Visible pour |
|---|---|
| Direction Générale | DG, DGA, System Manager |
| Espace RH | HR Manager/User, Responsable RH, DG, System Manager |
| Espace Achats | Purchase Mgr/User, Resp. Achats, Resp. Comptable, DG, DGA, Auditeur, System Manager |
| Espace Stock | Stock Mgr/User, Chargé des Stocks, Resp. Comptable, Auditeur, DG, DGA, System Manager |
| Espace Comptabilité | Accounts Mgr/User, Resp. Comptable, Auditeur, DG, DGA, System Manager |
| Logistique | Fleet Mgr, Resp. Logistique, Driver, Resp. Comptable, DG, DGA, System Manager |
| Inventaire & Sorties Matériel | Stock Mgr/User, Chargé des Stocks, Resp. Achats, Auditeur, Resp. Comptable, DG, DGA, System Manager |
| Espace Employés | Tous les rôles qui doivent voir une fiche autre que la leur (RH, Chef Service, supérieurs, Stock, Achats, Audit…) |
| Espace Stagiaires | Maître de Stage, Resp. Stagiaires, RH, DG, System Manager |
| KYA Services | KYA Survey Admin, System Manager |

> Pour qu'un utilisateur Compta voie *uniquement* Espace Comptabilité + ses modules Accounting natifs, lui donner `Accounts User` + `Responsable Comptable` et **rien d'autre**. Il ne doit pas avoir `HR User`, `Stock User`, etc.

## 3. Scope « équipe » pour Chef d'Équipe

Filtres SQL définis dans `kya_hr/permissions.py`, wirés via `permission_query_conditions` :

- **Equipe KYA** — un Chef d'Équipe ne voit que les équipes où il est `chef_equipe`, ou dont il est membre via `Employee.custom_kya_equipe`.
- **Tache Equipe** — un Chef d'Équipe voit uniquement les tâches dont `tache.equipe.chef_equipe = lui`. Un employé sans rôle de chef voit uniquement les tâches où il est dans `tache.attributions[].employe`, ou celles de sa propre équipe.
- Les rôles transverses (HR/DG/Resp. Comptable/Auditeur/System Manager…) gardent une vue globale.

## 4. Flux et signataires

Légende : **(S)** soumet, **(V)** valide, **(N)** notifié.

### 4.1 Permission de Sortie — Employé
1. Employé **(S)** soumet
2. `Chef Service` **(V)** approuve / refuse
3. `Responsable RH` **(V)** enregistre
4. `DGA` ou `Directeur Général` **(V)** vise (selon délégation)
- **(N)** : demandeur à chaque transition + RH globale en copie

### 4.2 Permission de Sortie — Stagiaire
1. Stagiaire **(S)** soumet
2. `Maître de Stage` **(V)**
3. `Responsable des Stagiaires` **(V)**
4. `Directeur Général` **(V)** (en cas d'urgence/longue durée)
- **(N)** : demandeur + RH

### 4.3 Planning de Congé annuel
1. Employé **(S)** dépose son planning depuis `/mon-espace` → `/planning-conge`
2. `Chef Service` **(V)** valide le calendrier équipe
3. `Responsable RH` **(V)** enregistre + ajuste les soldes
4. `Directeur Général` **(V)** approuve définitivement
5. Auto : `kya_hr.leave_bridge.create_leave_from_planning` crée les `Leave Application` HRMS approuvées → décompte solde
- **(N)** : demandeur + RH à chaque étape

### 4.4 Demande d'Achat
1. Demandeur **(S)**
2. `Chef Service` **(V)** (palier 1+)
3. `Auditeur Interne` **(V)** (palier 2+)
4. `Responsable Comptable` (ex-DAAF) **(V)** (palier 3+)
5. `Directeur Général` **(V)** (palier 4, > 15 M XOF)

Palier auto-calculé sur `montant_total` (cf. `auto_calc_logic.compute_demande_achat`). Si `urgence = Urgent`, validation accélérée DG même sur petit montant.

### 4.5 Bon de Commande
1. `Responsable Achats` **(S)** (depuis une Demande d'Achat approuvée)
2. `Responsable Comptable` **(V)**
3. `Directeur Général` **(V)**

### 4.6 PV de Sortie / Entrée Matériel
- Sortie : Demandeur **(S)** → `Chef Service` **(V)** → `Auditeur` **(V)** → `Direction` **(V)** → `Chargé des Stocks` **(V)** (remise effective)
- Entrée : `Livreur/Demandeur` **(S)** → `Chargé des Stocks` **(V)** → `Auditeur` **(V)**

### 4.7 Bilan de Fin de Stage
1. Stagiaire **(S)**
2. `Maître de Stage` **(V)** + note finale
3. `Responsable RH` **(V)** archive

### 4.8 État Récap Chèques (Comptabilité)
1. `Responsable Comptable` ou Comptable **(S)** (rôle `Accounts User`)
2. `Directeur Général` **(V)** vise
3. `DGA` **(N)** en copie
- Workflow affiché : `Rédacteur (Comptable / DFC) → DG → DGA`

### 4.9 Brouillard de Caisse
1. Caissier **(S)** journée
2. Comptable **(V)** rapproche
3. `Responsable Comptable` **(V)**
- Cron vendredi 17h : envoi récap hebdo DG + DGA (`brouillard_caisse.send_weekly_dg_summary`)

### 4.10 Tâche Équipe
1. `Chef Equipe` **(S)** crée la tâche + attributions
2. Membre attributaire **(N)** par email + visible dans `/mon-espace`
3. Membre met à jour `taux_effectif` → statut auto recalculé (`auto_calc_logic.compute_tache_equipe`)
4. `Chef Equipe` **(V)** clôture

## 5. Notifications

Centralisées dans :
- `kya_hr/email_notifications.py` (`send_submission_recap`, `send_workflow_update`)
- `kya_hr/fixtures/notification.json` (templates par DocType)
- `kya_hr/fixtures/email_template.json` (corps emails)

### 5.1 Règles d'or
- Toute soumission → email récap au demandeur (confirmation).
- Toute transition workflow → email au demandeur + aux validateurs de l'étape suivante.
- Email RH globale (`KYA Dashboard Settings.rh_email`) en copie pour tous les flux RH.
- DG / DGA : en copie uniquement pour les paliers qui les concernent (pas tout en CC).
- Comptes `KYA Destinataire Notif` : reçoivent les emails mais ne se connectent pas — pratique pour les "groupes" (info@, rh@…).

### 5.2 Incohérences classiques à éviter
- **Mauvais rôle sur Workflow Transition** → l'utilisateur ne voit pas le bouton d'action. Vérifier `Workflow > Transitions > Allowed` après chaque migration.
- **Notif envoyée 2× au DG** → vérifier qu'on ne l'a pas mis en `for_role` ET dans `recipients.email`. Garder un seul vecteur.
- **Stagiaire dans rôle Employee + Stagiaire** → l'employee_query_condition donne accès limité, mais des notifs Employee peuvent fuir. À chaque création de stagiaire, retirer le rôle `Employee` si le stagiaire n'est pas un employé.
- **Resp. Comptable sans `Accounts User`** → il valide la Demande Achat mais ne peut pas ouvrir le module Accounting. Toujours combiner les deux.

## 6. Matrice rôles standards à attribuer

À cocher sur la fiche User avant tout le reste :

| Profil | Rôles à activer | Rôles à retirer (souvent par erreur) |
|---|---|---|
| Comptable | `Accounts User` + `Employee` | `HR User`, `Stock User`, `Purchase User` |
| Responsable Comptable | `Accounts Manager` + `Responsable Comptable` + `Employee` + `Auditeur Interne` | `System Manager` |
| Caissier | `Accounts User` + `Employee` | autres modules |
| Chef de Service | `Chef Service` + `Employee` | `HR Manager` (sauf si vraiment RH) |
| Chef d'Équipe (opérationnel) | `Chef Equipe` + `Employee` | autres modules métiers |
| Responsable Achats | `Purchase Manager` + `Responsable Achats` + `Employee` + `Auditeur Interne` (si audit interne croisé) | `Accounts User` |
| Responsable Stock | `Stock Manager` + `Responsable Stock` + `Employee` | `HR User` |
| Magasinier | `Stock User` + `Chargé des Stocks` + `Employee` | |
| Stagiaire | `Stagiaire` + `Employee` (Employee à retirer si stage non-rémunéré) | tout le reste |
| Responsable RH | `HR Manager` + `Responsable RH` + `Employee` | |
| Maître de Stage | `Maître de Stage` + son rôle métier + `Employee` | |
| DG | `Directeur Général` + `Employee` | `System Manager` (sauf si IT) |
| DGA | `DGA` + `Employee` | |
| Admin IT/DSI | `System Manager` | rien d'autre (pour préserver la séparation des préoccupations) |

## 7. Procédure rapide pour onboarder un nouvel utilisateur

1. Créer l'**Employee** (matricule auto-incrémenté, champ `sexe`, `gender`, dates).
2. Créer le **User** lié (link `user_id` sur la fiche Employee).
3. Sur le User, attribuer **uniquement** les rôles de §6 selon le profil.
4. Si Chef d'Équipe : créer l'**Equipe KYA** correspondante, le mettre comme `chef_equipe`, ajouter les membres via `Employee.custom_kya_equipe`.
5. Vérifier dans `/mon-espace` que :
   - Les espaces visibles correspondent au §2.
   - Les formulaires listés correspondent au profil (Employee voit Demande Achat / Permission Sortie / Planning Congé ; Stagiaire voit Permission Stagiaire / Bilan / Demande Congé Stagiaire).
6. Lancer un test de bout en bout sur un flux représentatif avant d'ouvrir l'accès.

## 8. Maintenance des rôles

- À chaque ajout d'un nouveau rôle métier : l'ajouter dans `GLOBAL_ROLES` (`kya_hr/permissions.py`) **uniquement** s'il doit voir tout le périmètre. Sinon, l'ajouter dans la liste blanche du flux concerné.
- Lors d'un renommage de rôle, lancer `kya_hr.maintenance.role_merge.run` (script de migration des `Has Role` + `DocPerm` + `Workflow Transition` + `Notification Recipient`).
- Après toute modification, lancer `bench --site <site> migrate` puis vider le cache (`bench clear-cache`) — sinon les nouveaux filtres de permission ne s'appliquent pas.
