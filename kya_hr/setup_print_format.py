import frappe

def create_print_format():
    print("Creating Print Format for KYA Purchase Request...")
    if frappe.db.exists("Print Format", "KYA Purchase Request PDF"):
        frappe.delete_doc("Print Format", "KYA Purchase Request PDF")
        
    doc = frappe.get_doc({
        "doctype": "Print Format",
        "name": "KYA Purchase Request PDF",
        "module": "KYA HR",
        "doc_type": "KYA Purchase Request",
        "standard": "Yes",
        "custom_format": 1,
        "format_data": "[]",
        "html": """
<style>
    .kya-print-container { max-width: 100%; font-family: sans-serif; font-size: 12px; }
    .kya-header { text-align: center; border-bottom: 2px solid #1a5276; padding-bottom: 15px; margin-bottom: 20px; }
    .kya-logo { max-height: 60px; }
    .kya-title { margin: 10px 0 0 0; color: #1a5276; font-size: 20px; font-weight: bold; }
    .kya-section-title { background: #1a5276; color: white; padding: 5px; font-weight: bold; margin-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
    th { background-color: #f4f4f4; }
    .signature-box { border: 1px solid #ccc; height: 80px; text-align: center; vertical-align: bottom; padding: 5px; width: 25%; display: inline-block; box-sizing: border-box; margin-right: 2%; }
    .signature-box img { max-height: 50px; }
</style>

<div class="kya-print-container">
    <div class="kya-header">
        <img src="/files/kya logo.png" alt="Logo KYA" class="kya-logo">
        <h2 class="kya-title">FICHE DE DEMANDE D'ACHAT N° {{ doc.name }}</h2>
    </div>

    <div class="kya-section-title">1. Informations Générales</div>
    <table>
        <tr>
            <th>Demandeur</th><td>{{ doc.requester }}</td>
            <th>Date</th><td>{{ doc.get_formatted("date") }}</td>
        </tr>
        <tr>
            <th>Département</th><td>{{ doc.department }}</td>
            <th>Urgence</th><td>{{ doc.urgency }}</td>
        </tr>
        <tr>
            <th>Objet</th><td colspan="3">{{ doc.purpose }}</td>
        </tr>
    </table>

    <div class="kya-section-title">2. Détails de la demande</div>
    <div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 15px;">
        {{ doc.description }}
    </div>

    <div class="kya-section-title">3. Articles demandés</div>
    <table>
        <thead>
            <tr>
                <th>Article / Description</th>
                <th>Qté</th>
                <th>Prix U. Estimé</th>
                <th>Montant Total Estimé</th>
            </tr>
        </thead>
        <tbody>
            {% for item in doc.items %}
            <tr>
                <td>{{ item.item_name }}</td>
                <td>{{ item.qty }}</td>
                <td>{{ item.get_formatted("estimated_rate") }}</td>
                <td>{{ item.get_formatted("estimated_amount") }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="kya-section-title">4. Sourcing (Service Achats)</div>
    <table>
        <tr>
            <th>Fournisseur Retenu</th><td>{{ doc.selected_supplier or 'N/A' }}</td>
            <th>Montant Total (Devis)</th><td>{{ doc.get_formatted("total_amount") }}</td>
        </tr>
    </table>

    <div class="kya-section-title">5. Signatures et Visas</div>
    <div style="width: 100%; margin-top: 10px;">
        <div class="signature-box">
            <strong>Demandeur</strong><br><br>
            {% if doc.requester_signature %}<img src="{{ doc.requester_signature }}">{% endif %}
        </div>
        <div class="signature-box">
            <strong>Chef de Dept.</strong><br><br>
            {% if doc.dept_head_signature %}<img src="{{ doc.dept_head_signature }}">{% endif %}
        </div>
        <div class="signature-box">
            <strong>Responsable Achats</strong><br><br>
            {% if doc.purchasing_signature %}<img src="{{ doc.purchasing_signature }}">{% endif %}
        </div>
        <div class="signature-box" style="margin-right:0;">
            <strong>Direction Générale</strong><br><br>
            {% if doc.dg_signature %}<img src="{{ doc.dg_signature }}">{% endif %}
        </div>
    </div>
</div>
        """
    })
    doc.insert(ignore_permissions=True)
    print("✅ KYA Purchase Request Print Format created.")

if __name__ == "__main__":
    create_print_format()
