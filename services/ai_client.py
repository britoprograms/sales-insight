# services/ai_client.py
from __future__ import annotations
import os, json, requests
from typing import List, Dict, Any, Optional

class LLMClient:
    """
    Minimal OpenAI-compatible chat client.
    Works with: llama.cpp server (--server), vLLM OpenAI API server, LM Studio, Oobabooga (OpenAI ext), etc.
    """

    def __init__(self, base_url: str, model: str, api_key: Optional[str] = None, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.getenv("AI_API_KEY", "sk-local")
        self.timeout = timeout
        self._chat_url = f"{self.base_url}/chat/completions"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 1200) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:  # many local servers just ignore it
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,   # keep simple for TUI
        }
        r = requests.post(self._chat_url, headers=headers, data=json.dumps(payload), timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]

    # ---------- domain helpers (ready to call from views) ----------

    def suggest_root_causes(self, customer_id: str, pvm: Dict[str, Any], cadence: Dict[str, Any], geo: Dict[str, Any]) -> str:
        sys = (
            "You are a retail analytics copilot. "
            "Data lives in ClickHouse; when proposing insights, include ClickHouse SQL that can reproduce the metric. "
            "Use the PVM (Price/Volume/Mix), returns, cadence, and geo frames. "
            "Output sections: Summary, Root-Cause Tags, Recommended Actions, SQL."
        )
        usr = f"""
Customer: {customer_id}
Context:
PVM={json.dumps(pvm, default=str)}
Cadence={json.dumps(cadence, default=str)}
Geography={json.dumps(geo, default=str)}

Task: Explain YoY change, tag root causes (price, volume, mix, returns, cadence, geography, substitution), and propose actions for Buy/Sales/Ops.
Also include concrete ClickHouse SQL queries to reproduce each cited metric (use the customer_weekly_sales table).
"""
        return self.chat(
            [{"role": "system", "content": sys}, {"role": "user", "content": usr}],
            temperature=0.15,
            max_tokens=1600,
        )

    def generate_sql(self, question: str, schema_hint: str = "table: customer_weekly_sales") -> str:
        sys = (
            "You generate ClickHouse SQL only. Use raw SQL; avoid CTEs if simple is enough. "
            "Prefer stable column names and include comments. Return ONLY SQL in a fenced code block."
        )
        usr = f"Schema hint: {schema_hint}\nUser question: {question}\nReturn SQL only."
        return self.chat([{"role":"system","content":sys},{"role":"user","content":usr}], temperature=0.0, max_tokens=800)

    def recommend_actions(self, signals: Dict[str, Any]) -> str:
        sys = (
            "You are an action planner. Given tagged root causes, map actions to Buy, Sales, Ops. "
            "Return a concise checklist with owners and a 4–8 week measurement plan."
        )
        usr = json.dumps(signals, default=str)
        return self.chat([{"role":"system","content":sys},{"role":"user","content":usr}], temperature=0.2, max_tokens=800)

