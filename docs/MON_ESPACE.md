# Mon Espace — Portail Employé KYA

**Mon Espace** (`/mon-espace`) est le point d'entrée **unique et personnalisé** pour chaque collaborateur KYA Energy Group. Il s'adapte automatiquement au profil de la personne connectée : employé CDI/CDD, stagiaire, prestataire, chef de service, chef d'équipe, responsable RH, direction.

---

## Accès

| Profil | Comment accéder |
|---|---|
| Tous les employés (CDI/CDD) | Icône **Espace Employés** → "Mon Espace" sur le bureau Frappe |
| Stagiaires | Idem + icône **Espace Stagiaires** |
| Chefs de service / Equipe | Idem → section supplémentaire "Demandes en attente" |
| RH / Direction | Idem → section RH et tableaux de bord avancés |
| Lien direct | `https://<site>/mon-espace` (signet à partager avec les équipes) |

> **Tous les comptes liés à un Employee actif voient le bureau Frappe avec au moins l'icône Espace Employés.** Aucun utilisateur ne peut se retrouver sans accès à Mon Espace.

---

## Ce que chacun voit

### Sections universelles (tous les profils)

| Section | Contenu |
|---|---|
| **En-tête** | Photo de profil · Nom · Poste · Département · Matricule |
| **Statistiques** | Total demandes · En cours · Approuvées · Rejetées |
| **Mes demandes récentes** | Historique des 40 dernières fiches, avec statut coloré et lien direct vers la fiche web form |
| **Formulaires disponibles** | Raccourcis vers les formulaires autorisés selon le profil (voir tableau §Formulaires) |
| **Formulaires & enquêtes** | Enquêtes / évaluations assignées et en attente de réponse |

### Sections conditionnelles

| Section | Condition d'affichage |
|---|---|
| **📌 Mes tâches attribuées** | Employé assigné dans au moins une `Tache Equipe Attribution` |
| **⏳ Demandes en attente de validation** | Rôle `Chef Service`, `Supérieur Immédiat`, HR Manager/User |
| **👥 Gestion de mon Équipe** | Désigné comme `chef_equipe` d'au moins une `Equipe KYA` active |
| **📊 Formulaires enquêtes (KYA Services)** | Formulaires `KYA Form` assignés à l'employé avec `soumis_le` vide |

---

## Formulaires disponibles par profil

Le système détermine automatiquement les formulaires à afficher selon le **type d'emploi** (`employment_type`) :

### Employé CDI/CDD + Prestataire
- 🚪 Permission de Sortie
- 📦 PV Sortie Matériel
- 🛒 Demande d'Achat
- 🏖️ Planning de Congé
- ✈️ Demande de Congé

### Stagiaire (`employment_type = Stage`)
- 🎓 Permission de Sortie Stagiaire
- 📋 Bilan de Fin de Stage
- 🏖️ Demande de Congé Stagiaire
- 📦 PV Sortie Matériel
- 🛒 Demande d'Achat

### Tous les profils
- Les enquêtes et évaluations kya_services assignées

---

## Suivi des demandes

Chaque demande soumise via un formulaire web (Permission, Planning Congé, Demande Achat, etc.) est listée dans "Mes demandes récentes" avec :

- **Référence** (ex: `PSE-2026-00024`)
- **Type de demande** (label lisible)
- **Statut actuel** avec code couleur : 🔵 En cours · 🟢 Approuvé · 🔴 Rejeté · ⚫ Brouillon
- **Date de modification**
- **Lien direct** vers la fiche dans le web form (lecture ou édition selon l'état)

> Un clic sur n'importe quelle demande ouvre la **fiche web form** — jamais le formulaire Frappe Desk. Le rendu est celui du formulaire original, signé et mis en page.

---

## Notifications dans Mon Espace

### Qu'est-ce qui déclenche une notification ?
1. **Changement de statut d'une demande** → email + entrée dans "Mes demandes récentes"
2. **Nouvelle tâche attribuée** par un chef d'équipe → email + apparition dans "Mes tâches"
3. **Enquête/évaluation assignée** → bandeau "Formulaires & enquêtes" + email
4. **Rappel anniversaire / ancienneté** → email au responsable RH (pas à l'employé directement)

### Mise à jour des données
Mon Espace recharge les données à **chaque accès** (no_cache = 1). Pas de délai : les informations sont toujours en temps réel.

---

## Section "Gestion de mon Équipe" (Chef d'Équipe)

Pour un utilisateur désigné comme `chef_equipe` d'au moins une équipe active :

| Fonctionnalité | Détail |
|---|---|
| **Dashboard Équipe** | Taux d'avancement global, membres actifs |
| **Liste membres** | Voir les membres avec leur tâche principale + taux |
| **Importer Excel Évaluation** | Mise à jour en masse des taux d'avancement depuis un fichier (cf. `GUIDES_IMPORT.md §3`) |
| **Plans Trimestriels** | Accès à la liste des plans liés à ses équipes |

Un chef d'équipe gérant **plusieurs équipes** voit un sélecteur déroulant pour switcher entre ses équipes.

---

## Section "Demandes en attente" (Chef de Service)

Pour les rôles `Chef Service`, `Supérieur Immédiat`, `HR Manager/User` :

- Liste des demandes de workflow **en attente de leur validation** (filtrées sur `workflow_state` contenant "attente")
- Lien direct vers la fiche pour approuver ou rejeter
- Indique le type de demande, le demandeur, le statut actuel

---

## Règles de visibilité des données

| Ce que l'employé voit | Périmètre |
|---|---|
| Ses propres fiches Employee | Sa seule fiche (Employee scope limité si stagiaire) |
| Ses demandes récentes | Uniquement celles liées à son `employee_id` |
| Ses tâches attribuées | Uniquement les `Tache Equipe Attribution` à son nom |
| Les membres de son équipe | Uniquement si chef_equipe de l'équipe concernée |
| Les fiches Employee des autres | Limité selon `permission_query_conditions.employee_query` (Employee scope) |

---

## Configuration et maintenance (RH/IT)

### Rattacher un utilisateur à un employé
Fiche Employee → champ **Lien Utilisateur** (`user_id`). Sans ce lien, Mon Espace ne peut pas identifier l'employé connecté et affichera le bureau vide.

### Un employé ne voit pas son Espace Employés
1. Vérifier que son compte a le rôle `Employee` (Frappe HRMS → User → Roles).
2. Vérifier que sa fiche Employee a `status = Active`.
3. Vérifier le lien `user_id` sur la fiche Employee.
4. Lancer `bench --site <site> execute kya_hr.desktop_icons.execute` pour resynchroniser les icônes.

### Ajouter un nouveau formulaire dans Mon Espace
Modifier `kya_hr/mon_espace_sync.py` :
- `REQUEST_SPECS` : pour qu'il apparaisse dans "Mes demandes récentes" (historique)
- `FORM_SPECS` : pour qu'il apparaisse dans "Formulaires disponibles" (accès rapide)

---

## URL de référence

| Page | URL |
|---|---|
| Mon Espace employé | `/mon-espace` |
| Tableau de bord RH | `/kya-rh-dashboard` *(RH / Direction uniquement)* |
| Dashboard équipe | `/kya-dashboard-equipe` |
| Dashboard stagiaires | `/kya-dashboard-stagiaires` |
| Portail contrat (signature) | `/kya-contrat?name=XXX&token=YYY` |
