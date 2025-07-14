import json
from pathlib import Path
from typing import Dict, Any

def load_mapping_config(config_path: str) -> Dict[str, Any]:
    """Loads the JSON mapping configuration file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    
    with open(path, 'r') as f:
        return json.load(f)