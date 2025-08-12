
# views/decliners.py
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

class DeclinersView(Vertical):
    """Decliner list that opens One‑Pager on Enter, without ever exiting the app."""

    # Fallback keybinding in case the DataTable doesn't emit RowSelected
    BINDINGS = [("enter", "open_selected", "Open One‑Pager")]

    def __init__(self, store, on_open_onepager, theme):
        super().__init__()
        self.store = store
        self.on_open_onepager = on_open_onepager  # NON-async callback in App
        self.theme = theme
        self.table = DataTable()
        self._columns_built = False
        self._hint = Static("", id="decliners-hint")

    def compose(self) -> ComposeResult:
        yield Static("Decliner Queue (YoY) — ↑/↓ select • Enter opens One‑Pager • R refresh", id="title")
        yield self.table
        yield self._hint

    def on_mount(self):
        try:
            self.table.cursor_type = "row"
            self.table.show_header = True
            self.table.zebra_stripes = True
        except Exception:
            pass
        self._ensure_columns()
        self.refresh_rows()
        # Focus table so Enter goes to it
        try:
            self.table.focus()
            if getattr(self.table, "row_count", 0) > 0:
                try:
                    self.table.cursor_coordinate = (0, 0)
                except Exception:
                    pass
        except Exception:
            pass

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
        rows = self.store.decliners(limit=50)
        for r in rows:
            # Prefer row keys if supported
            try:
                self.table.add_row(
                    r.customer_id,
                    f"${r.cy_sales:,.0f}",
                    f"${r.py_sales:,.0f}",
                    f"${r.yoy_delta:,.0f}",
                    f"{r.yoy_pct:.1f}%",
                    f"{r.priority_score:.3f}",
                    key=r.customer_id,
                )
            except TypeError:
                self.table.add_row(
                    r.customer_id,
                    f"${r.cy_sales:,.0f}",
                    f"${r.py_sales:,.0f}",
                    f"${r.yoy_delta:,.0f}",
                    f"{r.yoy_pct:.1f}%",
                    f"{r.priority_score:.3f}",
                )
        self._set_hint("Select a row and press Enter to open One‑Pager.")

    async def key_r(self):
        self.refresh_rows()

    # ---------- Event path A: DataTable emits a RowSelected on Enter/double-click ----------
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # Prevent any further bubbling that could quit the app
        try:
            event.stop()
        except Exception:
            pass
        try:
            cust_id = None
            try:
                cust_id = event.row_key or None  # works on newer Textual when we set key=
            except Exception:
                cust_id = None

            if not cust_id:
                cust_id = self._read_customer_from_cursor()

            if cust_id:
                self._set_hint(f"Opening One‑Pager for {cust_id}…")
                # Non-async App callback; never awaits here
                self.on_open_onepager(str(cust_id))
        except Exception:
            # Swallow everything; never exit the app
            self._set_hint("Could not open One‑Pager (unexpected error).")

    # ---------- Event path B: Our own Enter binding (fallback) ----------
    def action_open_selected(self) -> None:
        try:
            cust_id = self._read_customer_from_cursor()
            if cust_id:
                self._set_hint(f"Opening One‑Pager for {cust_id}…")
                self.on_open_onepager(str(cust_id))
        except Exception:
            self._set_hint("Could not open One‑Pager (unexpected error).")

    # ---------- helpers ----------
    def _read_customer_from_cursor(self):
        """Read currently selected CustomerID from first column, robust to Textual version."""
        if getattr(self.table, "row_count", 0) == 0:
            return None

        # Try modern API
        row_index = None
        try:
            cc = getattr(self.table, "cursor_coordinate", None)
            if cc is not None:
                row_index = cc.row if hasattr(cc, "row") else cc[0]
        except Exception:
            row_index = None

        # Fallback: older API
        if row_index is None:
            try:
                row_index = int(getattr(self.table, "cursor_row", 0))
            except Exception:
                row_index = 0

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
            self._hint.update(msg)
        except Exception:
            pass
