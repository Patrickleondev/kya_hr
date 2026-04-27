import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_url


class AppelOffreKYA(Document):
    def validate(self):
        self.numero_ao = self.name
        if self.items and len(self.items) == 0:
            frappe.throw(_("Au moins un article doit \u00eatre renseign\u00e9"))
        if self.fournisseurs and len(self.fournisseurs) == 0:
            frappe.throw(_("Au moins un fournisseur doit \u00eatre renseign\u00e9"))

    def before_save(self):
        # Auto-rempli signataires depuis session
        user = frappe.session.user
        emp = frappe.db.get_value("Employee", {"user_id": user}, "employee_name")
        if self.signature_demandeur and not self.signataire_demandeur:
            self.signataire_demandeur = emp or user
            self.date_signature_demandeur = now_datetime()
        if self.signature_daaf and not self.signataire_daaf:
            self.signataire_daaf = emp or user
            self.date_signature_daaf = now_datetime()
        if self.signature_dg and not self.signataire_dg:
            self.signataire_dg = emp or user
            self.date_signature_dg = now_datetime()


@frappe.whitelist()
def send_to_suppliers(name, only_unsent=1):
    """Envoie l'appel d'offre par email aux fournisseurs qui ont une adresse email."""
    only_unsent = int(only_unsent)
    doc = frappe.get_doc("Appel Offre KYA", name)

    # V\u00e9rif permission : Purchase Manager / DAAF / DG / System Manager / Owner
    roles = set(frappe.get_roles(frappe.session.user))
    allowed = roles & {"System Manager", "Purchase Manager", "Purchase User", "DAAF", "DG"}
    if not allowed and doc.owner != frappe.session.user:
        frappe.throw(_("Vous n'avez pas la permission d'envoyer cet appel d'offre"))

    sent_count = 0
    skipped_no_email = []
    errors = []

    print_url = get_url() + "/api/method/frappe.utils.print_format.download_pdf?doctype=Appel+Offre+KYA&name=" + frappe.utils.escape_html(name) + "&format=Appel+Offre+KYA"

    for row in doc.fournisseurs:
        if only_unsent and row.envoye:
            continue
        if not row.email:
            skipped_no_email.append(row.fournisseur_nom or row.fournisseur or "(sans nom)")
            continue
        try:
            subject = f"Appel d'Offre {doc.name} \u2013 {doc.objet[:60] if doc.objet else 'KYA-Energy Group'}"
            salutation = row.contact or row.fournisseur_nom or "Madame, Monsieur"
            body = f"""
            <p>{salutation},</p>
            {doc.message_fournisseur or ''}
            <hr>
            <p><strong>Objet&nbsp;:</strong> {frappe.utils.escape_html(doc.objet or '')}</p>
            <p><strong>N\u00b0 AO&nbsp;:</strong> {doc.name}<br>
            <strong>Date&nbsp;:</strong> {doc.date_ao}<br>
            <strong>Date limite de r\u00e9ponse&nbsp;:</strong> {doc.date_limite}</p>
            <p><strong>Modalit\u00e9s&nbsp;:</strong></p>
            {doc.modalites or ''}
            <hr>
            <p>Le d\u00e9tail des articles est en pi\u00e8ce jointe (PDF).</p>
            <p>Cordialement,<br>
            <strong>KYA-Energy Group</strong><br>
            T\u00e9l. : +228 70 45 34 81 &nbsp;|&nbsp; info@kya-energy.com</p>
            """

            attachments = []
            try:
                pdf = frappe.attach_print(
                    doctype="Appel Offre KYA",
                    name=doc.name,
                    file_name=f"AO-{doc.name}.pdf",
                    print_format="Standard",
                )
                attachments = [pdf]
            except Exception:
                attachments = []

            frappe.sendmail(
                recipients=[row.email],
                subject=subject,
                message=body,
                attachments=attachments,
                reference_doctype="Appel Offre KYA",
                reference_name=doc.name,
                now=True,
            )
            row.envoye = 1
            row.date_envoi = now_datetime()
            sent_count += 1
        except Exception as e:
            errors.append(f"{row.fournisseur_nom}: {str(e)}")
            frappe.log_error(frappe.get_traceback(), f"AO {doc.name} envoi {row.email}")

    # Mise \u00e0 jour doc
    doc.date_envoi = now_datetime()
    doc.nombre_envois = (doc.nombre_envois or 0) + sent_count
    total_envoyes = sum(1 for r in doc.fournisseurs if r.envoye)
    if total_envoyes == 0:
        doc.statut_envoi = "Non envoy\u00e9"
    elif total_envoyes < len(doc.fournisseurs):
        doc.statut_envoi = "Envoy\u00e9 partiellement"
    else:
        doc.statut_envoi = "Envoy\u00e9 \u00e0 tous"
    if doc.statut == "Brouillon" or doc.statut == "Valid\u00e9":
        doc.statut = "Envoy\u00e9"
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "sent": sent_count,
        "skipped_no_email": skipped_no_email,
        "errors": errors,
        "statut_envoi": doc.statut_envoi,
    }


@frappe.whitelist()
def update_reponses(name):
    """Recalcule le nombre de r\u00e9ponses re\u00e7ues \u00e0 partir du tableau fournisseurs."""
    doc = frappe.get_doc("Appel Offre KYA", name)
    nb = sum(1 for r in doc.fournisseurs if r.reponse_recue)
    doc.db_set("nombre_reponses", nb)
    if nb > 0 and doc.statut == "Envoy\u00e9":
        doc.db_set("statut", "R\u00e9ponses re\u00e7ues")
    return nb
