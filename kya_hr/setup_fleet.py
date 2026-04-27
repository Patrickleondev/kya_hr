# Copyright (c) 2026, KYA-Energy Group
"""Setup du module Gestion de Flotte KYA :
- Custom Fields sur Vehicle (couleur localisée, statut, chauffeur principal, expirations)
- Property Setters (labels FR sur Vehicle / Driver)
- Permissions DocPerm sur Vehicle / Driver / Vehicle Log / Vehicle Service pour Gestionnaire de Flotte
- UOM "Litre" si manquant
- Seed des 6 véhicules KYA fournis par le contrôleur de flotte
- Workspace Logistique (sidebar)
"""
import frappe


# ───────────────────────────────────────────────────────────────────
# 1. CUSTOM FIELDS sur Vehicle
# ───────────────────────────────────────────────────────────────────
VEHICLE_CUSTOM_FIELDS = [
    {
        "fieldname": "kya_section_kya",
        "label": "Spécifique KYA",
        "fieldtype": "Section Break",
        "insert_after": "doors",
    },
    {
        "fieldname": "kya_couleur",
        "label": "Couleur",
        "fieldtype": "Select",
        "options": "\nRouge\nGrise\nBlanche\nNoire\nBleue\nVerte\nJaune\nAutre",
        "insert_after": "kya_section_kya",
        "in_list_view": 1,
        "in_standard_filter": 1,
    },
    {
        "fieldname": "kya_statut",
        "label": "Statut KYA",
        "fieldtype": "Select",
        "options": "Disponible\nEn mission\nEn entretien\nHors service",
        "default": "Disponible",
        "insert_after": "kya_couleur",
        "in_list_view": 1,
        "in_standard_filter": 1,
    },
    {
        "fieldname": "kya_chauffeur_principal",
        "label": "Chauffeur principal",
        "fieldtype": "Link",
        "options": "Employee",
        "insert_after": "kya_statut",
    },
    {
        "fieldname": "kya_column_break_1",
        "fieldtype": "Column Break",
        "insert_after": "kya_chauffeur_principal",
    },
    {
        "fieldname": "kya_carte_grise_no",
        "label": "N° Carte grise",
        "fieldtype": "Data",
        "insert_after": "kya_column_break_1",
    },
    {
        "fieldname": "kya_assurance_expiration",
        "label": "Expiration assurance",
        "fieldtype": "Date",
        "insert_after": "kya_carte_grise_no",
    },
    {
        "fieldname": "kya_visite_technique_expiration",
        "label": "Expiration visite technique",
        "fieldtype": "Date",
        "insert_after": "kya_assurance_expiration",
    },
]


def _create_custom_field(dt, spec):
    name = f"{dt}-{spec['fieldname']}"
    if frappe.db.exists("Custom Field", name):
        cf = frappe.get_doc("Custom Field", name)
        for k, v in spec.items():
            cf.set(k, v)
        cf.save(ignore_permissions=True)
        return f"updated: {name}"
    cf = frappe.new_doc("Custom Field")
    cf.dt = dt
    for k, v in spec.items():
        cf.set(k, v)
    cf.insert(ignore_permissions=True)
    return f"created: {name}"


# ───────────────────────────────────────────────────────────────────
# 2. PROPERTY SETTERS — labels FR sur Vehicle
# ───────────────────────────────────────────────────────────────────
VEHICLE_TRANSLATIONS = {
    "license_plate": ("label", "Plaque d'immatriculation"),
    "make": ("label", "Marque"),
    "model": ("label", "Modèle"),
    "vehicle_details": ("label", "Détails du véhicule"),
    "last_odometer": ("label", "Kilométrage actuel"),
    "acquisition_date": ("label", "Date d'acquisition"),
    "location": ("label", "Localisation"),
    "chassis_no": ("label", "N° de châssis"),
    "vehicle_value": ("label", "Valeur du véhicule"),
    "employee": ("label", "Employé responsable"),
    "insurance_details": ("label", "Détails assurance"),
    "insurance_company": ("label", "Compagnie d'assurance"),
    "policy_no": ("label", "N° de police"),
    "start_date": ("label", "Début assurance"),
    "end_date": ("label", "Fin assurance"),
    "additional_details": ("label", "Détails supplémentaires"),
    "fuel_type": ("label", "Type de carburant"),
    "uom": ("label", "Unité de carburant"),
    "carbon_check_date": ("label", "Dernier contrôle carbone"),
    "color": ("label", "Couleur (libre)"),
    "wheels": ("label", "Roues"),
    "doors": ("label", "Portes"),
}


def _set_property(dt, fieldname, prop, value, prop_type="Data"):
    name = f"{dt}-{fieldname}-{prop}"
    if frappe.db.exists("Property Setter", name):
        ps = frappe.get_doc("Property Setter", name)
        ps.value = value
        ps.save(ignore_permissions=True)
        return f"updated PS: {name}"
    ps = frappe.new_doc("Property Setter")
    ps.doctype_or_field = "DocField"
    ps.doc_type = dt
    ps.field_name = fieldname
    ps.property = prop
    ps.value = value
    ps.property_type = prop_type
    ps.insert(ignore_permissions=True)
    return f"created PS: {name}"


