# services/ai.py
from __future__ import annotations
import os, requests
from typing import Optional

DEFAULT_BASE = os.getenv("AI_BASE_URL", "http://10.8.29.155:8000/v1")
DEFAULT_MODEL = os.getenv("AI_MODEL", "qwen2.5")
DEFAULT_KEY = os.getenv("AI_API_KEY", "sk-local")

class AIClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE,
        api_key: str = DEFAULT_KEY,
        model: str = DEFAULT_MODEL,
        timeout: float = 20.0,
    ) -> None:
        self.base = base_url.rstrip("/")
        self.key = api_key
        self.model = model
        self.timeout = timeout
        self._sess = requests.Session()
        self._sess.headers.update({"Authorization": f"Bearer {self.key}"})

    def ask(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Calls /v1/chat/completions on an OpenAI-compatible server.
        Returns model text or a readable error string.
        """
        url = f"{self.base}/chat/completions"
        data = {
            "model": self.model,
            "messages": (
                [{"role": "system", "content": system}] if system else []
            ) + [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        try:
            r = self._sess.post(url, json=data, timeout=self.timeout)
            r.raise_for_status()
            j = r.json()
            return j["choices"][0]["message"]["content"]
        except requests.Timeout:
            return "AI error: request timed out. Is the local server reachable?"
        except Exception as e:
            try:
                msg = r.text  # type: ignore[name-defined]
            except Exception:
                msg = repr(e)
            return f"AI error: {msg}"

def get_client() -> AIClient:
    return AIClient()

