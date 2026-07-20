import requests

from lib.config import AGENT_API_BASE_URL, AGENT_API_KEY, AGENT_MODEL, require_agent_api
from lib.logger import get_logger

log = get_logger("llm_client")


def chat_completion(system_prompt: str, user_prompt: str, *, temperature: float = 0.4, timeout: int = 240) -> str:
    """OpenAI-compatible /chat/completions call. Returns the raw text content."""
    require_agent_api()

    url = f"{AGENT_API_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AGENT_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": AGENT_MODEL,
        "temperature": temperature,
        "stream": False,  # this gateway streams SSE by default even when unset
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    log.info("Calling AGENT API (%s, model=%s)", url, AGENT_MODEL)
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
