
# views/ai_modal.py
from __future__ import annotations
import asyncio, os
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Button, Label, Log
from services.ai import ensure_client_ready

SQL_SYSTEM_DEFAULT = "SQL assistant. Be concise."  # Minimal system prompt for speed
SQL_SYSTEM = os.getenv("AI_SYSTEM", SQL_SYSTEM_DEFAULT)

class AIModal(ModalScreen[None]):
    """Minimal AI prompt modal."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        ("enter", "submit", "Submit"),  # fallback if focus isn’t in Input
    ]

    def __init__(self, title: str = "Ask AI") -> None:
        super().__init__()
        self._title = title
        self._busy = False

    def compose(self) -> ComposeResult:
        with Vertical(id="ai_modal"):
            with Horizontal():
                yield Label(self._title)
            yield Input(placeholder="Type your question and press Enter…", id="ai_input")
            with Horizontal():
                yield Button("Submit", id="btn_submit", variant="primary")
                yield Button("Close", id="btn_close")
            log = Log(id="ai_log", highlight=True)
            log.can_focus = False
            yield log

    def on_mount(self) -> None:
        # autofocus input
        try:
            self.query_one("#ai_input", Input).focus()
        except Exception:
            pass

    # -------- Submission paths --------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._kickoff(event.value.strip())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_submit":
            prompt = self.query_one("#ai_input", Input).value.strip()
            self._kickoff(prompt)
        elif event.button.id == "btn_close":
            self.action_close()

    def action_submit(self) -> None:
        prompt = self.query_one("#ai_input", Input).value.strip()
        self._kickoff(prompt)

    def _kickoff(self, prompt: str) -> None:
        if self._busy or not prompt:
            return
        self._busy = True
        log = self.query_one("#ai_log", Log)
        log.clear()
        log.write("[b]Thinking…[/b]")

        # Use Textual's native worker method instead of asyncio.create_task
        self.run_worker(self._async_request(prompt, log), exclusive=True)
    
    async def _async_request(self, prompt: str, log: Log) -> None:
        """Async request handler - eliminates threading overhead."""
        import time
        start_time = time.time()
        print(f"DEBUG: Modal async_request started")
        
        try:
            client_start = time.time()
            client = await ensure_client_ready()
            client_time = time.time() - client_start
            print(f"DEBUG: Client ready in {client_time:.3f}s")
            
            ask_start = time.time()
            text = await client.ask(prompt, system=SQL_SYSTEM)
            ask_time = time.time() - ask_start
            print(f"DEBUG: client.ask() completed in {ask_time:.3f}s")
            
            # Update UI directly (no call_from_thread needed)
            log.clear()
            log.write(text or "(empty response)")
            
            total_time = time.time() - start_time
            print(f"DEBUG: Modal total time: {total_time:.3f}s")
        except Exception as e:
            log.clear()
            log.write(f"Error: {str(e)}")
            total_time = time.time() - start_time
            print(f"DEBUG: Modal exception after {total_time:.3f}s: {e}")
        finally:
            self._busy = False

    def action_close(self) -> None:
        if not self._busy:
            self.dismiss(None)
