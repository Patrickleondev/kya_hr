# Scénario de Test : Permission de Sortie Stagiaire (PWA)

Ce document décrit les étapes pour tester le flux de permission de sortie des **Stagiaires**, accessible via l'interface **PWA KYA Stagiaires**, avec validation à 3 niveaux.

---

## 🏁 Rôles & Pré-requis

| Rôle | Description |
|------|-------------|
| **Stagiaire** | Demande la permission de sortie via la PWA. |
| **Chef Service** | Supérieur immédiat — 1er validateur. |
| **Responsable des Stagiaires** | Garant du parcours pédagogique — 2e validateur. |
| **Directeur Général (DG)** | Validateur final et stratégique. |
| **RH** | Peut créer ou corriger manuellement une permission. |
| **Guérite** | Contrôle physique du Ticket de Sortie (PDF). |

> ⚠️ **Différence avec les Employés** : Le flux de sortie des stagiaires nécessite **3 niveaux d'approbation** (Chef Service → Responsable Stagiaires → DG), contrairement aux employés permanents (Chef Service → RH uniquement). Le Workspace **KYA Stagiaires** n'est accessible qu'avec le rôle `Stagiaire`.

---

## 🚀 Étapes du Scénario

### Étape 1 : Connexion PWA & Vérification de l'Espace de Travail

1. **Accès** : Se connecter via l'URL de la PWA en tant que **Stagiaire**.
2. **Vérification de l'Isolation** :
    - ✅ Visible : Workspace **KYA Stagiaires** (graphiques stagiaires, permissions, planning stage).
    - ❌ Non visible : Workspace **Leaves** (Congés employés), Paie, Grille Salariale.
3. **Dashboard** : Vérifier la présence des graphiques : Statut, Présence Mensuelle, Fins de Contrat, Bilan Permissions.

### Étape 2 : Création d'une Demande de Permission de Sortie

1. **Navigation** : Cliquer sur **Permission de Sortie** dans le Workspace KYA Stagiaires.
2. **Saisie** :
    - Motif : `Consultation médicale`.
    - Date et heure de sortie prévue.
3. **Actions** :
    - Cliquer **Enregistrer** → État : `Brouillon`.
    - Cliquer **Soumettre** → État : `En attente du Supérieur Immédiat`.
    - 📧 *Email auto envoyé au Chef Service* avec footer KYA (logo + signature DG).

### Étape 3 : Validation à 3 Niveaux

1. **Niveau 1 — Chef Service** :
    - Ouve notification (mail ou To-Do) → Ouvre document via **lien direct**.
    - Cliquer **Approuver** → État : `En attente du Responsable des Stagiaires`.
    - 📧 *Email auto envoyé au Responsable des Stagiaires*.

2. **Niveau 2 — Responsable des Stagiaires** :
    - Accède à la liste "Permission de Sortie" depuis son Workspace.
    - Cliquer **Approuver** → État : `En attente du DG`.
    - 📧 *Email auto envoyé au DG* avec lien direct.

3. **Niveau 3 — Directeur Général** :
    - Ouvre le document via lien mail.
    - Cliquer **Approuver** → État : `Approuvé`.
    - 🖨️ *Le Ticket de Sortie PDF est généré automatiquement*.

### Étape 4 : Contrôle Physique (Guérite)

1. Le stagiaire se présente avec son **Ticket de Sortie** (imprimé ou sur écran).
2. L'agent **Guérite** se connecte sur sa vue dédiée et vérifie que le document est bien en état **Approuvé**.
3. Le stagiaire est autorisé à sortir des locaux.

### Étape 5 : Traçabilité & Bilan

1. **Navigation** : Retourner sur le Workspace **KYA Stagiaires**.
2. **Vérification Graphique** : Le compteur "Bilan Permissions Stagiaires" est mis à jour.
3. **RH (Accès Manuel)** : Si nécessaire, la RH peut ouvrir la liste de toutes les permissions et en créer ou corriger une manuellement pour un stagiaire.
