# Scénario de Test : Achat / Dépense (KYA Purchase Request)

Ce document décrit les étapes pour tester le flux de demande d'achat avec validation financière.

## 🏁 Pré-requis

- Un utilisateur avec le rôle **Employé** (Demandeur).
- Un utilisateur avec le rôle **Chef Service**.
- Un utilisateur avec le rôle **Auditeur** (Contrôle budget/devis).
- Un utilisateur avec le rôle **DG** ou **DGA** (Approbation finale).

## 🚀 Étapes du Scénario

### Étape 1 : Demande d'Achat (Employé)

1. **Accès** : Se connecter en tant qu'**Employé**.
2. **Navigation** : Ouvrir le module Achats (Purchase Request).
3. **Saisie** :
    - Compléter la description du besoin (ex: "Achat de licences logicielles").
    - Joindre un devis si applicable.
4. **Soumission** : Cliquer sur **Soumettre**.
    - L'état passe à `En attente du Supérieur`.
    - 📧 *Vérification Mail* : Le Chef Service reçoit une notification par email (avec branding KYA).

### Étape 2 : Validation au niveau Service (Chef Service)

1. **Validation** : Connecté en tant que **Chef Service**, ouvrir le document.
2. **Action** : Cliquer sur **Approuver** pour confirmer le besoin opérationnel.
    - L'état passe à `En attente de l'Auditeur`.
    - 📧 *Vérification Mail* : L'Auditeur est notifié.

### Étape 3 : Contrôle Financier (Auditeur)

1. **Validation Auditeur** : Connecté en tant qu'**Auditeur**.
2. **Action** :
    - L'auditeur vérifie la validité du devis et le cadre budgétaire.
    - En cas de conformité, cliquer sur **Approuver**.
    - L'état passe à `En attente du DG/DGA`.
    - 📧 *Vérification Mail* : La Direction Générale est notifiée.

### Étape 4 : Approbation Finale (Direction)

1. **Validation DGA/DG** : Connecté en tant que **DGA** ou **DG**.
2. **Action** : Cliquer sur **Approuver**.
    - L'état passe à `Terminé` ou `Approuvé`.
    - La procédure d'achat ou de décaissement peut alors se poursuivre auprès de la comptabilité via l'ERP.
