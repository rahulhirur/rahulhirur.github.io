# DIY Guide: Build Your Own Portfolio AI Chatbot with LLM Failover & Cal.com Scheduling

Step-by-step tutorial to construct and deploy a portfolio website featuring an autonomous AI chatbot widget capable of answering resume questions and booking calendar slots dynamically.

---

## What You Will Build
1. **Frontend**: A personal portfolio site with a floating AI chat widget (HTML5 + Tailwind CSS + JS) hosted on **GitHub Pages**.
2. **Backend Proxy**: A modular **FastAPI** webserver hosted on **Hugging Face Spaces** (Dockerized) to orchestrate queries and secure API keys.
3. **AI Agent**: A **LangChain** tool-calling agent with a custom prompt.
4. **Multi-LLM Failover**: Automatically cascades requests through **Cerebras** (Primary) ➔ **Groq** (Fallback 1) ➔ **OpenAI** (Fallback 2) in case of rate limits or provider downtime.
5. **Calendar Booker**: Integrates with **Cal.com API v2** to search open availability and create Google Meet invites directly from the chat.

---

## Prerequisites
* **Accounts**: GitHub, Hugging Face, Cal.com.
* **API Keys**:
  * Cerebras API Key (Primary)
  * Groq API Key (Fallback 1)
  * OpenAI API Key (Fallback 2)
  * Cal.com API Key & Event Type ID

---

## Step 1: Create the Frontend Layout
Add the floating chat icon, the panels, and the backdrop-blur profile photo modal.

### A. The HTML Markup (`index.html`)
Place this at the bottom of your portfolio body:
```html
<!-- Floating Chat Launcher -->
<button id="chatbot-launcher-btn" class="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-indigo-650 hover:bg-indigo-600 text-white flex items-center justify-center shadow-lg transition-transform hover:scale-105">
    <i class="fas fa-comments text-xl"></i>
</button>

<!-- Chat Widget Panel -->
<div id="chatbot-panel" class="fixed bottom-24 right-6 w-96 max-w-[90vw] h-[500px] z-50 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col opacity-0 pointer-events-none scale-95 transition-all duration-300">
    <!-- Header -->
    <div class="p-4 bg-indigo-600 text-white rounded-t-2xl flex justify-between items-center">
        <span class="font-semibold text-sm">Portfolio Assistant</span>
        <button id="chatbot-close-btn" class="text-white/80 hover:text-white"><i class="fas fa-times"></i></button>
    </div>
    <!-- Messages Stream -->
    <div id="chatbot-messages" class="flex-1 overflow-y-auto p-4 space-y-3"></div>
    <!-- Form -->
    <form id="chatbot-form" class="p-3 border-t border-slate-100 dark:border-slate-900 flex gap-2">
        <input id="chatbot-input" type="text" placeholder="Type a message..." class="flex-1 px-3 py-2 text-sm bg-slate-50 dark:bg-slate-900 border rounded-xl focus:outline-none focus:border-indigo-500 text-slate-800 dark:text-slate-150">
        <button type="submit" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm"><i class="fas fa-paper-plane"></i></button>
    </form>
</div>

<!-- Backdrop-Blurred Profile Lightbox Modal -->
<div id="profile-lightbox" class="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/60 backdrop-blur-md opacity-0 pointer-events-none transition-all duration-300">
    <!-- pointer-events-auto overrides parent wrapper pointer-events-none on hover open -->
    <div class="relative max-w-[90%] max-h-[85%] scale-90 transition-all duration-300 lightbox-content pointer-events-auto">
        <button id="lightbox-close" class="absolute -top-12 right-0 text-white hover:text-indigo-400 text-2xl"><i class="fas fa-times"></i></button>
        <img src="profile.jpg" class="max-w-full max-h-[75vh] rounded-2xl border-2 border-white/20 shadow-2xl object-contain" />
    </div>
</div>
```

### B. JavaScript Interaction (`app.js` / inline script)
To prevent infinite hover loop flickers on the profile photo trigger, toggle `pointer-events` dynamically:
```javascript
const profileTrigger = document.querySelector('.hero-photo-trigger');
const lightbox = document.getElementById('profile-lightbox');
const lightboxContent = lightbox?.querySelector('.lightbox-content');
const lightboxClose = document.getElementById('lightbox-close');

if (profileTrigger && lightbox && lightboxContent) {
    let openedByClick = false;

    const openLightbox = (byClick = false) => {
        openedByClick = byClick;
        lightbox.classList.remove('opacity-0', 'pointer-events-none');
        lightbox.classList.add('opacity-100');
        // Let mouse pointer pass through background during hover so it stays centered
        lightbox.classList.toggle('pointer-events-auto', byClick);
        lightbox.classList.toggle('pointer-events-none', !byClick);
        
        lightboxContent.classList.remove('scale-90');
        lightboxContent.classList.add('scale-100');
    };

    const closeLightbox = () => {
        openedByClick = false;
        lightbox.classList.add('opacity-0', 'pointer-events-none');
        lightbox.classList.remove('opacity-100', 'pointer-events-auto');
        lightboxContent.classList.add('scale-90');
        lightboxContent.classList.remove('scale-100');
    };

    // Taps/clicks lock modal open
    profileTrigger.addEventListener('click', (e) => {
        if (lightbox.classList.contains('opacity-0')) openLightbox(true);
        else closeLightbox();
        e.stopPropagation();
    });

    // PC Hovers open/close modal smoothly
    profileTrigger.addEventListener('mouseenter', () => {
        if (window.matchMedia('(pointer: fine)').matches && lightbox.classList.contains('opacity-0')) {
            openLightbox(false);
        }
    });

    profileTrigger.addEventListener('mouseleave', (e) => {
        if (window.matchMedia('(pointer: fine)').matches && !openedByClick) {
            if (e.relatedTarget && !lightboxContent.contains(e.relatedTarget)) closeLightbox();
        }
    });

    lightboxContent.addEventListener('mouseleave', (e) => {
        if (window.matchMedia('(pointer: fine)').matches && !openedByClick) {
            if (e.relatedTarget !== profileTrigger && !profileTrigger.contains(e.relatedTarget)) closeLightbox();
        }
    });

    lightboxClose?.addEventListener('click', closeLightbox);
    lightbox.addEventListener('click', closeLightbox);
    lightboxContent.addEventListener('click', (e) => e.stopPropagation());
}
```