# ───────────────────────────────────────────────────────────────────
# 3. PERMISSIONS — Gestionnaire de Flotte sur Vehicle/Driver/Logs/Services
# ───────────────────────────────────────────────────────────────────
FLEET_DOCTYPES = ["Vehicle", "Driver", "Vehicle Log", "Vehicle Service"]


def _ensure_role(role_name, desk_access=1, home_page=None):
    if frappe.db.exists("Role", role_name):
        role = frappe.get_doc("Role", role_name)
        role.desk_access = desk_access
        if home_page:
            role.home_page = home_page
        role.save(ignore_permissions=True)
        return f"updated role: {role_name}"
    role = frappe.new_doc("Role")
    role.role_name = role_name
    role.desk_access = desk_access
    role.is_custom = 1
    if home_page:
        role.home_page = home_page
    role.insert(ignore_permissions=True)
    return f"created role: {role_name}"


def _add_role_permission(dt, role):
    """Ajoute une DocPerm row au DocType pour un rôle (full access)."""
    existing = frappe.db.get_value(
        "DocPerm", {"parent": dt, "role": role, "permlevel": 0}, "name"
    )
    if existing:
        return f"perm already on {dt} for {role}"
    doc = frappe.get_doc("DocType", dt)
    perm = doc.append("permissions", {})
    perm.role = role
    perm.permlevel = 0
    perm.read = 1
    perm.write = 1
    perm.create = 1
    perm.delete = 1
    perm.submit = 1 if doc.is_submittable else 0
    perm.cancel = 1 if doc.is_submittable else 0
    perm.amend = 1 if doc.is_submittable else 0
    perm.report = 1
    perm.export = 1
    perm.share = 1
    perm.print = 1
    perm.email = 1
    doc.save(ignore_permissions=True)
    return f"added perm on {dt} for {role}"


# ───────────────────────────────────────────────────────────────────
# 4. UOM Litre
# ───────────────────────────────────────────────────────────────────
def _ensure_uom():
    if not frappe.db.exists("UOM", "Litre"):
        frappe.get_doc({"doctype": "UOM", "uom_name": "Litre", "must_be_whole_number": 0}).insert(
            ignore_permissions=True
        )
        return "created UOM Litre"
    return "UOM Litre already exists"


# ───────────────────────────────────────────────────────────────────
# 5. SEED des 6 véhicules KYA (photo du contrôleur)
# ───────────────────────────────────────────────────────────────────
KYA_VEHICLES = [
    {"license_plate": "TG-4363-BL", "make": "Toyota", "model": "RAV4",   "fuel_type": "Petrol", "kya_couleur": "Rouge"},
    {"license_plate": "TG-4366-BL", "make": "Toyota", "model": "Corolla","fuel_type": "Petrol", "kya_couleur": "Grise"},
    {"license_plate": "TG-9291-BK", "make": "Toyota", "model": "Hilux",  "fuel_type": "Diesel", "kya_couleur": "Blanche"},
    {"license_plate": "TG-9293-BK", "make": "Toyota", "model": "Hilux",  "fuel_type": "Diesel", "kya_couleur": "Blanche"},
    {"license_plate": "TG-7497-BS", "make": "Toyota", "model": "Hilux",  "fuel_type": "Diesel", "kya_couleur": "Grise"},
    {"license_plate": "TG-7496-BS", "make": "Hyundai","model": "H1",     "fuel_type": "Diesel", "kya_couleur": "Blanche"},
]


def _seed_vehicles():
    out = []
    company = frappe.db.get_single_value("Global Defaults", "default_company") or \
              frappe.db.get_value("Company", {}, "name")
    for spec in KYA_VEHICLES:
        if frappe.db.exists("Vehicle", spec["license_plate"]):
            out.append(f"skip existing: {spec['license_plate']}")
            continue
        doc = frappe.new_doc("Vehicle")
        doc.license_plate = spec["license_plate"]
        doc.make = spec["make"]
        doc.model = spec["model"]
        doc.fuel_type = spec["fuel_type"]
        doc.uom = "Litre"
        doc.last_odometer = 0
        doc.company = company
        doc.kya_couleur = spec["kya_couleur"]
        doc.kya_statut = "Disponible"
        doc.color = spec["kya_couleur"]  # standard ERPNext field aussi rempli
        doc.insert(ignore_permissions=True)
        out.append(f"created vehicle: {spec['license_plate']}")
    return out


# ───────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ───────────────────────────────────────────────────────────────────
def run():
    log = []
    # Role d'abord (référencé dans les perms et workspace)
    log.append(_ensure_role("Gestionnaire de Flotte", desk_access=1, home_page="/app/logistique"))

    # Custom fields
    for spec in VEHICLE_CUSTOM_FIELDS:
        log.append(_create_custom_field("Vehicle", spec))

    # Property setters
    for fieldname, (prop, value) in VEHICLE_TRANSLATIONS.items():
        log.append(_set_property("Vehicle", fieldname, prop, value))

    # UOM
    log.append(_ensure_uom())

    # Permissions
    for dt in FLEET_DOCTYPES:
        if frappe.db.exists("DocType", dt):
            log.append(_add_role_permission(dt, "Gestionnaire de Flotte"))

    # Seed vehicles
    log.extend(_seed_vehicles())

    frappe.db.commit()
    frappe.clear_cache()
    for line in log:
        print(f"  • {line}")
    print(f"\n✓ Setup Gestion de Flotte terminé ({len(log)} opérations).")
    return log
