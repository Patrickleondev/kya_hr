import frappe
from frappe.translate import print_language
from frappe.utils.pdf import get_pdf
from frappe.www.printview import validate_print_permission

from kya_hr.api.kya_contracts import _sanitize_contract_pdf_html


def _clean_optional(value):
    if isinstance(value, str) and value.strip().lower() in ("", "none", "null", "undefined"):
        return None
    return value


def _clean_pdf_generator(value):
    value = _clean_optional(value)
    if value in ("wkhtmltopdf", "chrome"):
        return value
    return None


@frappe.whitelist(allow_guest=True)
def download_pdf(
    doctype,
    name,
    format=None,
    doc=None,
    no_letterhead=0,
    language=None,
    letterhead=None,
    pdf_generator=None,
):
    format = _clean_optional(format)
    doc = _clean_optional(doc)
    language = _clean_optional(language)
    letterhead = _clean_optional(letterhead)
    pdf_generator = _clean_pdf_generator(pdf_generator)

    if doctype != "KYA Contrat":
        from frappe.utils.print_format import download_pdf as frappe_download_pdf

        return frappe_download_pdf(
            doctype=doctype,
            name=name,
            format=format,
            doc=doc,
            no_letterhead=no_letterhead,
            language=language,
            letterhead=letterhead,
            pdf_generator=pdf_generator,
        )

    if isinstance(doc, str):
        doc = frappe._dict(frappe.parse_json(doc))
    doc = doc or frappe.get_doc(doctype, name)
    validate_print_permission(doc)

    print_format = format or (
        "Contrat de Stage KYA"
        if (doc.contract_type or "").lower().startswith("stage")
        else "KYA Contrat PDF"
    )

    with print_language(language):
        html = frappe.get_print(
            doctype,
            name,
            print_format,
            doc=doc,
            letterhead=letterhead,
            no_letterhead=no_letterhead,
        )

    pdf_file = get_pdf(_sanitize_contract_pdf_html(html))
    frappe.local.response.filename = f"{name.replace(' ', '-').replace('/', '-')}.pdf"
    frappe.local.response.filecontent = pdf_file
    frappe.local.response.type = "pdf"