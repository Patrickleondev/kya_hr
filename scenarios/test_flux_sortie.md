# Scénario de Test : Permission de Sortie (Employé)

Ce document décrit les étapes pour tester le flux de permission de sortie standard pour un **Employé permanent**, incluant la vérification physique par la Guérite.

## 🏁 Pré-requis

- Un utilisateur avec le rôle **Employee** (Employé).
- Un utilisateur le rôle **Chef Service** (Supérieur hiérarchique).
- Un utilisateur le rôle **HR User** ou **HR Manager** (Validation RH).
- Un utilisateur avec le rôle **Guérite** (Agent de sécurité à l'entrée/sortie).

## 🚀 Étapes du Scénario

### Étape 1 : Demande de Permission (Employé)

1. **Accès** : Se connecter en tant qu'**Employé**.
2. **Navigation** : Ouvrir le Workspace **Leaves** (Congés & permissions).
    - *Note* : Ce workspace est exclusif aux employés réguliers (les stagiaires n'y ont pas accès).
3. **Création** : Cliquer sur **Permission de Sortie**.
4. **Saisie** :
    - Motif : `Urgence familiale`.
    - Date et Heure de sortie : `XXhXX`.
    - Statut attendu : Sauvegarder (Passe en `Brouillon`).
5. **Soumission** : Cliquer sur **Soumettre**.
    - L'état passe à `En attente du Supérieur Immédiat` (ou Chef Service).
    - 📧 *Vérification Mail* : Le Chef Service reçoit un mail de notification KYA.

### Étape 2 : Cycle d'Approbation (Chef & RH)

1. **Validation Niveau 1 (Chef Service)** :
    - Se connecter avec un compte ayant le rôle `Chef Service`.
    - Ouvrir le document via la ToDo list ou le lien du mail.
    - Cliquer sur **Approuver**. (L'état passe à `En attente de la RH`).
    - 📧 *Vérification Mail* : La RH reçoit le mail de notification KYA.
2. **Validation Niveau 2 (Ressources Humaines)** :
    - Se connecter avec un compte ayant le rôle `HR Manager` ou `HR User`.
    - Vérifier les compteurs d'absence de l'employé.
    - Cliquer sur **Approuver**.
    - L'état final passe à `Approuvé`.
    - 🖨️ *Action Automatique* : Le **Ticket de Sortie (PDF)** est généré et disponible.

### Étape 3 : Vérification Physique (Guérite)

1. **Présentation** : L'employé se présente à la sortie physique avec son Ticket de Sortie (imprimé ou sur smartphone).
2. **Contrôle (Rôle Guérite)** :
    - Se connecter (sur tablette/PC) avec le rôle **Guérite**.
    - La Guérite n'a accès qu'à une vue restreinte pour lire les Tickets générés / Permissions approuvées.
    - La Guérite vérifie que le Ticket (nom de l'employé, date, heure) correspond bien à une permission au statut **Approuvé**.
    - Une fois le contrôle passé, l'employé est autorisé à franchir le portail.
