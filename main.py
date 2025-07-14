# File: main.py
# Replace the entire contents of your file with this code.

import argparse
import csv
from datetime import datetime
from pathlib import Path

from form_filler.data_loader import load_data
from form_filler.config_handler import load_mapping_config
from form_filler.filler import FormFiller

def main():
    # This parser defines ALL the arguments the script accepts.
    parser = argparse.ArgumentParser(description="Automated Form Filler Tool")
    
    # --- THESE ARE THE MISSING ARGUMENTS ---
    parser.add_argument(
        "--data-file", required=True, help="Path to the data file (CSV, JSON, XLSX)."
    )
    parser.add_argument(
        "--config-file", required=True, help="Path to the JSON form mapping configuration file."
    )
    # --- END OF MISSING ARGUMENTS ---
    
    parser.add_argument(
        "--report-dir", default="reports", help="Directory to save the submission report."
    )
    parser.add_argument(
        "--no-delay", action="store_true", help="Disable random delays between actions."
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run the browser in headless mode (no GUI)."
    )
    args = parser.parse_args()

    results = []
    filler = None
    try:
        print("Loading data...")
        data_rows = load_data(args.data_file)
        print(f"Loaded {len(data_rows)} rows of data.")

        print("Loading form configuration...")
        config = load_mapping_config(args.config_file)
        print(f"Configuration loaded for form: {config['form_url']}")

        filler = FormFiller(
            config,
            randomize_delay=not args.no_delay,
            headless=args.headless
        )
        
        total = len(data_rows)
        print("\n--- Starting Form Submission ---")

        for i, row in enumerate(data_rows):
            print(f"[{i+1}/{total}] Processing row for: {row.get('full_name', 'N/A')}")
            result = filler.fill_form_for_row(row)
            print(f"  -> Status: {result['status']} | Reason: {result['reason']}")
            results.append(result)

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return
    finally:
        if filler:
            filler.close()
        print("\n--- Automation Finished ---")

    if results:
        report_path = Path(args.report_dir)
        report_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_path / f"report_{timestamp}.csv"

        with open(report_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Status', 'Reason', 'Data'])
            for res in results:
                writer.writerow([
                    datetime.now().isoformat(),
                    res['status'],
                    res['reason'],
                    str(res['data'])
                ])
        print(f"\nSubmission report saved to: {report_file}")

if __name__ == "__main__":
    main()