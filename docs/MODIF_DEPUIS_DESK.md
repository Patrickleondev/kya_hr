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

---

## 13. Pages `/www/...` cassées (`'X' is undefined`) — fix sans toucher au code

### Symptôme
Tu ouvres une page custom comme `/kya-reunion-dashboard`, `/logistique-dashboard`, `/tableau-bord-employes`… et tu vois un **Traceback Jinja** :
```
File "apps/kya_hr/kya_hr/www/<page>.html", line X
    {{ stats.total }} ou {{ flotte.total }}
jinja2.exceptions.UndefinedError: 'stats' is undefined
```

### Cause
Frappe v15+ remplace les `-` par des `_` pour trouver le module Python d'une page web (cf [`frappe/website/page_renderers/template_page.py:131`](https://github.com/frappe/frappe/blob/develop/frappe/website/page_renderers/template_page.py#L131)).

→ Pour `kya-reunion-dashboard.html`, Frappe cherche **`kya_reunion_dashboard.py`** (underscores).
→ Si le fichier `.py` est en `kya-reunion-dashboard.py` (dashes), Frappe ne le trouve **JAMAIS**, donc `get_context()` n'est pas appelé, donc les variables sont undefined côté Jinja.

### Fix immédiat depuis le serveur (sans toucher au repo) — 30 secondes
```bash
# 1. Trouver le container backend
docker ps | grep backend
# Ex : kya-preprod-8085-backend-1

# 2. Renommer le fichier dash → underscore DANS le container
docker exec <nom-container> mv \
  /home/frappe/frappe-bench/apps/kya_hr/kya_hr/www/kya-reunion-dashboard.py \
  /home/frappe/frappe-bench/apps/kya_hr/kya_hr/www/kya_reunion_dashboard.py

# 3. Vider le cache pour que Frappe recharge
docker exec <nom-container> bench --site <site> clear-cache
docker exec <nom-container> bench --site <site> clear-website-cache

# 4. Tester
curl -I http://localhost:<port>/kya-reunion-dashboard
# → HTTP 200 attendu
```

⚠️ **Volatile** : ce fix saute au prochain `docker compose pull` ou rebuild de l'image. Pour le rendre permanent, il faut renommer dans le repo Git (cf §16) ou attendre le merge de la PR qui contient le fix.

### Fix alternatif via UI Desk (durable, mais nouvelle URL)
Si tu ne peux pas / ne veux pas exec dans le container, créer une **Web Page** Frappe qui remplace la page cassée :

1. `/app/web-page/new`
2. Champs :
   - **Title** : `Dashboard Réunions KYA`
   - **Route** : `kya-reunion-dashboard-v2` ⬅️ nouvelle route (la cassée reste cassée)
   - **Content type** : `HTML`
   - **Module** : `KYA HR`
   - **Published** : ✅
   - **Content** : copier le HTML de la page d'origine, **remplacer toutes les variables Jinja** `{{ stats.total }}`, `{{ stats.actifs }}`, etc. par un placeholder `<span id="kpi-total">…</span>` + un script à la fin qui fetch les données en JS :
     ```html
     <script>
     fetch('/api/method/kya_hr.api.kya_reunion.get_dashboard_stats')
       .then(r => r.json()).then(r => {
         document.getElementById('kpi-total').textContent = r.message.total;
         document.getElementById('kpi-actifs').textContent = r.message.actifs;
         // ...
       });
     </script>
     ```
3. Save → la page `/kya-reunion-dashboard-v2` est immédiatement accessible.
4. **Mettre à jour les workspaces** (`Espace RH`, etc.) pour que les shortcuts pointent vers la nouvelle route.

### Comment savoir si une autre page www a le même problème
Liste tous les `.py` de `www/` qui ont des dashes (potentiellement cassés) :
```bash
docker exec <backend-container> bash -c \
  "ls /home/frappe/frappe-bench/apps/*/*/www/*.py | grep -- '-' | grep -v __init__"
```
Chaque fichier listé est candidat au même bug. Renomme-les tous avec la commande `mv` du paragraphe précédent.

---

## 14. CSS / design des Web Forms sans toucher au code

Le design KYA des Web Forms (en-tête bleu/orange, sections numérotées, signatures) vient de **2 fichiers source** :
- `kya_hr/public/js/kya_webform.js` — construit la mise en page
- `kya_hr/public/css/kya_webform.css` — couleurs/typo

Tu **ne peux pas** modifier ces fichiers depuis Desk. **MAIS** tu peux :

### Option A — Surcharger via le Client Script du Web Form lui-même (recommandé)

`/app/web-form/<route>` → champ **Client Script** :

