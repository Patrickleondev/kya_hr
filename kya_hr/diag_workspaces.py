"""Diagnostic des workspaces : sous-icones manquantes + labels corrompus.

Sert a comprendre pourquoi :
- Frappe HR / Comptabilite n'affichent pas leurs sous-icones (icone existe
  mais cliquer dessus donne page vide ou partiellement vide)
- Certains labels affichent du mojibake ('ehetuers' au lieu de 'Acheteurs')

Lancer en console :
    bench --site frontend execute kya_hr.diag_workspaces.execute

Aucune modification - lecture seule. Affiche un rapport texte.
"""
from __future__ import annotations

import json
import re

import frappe


# Caracteres typiques de mojibake UTF-8 vu comme CP1252/CP437
MOJIBAKE_PATTERNS = [
    re.compile(r"[ÃÂ]{1}[\x80-\xBF]"),       # é -> Ã©, ç -> Ã§
    re.compile(r"[├└┌┐┘┴┬┤┼─│]"),              # CP437 box drawing
    re.compile(r"╔ô|≡fô|╝ƒ|╪[a-z]"),          # emoji mojibake
    re.compile(r"\?{3,}"),                     # 3+ ? consecutifs = chars perdus
]


def _has_mojibake(text: str) -> bool:
    if not text:
        return False
    for pat in MOJIBAKE_PATTERNS:
        if pat.search(text):
            return True
    return False


def execute():
    print("=" * 70)
    print("DIAGNOSTIC WORKSPACES KYA + STANDARD")
    print("=" * 70)

    critical = (
        "Accounting", "HR", "Frappe HR", "Attendance", "Leaves", "Payroll",
        "Stock", "Buying", "Selling", "Manufacturing", "Projects",
        "Espace Employes", "Espace Stagiaires", "Espace RH", "Espace Achats",
        "Espace Stock", "Espace Comptabilité", "Direction Generale",
        "KYA Services", "Gestion Équipe",
    )

    rows = frappe.db.sql("""
        SELECT name, public, hide_custom, restrict_to_domain, parent_page,
               for_user, app, LENGTH(content) AS content_len, content
        FROM tabWorkspace
        WHERE name IN %s
        ORDER BY name
    """, (critical,), as_dict=True) or []

    print(f"\n{len(rows)} workspaces critiques trouves sur {len(critical)} attendus.\n")

    missing = set(critical) - {r["name"] for r in rows}
    if missing:
        print(f"⚠  ABSENT en DB : {sorted(missing)}\n")

    for r in rows:
        print(f"━━━━━━━━━━ {r['name']} ━━━━━━━━━━")
        print(f"  app             : {r['app']}")
        print(f"  public          : {r['public']}")
        print(f"  hide_custom     : {r['hide_custom']}")
        print(f"  restrict_domain : {r['restrict_to_domain']}")
        print(f"  parent_page     : {r['parent_page']}")
        print(f"  content_len     : {r['content_len']}")

        # Verifier le content JSON
        if not r["content"] or r["content_len"] < 50:
            print(f"  ❌ CONTENT VIDE OU TROP COURT  ← raison probable des sous-icones manquantes")

        # Compter les links + shortcuts enfants
        n_links = frappe.db.count("Workspace Link", {"parent": r["name"]})
        n_shortcuts = frappe.db.count("Workspace Shortcut", {"parent": r["name"]})
        n_cards = frappe.db.count("Workspace Number Card", {"parent": r["name"]})
        print(f"  links: {n_links} | shortcuts: {n_shortcuts} | number_cards: {n_cards}")

        if n_links == 0 and n_shortcuts == 0:
            print(f"  ❌ AUCUN LIEN NI RACCOURCI  ← workspace coquille vide")

        # Verifier les labels pour mojibake
        bad_links = frappe.db.sql("""
            SELECT name, label, link_to
            FROM `tabWorkspace Link`
            WHERE parent = %s
        """, (r["name"],), as_dict=True) or []
        for link in bad_links:
            if _has_mojibake(link.get("label") or ""):
                print(f"  🔥 LABEL CORROMPU dans Workspace Link {link['name']!r}: {link['label']!r}")

        bad_shortcuts = frappe.db.sql("""
            SELECT name, label, url, link_to
            FROM `tabWorkspace Shortcut`
            WHERE parent = %s
        """, (r["name"],), as_dict=True) or []
        for sc in bad_shortcuts:
            if _has_mojibake(sc.get("label") or ""):
                print(f"  🔥 LABEL CORROMPU dans Workspace Shortcut {sc['name']!r}: {sc['label']!r}")

    # Scan global mojibake sur tous workspace links/shortcuts
    print("\n" + "=" * 70)
    print("SCAN GLOBAL MOJIBAKE (tous workspaces)")
    print("=" * 70)
    all_bad = []
    for tbl in ("Workspace Link", "Workspace Shortcut"):
        rows = frappe.db.sql(f"""
            SELECT name, parent, label
            FROM `tab{tbl}`
            WHERE label IS NOT NULL AND label != ''
        """, as_dict=True) or []
        for row in rows:
            if _has_mojibake(row["label"]):
                all_bad.append((tbl, row["parent"], row["name"], row["label"]))

    if all_bad:
        print(f"\n{len(all_bad)} labels corrompus detectes :\n")
        for tbl, parent, name, label in all_bad:
            print(f"  [{tbl}] {parent} -> {name!r} : {label!r}")
        print("\nFix manuel via Desk :")
        print("  /app/workspace/<parent> -> editer le link/shortcut concerne")
        print("  Effacer le label corrompu, retaper en UTF-8 propre (depuis VS Code).")
    else:
        print("\n✅ Aucun mojibake detecte dans les labels.")

    # Resume final
    print("\n" + "=" * 70)
    print("RESUME")
    print("=" * 70)
    empty_critical = [r["name"] for r in rows if (r["content_len"] or 0) < 50]
    if empty_critical:
        print(f"⚠  Workspaces critiques VIDES : {empty_critical}")
        print("   Fix : bench --site frontend reload-doc <app> workspace <name>")
        print("   Ex  : bench --site frontend reload-doc hrms workspace hr")
        print("         bench --site frontend reload-doc erpnext workspace accounting")
    print(f"⚠  Labels mojibake : {len(all_bad)}")
    print("=" * 70)
