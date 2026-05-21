# Modifier KYA HR depuis Frappe Desk — sans toucher au code

Ce guide liste **tout ce qu'on peut adapter depuis l'UI Frappe** (rôle `System Manager` ou rôle métier équivalent) sans `git pull`/redeploy. Pour chaque type de modification : où aller, ce qu'on peut faire, ce qu'on ne peut PAS faire (cas où il faut quand même toucher au code).

> **Règle d'or** : après toute modification depuis Desk, vider le cache (`bench --site <site> clear-cache` ou bouton "Clear Cache" en haut à droite) pour que les changements soient visibles partout. Les Workflows et permissions ont du cache côté serveur ET client.

---

## 1. Workflows (Brouillon → En attente X → Approuvé)

### Où aller
`/app/workflow` → chercher le workflow concerné (ex : "Bon Commande KYA Workflow", "Permission Sortie Employe Workflow", "Retour Materiel KYA Workflow"…)

### Ce qu'on peut modifier depuis Desk
- **States** (`/app/workflow-state`) : libellé d'un état, couleur (Success/Warning/Danger/Info/Primary), ordre d'affichage.
- **Transitions** (dans le workflow lui-même) :
  - Ajouter une étape intermédiaire (ex : insérer "Vérification Audit" entre "Chef Service" et "DG").
  - Changer le rôle autorisé à valider une transition (`Allowed` → choisir un autre rôle).
  - Ajouter une condition Jinja (`Condition` → `doc.montant_total > 1000000` pour ne déclencher un palier que si le montant dépasse un seuil).
  - Changer le `Next State` après une action.
- **Champ piloté par le workflow** : le `workflow_state_field` du DocType (généralement `workflow_state` ou `statut`).

### Cas typiques
- **Ajouter une étape de validation** : ouvrir le workflow → bloc *Transitions* → "Add Row" → remplir `State` (état source), `Action` (libellé bouton), `Next State` (état cible), `Allowed` (rôle), éventuellement `Condition`.
- **Permettre au DGA de valider en plus du DG** : sur la transition concernée, dupliquer la ligne en remplaçant `Directeur Général` par `DGA`. Frappe accepte plusieurs transitions sortantes du même état si l'`Allowed` diffère.
- **Supprimer une étape obsolète** : décocher `Is Active` sur le State (préférable) plutôt que supprimer — préserve l'historique des docs déjà passés par là.

### Ce qu'il faut quand même toucher au code
- **Logique métier déclenchée par le passage à un état** (envoi email custom, création Stock Entry…) : c'est dans `<doctype>.py` (`on_update_after_submit`) ou `kya_hr.email_notifications`. Pas modifiable depuis Desk.
- **Auto-calcul de seuil dynamique** (palier par montant) : `kya_hr/auto_calc_logic.py`.

---

## 2. Notifications email

### Où aller
`/app/notification` → chercher par DocType (ex : "Notification soumission Bon Commande KYA")

### Ce qu'on peut modifier depuis Desk
- **Document Type** ciblé.
- **Trigger** :
  - `Save` / `Submit` / `Cancel` / `New`
  - `Value Change` (sur un champ spécifique → ex : `statut` change)
  - `Days After` / `Days Before` (rappel échéance)
  - `Cron` (expression cron pour notifs récurrentes)
- **Condition** Jinja (`doc.statut == "Approuvé"`)
- **Recipients** : 
  - `Receiver By Document Field` (ex : `owner`, `employee.user_id`, `report_to.user_id`)
  - `Receiver By Role` (ex : `Responsable RH`)
  - `CC` / `BCC` (champs ou emails fixes)
- **Subject** + **Message** (Jinja autorisé : `{{ doc.numero_bc }}`, `{{ frappe.utils.formatdate(doc.date_bc) }}`)
- **Send Reminder** (`Print Format` joint, fréquence répétition)
- **Channel** : Email / System Notification / Slack / SMS

### Cas typiques
- **Ajouter le DGA en CC sur les soumissions BC** : ouvrir la Notification → bloc *Recipients* → "Add Row" type `Receiver By Role` → `DGA` → cocher `CC`.
- **Envoyer un rappel J-3 avant le début d'un congé planifié** : créer une nouvelle Notification → `Document Type = Leave Application`, `Send Alert On = Days Before`, `Days In Advance = 3`, `Reference Date = from_date`, `Recipients = employee.user_id`.
- **Désactiver temporairement une notif spammeuse** : décocher `Enabled`. Pas besoin de la supprimer.

