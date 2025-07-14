import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

def load_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Loads data from a CSV, JSON, or Excel file into a list of dictionaries.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found at: {file_path}")

    file_extension = path.suffix.lower()
    
    if file_extension == '.csv':
        df = pd.read_csv(file_path)
    elif file_extension == '.json':
        df = pd.read_json(file_path)
    elif file_extension in ['.xls', '.xlsx']:
        df = pd.read_excel(file_path, engine='openpyxl')
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

    # Replace Pandas NaN with None for consistent handling
    df = df.where(pd.notna(df), None)
    return df.to_dict(orient='records')