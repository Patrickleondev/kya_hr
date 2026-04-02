import frappe
import json

def run():
    frappe.set_user("Administrator")
    
    # 1. Check installed apps
    apps = frappe.get_installed_apps()
    print(f"\n=== Installed Apps ===\n  {apps}")
    
    # 2. Check get_workspace_sidebar_items for KYA
    from frappe.desk.doctype.workspace.workspace import get_workspace_sidebar_items
    result = get_workspace_sidebar_items()
    items = result if isinstance(result, list) else []
    kya_items = [p for p in items if (p.get("app") or "").startswith("kya")]
    print(f"\n=== KYA Workspaces in sidebar ({len(kya_items)}) ===")
    for p in kya_items:
        print(f"  app={p.get('app')} | name={p.get('name')} | is_hidden={p.get('is_hidden')} | public={p.get('public')}")
    
    # 3. Check app icons source in Frappe
    # In Frappe v16, home page app tiles come from the apps.json or boot info
    import os, json
    apps_json_path = "/home/frappe/frappe-bench/sites/apps.json"
    if os.path.exists(apps_json_path):
        with open(apps_json_path) as f:
            print(f"\n=== apps.json ===\n  {f.read()}")
    else:
        print(f"\n=== apps.json NOT found at {apps_json_path} ===")
    
    # 4. Check frappe boot info for apps
    print("\n=== Boot info apps ===")
    try:
        boot = frappe.sessions.get_bootinfo()
        boot_apps = boot.get("apps", [])
        print(f"  boot apps: {[a.get('name') if isinstance(a, dict) else a for a in boot_apps] if isinstance(boot_apps, list) else boot_apps}")
    except Exception as e:
        print(f"  boot error: {e}")

    # 5. Check apps.json in workspace
    import os
    for p in [
        "/home/frappe/frappe-bench/sites/apps.json",
        "/home/frappe/frappe-bench/sites/frontend/apps.json",
    ]:
        if os.path.exists(p):
            with open(p) as f:
                print(f"\n=== {p} ===\n  {f.read()}")

    # 6. kya_hr hooks app_icon / app_color
    print("\n=== kya_hr app hooks ===")
    try:
        import kya_hr
        attrs = ["app_name","app_title","app_icon","app_color"]
        import kya_hr.kya_hr.hooks as kh
        for a in attrs:
            print(f"  {a} = {getattr(kh, a, 'N/A')}")
    except Exception as e:
        print(f"  kya_hr hooks error: {e}")
    
    return

def run_old():
    frappe.set_user("Administrator")
    from frappe.desk.doctype.workspace.workspace import get_workspace_sidebar_items
    result = get_workspace_sidebar_items()
    items = result if isinstance(result, list) else result.get("workspaces", result.get("pages", []))
    print(f"\n=== Workspace sidebar items: {len(items)} ===")
    for p in items:
        title = p.get("title") or p.get("label") or p.get("name")
        parent = p.get("parent_page") or "(root)"
        app = p.get("app") or ""
        hidden = p.get("is_hidden")
        pub = p.get("public")
        print(f"  [{str(pub)}/{str(hidden)}] parent={str(parent):20s} | {str(app):12s} | {title}")

    # Module Def icons
    print("\n=== Module Def (kya) ===")
    mods = frappe.db.sql("SELECT name, app_name, icon, color FROM `tabModule Def` WHERE app_name IN ('kya_hr','kya_services') ORDER BY name", as_dict=True)
    for m in mods:
        print(f"  {m.app_name} | {m.name} | icon={m.icon} | color={m.color}")

