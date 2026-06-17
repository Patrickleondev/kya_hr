# -*- coding: utf-8 -*-
"""API Gestion des Congés KYA — pilotage RH simple, adossé à HRMS natif.

Contexte métier : la RH trouve les écrans natifs Frappe (Leave Policy,
Leave Allocation, Leave Application) trop compliqués. Cette API expose des
actions SIMPLES (allouer un droit, enregistrer un congé déjà pris, voir les
soldes) tout en créant de VRAIS documents HRMS sous le capot → la paie, les
soldes et le rapport "Fiche Gestion Congés Annuels" restent cohérents et
chaque action est tracée (document daté, auteur).

Logique de solde identique au rapport fiche_gestion_conges_annuels :
    acquis  = SUM(Leave Allocation.total_leaves_allocated) de l'année
    pris    = SUM(Leave Application.total_leave_days) approuvées de l'année
    restant = acquis - pris

Endpoints whitelistés (réservés RH) :
- get_overview(year, leave_type)              : tableau soldes par employé
- set_allocation(employee, leave_type, total) : poser/ajuster le droit annuel
- record_taken(employee, leave_type, ...)     : enregistrer un congé pris
- get_employee_history(employee, year)        : historique tracé d'un employé
- cancel_application(name) / cancel_allocation(name) : annulation tracée
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today

# Types "congé annuel" possibles selon le paramétrage (cf. rapport).
ANNUEL_CANDIDATES = ["Congé Annuel", "Congé Annuel KYA", "Annual Leave", "Privilege Leave"]

RH_ROLES = {
    "Responsable RH",
    "HR Manager",
    "HR User",
    "DAAF",
    "Directeur Général",
    "DG",
    "System Manager",
}


def _check_rh_role():
    if not (RH_ROLES & set(frappe.get_roles(frappe.session.user))):
        frappe.throw(
            _("Accès réservé aux rôles RH (Responsable RH, HR Manager/User, DAAF, Direction)."),
            frappe.PermissionError,
        )


def _year_bounds(year=None):
    year = cint(year) or getdate(today()).year
    return year, f"{year}-01-01", f"{year}-12-31"


def _resolve_annual_type():
    existing = set(frappe.get_all("Leave Type", pluck="name"))
    for cand in ANNUEL_CANDIDATES:
        if cand in existing:
            return cand
    return existing and sorted(existing)[0] or None


def _acquis(employee, leave_type, year_start, year_end):
    return flt(frappe.db.sql(
        """
        SELECT COALESCE(SUM(total_leaves_allocated), 0)
        FROM `tabLeave Allocation`
        WHERE docstatus = 1 AND employee = %(e)s AND leave_type = %(lt)s
          AND from_date >= %(ys)s AND to_date <= %(ye)s
        """,
        {"e": employee, "lt": leave_type, "ys": year_start, "ye": year_end},
    )[0][0] or 0)


def _pris(employee, leave_type, year_start, year_end):
    return flt(frappe.db.sql(
        """
        SELECT COALESCE(SUM(total_leave_days), 0)
        FROM `tabLeave Application`
        WHERE docstatus = 1 AND status = 'Approved'
          AND employee = %(e)s AND leave_type = %(lt)s
          AND from_date >= %(ys)s AND to_date <= %(ye)s
        """,
        {"e": employee, "lt": leave_type, "ys": year_start, "ye": year_end},
    )[0][0] or 0)


def _solde(employee, leave_type, year_start, year_end):
    acquis = _acquis(employee, leave_type, year_start, year_end)
    pris = _pris(employee, leave_type, year_start, year_end)
    return {"acquis": acquis, "pris": pris, "restant": round(acquis - pris, 1)}


def _company_for(employee):
    return frappe.db.get_value("Employee", employee, "company") \
        or frappe.defaults.get_global_default("company")


# Jours fériés togolais à DATE FIXE (les fêtes religieuses mobiles — Pâques,
# Ascension, Aïd… — varient et sont à ajouter par la RH si besoin).
TOGO_FIXED_HOLIDAYS = {
    "01-01": "Jour de l'An",
    "01-13": "Fête de la libération nationale",
    "04-27": "Fête de l'Indépendance",
    "05-01": "Fête du Travail",
    "08-15": "Assomption",
    "11-01": "Toussaint",
    "12-25": "Noël",
}


def ensure_holiday_list(year=None, company=None):
    """Garantit qu'une Holiday List existe pour l'année et qu'elle est le
    défaut de la société — sinon HRMS ne peut pas décompter les congés.

    Repos hebdomadaire = dimanche (jours ouvrables Togo) + fêtes fixes.
    Idempotent : ne recrée pas, complète juste le défaut société manquant.
    Retourne le nom de la Holiday List.
    """
    year, ys, ye = _year_bounds(year)
    name = f"Jours fériés KYA {year}"
    company = company or frappe.defaults.get_global_default("company") \
        or frappe.db.get_value("Company", {}, "name")

    if not frappe.db.exists("Holiday List", name):
        hl = frappe.new_doc("Holiday List")
        hl.holiday_list_name = name
        hl.from_date = ys
        hl.to_date = ye
        # Semaine de 5 jours : samedi (5) ET dimanche (6) en repos. Frappe
        # weekly_off ne gère qu'un seul jour -> on pose les week-ends à la main.
        added = set()
        d, end = getdate(ys), getdate(ye)
        while d <= end:
            if d.weekday() >= 5:
                hl.append("holidays", {"holiday_date": d, "description": "Week-end", "weekly_off": 1})
                added.add(d)
            d = add_days(d, 1)
        for mmdd, desc in TOGO_FIXED_HOLIDAYS.items():
            hd = getdate(f"{year}-{mmdd}")
            if hd not in added:
                hl.append("holidays", {"holiday_date": hd, "description": desc})
                added.add(hd)
        hl.insert(ignore_permissions=True)

    # Défaut société (utile pour d'autres modules ERPNext).
    if company and not frappe.db.get_value("Company", company, "default_holiday_list"):
        frappe.db.set_value("Company", company, "default_holiday_list", name)
        frappe.clear_document_cache("Company", company)

    # HRMS v16 résout via "Holiday List Assignment" (docstatus=1), PAS via le
    # défaut société. On affecte la liste à la société (couvre tous ses
    # employés) si aucune affectation soumise n'existe déjà pour l'année.
    if company and frappe.db.exists("DocType", "Holiday List Assignment"):
        already = frappe.db.exists(
            "Holiday List Assignment",
            {"assigned_to": company, "holiday_list": name, "docstatus": 1},
        )
        if not already:
            hla = frappe.new_doc("Holiday List Assignment")
            hla.applicable_for = "Company"
            hla.assigned_to = company
            hla.holiday_list = name
            hla.from_date = ys
            hla.insert(ignore_permissions=True)
            hla.submit()
    return name


# ════════════════════════════════════════════════════════════════════
#  LECTURE
# ════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_overview(year=None, leave_type=None, include_stagiaires=0):
    """Tableau de bord congés : 1 ligne par employé avec acquis/pris/restant."""
    _check_rh_role()
    year, ys, ye = _year_bounds(year)
    leave_type = leave_type or _resolve_annual_type()

    emp_filters = {"status": "Active"}
    if not cint(include_stagiaires):
        emp_filters["employment_type"] = ["not in", ["Stage", "Intern"]]

    employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=["name", "employee_name", "department", "designation", "employment_type"],
        order_by="employee_name asc",
    )

    rows = []
    tot = {"acquis": 0.0, "pris": 0.0, "restant": 0.0}
    for emp in employees:
        s = _solde(emp.name, leave_type, ys, ye) if leave_type else {"acquis": 0, "pris": 0, "restant": 0}
        rows.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "department": emp.department or "—",
            "designation": emp.designation or "",
            "employment_type": emp.employment_type or "",
            "acquis": s["acquis"],
            "pris": s["pris"],
            "restant": s["restant"],
        })
        for k in tot:
            tot[k] += s[k]

    leave_types = frappe.get_all(
        "Leave Type",
        filters={"is_lwp": 0},
        fields=["name", "max_leaves_allowed"],
        order_by="name asc",
    )

    return {
        "year": year,
        "leave_type": leave_type,
        "leave_types": leave_types,
        "rows": rows,
        "totals": {k: round(v, 1) for k, v in tot.items()},
        "count": len(rows),
        "en_conge": sum(1 for r in rows if r["pris"] > 0),
    }


@frappe.whitelist()
def get_employee_history(employee, year=None):
    """Historique tracé d'un employé : allocations + demandes, tous types."""
    _check_rh_role()
    year, ys, ye = _year_bounds(year)

    allocations = frappe.get_all(
        "Leave Allocation",
        filters={"employee": employee, "docstatus": 1,
                 "from_date": [">=", ys], "to_date": ["<=", ye]},
        fields=["name", "leave_type", "total_leaves_allocated", "from_date",
                "to_date", "owner", "creation"],
        order_by="creation desc",
    )
    applications = frappe.get_all(
        "Leave Application",
        filters={"employee": employee, "docstatus": 1,
                 "from_date": [">=", ys], "to_date": ["<=", ye]},
        fields=["name", "leave_type", "total_leave_days", "from_date", "to_date",
                "status", "description", "owner", "creation"],
        order_by="from_date desc",
    )
    return {"year": year, "employee": employee,
            "allocations": allocations, "applications": applications}


