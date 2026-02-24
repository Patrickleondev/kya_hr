# Plan Complet : Module Recrutement & Enquêtes RH — `kya_hr`

## Vue d'Ensemble

Ce document détaille la stratégie pour étendre le module `kya_hr` avec deux composantes majeures :

1. **Module Recrutement Enrichi** — Critères de sélection, grilles de notation, bank de questions d'entretien.
2. **Module Enquêtes RH (Survey)** — Création et publication d'enquêtes par les admins, réponses via une interface PWA mobile-first.

---

## 1. Analyse du Contexte Existant

### Ce qui existe dans ERPNext HRMS
- `Job Applicant`, `Job Opening`, `Interview`, `Interview Feedback` — déjà disponibles.
- `Web Form` — Frappe supporte des formulaires publics accessibles sans connexion.
- `/hrms` — interface mobile PWA fournie par `hrms` app.

### Les Lacunes Identifiées
| Problème | Impact |
|---|---|
| Pas de banque de questions d'entretien réutilisables | Chaque interview repart de zéro |
| Pas de grille de scoring/critères pondérés | Évaluation subjective |
| Pas d'enquêtes internes RH (satisfaction, climat, onboarding) | Données RH manquantes |
| Pas d'interface mobile dédiée pour répondre aux enquêtes | Faible taux de réponse |

---

## 2. Architecture Cible

```
kya_hr/
├── kya_hr/
│   ├── doctype/
│   │   ├── kya_question_bank/          # Banque de questions
│   │   ├── kya_interview_criteria/     # Critères d'entretien pondérés
│   │   ├── kya_survey/                 # Template d'enquête
│   │   ├── kya_survey_question/        # Questions d'une enquête (child)
│   │   ├── kya_survey_response/        # Réponses soumises
│   │   └── kya_survey_answer/          # Détail réponse par question (child)
│   ├── web_template/
│   │   └── kya_survey_portal/          # Interface Web Form PWA
│   ├── www/
│   │   └── enquetes/                   # Route publique /enquetes
│   └── api.py                          # API REST pour les réponses mobiles
```

---

## 3. Module Recrutement — Détail

### 3.1 Banque de Questions (`KYA Question Bank`)

**Champs :**
| Champ | Type | Description |
|---|---|---|
| `question_text` | Text | La question |
| `category` | Select | Technique / RH / Comportemental / Culture |
| `competency` | Link → `Competency` | Compétence évaluée |
| `expected_answer` | Long Text | (Optionnel) Réponse attendue |
| `scoring_guide` | Long Text | Grille de niveau 1–5 |
| `is_active` | Check | Actif/Inactif |

### 3.2 Critères d'Entretien (`KYA Interview Criteria`)

**DocType Parent :**
| Champ | Type | Description |
|---|---|---|
| `job_opening` | Link → `Job Opening` | Poste ciblé |
| `designation` | Link → `Designation` | Alternative : par désignation |
| `criteria_items` | Table → `KYA Interview Criteria Item` | |

**DocType Enfant `KYA Interview Criteria Item` :**
| Champ | Type | Description |
|---|---|---|
| `criterion_name` | Data | Ex: "Maîtrise Python" |
| `weight` | Float | Pondération (ex: 30%) |
| `max_score` | Int | Score max (ex: 10) |
| `linked_questions` | Table | Questions de la banque liées |

### 3.3 Intégration avec `Interview Feedback`

Un **Custom Field** sera ajouté sur `Interview Feedback` :
- `kya_criteria_scores` (Table HTML) — affiche les critères avec score saisi par l'intervieweur.
- `kya_total_score` (Float, Read Only) — score pondéré calculé automatiquement.

**Logique (via `doc_events`) :**
```python
# kya_hr/hooks.py
doc_events = {
    "Interview Feedback": {
        "before_save": "kya_hr.recruitment.calculate_weighted_score"
    }
}
```

---

## 4. Module Enquêtes RH — Détail

### 4.1 Template d'Enquête (`KYA Survey`)

| Champ | Type | Description |
|---|---|---|
| `survey_title` | Data | "Enquête de satisfaction T1 2026" |
| `target_audience` | Select | Tous / Par département / Nominatif |
| `department` | Link → `Department` | (Si target = département) |
| `employees` | Table | Liste nominative (si target = nominatif) |
| `start_date` | Date | Date d'ouverture |
| `end_date` | Date | Date de clôture |
| `is_anonymous` | Check | Réponses anonymisées |
| `status` | Select | Brouillon / Publié / Clôturé |
| `questions` | Table → `KYA Survey Question` | |

**DocType Enfant `KYA Survey Question` :**
| Champ | Type | Description |
|---|---|---|
| `question_text` | Text | La question |
| `question_type` | Select | Texte / Note 1-5 / Oui-Non / Choix Multiple |
| `choices` | Text | (Si Choix Multiple) options séparées par `\n` |
| `required` | Check | Obligatoire |

### 4.2 Réponses (`KYA Survey Response`)

| Champ | Type | Description |
|---|---|---|
| `survey` | Link → `KYA Survey` | |
| `employee` | Link → `Employee` | (Null si anonyme) |
| `submission_date` | Datetime | |
| `answers` | Table → `KYA Survey Answer` | |

**DocType Enfant `KYA Survey Answer` :**
| Champ | Type | Description |
|---|---|---|
| `survey_question` | Link / Data | Référence à la question |
| `answer_text` | Long Text | Réponse libre |
| `answer_score` | Int | Score (si Note) |
| `answer_choice` | Data | Choix sélectionné |

---

## 5. Interface Mobile PWA (`/enquetes`)

### 5.1 Approche Technique

