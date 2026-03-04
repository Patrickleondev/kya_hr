# Scénario de Test : Procédure d'Achat KYA (Réf. AEA-PRO-01-V01)

Ce document décrit les étapes unifiées pour tester la procédure d'achat numérisée sur la plateforme KYA, conformément à la procédure officielle **AEA-PRO-01-V01** (validée par le DG le 03/09/2023).

---

## 🏁 Rôles & Pré-requis

| Rôle | Correspondance Système (ERPNext) |
|------|----------------------------------|
| **Demandeur** | `Employee` / `Stagiaire` |
| **Chef de Département / Directeur d'Activité** | `Chef Service` |
| **Responsable Achats & Approvisionnement** | `Responsable Achats` |
| **Audit Interne** | `Auditeur` (contrôle procédure) |
| **DAAF** (Dir. Administratif & Financier) | `DAAF` (contrôle budgétaire/financier) |
| **Direction Générale** | `Directeur Général` |
| **Comptabilité** | `Comptable` (paiement final) |

> ⚠️ **DAAF ≠ Auditeur** : Le DAAF supervise le budget et les finances. L'Auditeur Interne vérifie le bon suivi de la procédure. Les deux interviennent lors de la validation du Bon de Commande.

---

## 🚀 PALIER 1 : Petit Achat (≤ 100 000 FCFA) — Délai : 72h

### Étapes

1. **Demande (Employé)** : Créer une `Purchase Request` avec une description précise du besoin, une estimation de coût et un pro-forma en pièce jointe.
2. **Validation Chef de Département** : Le Chef de Service valide la demande (24h max).
    - Met **Responsable Achats**, **Auditeur Interne** et **DAAF** en copie.
3. **Traitement Responsable Achats** :
    - Le demandeur remplit la **Fiche d'Engagement**, visée par le Directeur d'Activité.
    - Émission du **Bon de Commande** → visé par l'**Auditeur Interne** et la **DAAF** (contrôle budgétaire).
4. **Réception & Décharge** : Le demandeur vérifie la conformité et signe le **Bon de Livraison** (visé par l'Audit Interne + Responsable Achats).
5. **Paiement (Comptabilité)** : Dossier complet envoyé (BC, BL, facture, pro-forma). Décaissement sous 48h si trésorerie disponible.

*Vérification Système* : La `Purchase Request` passe par : `Brouillon → Validé Chef → Visé DAAF+Auditeur → Apprové DG → Terminé`.

---

## 🚀 PALIER 2 : Achat Modéré (100 000 — 2 000 000 FCFA) — Délai : 1 semaine

### Étapes Clés

1. **Demande formalisée** avec spécifications précises + 3 devis obligatoires en 3 jours max.
2. **Validation du Directeur d'Activité** (24h).
3. **Sélection fournisseur** par la Responsable Achats + le Demandeur (qualité technique + aspect financier).
4. **Validation du Bon de Commande** : visé par l'Auditeur Interne, puis approuvé par le DG.
    > 📧 *Email* : Notification auto au DG avec branding KYA et lien vers le document.
5. **Réception** : Conformité vérifiée par le Demandeur + Auditeur.
6. **Facturation & Paiement** : Réconciliation et archivage par la comptabilité.

---

## 🚀 PALIER 3 : Achat Important (2M — 15M FCFA) — Délai : 30 jours (Appel d'Offre National)

- Ouverture d'un appel d'offre national (2 semaines) via presse nationale.
- Commission d'Étude de Passation de Marché, présidée par la Responsable Achats.
- L'Auditeur vérifie le bon déroulement et fait son rapport au DG.
- Lettre d'attribution + Contrat rédigé par le cabinet juridique.

---

## ⚠️ Cas d'Urgence

- Un achat peut être effectué sans Bon de Commande uniquement sur **dérogation écrite du DG** (email validant la demande).
- Les procédures d'urgence ne sont décrétées que par la plus haute hiérarchie.

---

## 🖨️ Documents Imprimables

- **Bon de Commande KYA-ENERGY GROUP** (Format standard avec signatures)
- **Fiche d'Engagement** (Signée par le Directeur d'Activité)
- **Bon de Livraison** (Visé par l'Audit Interne et la Responsable Achats)
