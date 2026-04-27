# Plan de Test — Système Contrats KYA-Energy avec Token & Signature par Sections

**Version**: 2026-04-25  
**Branch**: `feat-notifs-refs`  
**Container**: `kya-8087-backend` / site `frontend` / port 8087

## Architecture de sécurité

- **Aucun compte Frappe n'est créé pour le stagiaire** — accès via lien magique signé `?name=...&token=...`
- Token stocké côté serveur sur le contrat (`access_token_signataire`, `access_token_dg`), comparaison `hmac.compare_digest`
- Vérification supplémentaire avant signature : **confirmation du téléphone** (anti-fuite si le lien est intercepté)
- Endpoints `allow_guest=True` mais protégés par token + (téléphone confirmé pour le stagiaire)
- Anti-bruteforce léger : `time.sleep(1.5)` sur tentative téléphone incorrect

## Workflow complet

| Étape | Acteur | Action | Email envoyé |
|-------|--------|--------|---------------|
| 1 | RH | Crée contrat, sélectionne template, vérifie le téléphone du stagiaire | — |
| 2 | RH | Clique "Envoyer au signataire" → API `send_to_signataire` génère token, stocke `rh_sender_email` | Stagiaire reçoit lien magique + indication des 4 derniers chiffres du téléphone |
| 3 | Stagiaire | Ouvre le lien → portail demande de confirmer son numéro de téléphone | — |
| 4 | Stagiaire | Saisit téléphone → `verify_phone` → `phone_confirmed=1` | — |
| 5 | Stagiaire | Complète Père/Mère/Domicile/Date naissance → `update_personal_info` | — |
| 6 | Stagiaire | Coche "Lu et approuvé" sur chaque section → `mark_section_signed` | — |
| 7 | Stagiaire | Coche case finale + dessine OU importe signature → `sign_contract(role=employe)` | DG reçoit notification |
| 8 | DG | Ouvre lien magique DG (token DG distinct) → coche sections → signe → `sign_contract(role=dg)` | — |
| 9 | Système | Trigger `on_update` → `_generate_and_attach_pdf` + `_send_final_emails` | Email final avec PDF à : stagiaire + RH expéditrice + RH globale + tous les DG |

## Prérequis test

1. Container backend up : `docker ps | grep kya-8087-backend`
2. Migration appliquée : nouveaux champs DocType visibles
3. Fichier print format à jour dans BDD
4. Au moins un contrat à l'état "Brouillon" avec `employee_email` et `telephone` renseignés

## Tests à effectuer

### TEST 1 — Token URL valide (signataire)

```bash
# Créer un contrat de test
docker exec kya-8087-backend bench --site frontend execute kya_hr.kya_hr.tests_contrats.create_test_contract
```

**Attendu** : retourne `{name, employee_email, telephone, token_signataire, url}`

Ouvrir l'URL dans navigateur incognito (sans login Frappe).
- ✓ La page s'affiche
- ✓ On voit l'écran "🔒 Vérification d'identité" demandant le téléphone
- ✓ Le contrat n'est PAS encore visible

### TEST 2 — Token invalide

URL : `/kya-contrat?name=KYA-CTR-XXX&token=INVALIDTOKEN`

**Attendu** : page d'erreur "Lien invalide ou expiré".

### TEST 3 — Téléphone incorrect

Saisir un mauvais numéro.
- ✓ Délai ~1.5s
- ✓ Message d'erreur "Numéro de téléphone incorrect"
- ✓ La page reste sur l'écran de vérification

### TEST 4 — Téléphone correct

Saisir le bon numéro.
- ✓ Page rechargée
- ✓ Affiche les sections du contrat + formulaire infos perso éditable
- ✓ `phone_confirmed=1` en BDD

```sql
SELECT phone_confirmed FROM `tabKYA Contrat` WHERE name = 'KYA-CTR-...'
-- 1
```

### TEST 5 — Sections : 1 section validée

Cocher "Lu et approuvé" sur la première section.
- ✓ Bordure de la section devient verte
- ✓ Paraphes (initiales) apparaissent
- ✓ Compteur "1/N sections validées"
- ✓ La case devient grisée (impossible de décocher)

```sql
SELECT sections_signees FROM `tabKYA Contrat` WHERE name = 'KYA-CTR-...'
-- {"employe": ["sec-1"]}
```

### TEST 6 — Sections : signer sans toutes valider

Cliquer "Signer et Soumettre" alors qu'il manque des sections.
- ✓ Message rouge : "⚠️ Validez les N sections (1/N)"
- ✓ Pas de signature enregistrée

### TEST 7 — Signature : canvas vide

Cocher toutes les sections + case finale, ne rien dessiner, cliquer Signer.
- ✓ Message : "Veuillez dessiner votre signature"

### TEST 8 — Signature : import image

Cliquer "Importer une image", sélectionner un PNG.
- ✓ Aperçu affiché
- ✓ Au clic Signer (avec sections + case validés) → signature sauvegardée
- ✓ Workflow passe à "Signé Employé"
- ✓ DG reçoit email

### TEST 9 — Signature : dessin canvas

Mode dessin, dessiner avec la souris, signer.
- ✓ Sauvegarde OK

### TEST 10 — Image trop volumineuse

Importer une image > 2 Mo.
- ✓ Alerte "Image trop volumineuse (max 2 Mo)"

### TEST 11 — DG : token séparé

Vérifier que `access_token_dg` est généré après signature signataire :

```sql
SELECT access_token_signataire, access_token_dg, workflow_state
FROM `tabKYA Contrat` WHERE name = 'KYA-CTR-...'
```

**Attendu** : les 2 tokens présents et différents, `workflow_state='Signé Employé'`.

