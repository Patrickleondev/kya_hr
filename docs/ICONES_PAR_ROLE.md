# 🗂️ Icônes (espaces) visibles par profil — KYA-Energy Group

_Généré automatiquement depuis les rôles réels des workspaces (instance 8092) le 2026-06-17._

## Comment lire ce document

- Chaque **icône** du bureau = un **espace de travail** (workspace).
- Un espace n'est visible que par les **rôles** listés ci-dessous (plus *System Manager*/*Administrator*, toujours).
- ⚠️ Si un compte **voit une icône grisée qui « plante » au clic**, c'est qu'il a l'icône mais **pas le rôle** requis par l'espace. La solution = lui attribuer le bon rôle (ou retirer l'icône). C'était le cas de **Gestion Équipe** (corrigé : élargi à toutes les variantes de chef).

## 1) Par espace → qui le voit

| Icône | Espace | Rôles qui le voient |
|---|---|---|
| 🏛️ | **Direction Générale** | DAAF, DG, DGA, Directeur Général |
| 👥 | **Espace RH** | DAAF, DGA, Directeur Général, HR Manager, HR User, Maître de Stage, Responsable RH, Responsable des Stagiaires |
| 🛒 | **Espace Achats** | Auditeur Interne, Chef Service, DAAF, DGA, Directeur Général, Purchase Manager, Purchase User, Responsable Achats |
| 📦 | **Espace Stock** | Auditeur Interne, Chargé des Stocks, Chef Service, DAAF, DGA, Directeur Général, Responsable Stock, Stock Manager, Stock User |
| 💰 | **Espace Comptabilité** | Accounts Manager, Accounts User, Auditeur Interne, Caissier, Comptable, DAAF, DFC, DGA, Directeur Général |
| 🚚 | **Logistique** | Chef Service, DG, DGA, DST - Responsable Logistique, Directeur Général, Fleet Manager, Gestionnaire de Flotte, HR Manager, Responsable RH |
| 👤 | **Espace Employés** | Auditeur Interne, Chargé des Stocks, Chef Equipe, Chef Service, DAAF, DGA, Directeur Général, Employee, HR Manager, HR User, KYA Destinataire Notif, Purchase User, Responsable Achats, Responsable RH, Stagiaire, Stock User, Supérieur Immédiat |
| education | **Espace Stagiaires** | Directeur Général, HR Manager, HR User, Maître de Stage, Responsable RH, Responsable des Stagiaires, Stagiaire |
| 🧾 | **Inventaire Sorties Materiel** | Auditeur, DG, DGA, Magasinier, Stock Manager |
| 📋 | **KYA Services** | KYA Survey Admin |
| 🤝 | **Gestion Equipe** | Chef Equipe, Chef Service, Chef d'Équipe, DGA, DST - Chef Equipe Audit Interne, DST - Chef Equipe Installation, DST - Chef Equipe Offres et Formations, Directeur Général, Responsable RH |

## 2) Par profil → quelles icônes il voit (du bas vers le DG)

### Employé
- 👤 Espace Employés

### Stagiaire
- education Espace Stagiaires
- 👤 Espace Employés

### Chef d'équipe
- 👤 Espace Employés
- 🤝 Gestion Equipe

### Chef de service
- 👤 Espace Employés
- 📦 Espace Stock
- 🚚 Logistique
- 🛒 Espace Achats
- 🤝 Gestion Equipe

### Caissier
- 💰 Espace Comptabilité

### Comptable
- 💰 Espace Comptabilité

### DFC
- 💰 Espace Comptabilité

### Responsable Achats
- 👤 Espace Employés
- 🛒 Espace Achats

### Chargé des stocks / Magasinier
- 👤 Espace Employés
- 📦 Espace Stock
- 🧾 Inventaire Sorties Materiel

### Gestionnaire de flotte / Logistique
- 🚚 Logistique

### Maître de stage / Resp. stagiaires
- education Espace Stagiaires
- 👥 Espace RH

### Auditeur interne
- 👤 Espace Employés
- 💰 Espace Comptabilité
- 📦 Espace Stock
- 🛒 Espace Achats
- 🧾 Inventaire Sorties Materiel

### Responsable RH / HR
- education Espace Stagiaires
- 👤 Espace Employés
- 👥 Espace RH
- 🚚 Logistique
- 🤝 Gestion Equipe

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
- 🤝 Gestion Equipe
- 🧾 Inventaire Sorties Materiel

### DG / Directeur Général
- education Espace Stagiaires
- 🏛️ Direction Générale
- 👤 Espace Employés
- 👥 Espace RH
- 💰 Espace Comptabilité
- 📦 Espace Stock
- 🚚 Logistique
- 🛒 Espace Achats
- 🤝 Gestion Equipe
- 🧾 Inventaire Sorties Materiel

## 3) Note technique

- Visibilité gérée par `ensure_workspace_roles` ; icônes bureau par `desktop_icons` ; anomalies (parent NULL, accents, rôles doublons) par `fix_workspace_anomalies` — tous rejoués au `bench migrate`.
- Rôles **doublons** connus à rationaliser : `Chef Equipe` vs `Chef d'Équipe` vs `Chef Service` ; `DG` vs `Directeur Général` ; `DAAF`/`DFC`. Voir la refonte des rôles prévue.
