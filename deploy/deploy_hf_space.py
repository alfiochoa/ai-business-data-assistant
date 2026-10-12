"""Deploy UI + API to a free Hugging Face Docker Space and set its secrets.

Reads HF_TOKEN, HF_SPACE (default: <user>/northstar-goods-assistant), and the
runtime secrets DATABASE_URL, LLM_API_KEY (+ optional LLM_BASE_URL, LLM_MODEL,
LLM_FALLBACK_*) from the environment (e.g. `set -a; . ./.env`). Secrets go to
the Space via the HF API, never into git or the uploaded files.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ["DATABASE_URL", "LLM_API_KEY"]
OPTIONAL = ["LLM_BASE_URL", "LLM_MODEL", "LLM_FALLBACK_BASE_URL", "LLM_FALLBACK_API_KEY", "LLM_FALLBACK_MODEL"]

README = """---
title: Northstar Goods Payment Loss Assistant
emoji: 💳
sdk: docker
app_port: 7860
pinned: false
---
Fictional portfolio demo with synthetic data. Source: https://github.com/alfiochoa/ai-business-data-assistant
"""


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("Set HF_TOKEN (write scope).")
    api = HfApi(token=token)
    space = os.environ.get("HF_SPACE") or f"{api.whoami()['name']}/northstar-goods-assistant"
    missing = [k for k in SECRETS if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing env: {', '.join(missing)}")

    api.create_repo(space, repo_type="space", space_sdk="docker", exist_ok=True)
    for key in SECRETS + [k for k in OPTIONAL if os.environ.get(k)]:
        api.add_space_secret(space, key, os.environ[key])

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        shutil.copytree(ROOT / "app", out / "app", ignore=shutil.ignore_patterns("__pycache__"))
        (out / "deploy").mkdir()
        shutil.copy(ROOT / "deploy" / "start.sh", out / "deploy" / "start.sh")
        shutil.copy(ROOT / "deploy" / "Dockerfile", out / "Dockerfile")
        shutil.copy(ROOT / "requirements.txt", out / "requirements.txt")
        shutil.copy(ROOT / "streamlit_app.py", out / "streamlit_app.py")
        (out / "README.md").write_text(README)
        api.upload_folder(folder_path=str(out), repo_id=space, repo_type="space", commit_message="Deploy")
    owner, name = space.split("/")
    print(f"Deployed: https://huggingface.co/spaces/{space}  (app: https://{owner}-{name}.hf.space)")


if __name__ == "__main__":
    main()