# ════════════════════════════════════════════════════════════════════
#  ÉCRITURE (tracée)
# ════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def set_allocation(employee, leave_type, total, year=None):
    """Pose ou ajuste le droit annuel d'un employé pour un type de congé.

    Stratégie « 1 allocation = le droit » : on annule l'allocation existante
    de l'année (traçable, docstatus=2) puis on en crée une neuve au montant
    demandé. La paie/le solde restent cohérents.
    """
    _check_rh_role()
    total = flt(total)
    if total < 0:
        frappe.throw(_("Le droit ne peut pas être négatif."))
    year, ys, ye = _year_bounds(year)

    frappe.flags.mute_emails = True

    # Annuler les allocations existantes de l'année pour ce type.
    existing = frappe.get_all(
        "Leave Allocation",
        filters={"employee": employee, "leave_type": leave_type, "docstatus": 1,
                 "from_date": [">=", ys], "to_date": ["<=", ye]},
        pluck="name",
    )
    for name in existing:
        doc = frappe.get_doc("Leave Allocation", name)
        doc.cancel()

    created = None
    if total > 0:
        alloc = frappe.new_doc("Leave Allocation")
        alloc.employee = employee
        alloc.leave_type = leave_type
        alloc.from_date = ys
        alloc.to_date = ye
        alloc.new_leaves_allocated = total
        alloc.company = _company_for(employee)
        alloc.insert(ignore_permissions=True)
        alloc.submit()
        created = alloc.name

    frappe.db.commit()
    s = _solde(employee, leave_type, ys, ye)
    return {"ok": True, "allocation": created, "cancelled": existing, **s}


