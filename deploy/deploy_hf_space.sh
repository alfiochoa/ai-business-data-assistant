#!/usr/bin/env bash
# Deploy UI + API to a free Hugging Face Docker Space.
# Requires: HF_TOKEN (write access) and HF_SPACE (e.g. alfiochoa/northstar-goods-assistant).
# Runtime secrets (DATABASE_URL, LLM_API_KEY, ...) are set in the Space UI, NOT here.
set -euo pipefail
: "${HF_TOKEN:?Set HF_TOKEN (https://huggingface.co/settings/tokens, write scope)}"
: "${HF_SPACE:?Set HF_SPACE as <user>/<space-name>}"

root="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

git clone "https://user:${HF_TOKEN}@huggingface.co/spaces/${HF_SPACE}" "$work/space" 2>/dev/null || {
  echo "Space not found. Create it first: huggingface.co/new-space -> SDK: Docker, free CPU basic." >&2; exit 1; }
cd "$work/space"
rm -rf ./* 
cp -r "$root/app" "$root/requirements.txt" "$root/streamlit_app.py" .
mkdir deploy && cp "$root/deploy/start.sh" deploy/ && cp "$root/deploy/Dockerfile" ./Dockerfile
cat > README.md <<'YAML'
---
title: Northstar Goods Payment Loss Assistant
emoji: 💳
sdk: docker
app_port: 7860
pinned: false
---
Fictional portfolio demo. Source: https://github.com/alfiochoa/ai-business-data-assistant
YAML
find . -name __pycache__ -prune -exec rm -rf {} +
git add -A && git -c user.name=deploy -c user.email=deploy@example.com commit -qm "Deploy" || true
git push -q origin main
echo "Pushed. Add the Space secrets listed in deploy/README.md, then restart the Space."
