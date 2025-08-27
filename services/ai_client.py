# services/ai_client.py
from __future__ import annotations
import os, json, requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    """
    Minimal OpenAI-compatible chat client.
    Works with: llama.cpp server (--server), vLLM OpenAI API server, LM Studio, Oobabooga (OpenAI ext), etc.
    """
    def __init__(self, base_url=os.getenv("AI_BASE_URL", "http://localhost:8080/v1"), model=os.getenv("AI_MODEL", "Meta-Llama-3-8B-Instruct-Q5_K_M"), api_key=os.getenv("AI_API_KEY", ""), timeout=30):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self._chat_url = f"{self.base_url}/chat/completions"
        self._completions_url = f"{self.base_url}/completions"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 1200) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key.strip():  # only add if non-empty
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Try /chat/completions first
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,  # keep simple for TUI
        }
        try:
            r = requests.post(self._chat_url, headers=headers, data=json.dumps(payload), timeout=self.timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            # Fallback to /completions with Llama-3 prompt format
            prompt = ""
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                prompt += f"<|start_header_id|>{role}<|end_header_id|>\n{content}<|eot_id|>"
            prompt += "<|start_header_id|>assistant<|end_header_id|>\n"
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            r = requests.post(self._completions_url, headers=headers, data=json.dumps(payload), timeout=self.timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["text"]

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