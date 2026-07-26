import json

import frappe
from frappe.desk.doctype.desktop_icon.desktop_icon import clear_desktop_icons_cache

WORKSPACE_ICONS = [
    # NB labels SANS accent (ASCII) = invariant des icônes qui marchent :
    # label == Workspace Sidebar.name == Workspace.name. L'accent à l'AFFICHAGE
    # vient de la traduction __(label) (fr.csv) ; en prod (français) ça affiche
    # « Direction Générale » etc. Un accent dans le label imposerait un accent
    # dans le name du sidebar (clé du boot) ET dans la route slug() -> 404.
    {"label": "Direction Generale", "link_to": "Direction Generale", "sidebar": "Direction Generale", "icon": "🏛️", "app": "kya_hr", "idx": 10},
    {"label": "Gestion Equipe", "link_to": "Gestion Equipe", "sidebar": "Gestion Equipe", "icon": "🤝", "app": "kya_services", "idx": 20},
    {"label": "Espace RH", "link_to": "Espace RH", "icon": "👥", "app": "kya_hr", "idx": 11},
    {"label": "Espace Achats", "link_to": "Espace Achats", "icon": "🛒", "app": "kya_hr", "idx": 12},
    {"label": "Espace Stock", "link_to": "Espace Stock", "icon": "📦", "app": "kya_hr", "idx": 13},
    {"label": "Espace Comptabilite", "link_to": "Espace Comptabilite", "icon": "💰", "app": "kya_hr", "idx": 14},
    {"label": "Logistique", "link_to": "Logistique", "icon": "🚚", "app": "kya_hr", "idx": 15},
    {"label": "Espace Employes", "link_to": "Espace Employes", "icon": "👤", "app": "kya_hr", "idx": 16},
    {"label": "Espace Stagiaires", "link_to": "Espace Stagiaires", "icon": "🎓", "app": "kya_hr", "idx": 17},
    # "Inventaire & Sorties Matériel" retiré : redondant avec Espace Stock + le
    # libellé avec '&' cassait la route (404). Le workspace est masqué (cf.
    # fix_workspace_anomalies). Inventaire/PV sortie restent dans Espace Stock.
    {"label": "KYA Services", "link_to": "KYA Services", "icon": "📋", "app": "kya_services", "idx": 19},
]

RESTRICTED_LAYOUT_ROLES = {
    "Direction Generale": ["Directeur Général", "DG", "DGA", "DAAF", "System Manager", "Administrator"],
    "Gestion Equipe": [
        "Chef Equipe", "Chef d'Équipe", "Chef Service", "Responsable Equipe",
        "Supérieur Immédiat", "Directeur Général", "DG", "DGA", "System Manager",
    ],
    "Espace RH": ["HR Manager", "HR User", "Responsable RH", "Directeur Général", "System Manager"],
    "Espace Achats": [
        "Purchase Manager",
        "Purchase User",
        "Responsable Achats",
        "Responsable Comptable",
        "Directeur Général",
        "DG",
        "DGA",
        "Auditeur Interne",
        "System Manager",
    ],
    "Espace Stock": [
        "Stock Manager",
        "Stock User",
        "Chargé des Stocks",
        "Responsable Comptable",
        "Auditeur Interne",
        "Directeur Général",
        "DG",
        "DGA",
        "System Manager",
    ],
    "Espace Comptabilite": [
        "Accounts Manager",
        "Accounts User",
        "Responsable Comptable",
        "Auditeur Interne",
        "Directeur Général",
        "DG",
        "DGA",
        "System Manager",
    ],
    "Logistique": [
        "Fleet Manager",
        "Responsable Logistique",
        "Driver",
        "Responsable Comptable",
        "Directeur Général",
        "DG",
        "DGA",
        "System Manager",
    ],
    "Inventaire & Sorties Matériel": [
        "Stock Manager",
        "Stock User",
        "Chargé des Stocks",
        "Responsable Achats",
        "Auditeur Interne",
        "Responsable Comptable",
        "Directeur Général",
        "DG",
        "DGA",
        "System Manager",
    ],
    # Espace Employés contient Mon Espace + raccourcis formulaires de base.
    # Accessible à TOUS les comptes liés à un employé actif : rôle Employee
    # est le rôle par défaut HRMS. Les rôles métier élargissent simplement
    # la portée (gestion RH, stock, achats, direction).
    "Espace Employes": [
        "Employee",          # ← tout employé KYA (CDI/CDD/Stage/Prestataire)
        "Stagiaire",
        "Chef Service",
        "Supérieur Immédiat",
        "Chef Equipe",
        "Responsable RH",
        "HR User",
        "HR Manager",
        "Directeur Général",
        "DG",
        "DGA",
        "Responsable Comptable",
        "Auditeur Interne",
        "Stock User",
        "Purchase User",
        "Responsable Achats",
        "Chargé des Stocks",
        "KYA Destinataire Notif",
        "System Manager",
    ],
    "Espace Stagiaires": [
        # Espace de GESTION (décision RH) : le stagiaire n'y accède pas, il
        # utilise « Mon Espace » (self-service). Donc PAS de rôle "Stagiaire".
        "Maître de Stage",
        "Responsable des Stagiaires",
        "Responsable RH",
        "HR User",
        "HR Manager",
        "Directeur Général",
        "DG",
        "System Manager",
    ],
    "KYA Services": ["KYA Survey Admin", "System Manager"],
}

