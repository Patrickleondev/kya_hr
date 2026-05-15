"""Restaure le shortcut 'Demandes de Congé' au format DocType → Leave Application.

Sur certaines instances historiques, ce shortcut a été créé avec
`type=URL, url=/demande-conge/new` (clic = redirection directe vers le web form),
au lieu du `type=DocType, link_to=Leave Application` attendu (clic = ouvre la
liste Desk, puis bouton "+ Add" est intercepté par kya_webform.js pour rediriger
vers le web form — comportement cohérent avec Permission Sortie Employé/Stagiaire).

Idempotent. Ne touche que le shortcut au label exact "Demandes de Congé"
sous le workspace "Espace RH".
"""

import frappe


def execute():
    if not frappe.db.has_table("Workspace Shortcut"):
        return

    rows = frappe.db.sql(
        """
        SELECT name, type, link_to, url
        FROM `tabWorkspace Shortcut`
        WHERE parent = 'Espace RH' AND label = 'Demandes de Congé'
        """,
        as_dict=True,
    )
    if not rows:
        print("[fix_conge_shortcut_type] shortcut introuvable, skipped.")
        return

    fixed = 0
    for r in rows:
        if r.type == "DocType" and r.link_to == "Leave Application" and not r.url:
            continue
        frappe.db.sql(
            """
            UPDATE `tabWorkspace Shortcut`
            SET type='DocType', link_to='Leave Application', url=NULL
            WHERE name = %s
            """,
            (r.name,),
        )
        fixed += 1

    frappe.db.commit()
    print(f"[fix_conge_shortcut_type] {fixed} shortcut(s) corrigé(s) sur {len(rows)} trouvé(s).")
