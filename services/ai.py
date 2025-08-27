# services/ai.py
from __future__ import annotations
import os, asyncio
import httpx
from typing import Optional

# Load .env file explicitly to ensure environment variables are available
def _load_env():
    """Explicitly load .env file if it exists."""
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

# Ensure .env is loaded
_load_env()

DEFAULT_BASE = os.getenv("AI_BASE_URL", "http://localhost:8080/v1")
DEFAULT_MODEL = os.getenv("AI_MODEL", "Meta-Llama-3-8B-Instruct-Q5_K_M")
DEFAULT_KEY = os.getenv("AI_API_KEY", "sk-local")

class AIClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE,
        api_key: str = DEFAULT_KEY,
        model: str = DEFAULT_MODEL,
        timeout: float = 120.0,
    ) -> None:
        self.base = base_url.rstrip("/")
        self.key = api_key
        self.model = model
        self.timeout = timeout
        # Use httpx async client with simple configuration
        base_headers = {"Connection": "keep-alive"}
        if self.key and self.key.strip():
            base_headers["Authorization"] = f"Bearer {self.key}"
        
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=2, max_connections=5),
            headers=base_headers,
            http2=False,
            verify=False  # Disable SSL verification for localhost
        )

    async def ask(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Calls /v1/chat/completions on an OpenAI-compatible server.
        Returns model text or a readable error string.
        """
        url = f"{self.base}/chat/completions"
        # Optimize: Minimize system prompt overhead - only add if really needed
        messages = [{"role": "user", "content": prompt}]
        if system and len(system.strip()) > 10:  # Only add substantial system prompts
            messages = [{"role": "system", "content": system}] + messages
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,  # Zero temperature for fastest generation
            "max_tokens": 200,   # Increased for action generation
            "top_p": 0.8,       # Focus on most likely tokens  
            "stream": False,    # Non-streaming
        }
        
        try:
            r = await self._client.post(url, json=data)
            r.raise_for_status()
            j = r.json()
            
            return j["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            return "AI error: request timed out. Is the local server reachable?"
        except KeyError as e:
            try:
                response_text = r.text
                return f"AI error: Unexpected response format. Missing key {e}. Response: {response_text[:200]}..."
            except Exception:
                return f"AI error: Unexpected response format. Missing key {e}"
        except httpx.RequestError as e:
            return f"AI error: Request failed - {str(e)}"
        except Exception as e:
            try:
                msg = r.text  # type: ignore[name-defined]
                return f"AI error: {str(e)} - Response: {msg[:200]}..."
            except Exception:
                return f"AI error: {repr(e)}"
    
    async def generate_sales_actions(self, customer_id: str, customer_data: dict) -> str:
        """
        Generate recommended sales actions for a specific customer.
        Acts as a sales analyst focused on actionable business recommendations.
        """
        # Sales analyst system prompt
        system_prompt = (
            "You are a senior sales analyst. Based on customer performance data, "
            "provide at least 3 specific, actionable recommendations that a sales team can implement immediately. "
            "Focus on practical actions like pricing adjustments, targeted outreach, product positioning, "
            "inventory management, or relationship building. Be concise and specific. "
            "Format as a numbered list with brief, actionable statements."
        )
        
        # Create user prompt with customer context
        cy_sales = customer_data.get('cy_sales', 0)
        py_sales = customer_data.get('py_sales', 0)
        yoy_delta = customer_data.get('yoy_delta', 0)
        yoy_pct = customer_data.get('yoy_pct', 0)
        
        performance_context = "growing" if yoy_delta > 0 else "declining"
        
        user_prompt = f"""
Customer: {customer_id}
Current Year Sales: ${cy_sales:,.0f}
Previous Year Sales: ${py_sales:,.0f}
YoY Change: ${yoy_delta:,.0f} ({yoy_pct:+.1f}%)
Performance: {performance_context}

Generate specific sales actions for this {performance_context} customer.
        """.strip()
        
        return await self.ask(user_prompt, system_prompt)
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

# Global singleton client instance
_client_instance = None

def get_client() -> AIClient:
    """Get singleton AI client instance to avoid recreation overhead."""
    global _client_instance
    if _client_instance is None:
        _client_instance = AIClient()
    return _client_instance

async def ensure_client_ready() -> AIClient:
    """Ensure client is ready and optionally pre-warm connection."""
    client = get_client()
    return client

