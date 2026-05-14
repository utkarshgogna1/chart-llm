# Deploying to Streamlit Community Cloud

Streamlit Community Cloud is free and requires no server configuration.

## Steps

**1. Push the repo to GitHub** (already done).

**2. Go to [share.streamlit.io](https://share.streamlit.io)** and click **"New app"**.

**3. Connect your repo:**
- Repository: `utkarshgogna1/chart-llm`
- Branch: `main`
- Main file path: `app.py`

**4. Add secrets** under **Settings → Secrets** using the same `KEY = "value"` format as a `.env` file:

```toml
GEMINI_API_KEY = "your-key-here"
GROQ_API_KEY   = "your-key-here"
```

**5. Click Deploy.** Streamlit reads `pyproject.toml` and installs dependencies automatically. `vl-convert-python` is a pure-Rust wheel — no `packages.txt` or system dependencies needed. The public URL is shareable immediately.

## Cloud limitations

**Ollama is not available on Streamlit Cloud.** The `llama-8b-local` model requires a local Ollama process (`http://localhost:11434`), which cannot run in a hosted environment. The cloud demo will only work with `gemini-flash` and `llama-70b-groq`.

If you select `llama-8b-local` in the cloud UI, the app will raise a connection error on the first generate call. Set the `OLLAMA_BASE_URL` environment variable to a remotely accessible Ollama instance if you need it from the cloud.

## Local alternative

```bash
uv sync
cp .env.example .env   # fill in GROQ_API_KEY
uv run streamlit run app.py
```
