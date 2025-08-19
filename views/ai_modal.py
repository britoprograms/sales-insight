
# views/ai_modal.py
from __future__ import annotations
import threading, os
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Button, Label, Log
from services.ai import get_client

SQL_SYSTEM_DEFAULT = (
    "You are an analytics assistant. The data lives in ClickHouse; "
    "return ClickHouse-compatible raw SQL and a one-sentence rationale."
)
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
        self._client = get_client()
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

        def worker():
            text = self._client.ask(prompt, system=SQL_SYSTEM)
            def done():
                try:
                    log.clear()
                    log.write(text or "(empty response)")
                except Exception:
                    pass
                self._busy = False
            self.app.call_from_thread(done)

        threading.Thread(target=worker, daemon=True).start()

    def action_close(self) -> None:
        if not self._busy:
            self.dismiss(None)
