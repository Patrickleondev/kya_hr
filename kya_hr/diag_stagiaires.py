import frappe


def execute():
    # Workspaces avec 'tagi' ou 'Stagi' dans le nom
    ws_list = frappe.db.sql(
        "SELECT name, module, is_standard, `public`, allow_guest FROM tabWorkspace "
        "WHERE name LIKE '%tagi%' OR name LIKE '%Stagi%'",
        as_dict=True,
    )
    print("\n=== WORKSPACES STAGIAIRES ===")
    for w in ws_list:
        print(f"  name={w.name!r} module={w.module!r} public={w.public} is_standard={w.is_standard}")

    # Roles assignés à chaque workspace
    for w in ws_list:
        roles = frappe.db.sql(
            "SELECT role FROM `tabHas Role` WHERE parent=%s AND parenttype='Workspace'",
            w.name,
            as_dict=True,
        )
        print(f"  [{w.name}] roles: {[r.role for r in roles]}")

    # DocTypes du module KYA HR
    print("\n=== DOCTYPE KYA HR (is_virtual=0) ===")
    dts = frappe.db.sql(
        "SELECT name, module FROM tabDocType WHERE module LIKE '%KYA%' OR module LIKE '%Stagiaire%'",
        as_dict=True,
    )
    for d in dts:
        print(f"  {d.name!r} [{d.module}]")

    # Roles existants
    print("\n=== ROLES STAGIAIRE ===")
    r_list = frappe.db.sql(
        "SELECT name FROM tabRole WHERE name LIKE '%tagi%' OR name LIKE '%Stagi%'",
        as_dict=True,
    )
    for r in r_list:
        print(f"  {r.name!r}")

    # Users avec role stagiaire
    print("\n=== USERS ROLE STAGIAIRE ===")
    users = frappe.db.sql(
        "SELECT ur.parent as user, ur.role FROM `tabHas Role` ur "
        "WHERE ur.role LIKE '%tagi%' OR ur.role LIKE '%Stagi%' LIMIT 10",
        as_dict=True,
    )
    for u in users:
        print(f"  user={u.user!r} role={u.role!r}")

    # Vérifier les permissions doctype PSE Stagiaire
    print("\n=== PERMS Permission Sortie Stagiaire ===")
    perms = frappe.db.sql(
        "SELECT role, `read`, `write`, `create` FROM tabDocPerm "
        "WHERE parent='Permission Sortie Stagiaire'",
        as_dict=True,
    )
    for p in perms:
        print(f"  role={p.role!r} read={p.read} write={p.write} create={p.create}")

    print("\n=== DONE ===")
