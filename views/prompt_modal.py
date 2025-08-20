# views/prompt_modal.py
from __future__ import annotations
from typing import Callable, Optional
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Input, Button, Label
from textual.containers import Vertical, Horizontal

class PromptModal(ModalScreen[None]):
    DEFAULT_CSS = """
    PromptModal { align: center middle; }
    #wrap { width: 70%; padding: 1 2; background: $panel; }
    #prompt { width: 100%; }
    """

    def __init__(self, title: str = "Prompt", placeholder: str = "", on_submit: Optional[Callable[[str | None], None]] = None):
        super().__init__()
        self._title = title
        self._placeholder = placeholder
        self._on_submit = on_submit
        self._input: Input | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="wrap"):
            yield Label(self._title)
            self._input = Input(placeholder=self._placeholder, id="prompt")
            yield self._input
            with Horizontal():
                yield Button("OK", id="ok")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        try: self.set_focus(self._input)
        except: pass

    def _do_submit(self) -> None:
        value = self._input.value if self._input else None
        cb = self._on_submit
        if callable(cb):
            try: cb(value)
            except Exception: pass
        # We dismiss last; app schedules the loader/result AFTER we’re closed
        self.dismiss(None)

    def key_enter(self) -> None:
        self._do_submit()

    def key_escape(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self._do_submit()
        else:
            self.dismiss(None)

