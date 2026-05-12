# Icônes du bureau Frappe — KYA Energy

Référence complète : qui voit quelle icône, pourquoi, et comment configurer.

---

## Principe général

À la connexion sur le desk Frappe (`/app`), chaque utilisateur voit uniquement les espaces de travail auxquels ses rôles donnent accès. La logique est définie dans `kya_hr/desktop_icons.py` → `RESTRICTED_LAYOUT_ROLES`.

**Règle** : si un espace n'est PAS dans `RESTRICTED_LAYOUT_ROLES`, il est visible par tous. Si il y figure, seuls les rôles listés peuvent le voir.

---

## Tableau de visibilité par icône

| Icône (Workspace) | Rôles autorisés | Contenu principal |
|---|---|---|
| **Espace Employés** | `Employee` *(tous)*, `Stagiaire`, `Chef Service`, `Supérieur Immédiat`, `Chef Equipe`, `Responsable RH`, `HR User/Manager`, `DG`, `DGA`, `Resp. Comptable`, `Auditeur`, `Stock User`, `Purchase User`, `Resp. Achats`, `Chargé des Stocks`, `System Manager` | **Mon Espace**, Permissions, Congés, Demande Achat, PV Matériel |
| **Espace Stagiaires** | `Maître de Stage`, `Responsable des Stagiaires`, `Responsable RH`, `HR User/Manager`, `DG`, `System Manager` | Gestion des stagiaires, bilans, permissions stagiaires |
| **Espace RH** | `Responsable RH`, `HR Manager`, `HR User`, `DG`, `System Manager` | Fiches employés, contrats, congés, rapports RH, dashboard présences |
| **Direction Générale** | `Directeur Général`, `DGA`, `System Manager` | Dashboards direction, rapports synthétiques, validations DG |
| **Espace Achats** | `Purchase Manager/User`, `Responsable Achats`, `Resp. Comptable`, `DG`, `DGA`, `Auditeur`, `System Manager` | Demandes achat, bons de commande, appels d'offres, fournisseurs |
| **Espace Stock** | `Stock Manager/User`, `Chargé des Stocks`, `Resp. Comptable`, `Auditeur`, `DG`, `DGA`, `System Manager` | PV sortie/entrée matériel, inventaires, suivi stock |
| **Espace Comptabilité** | `Accounts Manager/User`, `Resp. Comptable`, `Auditeur`, `DG`, `DGA`, `System Manager` | Brouillard caisse, état récap chèques, import compta, rapports financiers |
| **Logistique** | `Fleet Manager`, `Responsable Logistique`, `Driver`, `Resp. Comptable`, `DG`, `DGA`, `System Manager` | Gestion flotte, missions, documents véhicules |
| **Inventaire & Sorties Matériel** | `Stock Manager/User`, `Chargé des Stocks`, `Resp. Achats`, `Auditeur`, `Resp. Comptable`, `DG`, `DGA`, `System Manager` | Inventaires KYA, tableau de bord inventaire |
| **KYA Services** | `KYA Survey Admin`, `System Manager` | Administration des formulaires d'enquête et d'évaluation |

---

## Matrices par profil

### Employé standard (CDI/CDD)
| Icône visible | Oui/Non |
|---|---|
| Espace Employés (→ Mon Espace) | ✅ |
| Espace RH | ❌ |
| Espace Achats | ❌ |
| Espace Stock | ❌ |
| Espace Comptabilité | ❌ |
| Direction Générale | ❌ |

### Stagiaire
| Icône visible | Oui/Non |
|---|---|
| Espace Employés (→ Mon Espace) | ✅ |
| Espace Stagiaires | ❌ *(visible seulement pour les encadrants)* |

> Un stagiaire accède à ses formulaires depuis **Mon Espace** directement (URL `/mon-espace`), sans passer par un espace dédié.

### Chef de Service / Supérieur Immédiat
| Icône visible | Oui/Non |
|---|---|
| Espace Employés (→ Mon Espace + demandes à valider) | ✅ |
| Espace Stagiaires | ❌ |
| Autres espaces métiers | ❌ *(sauf si rôle supplémentaire attribué)* |

