# Deploying to a free Hugging Face Space

One Docker Space runs both the Streamlit UI (public, port 7860) and the
FastAPI backend (internal, port 8000). Free CPU basic tier is enough.

## What you must provide

| Key | Where it goes | Where to get it (all free) |
|---|---|---|
| `HF_TOKEN` | your shell, when running the deploy script | huggingface.co/settings/tokens (write scope) |
| `HF_SPACE` | your shell, `<user>/<space-name>` | create an empty Docker Space at huggingface.co/new-space |
| `DATABASE_URL` | Space → Settings → Secrets | free Supabase project (see main README) |
| `LLM_API_KEY` | Space → Settings → Secrets | free Groq key, console.groq.com/keys |
| `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_API_KEY`, `LLM_FALLBACK_MODEL` (optional) | Space → Secrets | e.g. `https://router.huggingface.co/v1`, an HF token, `meta-llama/Llama-3.3-70B-Instruct` |

Optional overrides: `LLM_BASE_URL`, `LLM_MODEL`.

## Deploy

```bash
export HF_TOKEN=hf_... HF_SPACE=<user>/<space-name>
./deploy/deploy_hf_space.sh
```

Then add the secrets above in the Space settings and restart it. Load the
synthetic data into Supabase once, from your machine (`scripts/load_data.py`).
