"""
KYA Energy — Setup Branding
Applique le logo KYA sur la page de login et les settings Website/System.
À exécuter via : bench execute kya_hr.setup_branding.execute
Ou via after_migrate (appelé automatiquement).
"""
import frappe

KYA_LOGO_URL = "/assets/kya_hr/images/kya_logo.png"
KYA_APP_NAME = "KYA-Energy Group"


def execute():
    """Configure le logo KYA dans System Settings et Website Settings."""
    # ── 1. System Settings ────────────────────────────────────────
    try:
        ss = frappe.get_single("System Settings")
        changed = False
        if not ss.app_name or ss.app_name in ("ERPNext", "Frappe"):
            ss.app_name = KYA_APP_NAME
            changed = True
        if changed:
            ss.flags.ignore_permissions = True
            ss.save()
            frappe.db.commit()
            print(f"[KYA Branding] System Settings.app_name → {KYA_APP_NAME}")
    except Exception as e:
        print(f"[KYA Branding] System Settings warning: {e}")

    # ── 2. Website Settings (logo sur la page /login) ─────────────
    try:
        ws = frappe.get_single("Website Settings")
        changed = False
        # Force update si l'URL est externe (cassée) ou vide
        if not ws.app_logo or ws.app_logo.startswith("http"):
            ws.app_logo = KYA_LOGO_URL
            changed = True
        if not ws.favicon or ws.favicon.startswith("http"):
            ws.favicon = KYA_LOGO_URL
            changed = True
        if not ws.copyright:
            ws.copyright = "KYA-Energy Group"
            changed = True
        if not ws.app_name or ws.app_name in ("Frappe", "ERPNext", "frappe"):
            ws.app_name = KYA_APP_NAME
            changed = True
        if changed:
            ws.flags.ignore_permissions = True
            ws.save()
            frappe.db.commit()
            print(f"[KYA Branding] Website Settings.app_logo → {KYA_LOGO_URL}")
    except Exception as e:
        print(f"[KYA Branding] Website Settings warning: {e}")
