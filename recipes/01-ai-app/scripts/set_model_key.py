"""Read the provider key without echoing it or placing it in shell history."""

import getpass
from pathlib import Path

path = Path(__file__).resolve().parents[1] / ".secrets" / "model_api_key"
if not path.is_file():
    raise SystemExit("Run python scripts/init_local.py first")
path.write_text(getpass.getpass("Model API key (empty for a trusted keyless endpoint): ").strip())
print("Key saved locally. Recreate the application container after configuration changes.")
