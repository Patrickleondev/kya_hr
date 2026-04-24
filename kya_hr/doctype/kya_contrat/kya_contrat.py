"""KYA Contrat — Controller principal.

Lifecycle:
- validate: cohérence dates + sélection auto template + calcul date_fin
- before_submit: vérifier signatures employé + DG
- on_update: générer PDF + envoyer emails finaux quand workflow_state=Finalisé
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, getdate, now_datetime


class KYAContrat(Document):
    # ----- LIFECYCLE -----
    def validate(self):
        self._select_template()
        self._compute_date_fin()
        self._validate_signatures()

    def before_submit(self):
        # On submit only when workflow has reached Finalisé (after DG signature) or via direct submit by HR
        if self.workflow_state not in ("Finalisé", "Signé DG"):
            # allow direct submit only for HR Manager / System Manager fast-path
            if not any(r in frappe.get_roles() for r in ("HR Manager", "System Manager")):
                frappe.throw(_("Le contrat doit être signé par les deux parties avant soumission."))

    def on_update_after_submit(self):
        self._maybe_generate_pdf()

    def on_update(self):
        # Détecte transition vers Signé DG en édition standard (avant submit final)
        self._maybe_generate_pdf()

    # ----- HELPERS -----
    def _select_template(self):
        if self.template:
            return
        tpl = frappe.db.get_value(
            "KYA Contract Template",
            {"contract_type": self.contract_type, "is_active": 1},
            "name",
        )
        if tpl:
            self.template = tpl

    def _compute_date_fin(self):
        if self.contract_type == "CDI":
            return
        if self.date_debut and self.duree_mois and not self.date_fin:
            self.date_fin = add_months(getdate(self.date_debut), int(self.duree_mois))

    def _validate_signatures(self):
        # Si workflow passe en Signé Employé, exige signature + check lu/approuvé
        if self.workflow_state == "Signé Employé" and not self.signature_employe:
            frappe.throw(_("La signature du signataire est requise pour passer à 'Signé Employé'."))
        if self.workflow_state == "Signé Employé" and not self.contrat_lu:
            frappe.throw(_("Vous devez cocher 'J'ai lu et approuvé' avant de signer."))
        if self.workflow_state in ("Signé DG", "Finalisé") and not self.signature_dg:
            frappe.throw(_("La signature du Directeur Général est requise."))

        # Auto-fill nom signé + dates
        if self.signature_employe and not self.nom_signe_employe:
            self.nom_signe_employe = self.employee_name
            self.date_signature_employe = now_datetime()
        if self.signature_dg and not self.date_signature_dg:
            self.date_signature_dg = now_datetime()

    def _maybe_generate_pdf(self):
        if self.workflow_state == "Finalisé" and not self.pdf_final and self.signature_employe and self.signature_dg:
            try:
                self._generate_and_attach_pdf()
                self._send_final_emails()
            except Exception:
                frappe.log_error(frappe.get_traceback(), "KYA Contrat — Génération PDF")

    def _generate_and_attach_pdf(self):
        from frappe.utils.pdf import get_pdf

        html = frappe.get_print(
            "KYA Contrat",
            self.name,
            print_format="KYA Contrat PDF",
            no_letterhead=0,
        )
        pdf_bytes = get_pdf(html)
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"Contrat_{self.name}.pdf",
            "attached_to_doctype": "KYA Contrat",
            "attached_to_name": self.name,
            "content": pdf_bytes,
            "is_private": 1,
        }).insert(ignore_permissions=True)
        self.db_set("pdf_final", file_doc.file_url)

    def _send_final_emails(self):
        if not self.employee_email:
            return
        subject = f"📄 Contrat finalisé — {self.employee_name} — {self.name}"
        message = frappe.render_template(
            """
            <p>Bonjour {{ doc.employee_name }},</p>
            <p>Votre contrat de <b>{{ doc.contract_type }}</b> chez KYA-Energy Group est maintenant signé par les deux parties et archivé dans notre système.</p>
            <p>Vous trouverez en pièce jointe votre exemplaire signé (PDF). Conservez ce document précieusement.</p>
            <p><b>Date d'effet :</b> {{ frappe.format_date(doc.date_debut) }}<br>
            {% if doc.date_fin %}<b>Date d'échéance :</b> {{ frappe.format_date(doc.date_fin) }}{% else %}<b>Durée :</b> Indéterminée (CDI){% endif %}</p>
            <p>Cordialement,<br>KYA-Energy Group — Direction des Ressources Humaines</p>
            """,
            {"doc": self, "frappe": frappe},
        )
        attachments = []
        if self.pdf_final:
            attachments.append({"fid": frappe.db.get_value("File", {"file_url": self.pdf_final}, "name")})
        recipients = [self.employee_email]
        rh_email = frappe.db.get_single_value("KYA Dashboard Settings", "rh_email") or "rh@kya-energy.com"
        recipients.append(rh_email)
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            attachments=attachments,
            now=False,
        )
