---
title: Rahul J Hirur Portfolio AI Backend
emoji: 🤖
colorFrom: indigo
colorTo: violet
sdk: docker
app_port: 7860
pinned: false
---

# Portfolio AI Chatbot Backend

A provider-agnostic FastAPI backend proxy for Rahul J Hirur's Portfolio AI Chatbot widget. It utilizes the standard OpenAI SDK format, allowing you to connect it to **any LLM provider** (Cerebras, Mistral, Groq, OpenAI, DeepSeek, OpenRouter, etc.) by setting simple environment variables.

## Local Development with `uv`
1. Sync dependencies and set up the locked virtual environment:
   ```bash
   uv sync
   ```
2. Set environment variables in your terminal:
   - **For PowerShell (e.g. Cerebras)**:
     ```powershell
     $env:API_KEY="your_cerebras_api_key"
     $env:API_BASE_URL="https://api.cerebras.ai/v1"
     $env:MODEL_NAME="llama3.1-8b"
     ```
   - **For PowerShell (e.g. Groq)**:
     ```powershell
     $env:API_KEY="your_groq_api_key"
     $env:API_BASE_URL="https://api.groq.com/openai/v1"
     $env:MODEL_NAME="llama3-8b-8192"
     ```
   - **For PowerShell (e.g. OpenAI)**:
     ```powershell
     $env:OPENAI_API_KEY="your_openai_api_key"
     $env:MODEL_NAME="gpt-4o-mini"
     ```
3. Run the server locally:
   ```bash
   uv run uvicorn app:app --reload
   ```

---

## Hugging Face Spaces Deployment
Hugging Face automatically reads `requirements.txt` to provision dependencies in its container runtime.

### 1. Upload files
Upload `app.py` and `requirements.txt` to your FastAPI Space repository.

### 2. Configure Environment Variables / Secrets
Go to your Space's **Settings** tab and configure your secrets:
- **`API_KEY`** (or `OPENAI_API_KEY`): *Required*. Set your provider's API key.
- **`API_BASE_URL`** (or `OPENAI_BASE_URL`): *Optional*. Defaults to `https://api.openai.com/v1`. Override this with your provider's base endpoint.
- **`MODEL_NAME`**: *Optional*. Defaults to `gpt-4o-mini`. Set to the model identifier you wish to use.