### Responsable RH / HR Manager
| Icône visible | Oui/Non |
|---|---|
| Espace Employés | ✅ |
| Espace Stagiaires | ✅ |
| Espace RH | ✅ |
| Direction Générale | ❌ |

### Responsable Comptable (ex-DAAF/DFC)
| Icône visible | Oui/Non |
|---|---|
| Espace Employés | ✅ |
| Espace Comptabilité | ✅ |
| Espace Achats | ✅ *(supervision)* |
| Espace Stock | ✅ *(audit)* |
| Inventaire | ✅ *(audit)* |
| Direction Générale | ❌ |

### Directeur Général / DGA
| Icône visible | Oui/Non |
|---|---|
| Tous les espaces | ✅ *(sauf KYA Services et Espace Stagiaires natifs)* |

---

## Comment est gérée la visibilité ?

### Flux technique
1. À chaque connexion, `kya_hr.desktop_icons.execute()` est appelé (déclenché par `after_migrate` et `after_install`).
2. La fonction `_prune_restricted_layout_doc()` lit le `Desktop Layout` de l'utilisateur et **supprime** les icônes pour lesquelles l'utilisateur n'a pas les rôles requis.
3. Le résultat est mis en cache via `clear_desktop_icons_cache(user)`.

### Pour forcer la mise à jour
```bash
# Sur le serveur, dans le container bench :
bench --site <site> execute kya_hr.desktop_icons.execute
# Ou reload la page dans Frappe (Ctrl+Shift+R) pour rafraîchir le cache.
```

---

## Ajouter une nouvelle icône

1. Dans `kya_hr/desktop_icons.py`, ajouter dans `WORKSPACE_ICONS` :
```python
{"label": "Nom Espace", "link_to": "Nom Workspace", "icon": "emoji", "app": "kya_hr", "idx": 20},
```

2. Si l'espace doit être restreint, ajouter dans `RESTRICTED_LAYOUT_ROLES` :
```python
"Nom Espace": ["Role1", "Role2", "System Manager"],
```

3. Lancer `bench migrate` pour appliquer.

---

## Icônes des raccourcis dans chaque espace

### Espace Employés
- 🚪 Demander une Permission (→ `/permission-sortie-employe/new`)
- 📋 Permissions Employé (liste)
- 📅 Planning Congé (liste)
- 🏠 **Mon Espace** (→ `/mon-espace`) ← accès universel
- 🛒 Demande d'Achat (→ `/demande-achat/new`)
- 📦 Sortie de Matériel (→ `/pv-sortie-materiel/new`)
- 📅 Planifier un Congé (→ `/planning-conge/new`)
- ✈️ Demander un Congé (→ `/demande-conge/new`)

### Espace RH
- Fiches Employé, Leave Application, Planning Congé
- Tableau de bord présences (→ `/kya-rh-dashboard`)
- Rapports de gestion des congés

### Espace Comptabilité
- Brouillard de Caisse (→ `/brouillard-caisse/new`)
- État Récap Chèques (→ `/etat-recap/new`)
- Import Compta Excel (→ `/comptabilite-import/new`)
- Dashboard Comptabilité (→ `/comptabilite-dashboard`)

---

## FAQ

**Q : Un employé dit ne pas voir Mon Espace sur son bureau.**
→ Vérifier :
1. Le compte User a le rôle `Employee` → Settings > User > Roles.
2. La fiche Employee a `status = Active`.
3. `user_id` renseigné sur la fiche Employee.
4. Lancer `bench --site <site> execute kya_hr.desktop_icons.execute`.

**Q : Un chef de service voit trop d'espaces.**
→ Vérifier qu'il n'a PAS de rôles supplémentaires (Accounts User, Purchase User...) qu'il n'utilise pas.

**Q : Comment désactiver un espace pour tout le monde ?**
→ Ajouter l'espace dans `RESTRICTED_LAYOUT_ROLES` avec une liste vide `[]` (personne ne peut y accéder) ou juste `["System Manager"]`.

**Q : Différence Espace Employés vs Mon Espace ?**
→ **Espace Employés** = espace de travail Frappe Desk avec des raccourcis. **Mon Espace** = portail web personnalisé accessible à `/mon-espace`, adaptatif selon le profil, accessible même sans le Desk (juste un navigateur).
