
# views/growers.py
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static, Input


class GrowersView(Vertical):
    """Growers list with search and safe Enter → One‑Pager (keyboard-first)."""

    BINDINGS = [
        ("enter", "open_selected", "Open One‑Pager"),   # while table focused
        ("/", "focus_search", "Search"),
        ("escape", "clear_search", "Clear Search"),
        ("r", "refresh", "Refresh"),
        ("down", "focus_table", "Table ↓"),
        ("up", "focus_table", "Table ↑"),
    ]

    def __init__(self, store, on_open_onepager, theme):
        super().__init__()
        self.store = store
        self.on_open_onepager = on_open_onepager  # NON‑async callback in App
        self.theme = theme

        self.search = Input(
            placeholder="Search CustomerID…  (Press / to focus, Enter to move to table, Esc to clear)",
            id="search",
        )
        self.table = DataTable()
        self.hint = Static("", id="growers-hint")

        self._columns_built = False
        self._all_rows = []   # full (unfiltered) rows cache

    # ---------- layout ----------
    def compose(self) -> ComposeResult:
        yield Static("Growers (YoY ↑) — ↑/↓ select • Enter opens One‑Pager • / search", id="title")
        yield self.search
        yield self.table
        yield self.hint

    def on_mount(self):
        # Table look & feel
        try:
            self.table.cursor_type = "row"
            self.table.show_header = True
            self.table.zebra_stripes = True
        except Exception:
            pass

        self._ensure_columns()
        self.refresh_rows()

        # Focus table initially
        try:
            self.table.focus()
            if getattr(self.table, "row_count", 0) > 0:
                try:
                    self.table.cursor_coordinate = (0, 0)
                except Exception:
                    pass
        except Exception:
            pass

    # ---------- columns / rows ----------
    def _ensure_columns(self):
        if self._columns_built:
            return
        self.table.clear()
        self.table.add_columns("CustomerID", "CY Sales", "PY Sales", "YoY Δ $", "YoY %", "Priority")
        self._columns_built = True

    def _clear_rows(self):
        try:
            while getattr(self.table, "row_count", 0) > 0:
                self.table.remove_row(0)
        except Exception:
            self._columns_built = False
            self._ensure_columns()

    def refresh_rows(self):
        self._ensure_columns()
        self._clear_rows()

        # Pull from store and cache
        rows = self.store.growers(limit=500)
        self._all_rows = rows
        self._apply_filter(self.search.value or "")
        self._set_hint("Type to filter. Enter in search → move to table. Enter in table → open One‑Pager.")

    # ---------- filtering ----------
    def _apply_filter(self, q: str):
        q_norm = (q or "").strip().lower()

        self._clear_rows()

        def row_norm_id(r):
            return str(getattr(r, "customer_id", r[0] if isinstance(r, (list, tuple)) else "")).strip().lower()

        def fmt(r):
            return [
                r.customer_id,
                f"${r.cy_sales:,.0f}",
                f"${r.py_sales:,.0f}",
                f"${r.yoy_delta:,.0f}",
                f"{r.yoy_pct:.1f}%",
                f"{r.priority_score:.3f}",
            ]

        # Prefer exact match first if present
        exact = None
        if q_norm:
            for r in self._all_rows:
                if row_norm_id(r) == q_norm:
                    exact = r
                    break

        shown = 0
        if exact is not None:
            try:
                self.table.add_row(*fmt(exact), key=exact.customer_id)
            except TypeError:
                self.table.add_row(*fmt(exact))
            shown += 1

        for r in self._all_rows:
            if exact is not None and r is exact:
                continue
            if not q_norm or (q_norm in row_norm_id(r)):
                try:
                    self.table.add_row(*fmt(r), key=r.customer_id)
                except TypeError:
                    self.table.add_row(*fmt(r))
                shown += 1
                if shown >= 500:
                    break

        # Keep cursor sane
        try:
            if shown > 0:
                self.table.cursor_coordinate = (0, 0)
        except Exception:
            pass

        # Hint
        if q_norm:
            if exact is not None:
                self._set_hint(f"Exact match highlighted first • {shown} shown")
            else:
                self._set_hint(f"{shown} result(s) for “{q}”")
        else:
            self._set_hint(f"{shown} total rows")

    # Live filter as user types
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input is self.search:
            self._apply_filter(event.value)

    # Enter inside the search box
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input is self.search:
            try:
                rc = getattr(self.table, "row_count", 0)
                if rc == 1:
                    cust_id = self._read_customer_from_cursor()
                    if cust_id:
                        self.on_open_onepager(str(cust_id))
                        return
            except Exception:
                pass
            self.action_focus_table()

    # ---------- key actions ----------
    def action_focus_search(self):
        try:
            self.search.focus()
        except Exception:
            pass

    def action_focus_table(self):
        try:
            self.table.focus()
        except Exception:
            pass

    def action_clear_search(self):
        try:
            self.search.value = ""
            self._apply_filter("")
            self.table.focus()
        except Exception:
            pass

    def action_refresh(self):
        self.refresh_rows()

    def action_open_selected(self) -> None:
        """Open One‑Pager from currently selected table row."""
        try:
            cust_id = self._read_customer_from_cursor()
            if cust_id:
                self.on_open_onepager(str(cust_id))
        except Exception:
            self._set_hint("Could not open One‑Pager (unexpected error).")

    # Path A: newer Textual emits this on Enter/double‑click on a row
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            event.stop()
        except Exception:
            pass
        try:
            cust_id = None
            try:
                # Extract string value from RowKey object
                row_key = event.row_key
                if row_key is not None:
                    # Try to get the actual value from RowKey
                    if hasattr(row_key, 'value'):
                        cust_id = str(row_key.value)
                    elif hasattr(row_key, '_key'):
                        cust_id = str(row_key._key)
                    else:
                        # Fall back to reading from table data
                        cust_id = self._read_customer_from_cursor()
            except Exception:
                pass
            if not cust_id:
                cust_id = self._read_customer_from_cursor()
            if cust_id:
                self.on_open_onepager(str(cust_id))
        except Exception:
            self._set_hint("Could not open One‑Pager (unexpected error).")

    # ---------- helpers ----------
    def _read_customer_from_cursor(self):
        if getattr(self.table, "row_count", 0) == 0:
            return None

        # Prefer modern cursor_coordinate
        row_index = 0
        try:
            cc = getattr(self.table, "cursor_coordinate", None)
            if cc is not None:
                row_index = cc.row if hasattr(cc, "row") else cc[0]
        except Exception:
            pass

        # Bounds
        try:
            rc = int(getattr(self.table, "row_count", 1))
            if row_index < 0 or row_index >= rc:
                row_index = 0
        except Exception:
            pass

        # Read first column
        try:
            row = self.table.get_row_at(row_index)
            return row[0]
        except Exception:
            try:
                return self.table.get_cell_at(row_index, 0)
            except Exception:
                return None

    def _set_hint(self, msg: str):
        try:
            self.hint.update(msg)
        except Exception:
            pass
