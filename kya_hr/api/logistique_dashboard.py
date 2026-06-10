"""API Dashboard Logistique KYA - flotte + sorties + entretien.

Fournit a /kya-logistique-dashboard les KPIs et tables :
- Vue globale : nb vehicules, en mission, sorties 30j, alertes assurance
- Par vehicule : marque/model, chauffeur, km, statut, expirations doc
- Sorties recentes (Sortie Vehicule)
- Carburant par mois (Vehicle Log)
- Alertes : assurance/visite expirantes 60j

Roles autorises : Logistique, DG, DGA, System Manager, Chef Service.
"""
from __future__ import annotations

import frappe
from frappe.utils import today, add_days


LOGISTIQUE_ROLES = {
    "System Manager", "Directeur General", "DG", "DGA",
    "Responsable Logistique", "Logisticien", "Chef Service",
    "Chef Service Achats", "Auditeur",
}


def _check_role():
    user_roles = set(frappe.get_roles(frappe.session.user))
    if not (user_roles & LOGISTIQUE_ROLES):
        frappe.throw(
            "Acces refuse - role Logistique requis",
            frappe.PermissionError,
        )


def _table_exists(table: str) -> bool:
    return bool(frappe.db.sql(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_name=%s", (f"tab{table}",)
    ))


@frappe.whitelist()
def get_dashboard_overview() -> dict:
    """KPIs globaux Logistique."""
    _check_role()

    out = {
        "total_vehicles": 0,
        "available": 0,
        "in_mission": 0,
        "sorties_30d": 0,
        "fuel_30d_count": 0,
        "fuel_30d_qty": 0,
        "alertes_assurance": 0,
        "alertes_visite": 0,
        "as_of": today(),
    }

    if _table_exists("Vehicle"):
        out["total_vehicles"] = frappe.db.count("Vehicle")
        # kya_statut peut etre 'Disponible', 'En mission', 'En maintenance', 'Hors service'
        try:
            out["available"] = frappe.db.count("Vehicle", {"kya_statut": "Disponible"})
            out["in_mission"] = frappe.db.count("Vehicle", {"kya_statut": "En mission"})
        except Exception:
            pass

        # Alertes : doc expirant dans 60 jours
        try:
            in_60 = add_days(today(), 60)
            out["alertes_assurance"] = frappe.db.count(
                "Vehicle",
                {"kya_assurance_expiration": ["<=", in_60]},
            )
            out["alertes_visite"] = frappe.db.count(
                "Vehicle",
                {"kya_visite_technique_expiration": ["<=", in_60]},
            )
        except Exception:
            pass

    if _table_exists("Sortie Vehicule"):
        out["sorties_30d"] = frappe.db.count(
            "Sortie Vehicule",
            {"creation": [">=", add_days(today(), -30)]},
        ) or 0

    if _table_exists("Vehicle Log"):
        row = frappe.db.sql(
            """
            SELECT COUNT(*) AS n, COALESCE(SUM(fuel_qty), 0) AS qty
            FROM `tabVehicle Log`
            WHERE date >= %s
            """,
            (add_days(today(), -30),),
            as_dict=True,
        )
        if row:
            out["fuel_30d_count"] = row[0]["n"]
            out["fuel_30d_qty"] = float(row[0]["qty"] or 0)

    return out


@frappe.whitelist()
def get_fleet_summary() -> list[dict]:
    """Pour chaque vehicule : marque, modele, statut, chauffeur, alertes."""
    _check_role()

    if not _table_exists("Vehicle"):
        return []

    return frappe.db.sql(
        """
        SELECT
            v.name,
            v.make,
            v.model,
            v.last_odometer,
            v.fuel_type,
            v.kya_statut AS statut,
            v.kya_chauffeur_principal AS chauffeur,
            v.kya_carte_grise_no AS carte_grise,
            v.kya_assurance_expiration AS assurance_exp,
            v.kya_visite_technique_expiration AS visite_exp,
            (SELECT COUNT(*) FROM `tabSortie Vehicule` sv
             WHERE sv.vehicle = v.name AND sv.statut IN ('En mission', 'Approuvee')
            ) AS sorties_actives
        FROM `tabVehicle` v
        ORDER BY v.name
        """,
        as_dict=True,
    ) or []


