# 🗂️ Icônes (espaces) du bureau visibles par profil — KYA-Energy Group

_Généré depuis les rôles réels des workspaces (instance 8092) le 2026-06-18._

## Comment lire ce document

- Chaque **icône** du bureau `/desk` = un **espace de travail** (workspace).
- Un espace n'est visible que par les **rôles** listés ci-dessous (plus *System Manager* / *Administrator*, toujours).
- Les icônes KYA utilisent désormais de **vraies icônes vectorielles** (SVG livrés dans les apps `kya_hr` / `kya_services`, variantes claire et pleine), et non plus un emoji ou une simple lettre.

## ⚙️ Comment le clic d'une icône est résolu (et pourquoi ça plantait)

Le bureau résout une icône en deux temps :
1. **trouver l'espace** : clé = `Desktop Icon.label` en minuscules, qui doit égaler `Workspace Sidebar.name` en minuscules ;
2. **construire la route** : `/desk/<slug(nom du workspace)>`.

➡️ **Invariant appliqué** : `label == Workspace Sidebar.name == Workspace.name`, **en ASCII (sans accent)**.
Un accent dans le label imposait un accent dans le `name` du sidebar (étape 1) **et** dans la route (étape 2) → `/desk/gestion-équipe` alors que le workspace est `Gestion Equipe` → **404**. L'accent à l'**affichage** est rendu par la traduction `__(label)` (français en prod) et par le `title`/`label` accentué du workspace — l'identité technique reste ASCII.

Tout ceci est rejoué à chaque `bench migrate` par `fix_workspace_anomalies` (alignement + vérification automatique), `ensure_workspace_roles` (visibilité) et `desktop_icons` (icônes bureau).

## 1) Par espace → qui le voit

| Icône | Espace (affiché) | Identité technique | Rôles qui le voient |
|---|---|---|---|
| 🏛️ | **Direction Générale** | `Direction Generale` | DAAF, DG, DGA, Directeur Général |
| 👥 | **Espace RH** | `Espace RH` | DAAF, DGA, Directeur Général, HR Manager, HR User, Maître de Stage, Responsable RH, Responsable des Stagiaires |
| 🛒 | **Espace Achats** | `Espace Achats` | Auditeur Interne, Chef Service, DAAF, DGA, Directeur Général, Purchase Manager, Purchase User, Responsable Achats |
| 📦 | **Espace Stock** | `Espace Stock` | Auditeur Interne, Chargé des Stocks, Chef Service, DAAF, DGA, Directeur Général, Responsable Stock, Stock Manager, Stock User |
| 💰 | **Espace Comptabilité** | `Espace Comptabilite` | Accounts Manager, Accounts User, Auditeur Interne, Caissier, Comptable, DAAF, DFC, DGA, Directeur Général |
| 🚚 | **Logistique** | `Logistique` | Chef Service, DG, DGA, DST - Responsable Logistique, Directeur Général, Fleet Manager, Gestionnaire de Flotte, HR Manager, Responsable RH |
| 👤 | **Espace Employés** | `Espace Employes` | Auditeur Interne, Chargé des Stocks, Chef Equipe, Chef Service, DAAF, DGA, Directeur Général, Employee, HR Manager, HR User, KYA Destinataire Notif, Purchase User, Responsable Achats, Responsable RH, Stagiaire, Stock User, Supérieur Immédiat |
| 🎓 | **Espace Stagiaires** | `Espace Stagiaires` | Directeur Général, HR Manager, HR User, Maître de Stage, Responsable RH, Responsable des Stagiaires, Stagiaire |
| 📋 | **KYA Services** | `KYA Services` | KYA Survey Admin |
| 🤝 | **Gestion Équipe** | `Gestion Equipe` | Chef Equipe, Chef Service, Chef d'Équipe, DGA, DST - Chef Equipe Audit Interne, DST - Chef Equipe Installation, DST - Chef Equipe Offres et Formations, Directeur Général, Responsable RH |

> ℹ️ « Inventaire & Sorties Matériel » a été **retiré** (libellé avec `&` cassant la route + redondant avec **Espace Stock**, qui contient l'inventaire et les PV de sortie).

## 2) Par profil → quelles icônes il voit (du bas vers le DG)

### Employé
- 👤 Espace Employés

### Stagiaire
- 🎓 Espace Stagiaires
- 👤 Espace Employés

### Chef d'équipe
- 👤 Espace Employés
- 🤝 Gestion Équipe

### Chef de service
- 👤 Espace Employés
- 📦 Espace Stock
- 🚚 Logistique
- 🛒 Espace Achats
- 🤝 Gestion Équipe

### Caissier / Comptable / DFC
- 💰 Espace Comptabilité

### Responsable Achats
- 👤 Espace Employés
- 🛒 Espace Achats

### Chargé des stocks
- 👤 Espace Employés
- 📦 Espace Stock

### Gestionnaire de flotte / Logistique
- 🚚 Logistique

### Maître de stage / Resp. stagiaires
- 🎓 Espace Stagiaires
- 👥 Espace RH

### Auditeur interne
- 👤 Espace Employés
- 💰 Espace Comptabilité
- 📦 Espace Stock
- 🛒 Espace Achats

### Responsable RH / HR
- 🎓 Espace Stagiaires
- 👤 Espace Employés
- 👥 Espace RH
- 🚚 Logistique
- 🤝 Gestion Équipe

### DAAF
- 🏛️ Direction Générale
- 👤 Espace Employés
- 👥 Espace RH
- 💰 Espace Comptabilité
- 📦 Espace Stock
- 🛒 Espace Achats

### DGA
- 🏛️ Direction Générale
- 👤 Espace Employés
- 👥 Espace RH
- 💰 Espace Comptabilité
- 📦 Espace Stock
- 🚚 Logistique
- 🛒 Espace Achats
- 🤝 Gestion Équipe

### DG / Directeur Général
- 🎓 Espace Stagiaires
- 🏛️ Direction Générale
- 👤 Espace Employés
- 👥 Espace RH
- 💰 Espace Comptabilité
- 📦 Espace Stock
- 🚚 Logistique
- 🛒 Espace Achats
- 🤝 Gestion Équipe

## 3) Note technique

- Visibilité gérée par `ensure_workspace_roles` ; icônes bureau (et leurs SVG) par `desktop_icons` ; anomalies (parent NULL, alignement label/sidebar/route ASCII, dédoublonnage du nav, rôles doublons) par `fix_workspace_anomalies` — **tous rejoués au `bench migrate`**, donc appliqués automatiquement au prochain déploiement en prod.
- Rôles **doublons** connus à rationaliser : `Chef Equipe` vs `Chef d'Équipe` vs `Chef Service` ; `DG` vs `Directeur Général` ; `DAAF` / `DFC`. Voir la refonte des rôles prévue.
