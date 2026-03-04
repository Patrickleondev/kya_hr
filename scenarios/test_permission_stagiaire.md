# Scénario de Test : Permission Stagiaire & PWA

Ce document décrit les étapes pour tester le flux de permission spécifique aux stagiaires.

## 🏁 Pré-requis

- Un utilisateur avec le rôle **Stagiaire**.
- Un utilisateur avec le rôle **RH** (Tuteur par défaut pour le test).

## 🚀 Étapes du Scénario

1. **Accès Stagiaire (Interface PWA)** :
    - Connectez-vous en tant que **Stagiaire**.
    - Accédez au Workspace **KYA Stagiaires**.
    - *Vérification* : Les menus de paie/salaire ne sont pas visibles. Le dashboard affiche les graphiques stagiaires.

2. **Demande de Permission** :
    - Cliquez sur le raccourci **Autorisation de Sortie** ou **Permission de Sortie**.
    - Remplissez le motif, la date et l'heure de sortie.
    - Cliquez sur **Enregistrer** (Brouillon) puis **Soumettre**.
    - *Vérification* : Le document est `En attente du Supérieur Immédiat`.
    - *Email* : Le Chef Service reçoit une notification avec le branding KYA (Signature DG).

3. **Validation 3 Niveaux (Chef -> Responsable -> DG)** :
    - **Niveau 1** : Le Chef Service approuve via le lien mail. L'état passe à `En attente du Responsable des Stagiaires`.
    - **Niveau 2** : Le Responsable des Stagiaires (rôle dédié) approuve. L'état passe à `En attente du DG`.
    - **Niveau 3** : Le DG (Directeur Général) approuve. L'état passe à `Approuvé`.
    - *Vérification* : Le ticket de sortie PDF est généré et prêt pour la guérite.

4. **Validation RH (Accès Manuel)** :
    - Connectez-vous en tant que **RH**.
    - Accédez au module **KYA Stagiaires**.
    - Ouvrez la liste des **Permissions de Sortie**.
    - *Note* : La RH peut entrer ou modifier manuellement une permission pour un stagiaire.
    - Approuvez la demande.

5. **Visualisation Graphique & Bilan** :
    - Retournez sur le Workspace **KYA Stagiaires**.
    - *Vérification* : Le "Bilan Permissions Stagiaires" (Graphique) et les compteurs sont mis à jour en temps réel.