---

## Step 2: Build the FastAPI Backend

### A. Provider Failover Manager (`providers.py`)
Implement automatic cascading of requests on rate limits or API downfalls:
```python
import os
import time

class ProviderManager:
    def __init__(self):
        self.cooldowns = {}  # Tracks cooled-down providers
        self.priority = ["cerebras", "groq", "openai"]
        
    def get_headers_and_model(self, provider: str) -> tuple:
        # Load API keys from Environment settings
        keys = {
            "cerebras": (os.getenv("CEREBRAS_API_KEY"), "https://api.cerebras.ai/v1", "gpt-oss-120b"),
            "groq": (os.getenv("GROQ_API_KEY"), "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
            "openai": (os.getenv("OPENAI_API_KEY"), "https://api.openai.com/v1", "gpt-4o-mini")
        }
        return keys.get(provider, (None, None, None))

    def resolve_provider(self):
        now = time.time()
        for p in self.priority:
            if p in self.cooldowns and now < self.cooldowns[p]:
                continue # Skip if in cooldown
            api_key, base_url, model = self.get_headers_and_model(p)
            if api_key:
                return p, api_key, base_url, model
        raise Exception("All LLM providers are offline or misconfigured.")

    def trigger_cooldown(self, provider: str):
        self.cooldowns[provider] = time.time() + 300  # 5-minute cooldown
```

---

## Step 3: Implement Cal.com Agents Tools
Create LangChain tools that bind the Cal.com APIs to the LLM agent.

### Cal.com Booking Payload schema (`scheduler.py`)
> [!IMPORTANT]
> Under Cal.com API v2, root-level payloads are strictly schema-verified. Passing custom visitor `notes` at the root level (e.g. `payload["description"]` or `payload["responses"]`) triggers a `400 Bad Request` exception. Answers must be mapped inside `bookingFieldsResponses`.

```python
from langchain_core.tools import tool
import httpx

@tool
def create_booking(name: str, email: str, slot_datetime: str, notes: str = "") -> str:
    """
    Confirm and create a meeting booking with Rahul.
    Args:
        name: Name of visitor.
        email: Email of visitor.
        slot_datetime: ISO string (e.g., '2026-06-25T13:30:00+05:30').
        notes: User agenda/notes.
    """
    headers = {
        "Authorization": f"Bearer {CALCOM_API_KEY}",
        "cal-api-version": "2024-08-13",
        "Content-Type": "application/json",
    }
    
    payload = {
        "eventTypeId": int(CALCOM_EVENT_TYPE_ID),
        "start": slot_datetime,
        "attendee": {"name": name, "email": email, "timeZone": "Asia/Kolkata"},
        "bookingFieldsResponses": {
            "notes": notes  # Correct v2 mapping
        }
    }
    
    try:
        r = httpx.post("https://api.cal.com/v2/bookings", headers=headers, json=payload, timeout=15.0)
        r.raise_for_status()
        booking = r.json().get("data", {})
        return f"Confirmed! Meet link: {booking.get('meetingUrl')}"
    except Exception as e:
        return f"Booking failed: {e}"
```

---

## Step 4: Configure Deployments & Secrets

### A. Dockerizing Hugging Face Spaces (`Dockerfile`)
```dockerfile
FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

### B. CI/CD Pipeline (`.github/workflows/deploy.yml`)
Save this to deploy both frontend and backend automatically:
```yaml
name: Deploy Stack

on:
  push:
    branches: ["main"]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Deploy Frontend to GitHub Pages
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      # ... run deploy-pages action ...

      - name: Force push backend to Hugging Face
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          cd backend
          git init
          git config user.name "actions"
          git config user.email "actions@github.com"
          git add .
          git commit -m "Deploy to Spaces"
          git remote add hf https://user:${HF_TOKEN}@huggingface.co/spaces/username/space-name
          git push --force hf HEAD:main
```

---

## Step 5: Save Keys & test
1. Save `HF_TOKEN` in GitHub Secrets.
2. Paste API keys (`CEREBRAS_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `CALCOM_API_KEY`) inside the Hugging Face Space settings console.
3. Commit and push. Everything is set!
