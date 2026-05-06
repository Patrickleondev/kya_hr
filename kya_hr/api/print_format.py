from typing import Literal

import frappe
from frappe.translate import print_language
from frappe.utils.pdf import get_pdf
from frappe.www.printview import validate_print_permission

from kya_hr.api.kya_contracts import _sanitize_contract_pdf_html


@frappe.whitelist(allow_guest=True)
def download_pdf(
    doctype: str,
    name: str,
    format=None,
    doc=None,
    no_letterhead=0,
    language=None,
    letterhead=None,
    pdf_generator: Literal["wkhtmltopdf", "chrome"] | None = None,
):
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