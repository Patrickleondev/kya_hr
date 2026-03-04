# Documentation des Flux KYA HR & Logistique (Version Enrichie)

Ce guide détaille les processus digitaux, les rôles et les scénarios d'utilisation pour garantir une gestion fluide au sein de KYA Energie.

## 👥 Rôles Fondamentaux

| Rôle | Intervention dans le Système | Exemple de Scénario |
| :--- | :--- | :--- |
| **Employé / Stagiaire** | Initiateur du flux (Matériel, Congé, Permission). | *Alice (Stagiaire) veut s'absenter 2h pour un rendez-vous.* |
| **Chef Service** | Premier validateur (Approuve la pertinence métier). | *M. Diallo valide que le départ d'Alice ne bloque pas le projet.* |
| **Responsable Stagiaires**| Validateur pédagogique (Suivi du parcours). | *Mme. Traore valide l'impact sur les thèmes d'apprentissage.* |
| **RH** | Validateur conformité (Vérifie le solde et les règles). | *La RH confirme qu'Alice a droit à cette sortie.* |
| **Auditeur** | Contrôle procédure (Vérifie le respect des règles internes). | *L'Auditeur vérifie la conformité du bon de commande.* |
| **DAAF** | Directeur Administratif & Financier (Contrôle budgétaire). | *Le DAAF valide la disponibilité des fonds avant paiement.* |
| **DGA / Direction** | Décisionnaire final (Impact budgétaire ou stratégique). | *Le DGA valide l'achat d'un nouveau laptop.* |
| **Guérite** | Contrôleur physique (Vérifie le Ticket de Sortie). | *L'agent à la guérite scanne le ticket d'Alice ou le PV avant la sortie.* |
| **Comptable** | Exécution paiement (Décaissement et archivage dossier). | *Le comptable classe les documents et effectue le virement.* |

---

## 📂 Détail des Flux & Scénarios

### 1. PV de Sortie de Matériel (Logistique)

**Objectif** : Formaliser la sortie d'équipements de l'entreprise.

* **Scénario Réel** : Un technicien a besoin d'un multimètre pour une intervention sur site.
* **Workflow** : `Brouillon (Technicien)` ➔ `Chef Service (Avis Technique)` ➔ `Auditeur / RH (Supervision Stock)` ➔ `DGA (Validation)` ➔ `Approuvé (Remise à la Guérite)`.
* **Impression** : Un PDF avec l'en-tête KYA et l'ID unique (ex: `PV-MAT-2026-001`) est généré. Les 4 signatures sont requises sur le document final. La **Guérite** vérifie le matériel à la sortie effective.

### 2. Gestion des Stagiaires (PWA & Dossier)

**Objectif** : Suivi complet du stagiaire sans accès aux données confidentielles.

* **Adaptation Stagiaire** : Interface simplifiée sur mobile (PWA) masquant les salaires.
* **Scénario Réel** : Le tuteur consulte le dashboard pour voir si le stagiaire a bien validé ses thèmes d'apprentissage.

### 3. Planning & Congés

**Objectif** : Synchroniser les présences et les repos.

* **Scénario Réel** : La RH saisit le planning annuel. Un employé demande 5 jours de congés via son portail.
* **Workflow** : `Demande (Employé)` ➔ `Chef Service` ➔ `RH` ➔ `Validé`.
* **Accès** : Accessible directement via le raccourci dans l'Espace **Congés**.

### 4. Demande de Permission & Sortie (Employé & Stagiaire)

**Objectif** : Autoriser une absence temporaire.

* **Flux Employé** : `Demande` ➔ `Chef Service` ➔ `RH`.
* **Flux Stagiaire (3 Niveaux)** : `Demande` ➔ `Chef Service` ➔ `Responsable des Stagiaires` ➔ `DG`.
* **Notifications** : Emails automatiques avec branding KYA (Signature DG) et lien direct vers le document.
* **Ticket de Sortie** : Impression d'un ticket compact pour la sécurité.

### 5. Flux de Sortie (Exit Procedure - Employé & Stagiaire)

**Objectif** : Gérer la fin de contrat et la restitution du matériel.

* **Scénario Réel** : Jean finit son stage. Il doit faire valider sa décharge par l'IT et la Logistique.
* **Workflow** : `Déclenchement (RH)` ➔ `Quitus IT` ➔ `Quitus Logistique` ➔ `Clôture RH`.
* **Imprimable** : Un certificat de travail ou une lettre de recommandation est généré avec les en-têtes officiels adaptés.

### 6. Procédure d'Achat & Dépense (KYA Purchase Request)

**Objectif** : Digitaliser les demandes d'achat avec validation hiérarchique et financière.

* **Scénario Réel** : Le bureau a besoin de nouvelles cartouches d'encre. Le demandeur initie la requête avec un devis.
* **Workflow** : `Demande` ➔ `Chef Service (Besoin opérationnel)` ➔ `Auditeur (Contrôle budget/devis)` ➔ `DG/DGA (Approbation financière)`.
* **Spécificité** : Signature digitale apposée directement sur le Web Form pour chaque rôle clé de la chaîne.

---

## 🖨️ Impressions & États Finaux

Tous les documents (PV, PR, Congés) sont adaptables en PDF :

* **En-têtes** : Logos KYA haute résolution et informations de l'entreprise.
* **Code ID** : Chaque document possède un ID unique (Naming Series) pour la traçabilité.
* **Structure Dédiée** : Mise en page optimisée pour l'impression A4 ou Ticket thermique.

---

## 📧 Notifications & Branding Mail

Chaque action de workflow déclenche un email structuré et professionnel :

* **Langue** : Français intégral (Terminologie KYA).
* **Branding** : Signature institutionnelle (Signature du DG, Logo 10 ans, Image promotionnelle KYA-SOP).
* **Navigation** : Bouton d'action direct avec lien dynamique vers la plateforme (instances 8084/8085).
* **Expéditeur** : `noreply@kya-energy.com` avec photo et adresse complète en footer.
