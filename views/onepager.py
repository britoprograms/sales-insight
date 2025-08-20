# views/onepager.py
from textual.app import ComposeResult
from textual.containers import Vertical, Grid
from textual.widgets import Static
import asyncio

from charts import option_from_sales
from chart_targets import BrowserChart  # native-free: only browser charts
from services.ai import ensure_client_ready
from views.action_modal import ActionSelectionModal


class OnePagerView(Vertical):
    """
    Customer One‑Pager (mock or real):
      - Headline: CY/PY, YoY%, GM
      - PVM: Price/Volume/Mix effects
      - Returns: qty + proxy $
      - Geography: branch deltas
      - Cadence: weekly CY (chart via 'b' opens in browser)
    """

    DEFAULT_CSS = """
    OnePagerView { height: 100%; }
    #hdr { padding: 1; }
    .card { padding: 1; }
    #grid { grid-size: 2 3; gap: 1; }
    """

    BINDINGS = [
        ("b", "chart_browser", "Browser Chart"),
        ("g", "generate_actions", "Generate Actions"),
    ]

    can_focus = True  # ensure this view can receive key events

    def __init__(self, store, customer_id: str, theme: str):
        super().__init__()
        self.store = store
        self.customer_id = customer_id
        self.theme = theme
        self._data = None

        # Chart target (lazy init)
        self._browser = None  # BrowserChart

        # Card widgets
        self.card_headline = None  # Static
        self.card_pvm = None       # Static
        self.card_returns = None   # Static
        self.card_geo = None       # Static
        self.card_cadence = None   # Static

    # ---------- lifecycle ----------
    def compose(self) -> ComposeResult:
        yield Static(f"One‑Pager — {self.customer_id}", id="hdr")

        grid = Grid(id="grid")
        self.card_headline = Static("Headline", classes="card")
        self.card_pvm = Static("PVM (Price–Volume–Mix)", classes="card")
        self.card_returns = Static("Returns Impact", classes="card")
        self.card_geo = Static("Geography (Branch deltas)", classes="card")
        self.card_cadence = Static("Cadence (Weekly CY)", classes="card")

        grid.mount(
            self.card_headline,
            self.card_pvm,
            self.card_returns,
            self.card_geo,
            self.card_cadence,
        )
        yield grid

    def on_mount(self):
        # Pull data bundle (mock if no DB)
        self._data = self.store.onepager_data(self.customer_id)
        # Render all sections
        self._render_headline()
        self._render_pvm()
        self._render_returns()
        self._render_geo()
        self._render_cadence()
        # Ensure our view gets key events (so 'b' works)
        try:
            self.focus()
        except Exception:
            pass

    # ---------- render helpers ----------
    def _render_headline(self):
        h = (self._data or {}).get("headline", {}) or {}
        text = (
            f"CY Sales: ${h.get('cy_sales', 0):,.0f}\n"
            f"PY Sales: ${h.get('py_sales', 0):,.0f}\n"
            f"YoY %: {h.get('yoy_pct', 0):.1f}%\n"
            f"CY GM: ${h.get('cy_gm', 0):,.0f} | PY GM: ${h.get('py_gm', 0):,.0f}"
        )
        self.card_headline.update(text)

    def _render_pvm(self):
        p = (self._data or {}).get("pvm", {}) or {}
        text = (
            f"Δ Total: {p.get('total_delta', 0):,.0f}\n"
            f"Volume: {p.get('volume_effect', 0):,.0f}\n"
            f"Price: {p.get('price_effect', 0):,.0f}\n"
            f"Mix: {p.get('mix_effect', 0):,.0f}"
        )
        self.card_pvm.update(text)

    def _render_returns(self):
        r = (self._data or {}).get("returns", {}) or {}
        text = (
            f"CY Returns Qty: {r.get('cy_ret_qty', 0):,.0f}\n"
            f"PY Returns Qty: {r.get('py_ret_qty', 0):,.0f}\n"
            f"Returns $ Δ (proxy): {r.get('returns_value_delta', 0):,.0f}"
        )
        self.card_returns.update(text)

    def _render_geo(self):
        geo = (self._data or {}).get("geo", []) or []
        if not geo:
            self.card_geo.update("No branch data.")
            return
        lines = ["Branch  |   CY     |   PY     |  YoY Δ"]
        for g in geo[:6]:
            lines.append(
                f"{g.get('branch',''):7} | ${g.get('cy_sales',0):,} | ${g.get('py_sales',0):,} | {g.get('yoy_delta',0):,.0f}"
            )
        self.card_geo.update("\n".join(lines))

    def _render_cadence(self):
        cadence = (self._data or {}).get("cadence", []) or []
        if not cadence:
            self.card_cadence.update("No cadence data.")
            return
        lines = ["Week | CY Sales"]
        for c in cadence[:12]:  # keep the card concise
            lines.append(f"{c.get('week')} | ${c.get('cy_sales',0):,}")
        self.card_cadence.update("\n".join(lines))

    # ---------- chart helpers & actions ----------
    def _records_from_cadence(self):
        """Map cadence list to chart records for ECharts."""
        recs = []
        cadence = (self._data or {}).get("cadence", [])
        for row in cadence:
            recs.append({
                "week": row.get("week"),
                "sales": row.get("cy_sales"),
                "subcommodity": None,  # set if you track subcommodity context
            })
        return recs

    def _theme_name(self) -> str:
        return getattr(self.app, "theme_name", "mono")

    def action_chart_browser(self):
        try:
            records = self._records_from_cadence()
            opt = option_from_sales(records, theme=self._theme_name(), title="Weekly Sales (CY)")
            if self._browser is None:
                self._browser = BrowserChart()
            self._browser.open_or_update(opt)
            getattr(self.app, "_status", lambda m: None)("Opened browser chart.")
        except Exception as e:
            getattr(self.app, "_status", lambda m: None)(f"Chart error: {e}")
        
        finally:
            try:
        # Ask the app to refocus nav with timers
                getattr(self.app, "_refocus_nav", lambda: None)()
            except Exception:
                pass

    def action_generate_actions(self):
        """Generate recommended sales actions for this customer."""
        if not self._data:
            getattr(self.app, "_status", lambda m: None)("No customer data available.")
            return
            
        try:
            # Start async action generation
            asyncio.create_task(self._generate_customer_actions())
            getattr(self.app, "_status", lambda m: None)("Generating sales actions...")
        except Exception as e:
            getattr(self.app, "_status", lambda m: None)(f"Action generation error: {e}")
    
    async def _generate_customer_actions(self):
        """Async method to generate and display customer actions."""
        try:
            # Get AI client and generate actions
            client = await ensure_client_ready()
            
            # Prepare customer data for AI
            headline = (self._data or {}).get("headline", {}) or {}
            customer_data = {
                'cy_sales': headline.get('cy_sales', 0),
                'py_sales': headline.get('py_sales', 0),
                'yoy_delta': headline.get('yoy_delta', 0),
                'yoy_pct': headline.get('yoy_pct', 0)
            }
            
            # Generate actions using AI
            actions_text = await client.generate_sales_actions(self.customer_id, customer_data)
            
            # Debug: Show what we got from AI
            getattr(self.app, "_status", lambda m: None)(f"AI Response length: {len(actions_text)} chars")
            
            # Open action selection modal
            def on_actions_confirmed(selected_actions):
                count = len(selected_actions)
                getattr(self.app, "_status", lambda m: None)(f"Added {count} actions for {self.customer_id}")
            
            modal = ActionSelectionModal(
                self.customer_id, 
                actions_text, 
                on_confirm=on_actions_confirmed
            )
            self.app.push_screen(modal)
            
        except Exception as e:
            getattr(self.app, "_status", lambda m: None)(f"Error generating actions: {e}")
