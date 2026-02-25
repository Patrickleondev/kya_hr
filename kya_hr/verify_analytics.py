
import frappe
import json

def verify():
    charts = frappe.get_all("Dashboard Chart", pluck="chart_name")
    cards = frappe.get_all("Number Card", pluck="label")
    
    kya_charts = [c for c in charts if "KYA" in c or "Stagiaire" in c or "Sortie" in c or "Carburant" in c]
    kya_cards = [c for c in cards if "KYA" in c or "Stagiaire" in c or "Sortie" in c]
    
    results = {
        "KYA Charts Found": kya_charts,
        "KYA Cards Found": kya_cards,
        "All Charts Count": len(charts),
        "All Cards Count": len(cards)
    }
    
    print("---VERIFICATION_START---")
    print(json.dumps(results, indent=2))
    print("---VERIFICATION_END---")

if __name__ == "__main__":
    verify()
