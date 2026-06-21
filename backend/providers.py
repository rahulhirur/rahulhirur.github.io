import os
import time
from typing import List, Dict, Tuple
from config import PROVIDERS

class ProviderManager:
    def __init__(self):
        # provider_name -> timestamp until which it is blocked
        self.cooldowns: Dict[str, float] = {}

    def get_configured_providers(self) -> List[str]:
        """Returns list of providers that have an API key configured in the environment."""
        configured = []
        # Check standard providers
        for p in ["cerebras", "groq", "openai"]:
            cfg = PROVIDERS[p]
            if os.getenv(cfg["api_key_env"]):
                configured.append(p)
        return configured

    def get_available_providers(self) -> List[str]:
        """Returns non-cooldown configured providers, ordered by priority."""
        configured = self.get_configured_providers()
        if not configured:
            return []

        now = time.time()
        available = [p for p in configured if self.cooldowns.get(p, 0) < now]

        # If all configured are in cooldown, reset cooldown to prevent complete failure
        if not available:
            print("[ProviderManager] All configured providers are in cooldown! Resetting cooldowns.")
            self.cooldowns.clear()
            return configured

        return available

    def mark_failed(self, provider: str, cooldown_seconds: int = 300):
        self.cooldowns[provider] = time.time() + cooldown_seconds
        print(f"[ProviderManager] Provider '{provider}' marked failed. Cooldown for {cooldown_seconds}s.")

    def resolve_config(self, provider: str) -> Tuple[str, str, str]:
        """Returns (api_key, base_url, model_name) for the given provider."""
        cfg = PROVIDERS[provider]
        api_key = os.getenv(cfg["api_key_env"])
        _prefix = provider.upper()
        base_url = os.getenv(f"{_prefix}_BASE_URL") or cfg["default_url"]
        model_name = os.getenv(f"{_prefix}_MODEL") or os.getenv("MODEL_NAME") or cfg["default_model"]
        return api_key, base_url, model_name

provider_manager = ProviderManager()