```javascript
frappe.web_form.after_load = function() {
  // 1. Cacher la signature DG si pas encore au bon état workflow
  if (frappe.web_form.doc.workflow_state !== 'En attente DG') {
    const sigDg = document.querySelector('[data-fieldname="signature_dg"]');
    if (sigDg) sigDg.style.display = 'none';
  }

  // 2. Ajouter une banderole d'info en haut
  const banner = document.createElement('div');
  banner.innerHTML = `
    <div style="padding:14px 20px; background:#fef3c7; border-left:4px solid #f59e0b;
                color:#92400e; font-weight:600; margin-bottom:16px; border-radius:6px;">
      ⚠️ Document confidentiel — diffusion restreinte à la Direction.
    </div>`;
  const wrapper = document.querySelector('.web-form-wrapper') || document.querySelector('.container');
  if (wrapper) wrapper.prepend(banner.firstElementChild);

  // 3. Forcer une couleur custom sur un champ
  const field = document.querySelector('[data-fieldname="montant_total"]');
  if (field) field.style.cssText = 'color:#c2410c; font-size:1.4rem; font-weight:800;';
};
```

→ Pas de redéploiement, prend effet au prochain reload de la page web form.

### Option B — Injecter du CSS via Client Script

Même endroit (Client Script du Web Form) :

```javascript
frappe.web_form.after_load = function() {
  const style = document.createElement('style');
  style.textContent = `
    .web-form-wrapper { max-width: 900px !important; }
    .web-form-wrapper input[type="text"]:focus,
    .web-form-wrapper select:focus,
    .web-form-wrapper textarea:focus {
      border-color: #F58220 !important;
      box-shadow: 0 0 0 3px rgba(245,130,32,.15) !important;
    }
    .web-form-wrapper label.control-label {
      font-weight: 600 !important;
      color: #0054A6 !important;
    }
    /* Cacher la sidebar pour ce form-ci uniquement */
    .web-form-sidebar { display: none !important; }
  `;
  document.head.appendChild(style);
};
```

→ CSS appliqué uniquement à ce Web Form, sans toucher au `kya_webform.css` global.

### Option C — Surcharge globale via Website Settings

