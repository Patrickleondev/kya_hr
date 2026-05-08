import frappe
from frappe import _
from frappe.utils import flt, formatdate

no_cache = 1

_ALLOWED_ROLES = {
    "Comptable", "DFC", "DAAF", "Accounts Manager",
    "Auditeur Interne", "Directeur Général", "System Manager",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw(_("Veuillez vous connecter"), frappe.AuthenticationError)

    user_roles = set(frappe.get_roles(frappe.session.user))
    if not _ALLOWED_ROLES.intersection(user_roles):
        frappe.throw(_("Accès réservé à la comptabilité."), frappe.PermissionError)

    imports = frappe.get_all(
        "KYA Compta Import",
        fields=[
            "name", "type_document", "periode", "statut_import", "total_lignes",
            "total_debit", "total_credit", "total_salaire_net", "total_facture",
            "imported_by", "date_import", "source_file", "modified",
        ],
        order_by="modified desc",
        limit_page_length=20,
    )

    stats = {
        "imports": len(imports),
        "lignes": sum(flt(row.total_lignes) for row in imports),
        "debit": sum(flt(row.total_debit) for row in imports),
        "credit": sum(flt(row.total_credit) for row in imports),
        "salaires": sum(flt(row.total_salaire_net) for row in imports),
        "factures": sum(flt(row.total_facture) for row in imports),
    }

    type_counts = {}
    for row in imports:
        type_counts[row.type_document] = type_counts.get(row.type_document, 0) + 1
        row.date_import_label = formatdate(row.date_import) if row.date_import else ""

    context.imports = imports
    context.stats = stats
    context.type_counts = type_counts
    context.no_breadcrumbs = True
