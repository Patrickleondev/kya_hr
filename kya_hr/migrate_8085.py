
import frappe
from kya_hr.master_setup_logintern import execute as setup_execute
from kya_hr.repair_fr_ultra import execute as repair_execute
from kya_hr.setup_analytics_final import execute as analytics_execute

def main():
    print("Starting HRMS Setup on 8085...")
    try:
        setup_execute()
        print("Setup completed.")
    except Exception as e:
        print(f"Error during setup: {e}")

    print("Starting Translation Repair on 8085...")
    try:
        repair_execute()
        print("Repair completed.")
    except Exception as e:
        print(f"Error during repair: {e}")

    print("Starting Analytics Setup on 8085...")
    try:
        analytics_execute()
        print("Analytics completed.")
    except Exception as e:
        print(f"Error during analytics: {e}")

    frappe.db.commit()
    print("Migration to 8085 completed successfully.")

if __name__ == "__main__":
    main()