Tenter d'utiliser le token signataire après que le stagiaire a signé : page doit afficher "à co-signer (DG)" mais pas permettre de re-signer.

### TEST 12 — DG signature

Ouvrir l'URL avec `access_token_dg` :
- ✓ Mode DG : pas de phone gate (DG accède direct)
- ✓ Pas de formulaire infos perso
- ✓ Sections à valider (RH a exigé signature DG aussi)
- ✓ Bouton "Co-signer le contrat"

Après signature DG :
- ✓ `workflow_state='Finalisé'`
- ✓ PDF généré et attaché (`pdf_final`)
- ✓ Email final envoyé aux 3 destinataires (stagiaire + RH expéditrice + RH globale)

### TEST 13 — PDF Branding

Ouvrir le PDF généré :
- ✓ Header avec logo KYA + "KYA-ENERGY GROUP"
- ✓ Mention "SAS au capital..." + "08 BP 81101 Lomé..."
- ✓ Référence + Date
- ✓ Corps du contrat avec sections
- ✓ "Fait à Lomé, en deux (2) exemplaires originaux."
- ✓ Bloc signatures : signataire (Lu et approuvé) + DG
- ✓ Footer "Document signé électroniquement · Réf. {name}"

### TEST 14 — Anti-rejeu

Tenter de signer 2 fois (même token) :
- ✓ Deuxième tentative refusée : "Le contrat n'est pas en attente de votre signature"

### TEST 15 — Page invalide (sans token ou name)

URL : `/kya-contrat`
- ✓ Page "Lien invalide. Utilisez le lien reçu par email."

URL : `/kya-contrat?name=KYA-CTR-XXX` (sans token)
- ✓ Idem

## Tests automatisés

Script à exécuter :

```bash
docker exec kya-8087-backend bench --site frontend execute \
  kya_hr.kya_hr.tests_contrats.run_full_test
```

Ce script :
1. Crée un contrat test avec employé fictif
2. Appelle `send_to_signataire` (vérifie génération token + email)
3. Appelle `verify_phone` (mauvais → ok puis bon → ok)
4. Appelle `update_personal_info`
5. Appelle `mark_section_signed` pour 3 sections
6. Appelle `sign_contract(role=employe)`
7. Vérifie : `access_token_dg` généré, état `Signé Employé`
8. Appelle `mark_section_signed` (DG) puis `sign_contract(role=dg)`
9. Vérifie : état `Finalisé`, PDF attaché, emails envoyés

Sortie attendue :
```
[1] Création contrat        : OK (KYA-CTR-2026-XXXXX)
[2] send_to_signataire      : OK token=XXX (48 chars)
[3] verify_phone (wrong)    : OK (rejeté)
[4] verify_phone (correct)  : OK phone_confirmed=1
[5] update_personal_info    : OK
[6] mark_section_signed x3  : OK 3/3
[7] sign_contract (employe) : OK state=Signé Employé
[8] DG token généré         : OK
[9] sign_contract (dg)      : OK state=Finalisé
[10] PDF attaché             : OK /private/files/Contrat_XXX.pdf
[11] Emails envoyés          : OK 4 destinataires (stagiaire+RH×2+DG)

✅ TOUS LES TESTS PASSENT
```

## Limites en environnement local

- Les emails sont envoyés via `frappe.sendmail` **en file (queue)** avec `now=False` → pour tester l'envoi réel en local, utiliser `now=True` ou vérifier la queue : 
  ```bash
  docker exec kya-8087-backend bench --site frontend execute frappe.email.queue.flush
  ```
- Le compte SMTP doit être configuré en local (Email Account "Default Outgoing") pour que les emails soient effectivement envoyés.
- En **prod** : configurer SMTP avec un compte type `noreply@kya-energy.com`.
- Le compte mail générique `contrat-stagiaires@kya-energy.com` envisagé initialement **n'est pas nécessaire** dans cette architecture (token URL = pas de login).

## Vérification BDD post-finalisation

```sql
SELECT name, workflow_state, phone_confirmed,
       LENGTH(access_token_signataire) AS sig_tok,
       LENGTH(access_token_dg) AS dg_tok,
       LENGTH(signature_employe) AS sig_emp_size,
       LENGTH(signature_dg) AS sig_dg_size,
       pdf_final, rh_sender_email,
       sections_signees
FROM `tabKYA Contrat`
WHERE name = 'KYA-CTR-2026-XXXXX';
```

Attendu :
- `workflow_state` = 'Finalisé'
- `phone_confirmed` = 1
- `sig_tok` = `dg_tok` = 48
- `sig_emp_size` et `sig_dg_size` > 1000 (dataURL PNG)
- `pdf_final` non vide
- `rh_sender_email` = email RH qui a cliqué "Envoyer"
- `sections_signees` = `{"employe": ["sec-1","sec-2",...], "dg": ["sec-1","sec-2",...]}`

## Sécurité — Points vérifiés

- ✅ Token 48 caractères hex (entropie ~192 bits) → bruteforce inviable
- ✅ `hmac.compare_digest` (constant-time)
- ✅ Téléphone normalisé (9 derniers chiffres) → résistant aux variations de format
- ✅ Anti-bruteforce téléphone : `time.sleep(1.5)`
- ✅ `phone_confirmed` requis pour `update_personal_info`, `mark_section_signed` (rôle employe), `sign_contract` (rôle employe)
- ✅ Workflow state vérifié avant chaque signature (anti-rejeu)
- ✅ DG token généré seulement après signature signataire (pas avant)
- ✅ Champs sensibles (`access_token_*`, `sections_signees`, `phone_confirmed`) en `hidden=1, read_only=1`
