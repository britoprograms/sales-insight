# app.py — Textual TUI with left sidebar, status bar, and reliable One‑Pager routing

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Static, ListView, ListItem, Label
from textual.reactive import reactive

from config import load_config
from themes import ORDER
from store import Store
from views.decliners import DeclinersView
from views.onepager import OnePagerView
from views.formulas import FORMULAS, FormulaModal
from views.growers import GrowersView   # <--- add


# Left‑nav items: label -> view_id
NAV_ITEMS = [
    ("Decliners", "decliners"),
    ("Growers", "growers"),
    ("One‑Pager", "onepager"),
    ("Actions (placeholder)", "actions"),
    ("Impact (placeholder)", "impact"),
    ("Settings", "settings"),
]


class YoYApp(App):
    """YoY Sales TUI with left nav and right content (mock mode by default)."""

    CSS = """
    Screen.theme-mono { background: #000000; color: #FFFFFF; }
    Screen.theme-matrix { background: #000000; color: #00FF7F; }
    Screen.theme-light { background: #FFFFFF; color: #111111; }

    #layout { height: 1fr; }
    #sidebar { width: 28; border: heavy white; }
    .nav-title { padding: 1 1; }

    #content { height: 1fr; padding: 1; }
    #panel { height: 1fr; }
    #statusbar { height: 1; color: #AAAAAA; }

    Footer { dock: bottom; }
    """
    def _refocus_nav(self):
    # Refocus a few times to beat the browser stealing focus
        def do():
            try:
                self.query_one("#nav").focus()
            except Exception:
                pass
        self.set_timer(0.05, do)
        self.set_timer(0.20, do)
        self.set_timer(0.50, do)

    # Only Esc quits the app. `q` does NOT quit.
    # Add global b/v so charts work even if focus isn't on the One‑Pager widget.
    BINDINGS = [
        ("escape", "quit", "Quit"),
        ("t", "cycle_theme", "Theme"),
        ("r", "refresh", "Refresh"),
        ("f", "show_formulas", "Formulas"),
        ("b", "chart_browser", "Browser Chart"),
    ]

    theme_name = reactive("mono")
    current_view = reactive("decliners")

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.store = Store(self.cfg)
        self._last_customer = None  # type: str | None
        self.panel = None           # type: Vertical | None
        self.statusbar = None       # type: Static | None

    # -------- Theming --------
    def watch_theme_name(self, _: str) -> None:
        self._apply_theme()

    def _apply_theme(self) -> None:
        for cls in ("theme-mono", "theme-matrix", "theme-light"):
            self.remove_class(cls)
        self.add_class(f"theme-{self.theme_name}")

    # -------- Layout --------
    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            # Left navigation
            with Vertical(id="sidebar"):
                yield Static("Reports", classes="nav-title")
                items = [ListItem(Label(label), id=f"nav-{vid}") for label, vid in NAV_ITEMS]
                # IMPORTANT: pass items via splat so we don't append during compose
                yield ListView(*items, id="nav")

            # Right content area
            with Vertical(id="content"):
                self.panel = Vertical(id="panel")     # where views mount
                yield self.panel
                self.statusbar = Static("", id="statusbar")
                yield self.statusbar

        yield Footer()

    def on_mount(self) -> None:
        self._apply_theme()
        # Select the first nav item and show Decliners
        self.query_one("#nav", ListView).index = 0
        self._show("decliners")
        self._status("Ready. ↑/↓ to select • Enter on a decliner opens One‑Pager • f formulas • b/v charts")

    # -------- Nav + Routing --------
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        view_id = item_id.replace("nav-", "")
        self._show(view_id)

    def _clear_panel(self) -> None:
        if self.panel:
            self.panel.remove_children()

    def _status(self, message: str) -> None:
        try:
            if self.statusbar:
                self.statusbar.update(message)
        except Exception:
            pass

    def _show(self, view_id: str) -> None:
        self.current_view = view_id
        self._clear_panel()

        if view_id == "decliners":
            # Pass NON‑ASYNC callback so the table can call it safely on Enter
            self.panel.mount(DeclinersView(self.store, self._open_onepager, self.theme_name))
            self._status("Decliners loaded. Select a row and press Enter.")
        elif view_id == "growers":  # <--- add this block
            self.panel.mount(GrowersView(self.store, self._open_onepager, self.theme_name))
            self._status("Growers loaded. Select a row and press Enter.")
        elif view_id == "onepager":
            if self._last_customer:
                self.panel.mount(OnePagerView(self.store, self._last_customer, self.theme_name))
                self._status(f"One‑Pager for {self._last_customer}. Press f for formulas; b/v for charts.")
            else:
                self.panel.mount(Static("Open a customer from Decliners first (Enter)."))
                self._status("No customer selected yet.")
        elif view_id == "actions":
            self.panel.mount(Static("Actions (placeholder) — coming soon"))
            self._status("Actions placeholder.")
        elif view_id == "impact":
            self.panel.mount(Static("Impact (placeholder) — pre vs post YoY uplift"))
            self._status("Impact placeholder.")
        elif view_id == "settings":
            mode = "DB" if self.store.client else "MOCK"
            info = [
                f"Mode: {mode}",
                f"ClickHouse URL: {self.cfg.ch_url or '(unset)'}",
                f"Database: {self.cfg.ch_database}",
                f"User: {self.cfg.ch_user or '(unset)'}",
                f"AI Provider: {self.cfg.ai_provider or '(unset)'}",
            ]
            self.panel.mount(Static("\n".join(info)))
            self._status("Settings loaded.")
        else:
            self.panel.mount(Static("Unknown view."))
            self._status("Unknown view id.")

    # Called by DeclinersView when Enter is pressed
    def _open_onepager(self, customer_id: str) -> None:
        self._last_customer = customer_id
        self._status(f"Opening One‑Pager for {customer_id}…")
        # Flip left‑nav selection to "One‑Pager"
        nav = self.query_one("#nav", ListView)
        for i, (_, vid) in enumerate(NAV_ITEMS):
            if vid == "onepager":
                nav.index = i
                break
        # Mount the One‑Pager
        self._show("onepager")

    # -------- App-level chart actions (global b/v) --------
    def _onepager_widget(self):
        if self.current_view != "onepager":
            return None
        try:
            return self.panel.query_one(OnePagerView)
        except Exception:
            return None


    def action_chart_webview(self) -> None:
        op = self._onepager_widget()
        if op:
            try:
                op.action_chart_webview()
            except Exception as e:
                self._status(f"Chart error: {e}")
            finally:
                self._refocus_nav()  # <-- add this
        else:
            self._status("Open a One‑Pager first (Enter on a decliner).")

    # -------- Other actions --------
    def action_cycle_theme(self) -> None:
        i = ORDER.index(self.theme_name) if self.theme_name in ORDER else 0
        i = (i + 1) % len(ORDER)
        self.theme_name = ORDER[i]
        self._status(f"Theme: {self.theme_name}")

    def action_refresh(self) -> None:
        if self.current_view == "decliners":
            try:
                self._show("decliners")
            except Exception:
                pass
        elif self.current_view == "onepager" and self._last_customer:
            self._show("onepager")

    def action_show_formulas(self) -> None:
        ctx = "onepager_headline" if self.current_view == "onepager" else "decliners"
        text = FORMULAS.get(ctx, "# Formulas\nNo formulas registered for this view yet.")
        self.push_screen(FormulaModal(text))


if __name__ == "__main__":
    YoYApp().run()