### Ce qu'il faut quand même toucher au code
- **Email avec PDF joint dynamique non-Print-Format** (génération à la volée) : c'est dans `kya_hr/email_notifications.py`.
- **Email envoyé via cron complexe** (récap hebdo DG sur Brouillard Caisse) : `kya_hr.brouillard_caisse.send_weekly_dg_summary`.

---

## 3. Web Forms (formulaires publics employés)

### Où aller
`/app/web-form` → ouvrir le web form (ex : "demande-conge", "retour-materiel", "planning-conge"…)

### Ce qu'on peut modifier depuis Desk
- **Titre**, **Route**, **Introduction Text** (HTML autorisé), **Success Message**.
- **Champs exposés** (`Web Form Field`) :
  - Ajouter / retirer un champ du DocType backing.
  - Changer le label affiché côté form (sans toucher le label DocType).
  - Marquer un champ comme `Read Only` ou `Required` côté form uniquement.
  - Ajouter une `Description` (aide affichée sous le champ).
  - Réordonner par drag-and-drop.
- **Login required** (Yes/No), **Allow Edit** / **Allow Delete** / **Allow Multiple**.
- **Client Script** (JS) : code exécuté au chargement / à la modification de champs.
- **Show Sidebar** (active la sidebar avec liste des records de l'utilisateur).

### Cas typiques
- **Ajouter un champ existant du DocType au web form** : aller dans le DocType → ajouter le champ s'il n'existe pas (cf. §5 Custom Fields), revenir sur le Web Form → bloc *Web Form Fields* → "Add Row" → choisir le champ.
- **Masquer un champ pour les employés** mais le garder visible côté Desk : ne pas l'ajouter au web form, ou le mettre `Hidden` côté DocType.
- **Modifier le design KYA appliqué** : ouvrir `kya_hr/public/js/kya_webform.js` → c'est ce qui injecte l'en-tête bleu/orange + sections numérotées. Modifier le mapping `FORM_SECTIONS` pour réorganiser visuellement. **Là il faut toucher le code.**

### Ce qu'il faut quand même toucher au code
- **Mise en page graphique sections + signatures** (en-tête KYA, grille 2 colonnes, etc.) → `kya_hr/public/js/kya_webform.js`.
- **CSS** des web forms → `kya_hr/public/css/kya_webform.css`.

---

## 4. Print Formats (impression officielle)

### Où aller
`/app/print-format` → ouvrir le print format (ex : "Bon Commande KYA Officiel")

### Ce qu'on peut modifier depuis Desk
- **Print Format Builder** (mode WYSIWYG) si `Print Format Type = Standard` : drag-and-drop des champs, ajout d'en-têtes, blocs.
- **HTML+Jinja** si `Print Format Type = Jinja` : édition libre du HTML (avec accès aux variables `doc`, `frappe.utils.*`, etc.). C'est le mode utilisé pour le BC Officiel KYA.
- **CSS** custom dans le champ `CSS`.
- **Default Print Language** (fr).
- **Page Size**, **Margin**.

### Cas typiques
- **Changer le titre / fonction sous la signature DG** : ouvrir le print format → dans le HTML, chercher `autorise_par_fonction` → modifier le fallback ('Directeur Général').
- **Ajouter un cachet visuel** : insérer une `<img src="/files/cachet-kya.png">` dans le bloc autorisation.
- **Masquer un champ à l'impression** : sur le DocType, marquer le champ `print_hide: 1`.

### Ce qu'il faut quand même toucher au code
- **Print Format Type = Jinja avec logique Python complexe** (filtres custom) → enregistrer le filtre dans `hooks.py` puis l'utiliser. Pas modifiable depuis Desk.
- **Print Format référencé par un PDF email-attached** : OK depuis Desk, mais l'attachement automatique est config dans la Notification (cf. §2).

---

## 5. Custom Fields (ajouter un champ à un DocType)

### Où aller
`/app/customize-form` (Customize Form) → choisir le DocType → ajouter le champ.
**OU** `/app/custom-field/new` → directement.

### Ce qu'on peut modifier depuis Desk
- Ajouter un nouveau champ à n'importe quel DocType (standard ou custom).
- Modifier `Label`, `Description`, `Default`, `Mandatory`, `Read Only`, `Hidden`, `In List View`, `In Standard Filter`, `In Global Search`.
- Changer l'**ordre** des champs (drag-and-drop dans Customize Form).
- Ajouter des **Custom Permissions** (DocPerm) pour un rôle.

### Cas typiques
- **Ajouter un champ `numero_dossier` à Bon de Commande KYA** : Customize Form → "Bon Commande KYA" → "Add Row" → fieldname `numero_dossier`, fieldtype `Data`, label `N° Dossier`. Sauvegarder. Le champ apparaît immédiatement (après refresh).
- **Cacher un champ obsolète** pour ne pas le supprimer : cocher `Hidden`. Le champ reste en BDD, l'historique est préservé.

### Ce qu'il faut quand même toucher au code
- **Ajouter une logique de calcul** sur le champ (fetch_from depuis un autre Link, formule auto) : `fetch_from` est OK depuis Desk, mais les formules complexes (Python) doivent aller dans `<doctype>.py`.
- **Ajouter un champ à un DocType déjà déployé en BDD avec une migration** : si le DocType est `custom:1` (la majorité de nos DocTypes KYA), le fichier JSON est la source de vérité — donc préférer modifier le JSON et lancer migrate pour avoir un suivi git. Customize Form sur un `custom:1` peut être écrasé à la prochaine migrate.

> **Attention** : pour les DocTypes KYA (`custom:1`), les ajouts via Customize Form sont **stockés dans `tabCustom Field`** et **non dans le JSON du DocType**. Ils survivent aux migrations. Mais pour cohérence, mieux vaut faire les ajouts directement dans le JSON + commit.

---

## 6. Permissions (qui voit quoi)

### Où aller
`/app/role-permissions-manager` (Role Permissions Manager) → choisir le DocType + le rôle.
**OU** depuis le DocType → bloc *Permissions* en bas de la fiche Customize Form.

### Ce qu'on peut modifier depuis Desk
- Pour chaque combinaison `DocType × Role × Permission Level` :
  - `Read`, `Write`, `Create`, `Delete`, `Submit`, `Cancel`, `Amend`, `Print`, `Email`, `Export`, `Report`, `Share`.
  - `If Owner` (l'utilisateur ne voit que ses propres records).
  - `Match` (User Permission filter — ex : ne voit que les records de son département).
- **User Permissions** (`/app/user-permission`) : restreindre un utilisateur à des valeurs précises d'un Link field (ex : un Chef de Service voit uniquement les Permissions Sortie dont `department = Service Technique`).
- **Role Profile** (`/app/role-profile`) : groupes de rôles à attribuer en un clic.

### Cas typiques
- **Donner à un Auditeur le droit de lire (mais pas modifier) toutes les fiches** : Role Permissions Manager → choisir le DocType → ligne `Auditeur Interne` → cocher `Read` + `Report` + `Export`, décocher le reste.
- **Limiter un utilisateur à son département** : User Permissions → ajouter une ligne pour cet utilisateur sur `Department = Service Technique` → tous les DocTypes ayant un Link vers Department filtreront automatiquement.

### Ce qu'il faut quand même toucher au code
- **Filtres de permission custom complexes** (ex : un Chef d'Équipe ne voit que les Tache Equipe dont il est `chef_equipe`) → `kya_hr/permissions.py` (`permission_query_conditions`).

---

## 7. Workspaces (les "espaces" du bureau)

### Où aller
`/app/workspace` → ouvrir l'espace (ex : "Espace RH", "Espace Achats"…) puis **bouton ⋮ → Edit**.

### Ce qu'on peut modifier depuis Desk
- **Shortcuts** (gros boutons en haut) : label, URL, icône (couleur, format Icon/Card).
- **Cards / Links** (sections cliquables avec liste de raccourcis) : ajouter / retirer / réordonner.
- **Charts** affichés dans l'espace.
- **Number Cards** affichées.
- **Roles** autorisés à voir l'espace (champ `Restrict To Domain` ou `Roles` sur le Workspace).
- **Public** vs privé.
- **Parent Workspace** (créer une hiérarchie d'espaces).

### Cas typiques
- **Ajouter un raccourci "Nouvelle Permission Stagiaire"** sur l'Espace Stagiaires : ouvrir le workspace en édition → bloc *Shortcuts* → "Add Row" → label `➕ Nouvelle Permission`, type `URL`, link_to `/permission-sortie-stagiaire/new`, color `#7c4dff`, format `Icon`. Sauver.
- **Retirer un raccourci obsolète** : drag pour le sortir, ou supprimer la ligne dans `Workspace Shortcut`.

### Cas particulier : redirections "+ Add" Desk → Web Form
Le bouton "+ Add" sur la liste Desk d'un DocType web-form-isé (ex : Bon Commande KYA) est intercepté par `kya_hr/public/js/kya_webform.js` qui redirige vers le web form custom. Cette config est en code (le mapping DocType → web form). Si tu veux **ajouter** un DocType à cette redirection (ex : tu crées une nouvelle entité web-form-isée), il faut modifier `DOCTYPE_TO_WEBFORM` dans `kya_webform.js`. Tout le reste (création/édition des shortcuts) est OK depuis Desk.

---

## 8. Dashboards (graphiques + KPIs)

### Où aller
- **Dashboard** : `/app/dashboard`
- **Dashboard Chart** : `/app/dashboard-chart`
- **Number Card** : `/app/number-card`

### Ce qu'on peut modifier depuis Desk
- **Dashboard Chart** :
  - `Chart Type` (Sum/Count/Average/Group By/Custom).
  - `Type` visuel (Bar/Line/Donut/Pie/Heatmap/Percentage).
  - `Document Type` source.
  - `Based On` (champ date pour timeseries) + `Time Interval` (Daily/Weekly/Monthly/Yearly).
  - `Group By Based On` + `Group By Type`.
  - `Filters JSON` (filtres standards Frappe).
  - `Color` hex.
- **Number Card** :
  - `Function` (Sum/Count/Average/Min/Max).
  - `Aggregate Function Based On` (champ pour Sum/Avg).
  - `Filters JSON`.
- **Dashboard** :
  - Sélectionner les charts + cards à afficher.
  - Largeur (Half/Full) pour chaque chart.

### Cas typiques
- **Modifier un seuil de filtre Number Card** : ouvrir le Number Card → modifier `Filters JSON` (ex : `[["amount",">",1000000]]`) → Save.
- **Ajouter un dashboard "Suivi Stagiaires"** : créer un Dashboard, choisir les charts existants ou en créer (Group By sur Employee.employment_type = Stage, etc.).

### Ce qu'il faut quand même toucher au code
- **Charts seedés au migrate** : `kya_hr/setup_inventaire_dashboard.py`, `kya_hr/setup_rh_dashboard.py`, `kya_hr/setup_fleet_dashboard.py`. Modifier dans Desk n'a pas d'effet pérenne si le seed est rejoué (`is_public=1, is_standard=0` → potentiellement écrasé). Pour qu'un changement Desk soit permanent, **soit** modifier aussi le seed Python, **soit** désactiver le seed pour ce chart.

---

## 9. Email Templates

### Où aller
`/app/email-template`

### Ce qu'on peut modifier depuis Desk
- Sujet + corps (HTML + Jinja).
- Référencé par nom dans les Notifications (`Email Template` field).

### Cas typique
- **Refondre la signature email RH KYA** : ouvrir le template "RH Submission Recap" → modifier le footer HTML → Save. Toutes les notifs utilisant ce template prennent le changement immédiatement.

---

## 9 bis. Notifications email — RH/Chef/DG n'a pas reçu son mail

> 📘 **Guide complet dédié à la racine du projet** : `GUIDE_NOTIFICATIONS_EMAIL.md`
>
> Procédure de diagnostic en 5 minutes + 7 causes typiques avec réparation depuis Desk uniquement.

Résumé express :

| Symptôme | Section du guide à lire | Endroit Desk |
|---|---|---|
| **Personne** ne reçoit rien | §1 Email Account | `/app/email-account` → Send Test Email |
| **Une personne** ne reçoit pas (RH par ex.) | §2 champ destinataire vide | Ouvrir le doc → champ `notif_rh_email` rempli ? |
| Un **type de mail** manque | §3 Notification désactivée | `/app/notification` → `Enabled` ? |
| Notif `Enabled` mais ne se déclenche jamais | §4 condition Jinja | Notification → Condition |
| Un **rôle entier** ignoré | §5 rôle mal orthographié | Notification → Receiver By Role |
| Email Queue bloquée en `Not Sent` | §7 worker arrêté | `docker restart queue-short-8086` |

Tests rapides :

- `/app/email-queue` → si le mail est `Sent` → c'est parti côté Frappe (regarder les spams)
- `/app/email-queue` → `Error` → cliquer pour voir le message SMTP exact
- Sur le doc → champs `notif_*_email` doivent être remplis automatiquement après soumission

Pour la liste exhaustive des 13 notifications KYA et leurs destinataires : voir §10 du `GUIDE_NOTIFICATIONS_EMAIL.md`.

---

## 10. Tableau récapitulatif "où modifier quoi"

| Je veux changer… | Aller dans Desk | Ou modifier le fichier… |
|---|---|---|
| L'ordre des étapes d'un workflow | `/app/workflow/<nom>` | `kya_hr/fixtures/workflow.json` |
| Le rôle qui valide une étape | `/app/workflow/<nom>` → Transitions | idem |
| Le destinataire d'une notif email | `/app/notification/<nom>` | `kya_hr/fixtures/notification.json` |
| Le sujet/corps d'un email | `/app/email-template/<nom>` ou `/app/notification/<nom>` | `kya_hr/fixtures/email_template.json` |
| Un champ exposé dans un web form | `/app/web-form/<route>` | `kya_hr/web_form/<wf>/<wf>.json` |
| L'introduction d'un web form | `/app/web-form/<route>` → Introduction Text | idem |
| Le design du web form (en-tête KYA, sections) | ❌ | `kya_hr/public/js/kya_webform.js` |
| Un champ d'un DocType `custom:1` | Customize Form (volatile) | `kya_hr/doctype/<dt>/<dt>.json` ✅ recommandé |
| La logique métier (auto-calc, hooks) | ❌ | `kya_hr/<module>.py` |
| Le print format BC officiel | `/app/print-format/Bon Commande KYA Officiel` | `kya_hr/print_format/bon_commande_kya_officiel/bon_commande_kya_officiel.json` |
| Les permissions d'un rôle | `/app/role-permissions-manager` | `kya_hr/doctype/<dt>/<dt>.json` (bloc permissions) |
| Les raccourcis d'un workspace | `/app/workspace/<nom>` → Edit | `kya_hr/workspace/<ws>/<ws>.json` |
| Une chart de dashboard | `/app/dashboard-chart/<nom>` | `kya_hr/setup_*_dashboard.py` |

---

## 11. Checklist avant tout changement en production

1. Tester sur 8087 d'abord (instance de dev).
2. Sauvegarder l'état initial (export du JSON du DocType / Workflow / Notification concerné).
3. Faire le changement.
4. Lancer `bench --site <site> clear-cache` + reload navigateur.
5. Tester le flux de bout en bout (créer un doc, le faire passer par toutes les étapes).
6. Documenter le changement dans `ROLES_ET_FLUX.md` si ça impacte le flux ou un rôle.

## 12. Quand un changement Desk doit aussi aller en code

Si tu modifies un fichier depuis Desk et que tu veux que **les autres environnements** (preprod, prod, nouvelles installations CI) en bénéficient :
- **Workflow / Notification / Email Template / Web Form** : exporter le fixture après modification.
  ```bash
  docker exec <backend> bench --site <site> export-fixtures
  ```
  → Met à jour `kya_hr/fixtures/*.json`. Commit + push.
- **Print Format** : ouvrir le print format dans Desk → bouton "Export to JSON" en haut → coller dans `kya_hr/print_format/<nom>/<nom>.json`. Commit + push.
- **DocType `custom:1`** : si tu as utilisé Customize Form, le changement est dans `tabCustom Field` — pas dans le JSON du DocType. Pour le rendre permanent, modifier directement le JSON et commit, ou exporter via `bench export-fixtures` (les custom_fields sont dans `kya_hr/fixtures/custom_field.json`).
- **Custom Permission** : `bench export-fixtures` exporte vers `kya_hr/fixtures/custom_docperm.json`.

Sans ces étapes, le changement reste **local au site** où il a été fait et sera perdu à la prochaine `bench migrate` d'une fresh install.