# ── Icônes NATIVES ERPNext : mêmes restrictions que les workspaces (sinon, une
# fois chaque user doté d'un layout, elles fuiraient — ex. le Comptable verrait
# « Accounting / Buying / Stock »). On miroir la matrice par rôle métier ;
# l'admin pur reste System Manager. Le DG (Directeur Général/DG/DGA) voit tout.
_DIR = ["Directeur Général", "DG", "DGA", "System Manager"]
_NATIVE_LAYOUT_ROLES = {
    # Finance / comptabilité
    "Accounting": ["Accounts Manager", "Accounts User", "Comptable", "Caissier", "DFC", "DAAF"] + _DIR,
    "Accounts Setup": ["Accounts Manager", "DFC", "DAAF"] + _DIR,
    "Invoicing": ["Accounts Manager", "Accounts User", "Comptable", "Caissier"] + _DIR,
    "Financial Reports": ["Accounts Manager", "Comptable", "DFC", "DAAF"] + _DIR,
    "Expenses": ["Accounts Manager", "Accounts User", "Expense Approver"] + _DIR,
    "Payments": ["Accounts Manager", "Accounts User", "Comptable"] + _DIR,
    "Banking": ["Accounts Manager", "DFC", "DAAF"] + _DIR,
    "Budget": ["Accounts Manager", "DFC", "DAAF"] + _DIR,
    "Taxes": ["Accounts Manager", "DFC", "DAAF"] + _DIR,
    "Assets": ["Accounts Manager"] + _DIR,
    # Achats
    "Buying": ["Purchase Manager", "Purchase User", "Responsable Achats"] + _DIR,
    # Stock
    "Stock": ["Stock Manager", "Stock User", "Chargé des Stocks", "Responsable Stock", "Magasinier"] + _DIR,
    # Commercial
    "Selling": ["Sales User", "Sales Manager", "Sales Master Manager"] + _DIR,
    # RH (espaces HRMS natifs)
    "Frappe HR": ["HR Manager", "HR User", "Responsable RH"] + _DIR,
    "HR Setup": ["HR Manager", "Responsable RH"] + _DIR,
    "Recruitment": ["HR Manager", "Responsable RH"] + _DIR,
    "Tenure": ["HR Manager", "Responsable RH"] + _DIR,
    "Shift & Attendance": ["HR Manager", "Responsable RH"] + _DIR,
    "Leaves": ["HR Manager", "Responsable RH"] + _DIR,
    "Performance": ["HR Manager", "Responsable RH"] + _DIR,
    "Payroll": ["HR Manager", "Responsable RH", "Accounts Manager"] + _DIR,
    "Tax & Benefits": ["HR Manager", "Responsable RH", "Accounts Manager"] + _DIR,
    # Technique (espaces DST de l'app servicestechniques)
    "Services Techniques": ["DST - Directeur Technique", "DST - Chef Equipe Installation",
                            "DST - Chef Equipe Audit Interne", "DST - Chef Equipe Offres et Formations",
                            "DST - Responsable Logistique"] + _DIR,
    "Manufacturing": ["Manufacturing Manager", "Manufacturing User"] + _DIR,
    "Subcontracting": ["Manufacturing Manager"] + _DIR,
    "Quality": ["Quality Manager"] + _DIR,
    "Projects": ["Projects Manager", "Projects User"] + _DIR,
    # Administration pure / framework → System Manager uniquement
    "ERPNext Settings": ["System Manager"],
    "Framework": ["System Manager"],
    "Organization": ["System Manager"],
    "System": ["System Manager"],
    "Users": ["System Manager"],
    "Integrations": ["System Manager"],
    "Build": ["System Manager"],
    "Automation": ["System Manager"],
    "Email": ["System Manager"],
    "Printing": ["System Manager"],
    "Data": ["System Manager"],
    "Website": ["System Manager", "Website Manager"],
    "Subscription": ["System Manager"],
    "Share Management": ["System Manager"],
}
# Les espaces DST individuels → leur chef + Direction + SM
for _dst in ["DST DIrecteur Technique", "DST Installation", "DST Audit Interne",
             "DST bureau externe", "DST Offres et Formations"]:
    _NATIVE_LAYOUT_ROLES[_dst] = ["DST - Directeur Technique", "DST - Chef Equipe Installation",
                                  "DST - Chef Equipe Audit Interne", "DST - Chef Equipe Offres et Formations",
                                  "DST - Responsable Logistique"] + _DIR