@frappe.whitelist()
def get_recent_sorties(limit: int = 30) -> list[dict]:
    """Dernieres sorties vehicule."""
    _check_role()
    try:
        limit = max(1, min(int(limit), 100))
    except (ValueError, TypeError):
        limit = 30

    if not _table_exists("Sortie Vehicule"):
        return []

    return frappe.db.sql(
        """
        SELECT
            name, vehicle, license_plate, chauffeur_name AS chauffeur,
            statut, date_depart, date_retour_prevue,
            destination, motif_mission AS motif,
            km_depart, km_retour, km_parcourus
        FROM `tabSortie Vehicule`
        ORDER BY date_depart DESC
        LIMIT %(limit)s
        """,
        {"limit": limit},
        as_dict=True,
    ) or []


@frappe.whitelist()
def get_recent_fuel_logs(limit: int = 30) -> list[dict]:
    """Derniers pleins de carburant (sans valeur monetaire)."""
    _check_role()
    try:
        limit = max(1, min(int(limit), 100))
    except (ValueError, TypeError):
        limit = 30

    if not _table_exists("Vehicle Log"):
        return []

    return frappe.db.sql(
        """
        SELECT
            name, license_plate, date, odometer,
            fuel_qty, employee, supplier
        FROM `tabVehicle Log`
        ORDER BY date DESC
        LIMIT %(limit)s
        """,
        {"limit": limit},
        as_dict=True,
    ) or []


@frappe.whitelist()
def get_alertes_documents() -> list[dict]:
    """Vehicules avec assurance/visite expirant dans 60 jours ou dejà expiree."""
    _check_role()

    if not _table_exists("Vehicle"):
        return []

    in_60 = add_days(today(), 60)
    return frappe.db.sql(
        """
        SELECT
            v.name, v.make, v.model,
            v.kya_chauffeur_principal AS chauffeur,
            v.kya_assurance_expiration AS assurance_exp,
            v.kya_visite_technique_expiration AS visite_exp,
            CASE WHEN v.kya_assurance_expiration < CURDATE() THEN 'EXPIRE'
                 WHEN v.kya_assurance_expiration <= %(in_60)s THEN 'BIENTOT'
                 ELSE 'OK' END AS statut_assurance,
            CASE WHEN v.kya_visite_technique_expiration < CURDATE() THEN 'EXPIRE'
                 WHEN v.kya_visite_technique_expiration <= %(in_60)s THEN 'BIENTOT'
                 ELSE 'OK' END AS statut_visite
        FROM `tabVehicle` v
        WHERE v.kya_assurance_expiration <= %(in_60)s
           OR v.kya_visite_technique_expiration <= %(in_60)s
        ORDER BY LEAST(
            COALESCE(v.kya_assurance_expiration, '9999-12-31'),
            COALESCE(v.kya_visite_technique_expiration, '9999-12-31')
        )
        """,
        {"in_60": in_60},
        as_dict=True,
    ) or []


@frappe.whitelist()
def get_fuel_by_month(months: int = 12) -> list[dict]:
    """Conso carburant par mois (quantite, pas valeur)."""
    _check_role()
    try:
        months = max(1, min(int(months), 36))
    except (ValueError, TypeError):
        months = 12

    if not _table_exists("Vehicle Log"):
        return []

    return frappe.db.sql(
        """
        SELECT
            DATE_FORMAT(date, '%%Y-%%m') AS month,
            COALESCE(SUM(fuel_qty), 0) AS total_qty,
            COUNT(*) AS n
        FROM `tabVehicle Log`
        WHERE date >= DATE_SUB(CURDATE(), INTERVAL %(months)s MONTH)
        GROUP BY month
        ORDER BY month
        """,
        {"months": months},
        as_dict=True,
    ) or []
