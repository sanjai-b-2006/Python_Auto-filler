import argparse
import json
import os
from pathlib import Path
from bs4 import BeautifulSoup
from thefuzz import process

from form_filler.data_loader import load_data

def get_label_for_element(element, soup):
    """Tries to find the human-readable label for a form element."""
    # 1. Check for a <label for="element_id">
    if element.get('id'):
        label = soup.find('label', {'for': element['id']})
        if label:
            return label.get_text(strip=True)

    # 2. Check if the element is wrapped in a <label>
    parent_label = element.find_parent('label')
    if parent_label:
        return parent_label.get_text(strip=True)

    # 3. Look for a <label> that is an immediate sibling
    prev_sibling = element.find_previous_sibling()
    if prev_sibling and prev_sibling.name == 'label':
        return prev_sibling.get_text(strip=True)
        
    return None

def find_submit_button(soup):
    """Heuristically finds the submit button."""
    # Look for button or input with type=submit
    buttons = soup.find_all(['button', 'input'])
    for button in buttons:
        if button.get('type') == 'submit':
            # Prefer ID, then name
            if button.get('id'):
                return {"type": "id", "value": button['id']}
            if button.get('name'):
                return {"type": "name", "value": button['name']}
    return {"type": "css_selector", "value": "[type='submit']"} # Fallback

def main():
    parser = argparse.ArgumentParser(description="Auto-detect form fields and generate a mapping config.")
    parser.add_argument("--form-url", required=True, help="Path to the local HTML form file.")
    parser.add_argument("--data-file", required=True, help="Path to the data file (CSV, JSON, XLSX) to get headers.")
    parser.add_argument("--output-file", required=True, help="Path to save the generated JSON mapping config.")
    parser.add_argument("--threshold", type=int, default=75, help="Fuzzy matching score threshold (0-100).")
    args = parser.parse_args()

    print("--- Starting Field Auto-Detection ---")

    # 1. Load data to get headers
    try:
        data_rows = load_data(args.data_file)
        if not data_rows:
            print("Error: Data file is empty.")
            return
        data_headers = list(data_rows[0].keys())
        print(f"Detected data headers: {data_headers}")
    except Exception as e:
        print(f"Error loading data file: {e}")
        return

    # 2. Parse HTML form to find fields
    form_path = Path(args.form_url)
    if not form_path.exists():
        print(f"Error: Form file not found at {args.form_url}")
        return
    
    with open(form_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    form_fields = {}
    form_elements = soup.find_all(['input', 'select', 'textarea'])
    
    for element in form_elements:
        name = element.get('name')
        elem_type = element.get('type')
        if name and elem_type not in ['submit', 'button', 'reset']:
            label = get_label_for_element(element, soup)
            if label:
                # Store the name and its best-guess label
                form_fields[label] = name
    
    print(f"Detected form fields: {list(form_fields.keys())}")

    # 3. Match data headers to form field labels
    field_mappings = {}
    print("\n--- Matching Fields (Threshold > {}%) ---".format(args.threshold))
    for header in data_headers:
        # Find the best match from the available form labels
        best_match, score = process.extractOne(header, form_fields.keys())
        
        if score >= args.threshold:
            form_field_name = form_fields[best_match]
            field_mappings[header] = form_field_name
            print(f"  ✅ Matched '{header}' (data) -> '{best_match}' (label) -> '{form_field_name}' (field) [Score: {score}]")
        else:
            print(f"  ❌ No confident match for '{header}' [Best guess: '{best_match}', Score: {score}]")

    # 4. Assemble the final config object
    config = {
        "form_url": os.path.relpath(args.form_url),
        "field_mappings": field_mappings,
        "submit_button": find_submit_button(soup)
    }

    # 5. Save the config to a file
    with open(args.output_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\n✅ Successfully generated mapping config at: {args.output_file}")

if __name__ == "__main__":
    main()