RESTRICTED_LAYOUT_ROLES.update(_NATIVE_LAYOUT_ROLES)

LAYOUT_FIELDS = [
    "label",
    "bg_color",
    "link",
    "link_type",
    "app",
    "icon_type",
    "parent_icon",
    "icon",
    "link_to",
    "idx",
    "standard",
    "logo_url",
    "hidden",
    "name",
    "restrict_removal",
    "icon_image",
]


def _get_icon_doc(label: str):
    name = frappe.db.get_value(
        "Desktop Icon",
        {"label": label, "link_type": "Workspace Sidebar"},
        "name",
    )
    if name:
        return frappe.get_doc("Desktop Icon", name)
    return frappe.new_doc("Desktop Icon")


def _serialize_icon(icon: dict) -> dict:
    item = {field: icon.get(field) for field in LAYOUT_FIELDS}
    item["child_icons"] = []
    return item


def _sync_workspace_icon(config: dict) -> bool:
    if not frappe.db.exists("Workspace", config["link_to"]):
        return False

    workspace_title = frappe.db.get_value("Workspace", config["link_to"], "title")
    workspace_label = frappe.db.get_value("Workspace", config["link_to"], "label")

    sidebar_name = frappe.db.get_value(
        "Workspace Sidebar",
        {"title": config.get("sidebar") or config["label"]},
        "name",
    ) or frappe.db.get_value(
        "Workspace Sidebar",
        {"title": config["label"]},
        "name",
    ) or frappe.db.get_value(
        "Workspace Sidebar",
        {"title": config["link_to"]},
        "name",
    ) or frappe.db.get_value(
        "Workspace Sidebar",
        {"title": workspace_title},
        "name",
    ) or frappe.db.get_value(
        "Workspace Sidebar",
        {"title": workspace_label},
        "name",
    ) or config["link_to"]

    icon = _get_icon_doc(config["label"])
    previous = {
        "label": icon.get("label"),
        "link_type": icon.get("link_type"),
        "icon_type": icon.get("icon_type"),
        "link_to": icon.get("link_to"),
        "icon": icon.get("icon"),
        "app": icon.get("app"),
        "idx": icon.get("idx"),
        "hidden": icon.get("hidden"),
        "parent_icon": icon.get("parent_icon"),
        "standard": icon.get("standard"),
    }

    icon.label = config["label"]
    icon.link_type = "Workspace Sidebar"
    icon.icon_type = "Link"
    icon.link_to = sidebar_name
    icon.icon = config["icon"]
    icon.app = config.get("app") or "kya_hr"
    icon.idx = config["idx"]
    icon.hidden = 0
    icon.parent_icon = None
    icon.standard = 1

    current = {
        "label": icon.get("label"),
        "link_type": icon.get("link_type"),
        "icon_type": icon.get("icon_type"),
        "link_to": icon.get("link_to"),
        "icon": icon.get("icon"),
        "app": icon.get("app"),
        "idx": icon.get("idx"),
        "hidden": icon.get("hidden"),
        "parent_icon": icon.get("parent_icon"),
        "standard": icon.get("standard"),
    }

    if icon.is_new() or previous != current:
        icon.flags.ignore_links = True
        icon.save(ignore_permissions=True)
        changed = True
    else:
        changed = False

    duplicate_values = {
        "link_type": "Workspace Sidebar",
        "icon_type": "Link",
        "link_to": sidebar_name,
        "icon": config["icon"],
        "app": config.get("app") or "kya_hr",
        "idx": config["idx"],
        "hidden": 0,
        "parent_icon": None,
        "standard": 1,
    }
    for duplicate in frappe.get_all("Desktop Icon", filters={"label": config["label"]}, pluck="name"):
        current_values = frappe.db.get_value("Desktop Icon", duplicate, list(duplicate_values), as_dict=True)
        updates = {key: value for key, value in duplicate_values.items() if current_values.get(key) != value}
        if updates:
            frappe.db.set_value("Desktop Icon", duplicate, updates, update_modified=False)
            changed = True

    return changed


