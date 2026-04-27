import frappe
from kya_hr.kya_hr.doctype.pv_sortie_materiel.pv_sortie_materiel import PVSortieMateriel

def run():
    print("=" * 50)
    print("Test direct controller PVSortieMateriel")
    print("=" * 50)

    # Test 1: Vérifier si get_doc instancie la bonne classe
    doc = frappe.get_doc({
        "doctype": "PV Sortie Materiel",
        "objet": "Test direct ctrl",
        "date_sortie": frappe.utils.today(),
        "demandeur_nom": "Test",
        "items": [
            {"designation": "Test", "qte_demandee": 5, "qte_reellement_sortie": 5, "valeur_unitaire": 1000},
        ],
    })
    print(f"  Type instance: {type(doc).__name__}")
    print(f"  Class is PVSortieMateriel: {isinstance(doc, PVSortieMateriel)}")
    print(f"  Has _compute_valorisation: {hasattr(doc, '_compute_valorisation')}")
    print(f"  items count: {len(doc.items)}")

    # Force validate
    if hasattr(doc, "_compute_valorisation"):
        doc._compute_valorisation()
        print(f"  After compute → valeur_totale_xof = {doc.valeur_totale_xof}")
    else:
        print("  ✗ Method MISSING — controller not bound")

    # Test app_hooks visibility
    from frappe.model.base_document import get_controller
    cls = get_controller("PV Sortie Materiel")
    print(f"  get_controller returns: {cls.__module__}.{cls.__name__}")

    # Diagnose import path
    from frappe.modules.utils import scrub
    module = frappe.db.get_value("DocType", "PV Sortie Materiel", "module")
    print(f"  DocType.module = {module}")
    module_app = frappe.local.module_app.get(scrub(module))
    print(f"  module_app[{scrub(module)}] = {module_app}")
    expected_path = f"{module_app}.{scrub(module)}.doctype.pv_sortie_materiel.pv_sortie_materiel"
    print(f"  Expected import: {expected_path}.PVSortieMateriel")

    try:
        import importlib
        mod = importlib.import_module(expected_path)
        print(f"  Module imported: {mod}")
        cls2 = getattr(mod, "PVSortieMateriel", None)
        print(f"  Class via importlib: {cls2}")
    except Exception as e:
        print(f"  ✗ Import error: {type(e).__name__}: {e}")
