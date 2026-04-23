"""
cleanup_icons.py
- Supprime les Desktop Icons pointant vers des pages KYA invalides
- Supprime les copies for_user (personnalisees par utilisateur) des workspaces KYA
  car elles contiennent l'ancien contenu et bloquent la mise a jour
- Affiche l'etat des workspace links en DB
"""
import frappe


def execute():
    print("=== CLEANUP ICONS & FOR_USER WORKSPACES ===\n")

    # -----------------------------------------------------------------
    # 1. Desktop Icons invalides (kya-evaluation-critere, etc.)
    # -----------------------------------------------------------------
    try:
        # Chercher les desktop icons avec des liens vers DocTypes KYA invalides
        invalid_patterns = [
            "kya-evaluation-critere",
            "kya-form-question",
            "kya-form-answer",
        ]

        # Frappe v16 - Desktop Icon columns vary; use only safe ones
        all_desk_icons = frappe.db.get_all(
            "Desktop Icon",
            filters=[["link", "like", "%kya%"]],
            fields=["name", "label", "link", "for_user"],
        )

        deleted_icons = 0
        for icon in all_desk_icons:
            link_lower = (icon.link or "").lower()
            is_invalid = any(p in link_lower for p in invalid_patterns)
            print(f"  Icon: [{icon.name}] {icon.label!r} link={icon.link!r} for_user={icon.for_user!r}")
            if is_invalid:
                frappe.db.delete("Desktop Icon", {"name": icon.name})
                deleted_icons += 1
                print(f"    -> DELETED (invalid link)")

        print(f"\n  Desktop Icons KYA trouves: {len(all_desk_icons)}, supprimes: {deleted_icons}")

    except Exception as e:
        print(f"  Desktop Icon error: {e}")

    # -----------------------------------------------------------------
    # 2. Workspace copies for_user (bloquent la mise a jour)
    # Quand un utilisateur visite un workspace, Frappe cree une copie
    # personnalisee (for_user != NULL). Cette copie stocke l'ANCIENNE
    # version du contenu et ne se met JAMAIS a jour automatiquement.
    # -----------------------------------------------------------------
    kya_workspaces = [
        "Espace Stagiaires",
        "KYA Services",
        "Cong\u00e9s & Permissions",
        "Achats & Approvisionnement",
        "Stock & Logistique",
    ]

    total_user_copies = 0
    for ws in kya_workspaces:
        copies = frappe.db.get_all(
            "Workspace",
            filters=[["name", "like", f"%{ws}%"], ["for_user", "!=", ""]],
            fields=["name", "for_user"],
        )
        for c in copies:
            frappe.db.delete("Workspace", {"name": c.name})
            print(f"  Deleted for_user copy: {c.name!r} (user={c.for_user!r})")
            total_user_copies += 1

    print(f"\n  for_user workspace copies supprimees: {total_user_copies}")

    # -----------------------------------------------------------------
    # 3. Workspace Links - verifier etat final
    # -----------------------------------------------------------------
    print("\n=== ETAT FINAL WORKSPACE LINKS ===")
    for ws in ["Espace Stagiaires", "KYA Services", "Buying", "Stock"]:
        links = frappe.db.get_all(
            "Workspace Link",
            filters={"parent": ws},
            fields=["label", "link_to", "type"],
            order_by="idx",
        )
        print(f"\n  [{ws}] {len(links)} links:")
        for lk in links:
            print(f"    [{lk.type}] {lk.label!r} -> {lk.link_to!r}")

    # -----------------------------------------------------------------
    # 4. Verifier is_hidden des workspaces
    # -----------------------------------------------------------------
    print("\n=== IS_HIDDEN STATUS ===")
    ws_status = frappe.db.get_all(
        "Workspace",
        filters=[["name", "in", ["Achats & Approvisionnement", "Stock & Logistique", "Buying", "Stock", "Espace Stagiaires", "KYA Services"]]],
        fields=["name", "is_hidden", "parent_page"],
    )
    for w in ws_status:
        print(f"  {w.name}: hidden={w.is_hidden} parent={w.parent_page!r}")

    frappe.db.commit()
    print("\n=== DONE ===")
    print("MAINTENANT: Ouvrir Chrome en mode PRIVE (Ctrl+Shift+N) sur http://localhost:8086")
    print("=> le localStorage sera vide, les changements seront visibles")