def _build_default_layout() -> list[dict]:
    icons = frappe.get_all(
        "Desktop Icon",
        fields=LAYOUT_FIELDS,
        filters={"standard": 1, "hidden": 0},
        order_by="idx asc, creation asc",
    )
    icon_map = {icon["label"]: _serialize_icon(icon) for icon in icons}
    layout = []

    for icon in icons:
        item = icon_map[icon["label"]]
        parent = icon.get("parent_icon")
        if parent and parent in icon_map:
            item["in_folder"] = True
            icon_map[parent]["child_icons"].append(item)
        else:
            layout.append(item)

    return layout


def _norm_label(value) -> str:
    """Comparaison SANS accents ni casse. MariaDB (collation *_ci) considère
    « Gestion Equipe » == « Gestion Équipe » mais Python non : le get_value SQL
    retrouvait l'icône (label accentué en base) tandis que le dédoublonnage
    Python ne la reconnaissait pas dans le layout -> une tuile de PLUS était
    appendée à chaque migrate (constaté en prod : ~24 tuiles « Gestion Équipe »
    dans le Desktop Layout d'Administrator)."""
    import unicodedata
    s = unicodedata.normalize("NFD", str(value or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()


def _sync_layout_doc(layout_doc) -> bool:
    layout = json.loads(layout_doc.layout or "[]")
    changed = False

    for config in WORKSPACE_ICONS:
        icon = frappe.db.get_value(
            "Desktop Icon",
            {"label": config["label"], "link_type": "Workspace Sidebar"},
            LAYOUT_FIELDS,
            as_dict=True,
        )
        if not icon:
            continue

        serialized = _serialize_icon(icon)
        wanted = _norm_label(config["label"])
        existing_items = [item for item in layout if _norm_label(item.get("label")) == wanted]
        if existing_items:
            keep = existing_items[0]
            for field in LAYOUT_FIELDS:
                if keep.get(field) != serialized.get(field):
                    keep[field] = serialized.get(field)
                    changed = True
            keep["child_icons"] = keep.get("child_icons") or []
            for duplicate in existing_items[1:]:
                layout.remove(duplicate)
                changed = True
        else:
            layout.append(serialized)
            changed = True

    layout.sort(key=lambda item: (item.get("idx") or 0, item.get("label") or ""))

    if changed:
        layout_doc.layout = json.dumps(layout, ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)
        return True

    return False


def _sync_all_desktop_layouts() -> bool:
    changed = False

    for row in frappe.get_all("Desktop Layout", fields=["name", "user"]):
        # Layout orphelin : le User a été supprimé/renommé. Personne ne le charge
        # et son `user` (Link) casse le save() -> LinkValidationError qui ferait
        # ÉCHOUER after_migrate. On purge silencieusement plutôt que crasher.
        owner = row.get("user") or row.name
        if owner and owner != "Administrator" and not frappe.db.exists("User", owner):
            frappe.delete_doc("Desktop Layout", row.name,
                              ignore_permissions=True, force=True, delete_permanently=True)
            changed = True
            continue
        try:
            layout_doc = frappe.get_doc("Desktop Layout", row.name)
            changed = _sync_layout_doc(layout_doc) or changed
        except Exception:
            # Un layout corrompu ne doit jamais bloquer la migration globale.
            frappe.log_error(frappe.get_traceback(), f"desktop_layout sync: {row.name}")

    # Ensure Administrator has a layout in fresh sites, then sync it too.
    if not frappe.db.exists("Desktop Layout", "Administrator"):
        layout_doc = frappe.new_doc("Desktop Layout")
        layout_doc.user = "Administrator"
        layout_doc.owner = "Administrator"
        layout_doc.layout = json.dumps(_build_default_layout(), ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)
        changed = True

    admin_doc = frappe.get_doc("Desktop Layout", "Administrator")
    changed = _sync_layout_doc(admin_doc) or changed

    return changed


def _user_has_any_role(user: str, allowed_roles: list[str]) -> bool:
    if user == "Administrator":
        return True
    roles = set(frappe.get_roles(user) or [])
    return bool(roles.intersection(allowed_roles))


def _prune_restricted_layout_doc(layout_doc) -> bool:
    layout = json.loads(layout_doc.layout or "[]")
    user = layout_doc.get("user") or layout_doc.get("owner")
    changed = False

    def allowed(item):
        label = item.get("label")
        roles = RESTRICTED_LAYOUT_ROLES.get(label)
        return not roles or _user_has_any_role(user, roles)

    pruned = []
    for item in layout:
        child_icons = item.get("child_icons") or []
        filtered_children = [child for child in child_icons if allowed(child)]
        if len(filtered_children) != len(child_icons):
            item["child_icons"] = filtered_children
            changed = True
        if allowed(item):
            pruned.append(item)
        else:
            changed = True

    if changed:
        layout_doc.layout = json.dumps(pruned, ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)

    return changed


def _managed_label_by_target() -> dict:
    """Cible (sidebar/workspace) -> libellé géré (accentué)."""
    m = {}
    for cfg in WORKSPACE_ICONS:
        m[cfg.get("sidebar") or cfg["link_to"]] = cfg["label"]
        m[cfg["link_to"]] = cfg["label"]
    return m


def _dedupe_layout_doc(layout_doc) -> bool:
    """Supprime les icônes en double DANS une Desktop Layout.

    Bug terrain : la même icône (ex. « Direction Generale ») se cumulait des
    dizaines de fois car la déduplication se faisait par LABEL et les entrées
    héritées portaient un libellé non accentué (« Direction Generale ») là où
    l'icône gérée est « Direction Générale ». On déduplique donc par
    (link_type, link_to) — l'identité stable du workspace — et on normalise au
    passage le libellé vers la version accentuée gérée.
    """
    layout = json.loads(layout_doc.layout or "[]")
    label_map = _managed_label_by_target()
    seen = set()
    out = []
    changed = False
    for item in layout:
        lt = item.get("link_type") or ""
        target = item.get("link_to") or item.get("label") or ""
        if lt == "Workspace Sidebar" and target in label_map and item.get("label") != label_map[target]:
            item["label"] = label_map[target]
            changed = True
        key = (lt, target)
        if key in seen:
            changed = True  # doublon -> on jette
            continue
        seen.add(key)
        out.append(item)
    if changed:
        layout_doc.layout = json.dumps(out, ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)
    return changed


def _dedupe_all_layouts() -> bool:
    changed = False
    for row in frappe.get_all("Desktop Layout", fields=["name"]):
        try:
            changed = _dedupe_layout_doc(frappe.get_doc("Desktop Layout", row.name)) or changed
        except Exception:
            try:
                frappe.log_error(frappe.get_traceback(), "desktop_icons: dedupe layout")
            except Exception:
                pass
    return changed


def _ensure_layouts_for_enabled_users() -> int:
    """Crée un Desktop Layout (depuis le défaut) pour chaque user actif qui n'en
    a pas. SANS ça, un user sans layout perso retombe sur le layout par DÉFAUT
    (toutes les icônes, NON élaguées) → fuite : le Comptable voyait l'icône
    « Direction Generale » etc. Une fois le layout créé, `_prune_restricted_*`
    l'élague selon les rôles. Idempotent (ne recrée pas un layout existant)."""
    created = 0
    default_layout = json.dumps(_build_default_layout(), ensure_ascii=False)
    for user in frappe.get_all("User", filters={"enabled": 1,
                               "user_type": "System User"}, pluck="name"):
        if user in ("Guest",):
            continue
        if frappe.db.exists("Desktop Layout", user):
            continue
        try:
            doc = frappe.new_doc("Desktop Layout")
            doc.user = user
            doc.owner = user
            doc.layout = default_layout
            doc.flags.ignore_links = True
            doc.insert(ignore_permissions=True)
            created += 1
        except Exception:
            try:
                frappe.log_error(frappe.get_traceback(),
                                 f"desktop_icons: create layout {user}")
            except Exception:
                pass
    return created


def _prune_restricted_desktop_layouts() -> bool:
    changed = False
    for row in frappe.get_all("Desktop Layout", fields=["name"]):
        layout_doc = frappe.get_doc("Desktop Layout", row.name)
        changed = _prune_restricted_layout_doc(layout_doc) or changed
    return changed


def _sync_administrator_layout() -> bool:
    if not frappe.db.exists("Desktop Layout", "Administrator"):
        layout_doc = frappe.new_doc("Desktop Layout")
        layout_doc.user = "Administrator"
        layout_doc.owner = "Administrator"
        layout_doc.layout = json.dumps(_build_default_layout(), ensure_ascii=False)
        layout_doc.save(ignore_permissions=True)
        return True

    admin_doc = frappe.get_doc("Desktop Layout", "Administrator")
    return _sync_layout_doc(admin_doc)


@frappe.whitelist()
def _ascii(value: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", str(value or ""))
    return "".join(c for c in s if not unicodedata.combining(c))


def _heal_accented_workspaces():
    """Invariant des routes bureau : Workspace.name == label/title == Workspace
    Sidebar.name, TOUS en ASCII (l'accent d'affichage vient de fr.csv, comme
    « Direction Générale »). Un workspace créé avec un label/title ACCENTÉ (ex.
    « Espace Comptabilité ») engendre un Workspace Sidebar accentué → route slug
    accentuée introuvable → 404 « Page introuvable ». On réaligne en ASCII.

    Idempotent : ne touche que ce qui est encore accentué. MariaDB étant
    accent-insensible (utf8mb4_general_ci), on cible la forme accentuée par
    `COLLATE utf8mb4_bin` (sinon un DELETE/UPDATE frapperait aussi la forme ASCII).
    """
    has_sidebar = frappe.db.has_table("Workspace Sidebar")
    for cfg in WORKSPACE_ICONS:
        ws = cfg["link_to"]                       # nom ASCII = identité
        if ws != _ascii(ws) or not frappe.db.exists("Workspace", ws):
            continue
        try:
            # 1) label/title du workspace en ASCII (== name)
            cur = frappe.db.get_value("Workspace", ws, ["label", "title"], as_dict=True) or {}
            upd = {}
            if cur.get("label") and cur["label"] != ws:
                upd["label"] = ws
            if cur.get("title") and cur["title"] != ws:
                upd["title"] = ws
            if upd:
                frappe.db.set_value("Workspace", ws, upd, update_modified=False)
            # 2) Workspace Sidebar : renommer la forme accentuée en ASCII (ou la
            #    supprimer si l'ASCII existe déjà).
            if has_sidebar:
                names = frappe.db.sql(
                    "SELECT name FROM `tabWorkspace Sidebar` WHERE name = %s", (ws,), pluck=True)
                ascii_present = any(n == ws for n in names)
                for n in [x for x in names if x != ws]:   # formes accentuées
                    if ascii_present:
                        frappe.db.sql(
                            "DELETE FROM `tabWorkspace Sidebar` WHERE name COLLATE utf8mb4_bin = %s", (n,))
                    else:
                        frappe.db.sql(
                            "UPDATE `tabWorkspace Sidebar` SET name=%s, title=%s "
                            "WHERE name COLLATE utf8mb4_bin = %s", (ws, ws, n))
                        ascii_present = True
            # 3) Desktop Icon accentué → ASCII (label + link_to)
            for r in frappe.db.sql(
                    "SELECT name, label FROM `tabDesktop Icon` WHERE label = %s", (ws,), as_dict=True):
                if r.label != ws:
                    frappe.db.set_value(
                        "Desktop Icon", r.name, {"label": ws, "link_to": ws}, update_modified=False)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"desktop_icons: heal {ws}")


def execute():
    """Sync KYA Desktop Icons. Defensive: never raise to avoid breaking install/migrate."""
    # Skip if Desktop Icon table doesn't exist (fresh install before frappe.desk migration)
    if not frappe.db.has_table("Desktop Icon") or not frappe.db.has_table("Desktop Layout"):
        print("[kya_hr.desktop_icons] Desktop Icon/Layout tables missing, skipping.")
        return {"skipped": True}

    # Répare d'abord l'invariant ASCII (sinon l'icône se recale sur un sidebar
    # accentué → 404). Doit précéder la synchro des icônes.
    _heal_accented_workspaces()

    changed = False
    errors = []

    for config in WORKSPACE_ICONS:
        try:
            changed = _sync_workspace_icon(config) or changed
        except Exception as e:
            errors.append(f"{config['label']}: {e}")

    try:
        # Re-sync TOUTES les Desktop Layout (pas seulement Administrator) : ajoute
        # les icônes standard manquantes à chaque utilisateur, PUIS élague par rôle.
        # Sinon une icône autrefois élaguée (ex. Direction pour un compte "DG")
        # n'était jamais re-ajoutée après correction des rôles.
        changed = _sync_all_desktop_layouts() or changed
        # Donne un layout perso à CHAQUE user actif (sinon défaut non-élagué = fuite)
        created_layouts = _ensure_layouts_for_enabled_users()
        if created_layouts:
            changed = True
        changed = _dedupe_all_layouts() or changed        # collapse les doublons hérités
        changed = _prune_restricted_desktop_layouts() or changed
    except Exception as e:
        errors.append(f"layouts: {e}")

    try:
        for user in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
            clear_desktop_icons_cache(user)
        frappe.clear_cache()
    except Exception as e:
        errors.append(f"clear_cache: {e}")

    if errors:
        print(f"[kya_hr.desktop_icons] Warnings: {errors}")

    return {
        "changed": changed,
        "labels": [config["label"] for config in WORKSPACE_ICONS],
        "errors": errors,
    }
