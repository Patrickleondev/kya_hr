import base64
import mimetypes
import os
import re

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


# ── Sanitisation générique pour la génération PDF en conteneur ────────────────
# wkhtmltopdf, dans cette installation Docker (backend séparé du frontend nginx),
# ne peut PAS récupérer les ressources via http (ConnectionRefused). On supprime
# donc tout <link>/<script> externe et on INLINE les images locales (logo, etc.)
# en data-URI pour qu'aucun appel réseau ne soit nécessaire.
_LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.I | re.S)
_IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'])', re.I)
_DL_ANCHOR_RE = re.compile(
    r'<a[^>]+href=["\']/api/method/[^"\']*download_pdf[^"\']*["\'][^>]*>.*?</a>',
    re.I | re.S,
)


def _local_path_for_url(url: str):
    """Convertit une URL de ressource locale en chemin disque, ou None."""
    if not url or url.startswith("data:"):
        return None
    # retirer schéma + hôte
    url = re.sub(r"^https?://[^/]+", "", url)
    url = url.split("?")[0].split("#")[0]
    if not url.startswith("/"):
        return None
    try:
        if url.startswith("/assets/"):
            # /assets/<app>/... -> apps/<app>/<app>/public/...
            parts = url[len("/assets/"):].split("/", 1)
            if len(parts) == 2:
                app, rest = parts
                return frappe.get_app_path(app, "public", *rest.split("/"))
        elif url.startswith("/files/"):
            return frappe.get_site_path("public", "files", url[len("/files/"):])
        elif url.startswith("/private/files/"):
            return frappe.get_site_path("private", "files", url[len("/private/files/"):])
        elif url.startswith("/public/"):
            return frappe.get_site_path("public", url[len("/public/"):])
    except Exception:
        return None
    return None


def _inline_images(html: str) -> str:
    def repl(match):
        pre, url, post = match.group(1), match.group(2), match.group(3)
        if url.startswith("data:"):
            return match.group(0)
        path = _local_path_for_url(url)
        if path and os.path.exists(path):
            try:
                with open(path, "rb") as fh:
                    data = base64.b64encode(fh.read()).decode("ascii")
                mime = mimetypes.guess_type(path)[0] or "image/png"
                return f"{pre}data:{mime};base64,{data}{post}"
            except Exception:
                pass
        # image locale introuvable / distante : neutraliser pour éviter l'appel réseau
        transparent = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
        return f"{pre}{transparent}{post}"

    return _IMG_SRC_RE.sub(repl, html)


def _sanitize_print_html(html: str) -> str:
    html = html or ""
    html = _LINK_RE.sub("", html)
    html = _SCRIPT_RE.sub("", html)
    html = _DL_ANCHOR_RE.sub("", html)
    html = _inline_images(html)
    return html


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

    if isinstance(doc, str):
        doc = frappe._dict(frappe.parse_json(doc))
    doc = doc or frappe.get_doc(doctype, name)
    validate_print_permission(doc)

    print_format = format
    if not print_format and doctype == "KYA Contrat":
        print_format = (
            "Contrat de Stage KYA"
            if (doc.contract_type or "").lower().startswith("stage")
            else "KYA Contrat PDF"
        )
    # Filet de sécurité : sans format explicite (ou en "Standard"), retomber sur
    # le format OFFICIEL du doctype — jamais sur le rendu Standard illisible.
    if not print_format or print_format == "Standard":
        from kya_hr.ensure_webform_print_formats import DOCTYPE_DEFAULT_PRINT_FORMATS
        official = DOCTYPE_DEFAULT_PRINT_FORMATS.get(doctype)
        if official and frappe.db.exists("Print Format", official):
            print_format = official

    with print_language(language):
        html = frappe.get_print(
            doctype,
            name,
            print_format,
            doc=doc,
            letterhead=letterhead,
            no_letterhead=no_letterhead,
        )

    # Le contrat a son propre nettoyage (gère placeholder signature + logo dédié) ;
    # tous les autres documents passent par le nettoyage générique.
    if doctype == "KYA Contrat":
        html = _sanitize_contract_pdf_html(html)
    html = _sanitize_print_html(html)

    pdf_file = get_pdf(html)
    frappe.local.response.filename = f"{name.replace(' ', '-').replace('/', '-')}.pdf"
    frappe.local.response.filecontent = pdf_file
    frappe.local.response.type = "pdf"