`/app/website-settings` → champ **Body HTML** (s'insère sur toutes les pages publiques) :
```html
<style>
/* CSS qui s'applique à toutes les pages web (web forms inclus) */
body { font-family: 'Plus Jakarta Sans', sans-serif !important; }
.web-form-wrapper .btn-primary {
  background: #F58220 !important;
  border-color: #F58220 !important;
}
</style>
```

⚠️ Affecte **toutes** les pages publiques. À utiliser uniquement pour des changements globaux (police, couleurs primaires).

### Cas typique : changer la couleur primaire des web forms
1. `/app/website-settings` → Body HTML → coller :
   ```html
   <style>
   :root { --primary-color: #00A651; }
   .btn-primary { background: var(--primary-color) !important; }
   .web-form-wrapper a { color: var(--primary-color); }
   </style>
   ```
2. Save → reload n'importe quel web form → ✅ couleur changée.

### Ce qu'il faut quand même toucher au code
- **Restructurer la mise en page** (ordre des sections, en-tête KYA, signatures côte à côte) → ces structures viennent du JS `kya_webform.js`. Pour les modifier, il faut éditer ce fichier (et redéployer). Pas faisable depuis Desk.
- **Ajouter un nouveau bouton dans toutes les pages web** → idem, modifier le JS global.

---

## 15. Remplacer une page www cassée par une Web Page Desk (durable, sans code)

Si une page `/www/...` est cassée et que tu **ne peux pas** :
- Renommer le fichier dans le container (cf §13)
- Attendre le merge d'une PR qui fixe ça

Alors **crée une Web Page** Desk qui remplit le même rôle. Pattern :

### Étape 1 — Créer la Web Page
`/app/web-page/new` :
- **Title** : `Mon Dashboard X` (clair pour l'utilisateur final)
- **Route** : `<route-de-remplacement>` (ex : `kya-reunion` au lieu de `kya-reunion-dashboard`)
- **Content type** : `HTML`
- **Published** : ✅
- **Show Title** : à toi de voir
- **Content** : voir Étape 2

### Étape 2 — Contenu HTML qui appelle une API en JS

Au lieu de variables Jinja serveur (qui ne marchent pas dans Web Page comme dans une page www `.py`+`.html`), utilise `fetch()` côté navigateur :

```html
<style>
.kya-kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }
.kya-kpi { background: white; padding: 18px; border-radius: 10px; border-left: 4px solid #0054A6; }
.kya-kpi .label { font-size: 11px; color: #6b7280; text-transform: uppercase; font-weight: 700; }
.kya-kpi .value { font-size: 26px; font-weight: 800; color: #0054A6; margin-top: 4px; }
.kya-loader { text-align: center; padding: 40px; color: #6b7280; }
</style>

<h1>🚗 Dashboard Réunions KYA</h1>

<div id="loader" class="kya-loader">Chargement…</div>

<div id="content" style="display:none;">
  <div class="kya-kpi-row">
    <div class="kya-kpi">
      <div class="label">Total réunions</div>
      <div class="value" id="kpi-total">—</div>
    </div>
    <div class="kya-kpi">
      <div class="label">Actives</div>
      <div class="value" id="kpi-actifs">—</div>
    </div>
    <div class="kya-kpi">
      <div class="label">Clôturées</div>
      <div class="value" id="kpi-clotures">—</div>
    </div>
    <div class="kya-kpi">
      <div class="label">Présences</div>
      <div class="value" id="kpi-presences">—</div>
    </div>
  </div>

  <h3>Réunions récentes</h3>
  <div id="meetings-list"></div>
</div>

<script>
fetch('/api/method/kya_hr.api.kya_reunion.get_dashboard_stats?period=30', {
  credentials: 'same-origin',
  headers: { 'X-Requested-With': 'XMLHttpRequest' }
})
.then(r => r.json())
.then(data => {
  const d = data.message || {};
  document.getElementById('kpi-total').textContent = d.total || 0;
  document.getElementById('kpi-actifs').textContent = d.active || 0;
  document.getElementById('kpi-clotures').textContent = d.closed || 0;
  document.getElementById('kpi-presences').textContent = d.participants || 0;

  const list = document.getElementById('meetings-list');
  (d.recent || []).forEach(m => {
    const div = document.createElement('div');
    div.style.cssText = 'padding:10px; border-bottom:1px solid #eee;';
    div.innerHTML = `<b>${m.title}</b> — ${m.start_at || ''} (${m.status})`;
    list.appendChild(div);
  });

  document.getElementById('loader').style.display = 'none';
  document.getElementById('content').style.display = 'block';
})
.catch(err => {
  document.getElementById('loader').textContent = '❌ Erreur : ' + err.message;
});
</script>
```

### Étape 3 — Mettre à jour les workspaces

`/app/workspace/<workspace-cible>` → Edit → trouver le Shortcut qui pointe vers l'ancienne route cassée → modifier l'URL pour pointer vers la nouvelle Web Page.

### Quand utiliser cette approche
- ✅ Tu n'as pas accès SSH au serveur (pas de `docker exec` possible)
- ✅ Tu veux que la fix soit **durable** (survit aux redeploy)
- ✅ Page simple à reproduire (KPIs + listes — pas de logique métier complexe)

### Limitations
- ❌ Pas de filtres de permissions Frappe natifs (à reproduire à la main en JS via l'API `frappe.session.user`).
- ❌ Si l'API backend est elle aussi cassée, ça ne marche pas (mais ici les API `kya_hr.api.*` marchent — c'était juste la page Jinja qui était cassée).

---

## 16. Récap "fix sans code" pour les 4 cas les plus fréquents

| Problème | Fix UI Desk (durable) | Fix container (volatile, 30s) |
|---|---|---|
| Page www `/foo` → `'X is undefined'` | Créer Web Page `/foo-v2` + JS API (§15) | `mv foo.py foo_py_with_underscores.py` (§13) |
| Web Form sans le bon design (CSS) | Client Script avec injection CSS (§14) | — |
| Dashboard chart obsolète | `/app/dashboard-chart/<nom>` (§8) | — |
| Notification email à modifier | `/app/notification/<nom>` (§2) | — |
| Permission rôle à ajuster | `/app/role-permissions-manager` (§6) | — |
| Workflow step à insérer | `/app/workflow/<nom>` (§1) | — |
| Print Format à modifier | `/app/print-format/<nom>` (§4) | — |
| Champ DocType custom à ajouter | Customize Form (§5) | — |
| Workspace shortcut à éditer | Workspace Edit (§7) | — |

**Règle générale** : si le fix demande de **toucher à du Python avec de la logique** (calculs, hooks, server-side validation), il faut passer par le code. Tout le reste (config, UI, contenu, permissions) → Desk.

---

## 17. Quand contacter le dev / faire une PR

Si tu as fait un fix volatile via `docker exec` (cf §13) ou via Web Page Desk (§15) et que tu veux que **toutes les futures installations** en bénéficient, ouvrir un ticket / PR avec :

1. **Description** : symptôme exact + URL + screenshot du traceback si applicable
2. **Fix appliqué** : ce que tu as fait dans le container ou en UI
3. **Branche** : la dev fera la modif source (rename du fichier, etc.) + push sur une branche `fix/<scope>` à merger sur `dev` puis `main`.

Le merge déclenche un rebuild de l'image `:dev` puis `:prod` (CI GitLab). Après le `docker compose pull` + restart, le fix est permanent et tu peux supprimer la Web Page de remplacement ou défaire le rename in-container.
