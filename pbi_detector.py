import os
from pathlib import Path
from typing import List, Dict

def get_open_pbi_models() -> List[Dict[str, str]]:
    """
    Scans the local AppData directory for open Power BI Desktop models.
    Returns a list of dictionaries containing the port and a generated name.
    """
    # The default path where Power BI Desktop stores its local SSAS instances
    app_data = os.getenv('LOCALAPPDATA')
    if not app_data:
        return []

    root = Path(app_data) / "Microsoft"
    if not root.exists():
        return []

    open_models = []
    search_dirs = list(root.glob("**/AnalysisServicesWorkspaces"))
    if not search_dirs:
        search_dirs = list(root.glob("**/AnalysisServicesWorkspace*"))

    for workspace_dir in search_dirs:
        # Power BI creates folders like AnalysisServicesWorkspace<random_id>
        # Inside, there is a Data folder with msmdsrv.port.txt
        port_files = workspace_dir.glob("*/Data/msmdsrv.port.txt")
        for port_file in port_files:
            workspace_root = port_file.parents[1]
            try:
                with open(port_file, 'r', encoding='utf-16le') as f:
                    port = f.read().strip()
                    if port:
                        open_models.append({
                            "port": port,
                            "name": f"Power BI Model (Port {port})",
                            "workspace": str(workspace_root),
                        })
            except UnicodeDecodeError:
                # Fallback if the file is not utf-16le
                try:
                    with open(port_file, 'r', encoding='utf-8') as f:
                        port = f.read().strip()
                        if port:
                            open_models.append({
                                "port": port,
                                "name": f"Power BI Model (Port {port})",
                                "workspace": str(workspace_root),
                            })
                except Exception:
                    pass
            except Exception:
                pass

    return open_models
