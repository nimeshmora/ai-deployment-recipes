"""Create local secrets without overwriting existing values. Run from recipe directory."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / ".secrets"
folder.mkdir(mode=0o700, exist_ok=True)
if os.name != "nt":
    folder.chmod(0o700)
for name, content in (("app_token", secrets.token_urlsafe(32)), ("model_api_key", "")):
    target = folder / name
    try:
        with target.open("x") as file:
            file.write(content)
    except FileExistsError:
        pass
    # Compose bind mounts preserve host ownership. Non-root container must read files.
    # Host parent directory remains owner-only; review ACLs separately on Windows.
    if os.name != "nt":
        target.chmod(0o644)
print("Local secret files ready. Existing values preserved. See .secrets/app_token.")