@frappe.whitelist()
def record_taken(employee, leave_type, from_date, to_date, half_day=0, description=""):
    """Enregistre un congé DÉJÀ pris (ou à venir) : crée une Leave Application
    approuvée et soumise → décompte automatique du solde, tracé."""
    _check_rh_role()
    if not (employee and leave_type and from_date and to_date):
        frappe.throw(_("employee, leave_type, from_date et to_date sont requis."))
    if getdate(to_date) < getdate(from_date):
        frappe.throw(_("La date de reprise doit être postérieure à la date de départ."))

    frappe.flags.mute_emails = True
    ensure_holiday_list(getdate(from_date).year, _company_for(employee))
    la = frappe.new_doc("Leave Application")
    la.employee = employee
    la.leave_type = leave_type
    la.from_date = from_date
    la.to_date = to_date
    la.half_day = cint(half_day)
    la.description = description or "Congé enregistré par la RH"
    la.company = _company_for(employee)
    la.status = "Approved"
    la.leave_approver = frappe.session.user
    la.follow_via_email = 0
    # Congé enregistré par la RH = autorité directe. On insère en Brouillon
    # puis submit() : set_workflow_state_on_action promeut automatiquement
    # l'état du workflow vers "Approuvé" (seul état docstatus=1) sans passer
    # par la chaîne de validation Sup./RH/DG.
    la.insert(ignore_permissions=True)
    la.submit()
    # Nettoyer les Workflow Action en attente créées à l'insert (état désormais
    # final) pour ne pas polluer les boîtes de validation.
    for wa in frappe.get_all("Workflow Action",
                             filters={"reference_doctype": "Leave Application",
                                      "reference_name": la.name, "status": "Open"},
                             pluck="name"):
        frappe.db.set_value("Workflow Action", wa, "status", "Completed")
    frappe.db.commit()

    year = getdate(from_date).year
    ys, ye = f"{year}-01-01", f"{year}-12-31"
    s = _solde(employee, leave_type, ys, ye)
    return {"ok": True, "application": la.name,
            "jours": flt(la.total_leave_days), **s}


@frappe.whitelist()
def cancel_application(name):
    """Annule une demande de congé (tracé : docstatus=2)."""
    _check_rh_role()
    doc = frappe.get_doc("Leave Application", name)
    frappe.flags.mute_emails = True
    doc.cancel()
    frappe.db.commit()
    return {"ok": True, "cancelled": name}


@frappe.whitelist()
def allocate_bulk(leave_type, total, year=None, include_stagiaires=0, only_missing=1):
    """Alloue un droit à TOUS les employés actifs en une fois.

    only_missing=1 : ne touche que ceux qui n'ont pas encore d'allocation
    (utile en mi-année pour ne pas écraser les droits déjà posés).
    """
    _check_rh_role()
    year, ys, ye = _year_bounds(year)
    emp_filters = {"status": "Active"}
    if not cint(include_stagiaires):
        emp_filters["employment_type"] = ["not in", ["Stage", "Intern"]]
    employees = frappe.get_all("Employee", filters=emp_filters, pluck="name")

    done, skipped = [], []
    for emp in employees:
        if cint(only_missing) and _acquis(emp, leave_type, ys, ye) > 0:
            skipped.append(emp)
            continue
        set_allocation(emp, leave_type, total, year=year)
        done.append(emp)
    return {"ok": True, "alloues": done, "ignores": skipped,
            "total_alloues": len(done)}
