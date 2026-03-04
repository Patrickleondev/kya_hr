# Scénario de Test : PV Sortie Matériel

Ce document décrit les étapes pour tester le flux de sortie de matériel sur les instances KYA.

## 🏁 Pré-requis

- Un utilisateur avec le rôle **Employé** (Demandeur).
- Un utilisateur avec le rôle **Chef Service**.
- Un utilisateur avec le rôle **Auditeur**.
- Un utilisateur le rôle **Guérite**.
- Un utilisateur avec le rôle **DGA**.

## 🚀 Étapes du Scénario

1. **Création de la Demande** :
    - Connectez-vous en tant qu'**Employé**.
    - Accédez au Workspace **Stock**.
    - Cliquez sur **Nouveau PV Sortie Materiel**.
    - Remplissez l'objet (ex: "Intervention Site A") et ajoutez des articles dans le tableau.
    - Cliquez sur **Enregistrer** puis sur **Envoyer pour Approbation**.
    - *Vérification* : Le document passe à l'état **En attente Chef Service**.

2. **Approbation Chef Service** :
    - Connectez-vous en tant que **Chef Service**.
    - Ouvrez le PV créé précédemment.
    - Cliquez sur **Approuver (Chef Service)**.
    - *Vérification* : Le document passe à l'état **En attente RH**. Un mail doit être envoyé à la RH.

3. **Contrôle Matériel & Audit (Auditeur)** :
    - Connectez-vous en tant qu'**Auditeur**.
    - Ouvrez le PV.
    - Vérifiez le motif de la sortie et les stocks associés.
    - Cliquez sur **Approuver**.
    - *Vérification* : Le document passe à l'état **En attente DGA**. Un mail avec header KYA doit être envoyé au DGA.

4. **Approbation Finale DGA** :
    - Connectez-vous en tant que **DGA**.
    - Ouvrez le PV.
    - Cliquez sur **Approuver (DGA)**.
    - *Vérification* : Le document passe à l'état **Approuvé**.

5. **Impression & Contrôle Guérite** :
    - Cliquez sur **Imprimer**.
    - Choisissez le format **Ticket de Sortie** pour l'employé ou **PV Officiel** pour l'archivage.
    - *Action* : Le collaborateur présente son fichier à la Guérite. L'utilisateur **Guérite** vérifie que le document est bien à l'état "Approuvé" dans le menu dédié.
    - *Vérification* : Le PDF généré contient le logo et les signatures finales de KYA.
