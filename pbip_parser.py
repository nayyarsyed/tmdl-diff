import json
import zipfile
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


def extract_pbip_model(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Extract model definition from a .pbip file.
    PBIP files can be ZIP archives or directory-based projects.
    Returns a model dict with structure information or None if extraction fails.
    """
    try:
        # Check if it's a directory-based PBIP (modern format)
        base_name = file_path.stem
        semantic_model_dir = file_path.parent / f"{base_name}.SemanticModel"
        
        if semantic_model_dir.exists() and semantic_model_dir.is_dir():
            return _extract_from_directory(semantic_model_dir)
        
        # Try as ZIP-based PBIP (older format or .pbix)
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                return _extract_from_zip(zip_ref)
        except (zipfile.BadZipFile, FileNotFoundError):
            return None
            
    except Exception:
        return None


def _extract_from_directory(sem_model_dir: Path) -> Optional[Dict[str, Any]]:
    """Extract model definition from a directory-based semantic model."""
    try:
        definition_dir = sem_model_dir / "definition"
        search_dir = definition_dir if definition_dir.exists() else sem_model_dir
        
        model_tmdl_path = search_dir / "model.tmdl"
        if not model_tmdl_path.exists():
            return None
        
        # Parse all TMDL files in the tables directory
        tables_dir = search_dir / "tables"
        model_data = {
            "name": sem_model_dir.stem.replace(".SemanticModel", ""),
            "tables": [],
            "relationships": []
        }
        
        # If tables dir exists, parse each table file
        target_dir = tables_dir if tables_dir.exists() else search_dir
        for tmdl_file in target_dir.rglob("*.tmdl"):
            if tmdl_file.name in ['model.tmdl', 'relationships.tmdl', 'expressions.tmdl', 'database.tmdl']:
                continue
            
            with open(tmdl_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                table_info = _parse_single_table_tmdl(content, tmdl_file.stem)
                model_data["tables"].append(table_info)
        
        return model_data
    except Exception:
        return None


def _parse_single_table_tmdl(content: str, default_name: str) -> Dict[str, Any]:
    """Extract table name, columns, and measures from a single TMDL file content."""
    # Find table name
    table_match = re.search(r'^\s*table\s+([^\n\r]+)', content, re.MULTILINE | re.IGNORECASE)
    if table_match:
        table_name = table_match.group(1).split('#')[0].strip().strip("'").strip()
    else:
        table_name = default_name
    
    # Find columns
    raw_columns = re.findall(r'^\s*column\s+([^\n\r]+)', content, re.MULTILINE | re.IGNORECASE)
    columns = []
    for c in raw_columns:
        clean_c = c.split(':')[0].split('=')[0].strip().strip("'").strip()
        if clean_c:
            columns.append(clean_c)
    
    # Find measures - capture name even if = is on next line
    raw_measures = re.findall(r'^\s*measure\s+([^\n\r=]+)', content, re.MULTILINE | re.IGNORECASE)
    measures = [m.strip().strip("'").strip() for m in raw_measures]

    # Find hierarchies
    raw_hierarchies = re.findall(r'^\s*hierarchy\s+([^\n\r]+)', content, re.MULTILINE | re.IGNORECASE)
    hierarchies = [h.split(':')[0].strip().strip("'").strip() for h in raw_hierarchies]
    
    return {
        "name": table_name,
        "columns": sorted(list(set(columns))),
        "measures": sorted(list(set(measures))),
        "hierarchies": sorted(list(set(hierarchies)))
    }


def _extract_from_zip(zip_ref: zipfile.ZipFile) -> Optional[Dict[str, Any]]:
    """Extract model definition from a ZIP-based PBIP/PBIX file."""
    try:
        files = zip_ref.namelist()
        model_file = None
        
        for candidate in ['model.json', 'Model/definition.json', 'definition.json']:
            if candidate in files:
                model_file = candidate
                break
        
        if not model_file:
            return None
        
        with zip_ref.open(model_file) as f:
            model_data = json.load(f)
            standardized = {"name": "Model", "tables": []}
            model_obj = model_data.get("model", model_data)
            for t in model_obj.get("tables", []):
                standardized["tables"].append({
                    "name": t.get("name"),
                    "columns": [c.get("name") for c in t.get("columns", [])],
                    "measures": [m.get("name") for m in t.get("measures", [])],
                    "hierarchies": [h.get("name") for h in t.get("hierarchies", [])]
                })
            return standardized
    except Exception:
        return None


def compare_models(file_a: Path, file_b: Path) -> Dict[str, Any]:
    """
    Perform a deep hierarchical comparison of two PBIP/TMDL models.
    """
    model_a = extract_pbip_model(file_a)
    model_b = extract_pbip_model(file_b)
    
    if not model_a or not model_b:
        return {"error": "Could not extract model data from one or both files."}

    diff = {
        "model_a_name": model_a["name"],
        "model_b_name": model_b["name"],
        "tables": {}
    }

    tables_a = {t["name"]: t for t in model_a["tables"]}
    tables_b = {t["name"]: t for t in model_b["tables"]}

    all_table_names = sorted(list(set(tables_a.keys()) | set(tables_b.keys())))

    for name in all_table_names:
        ta = tables_a.get(name)
        tb = tables_b.get(name)

        if not ta:
            diff["tables"][name] = {"status": "added", "data_b": tb}
        elif not tb:
            diff["tables"][name] = {"status": "removed", "data_a": ta}
        else:
            cols_a = set(ta["columns"])
            cols_b = set(tb["columns"])
            meas_a = set(ta["measures"])
            meas_b = set(tb["measures"])
            hiers_a = set(ta["hierarchies"])
            hiers_b = set(tb["hierarchies"])

            col_diff = {"added": sorted(list(cols_b - cols_a)), "removed": sorted(list(cols_a - cols_b))}
            meas_diff = {"added": sorted(list(meas_b - meas_a)), "removed": sorted(list(meas_a - meas_b))}
            hier_diff = {"added": sorted(list(hiers_b - hiers_a)), "removed": sorted(list(hiers_a - hiers_b))}

            if col_diff["added"] or col_diff["removed"] or meas_diff["added"] or meas_diff["removed"] or hier_diff["added"] or hier_diff["removed"]:
                diff["tables"][name] = {
                    "status": "modified",
                    "columns": col_diff,
                    "measures": meas_diff,
                    "hierarchies": hier_diff,
                    "data_a": ta,
                    "data_b": tb
                }
            else:
                diff["tables"][name] = {"status": "identical", "data_a": ta, "data_b": tb}

    return diff
