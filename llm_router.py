"""Multi-provider LLM router: tries free-tier providers in order, automatically
skipping any that are rate-limited/exhausted (tracked with a cooldown), and only
falls back to a paid provider (Kimi) as a last resort. Each provider is used
within its own free tier under its own account -- this is normal multi-provider
usage, not a workaround of anything.
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

COOLDOWN_FILE = Path(__file__).parent / "config" / "provider_cooldowns.json"
COOLDOWN_SECONDS = 6 * 3600  # skip an exhausted provider for 6 hours before retrying

# Ordered by priority: free, generous, reliable providers first. Kimi (paid) is last.
PROVIDERS = [
    {"name": "groq", "env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1", "model": "openai/gpt-oss-20b"},
    {"name": "cerebras", "env": "CEREBRAS_API_KEY", "base_url": "https://api.cerebras.ai/v1", "model": "llama-3.3-70b"},
    {"name": "sambanova", "env": "SAMBANOVA_API_KEY", "base_url": "https://api.sambanova.ai/v1", "model": "Meta-Llama-3.3-70B-Instruct"},
    {"name": "nvidia", "env": "NVIDIA_API_KEY", "base_url": "https://integrate.api.nvidia.com/v1", "model": "meta/llama-3.3-70b-instruct"},
    {"name": "openrouter", "env": "OPENROUTER_API_KEY", "base_url": "https://openrouter.ai/api/v1", "model": "openai/gpt-oss-20b:free"},
    {"name": "google", "env": "GOOGLE_AI_STUDIO_API_KEY", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-flash-latest"},
    {"name": "mistral", "env": "MISTRAL_API_KEY", "base_url": "https://api.mistral.ai/v1", "model": "open-mistral-nemo"},
    {"name": "deepseek", "env": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    {"name": "deepinfra", "env": "DEEPINFRA_API_KEY", "base_url": "https://api.deepinfra.com/v1/openai", "model": "meta-llama/Meta-Llama-3.1-8B-Instruct"},
    {"name": "fireworks", "env": "FIREWORKS_API_KEY", "base_url": "https://api.fireworks.ai/inference/v1", "model": "accounts/fireworks/models/llama-v3p1-8b-instruct"},
    {"name": "alibaba", "env": "ALIBABA_CLOUD_API_KEY", "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "model": "qwen-turbo"},
    {"name": "zai", "env": "ZAI_API_KEY", "base_url": "https://api.z.ai/api/paas/v4", "model": "glm-4.5-flash"},
    {"name": "kimi", "env": "KIMI_API_KEY", "base_url": "https://api.moonshot.ai/v1", "model": "moonshot-v1-8k", "paid": True},
]


def _load_cooldowns() -> dict:
    if COOLDOWN_FILE.exists():
        try:
            return json.loads(COOLDOWN_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cooldowns(cooldowns: dict) -> None:
    COOLDOWN_FILE.parent.mkdir(exist_ok=True)
    COOLDOWN_FILE.write_text(json.dumps(cooldowns, indent=2), encoding="utf-8")


def _mark_exhausted(name: str) -> None:
    cooldowns = _load_cooldowns()
    cooldowns[name] = time.time() + COOLDOWN_SECONDS
    _save_cooldowns(cooldowns)


def _is_in_cooldown(name: str, cooldowns: dict) -> bool:
    until = cooldowns.get(name)
    return bool(until and time.time() < until)


def generate(prompt: str, system: str = None) -> str:
    """Try each provider in priority order, skipping ones in cooldown or missing a key."""
    cooldowns = _load_cooldowns()
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]

    errors = []
    for provider in PROVIDERS:
        api_key = os.environ.get(provider["env"])
        if not api_key:
            continue
        if _is_in_cooldown(provider["name"], cooldowns):
            continue

        try:
            client = OpenAI(api_key=api_key, base_url=provider["base_url"])
            response = client.chat.completions.create(
                model=provider["model"],
                messages=messages,
                timeout=30,
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                print(f"[llm_router] {provider['name']} returned empty content, trying next provider")
                errors.append(f"{provider['name']}: empty response")
                continue
            print(f"[llm_router] used provider: {provider['name']}" + (" (paid)" if provider.get("paid") else ""))
            return content
        except Exception as e:
            msg = str(e).lower()
            if any(term in msg for term in ["rate limit", "quota", "429", "insufficient_quota", "too many requests"]):
                print(f"[llm_router] {provider['name']} exhausted, cooling down for {COOLDOWN_SECONDS/3600:.0f}h")
                _mark_exhausted(provider["name"])
            else:
                print(f"[llm_router] {provider['name']} failed: {e}")
            errors.append(f"{provider['name']}: {e}")
            continue

    raise RuntimeError("All providers exhausted or failed:\n" + "\n".join(errors))


if __name__ == "__main__":
    import sys
    prompt_arg = sys.argv[1] if len(sys.argv) > 1 else "Say hello in one short sentence."
    print(generate(prompt_arg))
