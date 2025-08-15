
# app.py — TUI with permanent live Dashboard (top) + tabbed reports (bottom)

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Static, ListView, ListItem, Label
from textual.reactive import reactive

from config import load_config
from themes import ORDER
from store import Store
from views.decliners import DeclinersView
from views.growers import GrowersView
from views.onepager import OnePagerView
from views.formulas import FORMULAS, FormulaModal
from views.dashboard import Dashboard


# Left nav items (Dashboard is permanent now, so it’s not a tab)
NAV_ITEMS = [
    ("Decliners", "decliners"),
    ("Growers", "growers"),
    ("One‑Pager", "onepager"),
    ("Actions (placeholder)", "actions"),
    ("Impact (placeholder)", "impact"),
    ("Settings", "settings"),
]


class YoYApp(App):
    """YoY Sales TUI: permanent Dashboard on top; tabbed content below."""

    CSS = """
    Screen.theme-mono { background: #000000; color: #FFFFFF; }
    Screen.theme-matrix { background: #000000; color: #00FF7F; }
    Screen.theme-light { background: #FFFFFF; color: #111111; }

    #layout { height: 1fr; }

    #sidebar { width: 28; border: heavy white; }
    .nav-title { padding: 1 1; }

    #content { height: 1fr; padding: 0; }

    /* Permanent top dashboard area (adjust height to taste) */
    #top_chart { height: 35%; min-height: 8; }
    #bottom    { height: 65%; }

    #panel { height: 1fr; padding: 1; }
    #statusbar { height: 1; color: #AAAAAA; }

    Footer { dock: bottom; }
    """

    # Only Esc quits the app. `q` does NOT quit.
    BINDINGS = [
        ("escape", "quit", "Quit"),
        ("t", "cycle_theme", "Theme"),
        ("r", "refresh", "Refresh"),
        ("f", "show_formulas", "Formulas"),
    ]

    theme_name = reactive("mono")
    current_view = reactive("decliners")

    def __init__(self) -> None:
        super().__init__()
        self.cfg = load_config()
        self.store = Store(self.cfg)
        self._last_customer: str | None = None

        self.panel: Vertical | None = None
        self.statusbar: Static | None = None

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
                # Create empty ListView; populate in on_mount after it's attached
                yield ListView(id="nav")

            # Right side: top = Dashboard (fixed), bottom = tab content
            with Vertical(id="content"):
                yield Dashboard(id="top_chart")  # permanent live dashboard
                with Vertical(id="bottom"):
                    self.panel = Vertical(id="panel")    # where views mount
                    yield self.panel
                    self.statusbar = Static("", id="statusbar")
                    yield self.statusbar

        yield Footer()

    def on_mount(self) -> None:
        self._apply_theme()

        # Populate left nav AFTER ListView is mounted (avoids mount errors)
        lv = self.query_one("#nav", ListView)
        for label, vid in NAV_ITEMS:
            lv.append(ListItem(Label(label), id=f"nav-{vid}"))

        # Select "Decliners" by default and show it
        for i, (_, vid) in enumerate(NAV_ITEMS):
            if vid == "decliners":
                lv.index = i
                break

        self._show("decliners")
        self._status("Dashboard live on top • Decliners loaded below. ↑/↓ to navigate, Enter to open a One‑Pager. '/' to search.")

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
            # Pass NON‑ASYNC callback so table can call it safely on Enter
            self.panel.mount(DeclinersView(self.store, self._open_onepager, self.theme_name))
            self._status("Decliners loaded. ↑/↓ then Enter to open a One‑Pager. '/' to search.")

        elif view_id == "growers":
            self.panel.mount(GrowersView(self.store, self._open_onepager, self.theme_name))
            self._status("Growers loaded. ↑/↓ then Enter to open a One‑Pager. '/' to search.")

        elif view_id == "onepager":
            if self._last_customer:
                self.panel.mount(OnePagerView(self.store, self._last_customer, self.theme_name))
                self._status(f"One‑Pager for {self._last_customer}. Press 'b' for browser chart; 'f' for formulas.")
            else:
                self.panel.mount(Static("Open a customer from Decliners/Growers first (Enter)."))
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

    # Called by Decliners/Growers when Enter is pressed
    def _open_onepager(self, customer_id: str) -> None:
        self._last_customer = customer_id
        self._status(f"Opening One‑Pager for {customer_id}…")
        # Flip left nav selection to "One‑Pager"
        nav = self.query_one("#nav", ListView)
        for i, (_, vid) in enumerate(NAV_ITEMS):
            if vid == "onepager":
                nav.index = i
                break
        # Mount the One‑Pager
        self._show("onepager")

    # -------- Actions --------
    def action_cycle_theme(self) -> None:
        i = ORDER.index(self.theme_name) if self.theme_name in ORDER else 0
        i = (i + 1) % len(ORDER)
        self.theme_name = ORDER[i]
        self._status(f"Theme: {self.theme_name}")

    def action_refresh(self) -> None:
        # Re-mount current bottom view (simple + reliable)
        if self.current_view in {"decliners", "growers", "onepager", "actions", "impact", "settings"}:
            self._show(self.current_view)

    def action_show_formulas(self) -> None:
        # Decide which formulas to show based on current tab
        ctx = "decliners"
        if self.current_view == "onepager":
            ctx = "onepager_headline"
        elif self.current_view == "growers":
            ctx = "growers"
        text = FORMULAS.get(ctx, "# Formulas\nNo formulas registered for this view yet.")
        self.push_screen(FormulaModal(text))


if __name__ == "__main__":
    YoYApp().run()