L'interface sera une **route publique Frappe** (`www/enquetes.py` + `www/enquetes.html`), accessible sans connexion (lien unique par employé avec token), construite comme une **PWA** (Progressive Web App).

### 5.2 Flux Utilisateur

```
Admin publie enquête
        ↓
Frappe génère un lien unique : /enquetes?token=<uuid>&survey=<name>
        ↓
Lien envoyé par email / affiché dans HRMS
        ↓
Employé ouvre le lien sur mobile
        ↓
Interface PWA affiche les questions
        ↓
Employé soumet ses réponses
        ↓
API Frappe crée le doc `KYA Survey Response`
        ↓
Admin voit les réponses dans le dashboard ERPNext
```

### 5.3 Mise en Œuvre Technique

**Fichier `www/enquetes.py` :**
```python
import frappe

def get_context(context):
    token = frappe.request.args.get("token")
    survey_name = frappe.request.args.get("survey")
    
    # Valider le token
    employee = frappe.db.get_value("Employee", {"survey_token": token}, "name")
    if not employee:
        frappe.throw("Lien invalide ou expiré.")
    
    context.survey = frappe.get_doc("KYA Survey", survey_name)
    context.employee = employee
    context.token = token
```

**Fichier `www/enquetes.html` (PWA) :**
```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#2490ef">
    <link rel="manifest" href="/enquetes/manifest.json">
    <title>{{ survey.survey_title }}</title>
    <!-- Style inspiré HRMS -->
</head>
<body>
    <!-- Questions générées dynamiquement par Jinja -->
    <!-- Formulaire soumis via fetch() → API Frappe -->
</body>
</html>
```

**API de soumission (`kya_hr/api.py`) :**
```python
@frappe.whitelist(allow_guest=True)
def submit_survey_response(survey, token, answers):
    # Valider token
    # Créer KYA Survey Response + KYA Survey Answer
    return {"status": "success"}
```

### 5.4 PWA — Manifest & Service Worker

```json
// enquetes/manifest.json
{
  "name": "KYA Enquêtes RH",
  "short_name": "KYA Enquêtes",
  "start_url": "/enquetes",
  "display": "standalone",
  "theme_color": "#2490ef",
  "background_color": "#ffffff",
  "icons": [...]
}
```

---

## 6. Dashboard Admin — Analyse des Réponses

Dans le module **kya_hr** workspace (espace RH Admin), ajouter :

- **Chart : Taux de participation** par enquête (réponses reçues / cibles).
- **Table : Résumé des réponses** par question (moyenne des scores, nuage de mots).
- **Export Excel** des réponses brutes.

Implémenté via **Frappe Dashboard Charts** (DocType `Dashboard Chart`) avec des queries SQL custom.

---

## 7. Plan d'Implémentation — Étapes

### Phase 1 : Fondations (Semaine 1–2)
- [ ] Créer les DocTypes : `KYA Question Bank`, `KYA Interview Criteria`, `KYA Interview Criteria Item`
- [ ] Ajouter les Custom Fields sur `Interview Feedback`
- [ ] Implémenter le calcul de score pondéré via `doc_events`

### Phase 2 : Module Enquêtes (Semaine 3–4)
- [ ] Créer les DocTypes : `KYA Survey`, `KYA Survey Question`, `KYA Survey Response`, `KYA Survey Answer`
- [ ] Implémenter la logique de génération de tokens (`uuid`) par employé
- [ ] Créer l'API `submit_survey_response`

### Phase 3 : Interface PWA (Semaine 5–6)
- [ ] Développer `www/enquetes.py` + `www/enquetes.html`
- [ ] Créer le `manifest.json` et le `service_worker.js` pour offline-first
- [ ] Design mobile-first inspiré de HRMS (Frappe UI components)
- [ ] Tester sur mobile (Android/iOS)

### Phase 4 : Dashboard & Notifications (Semaine 7)
- [ ] Créer les Dashboard Charts pour le suivi de participation
- [ ] Ajouter une Notification Frappe quand une nouvelle réponse est soumise
- [ ] Export Excel des réponses via une API dédiée

### Phase 5 : Tests & Déploiement (Semaine 8)
- [ ] Tests utilisateur : Envoyer une enquête pilote à 3–5 employés tests
- [ ] Corriger les UX bugs
- [ ] Exporter les fixtures (`bench export-fixtures`) et pousser en production

---

## 8. Points de Vigilance

> [!IMPORTANT]
> **Sécurité des tokens** : Chaque lien `/enquetes?token=...` doit être à usage unique ou expirant. Implémenter un champ `survey_token_expiry` sur Employee ou sur un DocType `KYA Survey Invitation`.

> [!WARNING]
> **Anonymat** : Si `is_anonymous = 1`, ne jamais stocker `employee` dans `KYA Survey Response`. Mettre un trigger `before_insert` pour forcer ce comportement côté serveur.

> [!TIP]
> **Réutilisation HRMS Web** : La route `/hrms` utilise Vue.js. Pour aller plus loin, le module enquête peut être intégré directement dans l'app HRMS comme une nouvelle page Vue — plus cohérent visuellement, mais plus complexe à maintenir.

---

## 9. Stack Technologique Résumé

| Couche | Technologie |
|---|---|
| Backend | Frappe Framework (Python), MariaDB |
| DocTypes | Frappe DocType (ORM automatique) |
| API | Frappe Whitelist (`@frappe.whitelist`) |
| Frontend Mobile | HTML5 + CSS3 + Vanilla JS (PWA) |
| Manifest PWA | `manifest.json` + `service_worker.js` |
| Notifications | Frappe Notification DocType |
| Dashboard | Frappe Dashboard Charts |
| Auth Tokens | UUID4 stocké côté Employee |
