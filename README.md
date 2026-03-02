# KYA_HR

Application ERPNext personnalisée pour **KYA Energie**, centralisant la digitalisation des processus RH, logistiques et administratifs.

## Fonctionnalités Clés

### Gestion des Stagiaires (Module Dédié)

- **Recrutement & Dossiers** : DocType `Employee` étendu pour les stagiaires avec champs spécifiques (Maître de stage, Domaine).
- **Permissions & Pointage** : Système complet de demande de permissions et suivi de présence via PWA.
- **Tableaux de Bord** : Statistiques dynamiques sur le statut des dossiers et l'assiduité.

### Gestion des Congés & Planning

- **Workflow de Validation** : Flux multi-niveaux pour les demandes de congés avec notifications automatiques.
- **Grille Salariale** : Calcul automatique de la `Valeur Indicielle` sur les fiches employés selon la catégorie/classe.

### Procédure d'Achat (KYA Purchase Request)

- **Formulaire Web Premium** : Interface stylisée avec Logo KYA et signature numérique (Canvas).
- **Workflow Approvisionnement** : Suivi rigoureux des étapes d'approbation (Urgences, Départements).

### Logistique & Flotte

- **Missions & Carburant** : Suivi des ordres de mission et consommation de carburant.
- **Bons de Sortie** : Gestion digitalisée des sorties de matériel.

## Localisation & UI

- **Français Intégral** : Personnalisation poussée des traductions pour un usage professionnel sans termes corrompus.
- **Branding Corporate** : Intégration du logo et de la charte graphique KYA dans les formulaires web et les notifications.

## Structure de l'App

- `api.py` : Fonctions serveurs pour les calculs de salaire et utilitaires.
- `hooks.py` : Liaisons d'événements et intégration des scripts clients.
- `translations/` : Fichiers CSV pour la localisation française.
