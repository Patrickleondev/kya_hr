"""API Dashboard Logistique KYA - flotte + sorties + entretien.

Fournit a /kya-logistique-dashboard les KPIs et tables :
- Vue globale : nb vehicules, en mission, sorties 30j, depenses 30j
- Par vehicule : km, dernier service, prochaine echeance, depenses YTD
- Sorties recentes (Sortie Vehicule)
- Entretiens (Vehicle Service) recents + a venir
- Carburant (Vehicle Log) par mois

Roles autorises : Logistique, DG, DGA, System Manager, Chef Service.
"""
from __future__ import annotations

import frappe
from frappe.utils import flt, today, add_days


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


def _get_default_currency() -> str:
    company = (frappe.defaults.get_user_default("Company")
               or frappe.db.get_single_value("Global Defaults", "default_company"))
    if not company:
        first = frappe.db.get_all("Company", fields=["name"], limit=1)
        company = first[0].name if first else None
    if company:
        return frappe.db.get_value("Company", company, "default_currency") or "XOF"
    return "XOF"


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
        "fuel_30d_amount": 0.0,
        "fuel_30d_count": 0,
        "service_due_30d": 0,
        "currency": _get_default_currency(),
        "as_of": today(),
    }

    if _table_exists("Vehicle"):
        out["total_vehicles"] = frappe.db.count("Vehicle")

    if _table_exists("Sortie Vehicule"):
        out["sorties_30d"] = frappe.db.count(
            "Sortie Vehicule",
            {"creation": [">=", add_days(today(), -30)]},
        ) or 0
        # En mission : statut En mission OU Approuve
        try:
            out["in_mission"] = frappe.db.count(
                "Sortie Vehicule",
                {"statut": ["in", ["En mission", "Approuvee"]]},
            )
        except Exception:
            out["in_mission"] = 0
        out["available"] = max(0, out["total_vehicles"] - out["in_mission"])

    if _table_exists("Vehicle Log"):
        # Vehicle Log peut contenir refuelling, donc summer price = sum(amount)
        row = frappe.db.sql(
            """
            SELECT COALESCE(SUM(price), 0) AS total_amount, COUNT(*) AS n
            FROM `tabVehicle Log`
            WHERE date >= %s
            """,
            (add_days(today(), -30),),
            as_dict=True,
        )
        if row:
            out["fuel_30d_amount"] = flt(row[0]["total_amount"], 2)
            out["fuel_30d_count"] = row[0]["n"]

    if _table_exists("Vehicle Service"):
        # Services dans les 30 derniers jours OU prevus dans les 30 prochains
        row = frappe.db.sql(
            """
            SELECT COUNT(*) AS n
            FROM `tabVehicle Service`
            WHERE service_date BETWEEN %s AND %s
            """,
            (add_days(today(), -15), add_days(today(), 30)),
        )
        if row:
            out["service_due_30d"] = row[0][0]

    return out


@frappe.whitelist()
def get_fleet_summary() -> list[dict]:
    """Pour chaque vehicule : licence, km, dernier service, depenses YTD."""
    _check_role()

    if not _table_exists("Vehicle"):
        return []

    return frappe.db.sql(
        """
        SELECT
            v.name,
            v.license_plate,
            v.make,
            v.model,
            v.last_odometer,
            v.fuel_type,
            (SELECT MAX(service_date) FROM `tabVehicle Service`
             WHERE serial_no = v.name OR license_plate = v.license_plate
            ) AS last_service,
            (SELECT COALESCE(SUM(price), 0) FROM `tabVehicle Log`
             WHERE license_plate = v.license_plate AND YEAR(date) = YEAR(CURDATE())
            ) AS fuel_ytd,
            (SELECT COUNT(*) FROM `tabSortie Vehicule`
             WHERE vehicule = v.name AND statut IN ('En mission', 'Approuvee')
            ) AS active_sorties
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
            name, vehicule, chauffeur, statut,
            date_depart, date_retour_prevue, date_retour_effective,
            destination, motif, km_depart, km_retour
        FROM `tabSortie Vehicule`
        ORDER BY date_depart DESC
        LIMIT %(limit)s
        """,
        {"limit": limit},
        as_dict=True,
    ) or []


@frappe.whitelist()
def get_recent_services(limit: int = 20) -> list[dict]:
    """Derniers entretiens + maintenance prevue."""
    _check_role()
    try:
        limit = max(1, min(int(limit), 100))
    except (ValueError, TypeError):
        limit = 20

    if not _table_exists("Vehicle Service"):
        return []

    return frappe.db.sql(
        """
        SELECT
            name, service_date, expense_account,
            type, frequency
        FROM `tabVehicle Service`
        ORDER BY service_date DESC
        LIMIT %(limit)s
        """,
        {"limit": limit},
        as_dict=True,
    ) or []


@frappe.whitelist()
def get_fuel_by_month(months: int = 12) -> list[dict]:
    """Conso carburant par mois (Vehicle Log)."""
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
            COALESCE(SUM(price), 0) AS total_amount,
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
