from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from config import SCHEDULING_ENABLED
from providers import provider_manager
from scheduler import fetch_calcom_slots
from agent import TOOLS, load_system_instruction

# ── Startup Log ───────────────────────────────────────────────────────────────
configured_list = provider_manager.get_configured_providers()
print("=" * 50)
print("  PORTFOLIO AI BACKEND -- STARTUP CONFIG")
print("=" * 50)
print(f"  Configured Providers : {', '.join(configured_list) if configured_list else 'NONE'}")
print(f"  Scheduling           : {'OK (cal.com enabled)' if SCHEDULING_ENABLED else 'DISABLED'}")
print("=" * 50)

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(title="Rahul J Hirur — Portfolio AI Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Model ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list = []   # [{"role": "user"|"model", "text": "..."}]

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    configured = provider_manager.get_configured_providers()
    available = provider_manager.get_available_providers()
    return {
        "status": "online",
        "message": "Rahul J Hirur Portfolio AI Backend is running.",
        "config": {
            "configured_providers": configured,
            "available_providers": available,
            "scheduling_enabled": SCHEDULING_ENABLED,
        },
    }

@app.get("/slots")
def slots_endpoint(date: str, duration: int = 30, timezone: str = "Asia/Kolkata"):
    """
    Return available slots for a given date directly from Cal.com.
    Called by the scheduling mini-form when the user picks a date.
    """
    res = fetch_calcom_slots(date=date, duration=duration, timezone=timezone)
    if "error" in res:
        return {"slots": [], "error": res["error"]}
    return res

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    available_providers = provider_manager.get_available_providers()
    if not available_providers:
        raise HTTPException(
            status_code=500,
            detail="No LLM providers configured. Set API keys in your environment variables.",
        )

    system_instruction = load_system_instruction()

    # Convert frontend history → LangChain message objects
    history_messages = []
    for h in request.history:
        role = h.get("role", "")
        text = h.get("text", "")
        if role == "user":
            history_messages.append(HumanMessage(content=text))
        elif role in ("model", "assistant"):
            history_messages.append(AIMessage(content=text))

    # Build the full message list
    messages = [SystemMessage(content=system_instruction)] + history_messages + [HumanMessage(content=request.message)]

    last_error = None

    for provider in available_providers:
        try:
            api_key, base_url, model_name = provider_manager.resolve_config(provider)
            if not api_key:
                continue

            print(f"[chat] Attempting request with provider '{provider}' using model '{model_name}'...")
            
            # Build LangChain-compatible LLM
            llm = ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model_name,
                temperature=0.7,
            )

            show_schedule_form = False

            if TOOLS:
                # ── Agentic mode: LangGraph react agent with scheduling tools ─
                agent  = create_react_agent(llm, TOOLS)
                result = agent.invoke({"messages": messages})

                # Check if the agent called request_scheduling_form during this turn
                for msg in result["messages"]:
                    if hasattr(msg, "content") and "__SCHEDULE_FORM_REQUESTED__" in str(msg.content):
                        show_schedule_form = True
                        break

                # Last message is always the final AI reply
                ai_response = result["messages"][-1].content
            else:
                # ── Simple chain mode: plain Q&A, no tools ────────────────────
                result      = llm.invoke(messages)
                ai_response = result.content

            response_payload: dict = {"response": ai_response}
            if show_schedule_form:
                response_payload["action"] = "show_schedule_form"
            return response_payload

        except Exception as e:
            print(f"[chat] Provider '{provider}' failed: {e}")
            provider_manager.mark_failed(provider, cooldown_seconds=300)
            last_error = e

    # If all available providers failed
    raise HTTPException(status_code=500, detail=f"All configured LLM providers failed. Last error: {last_error}")
