# views/dashboard.py — Futuristic live dashboard (clamped layout + timestamp)
from __future__ import annotations
from collections import deque
from typing import Deque, Tuple, List
import os, random
from datetime import datetime

from textual.widget import Widget
from textual.reactive import reactive
from textual.timer import Timer
from rich.text import Text


# ---------- helpers ----------

def _fit_text(text: Text, width: int) -> Text:
    """Trim or pad a Text to exactly width (no overflow)."""
    plain = text.plain
    if len(plain) > width:
        # simple clamp: take exact slice (colors will be lost past width)
        return Text(plain[:width], style=text.style)
    if len(plain) < width:
        out = Text(plain, style=text.style)
        out.append(" " * (width - len(plain)), style=text.style)
        return out
    return text


def _fit_str(s: str, width: int) -> str:
    return (s[:width]) if len(s) > width else (s + (" " * (width - len(s))))


def sparkline(values: List[float], width: int) -> str:
    """Return a fixed-width unicode sparkline using 8-level blocks; accepts negatives."""
    if width <= 0:
        return ""
    if not values:
        return " " * width
    vals = values[-width:]  # 1 char per col
    lo = min(vals)
    hi = max(vals)
    if hi == lo:
        return "▁" * width
    blocks = "▁▂▃▄▅▆▇█"
    out = []
    span = hi - lo
    for v in vals:
        t = (v - lo) / span
        out.append(blocks[int(t * (len(blocks) - 1))])
    return "".join(out)


def human_money(v: float) -> str:
    s = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000_000:
        return f"{s}${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{s}${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{s}${v/1_000:.2f}K"
    return f"{s}${v:,.0f}"


class Dashboard(Widget):
    """
    Live dashboard cards (fully clamped to their boxes):
      • Growers Up YoY
      • Decliners Down YoY
      • Net Momentum
      • Records row (counts + extra stat)

    Layout rules:
      - Uses ALL horizontal space inside the widget.
      - Card widths are computed to fit exactly with single spaces between cards.
      - Every gauge/sparkline/label is clamped to the card's inner width, preventing overflow.
      - Shows a timestamp in the title.
    """

    DEFAULT_CSS = """
    Dashboard {
        height: 1fr;
        background: #0b0f1a;
        color: #cbd5e1;
        border: heavy #00d0ff;
        padding: 1 1;
        content-align: left top;
    }
    """

    refresh_seconds = reactive(1.5)  # override with LIVE_DASH_INTERVAL

    def __init__(self, *args, **kwargs) -> None:
        # allow id= / classes= / name= to pass through
        super().__init__(*args, **kwargs)
        self._timer: Timer | None = None
        self._hist_g: Deque[float] = deque(maxlen=200)   # growers $
        self._hist_d: Deque[float] = deque(maxlen=200)   # decliners $ (neg)
        self._hist_n: Deque[float] = deque(maxlen=200)   # net $
        self._counts: Tuple[int, int] = (0, 0)           # (#decliners, #growers)

        try:
            iv = float(os.getenv("LIVE_DASH_INTERVAL", "0"))
            if iv > 0:
                self.refresh_seconds = iv
        except Exception:
            pass

    # ---------- lifecycle ----------
    def on_mount(self) -> None:
        # prime history so it looks full immediately
        for _ in range(24):
            self._sample(seed=True)
        self._timer = self.set_interval(self.refresh_seconds, self._tick)
        self.refresh()

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop(); self._timer = None

    def _tick(self) -> None:
        self._sample()
        self.refresh()

    # ---------- sampling ----------
    def _sample(self, seed: bool = False) -> None:
        try:
            decl = self.app.store.decliners(limit=500)
            grow = self.app.store.growers(limit=500)
            d_vals = [getattr(r, "yoy_delta", 0.0) for r in decl]
            g_vals = [getattr(r, "yoy_delta", 0.0) for r in grow]
            has_db = bool(self.app.store.client)
        except Exception:
            d_vals, g_vals, has_db = [], [], False

        d_sum = sum(v for v in d_vals if v < 0.0)          # negative
        g_sum = sum(v for v in g_vals if v > 0.0)          # positive
        net = d_sum + g_sum
        self._counts = (len(d_vals), len(g_vals))

        if not has_db and os.getenv("LIVE_CHART_JITTER", "1") == "1":
            j = 25_000 if seed else 75_000
            g_sum += random.uniform(-j, j)
            d_sum -= abs(random.uniform(0, j))
            net = d_sum + g_sum

        self._hist_g.append(g_sum)
        self._hist_d.append(d_sum)
        self._hist_n.append(net)

    # ---- simple gauge (clamped to width) ----
    def _gauge(self, value: float, width: int, pos_color: str, neg_color: str) -> Text:
        if width <= 0:
            return Text("")
        # scale using visible ranges across all three series (robust)
        lo = min(
            min(self._hist_g or [0.0]),
            min(self._hist_d or [0.0]),
            min(self._hist_n or [0.0]),
        )
        hi = max(
            max(self._hist_g or [0.0]),
            max(self._hist_d or [0.0]),
            max(self._hist_n or [0.0]),
        )
        span = max(1.0, hi - lo)
        frac = (value - lo) / span
        fill_cols = max(0, min(width, int(round(frac * width))))
        txt = Text()
        # left→right filled bar; remaining area is shaded
        if fill_cols:
            txt.append("█" * fill_cols, style=pos_color if value >= 0 else neg_color)
        if fill_cols < width:
            txt.append("░" * (width - fill_cols))
        return txt

    # ---------- renderer ----------
    def render(self) -> Text:
        width, _ = self.size
        # guard super-narrow terminals
        width = max(60, width)

        # theme palette
        fg = "#cbd5e1"
        cyan = "#00e5ff"
        magenta = "#ff00e5"
        green = "spring_green3"
        red = "red3"
        grid = "#223"

        # Current metrics
        g_now = self._hist_g[-1] if self._hist_g else 0.0
        d_now = self._hist_d[-1] if self._hist_d else 0.0
        n_now = self._hist_n[-1] if self._hist_n else 0.0
        c_d, c_g = self._counts
        style_net = green if n_now >= 0 else red

        # ---------- card geometry (FILL ALL horizontal space) ----------
        # We draw 3 KPI cards side-by-side with exactly 1 space between each and no side gutters.
        # Outer border chars occupy 2 columns per card; inner content width = card_w - 2.
        gaps = 2  # two single spaces between 3 cards
        # Fit three equal cards
        card_w = (width - gaps) // 3
        rem = (width - gaps) - (card_w * 3)
        # distribute remainder to first cards to fill the row exactly
        w1 = card_w + (1 if rem > 0 else 0)
        w2 = card_w + (1 if rem > 1 else 0)
        w3 = card_w
        inner1 = max(4, w1 - 2)
        inner2 = max(4, w2 - 2)
        inner3 = max(4, w3 - 2)

        # Common subwidths for contents
        # label area for "$x.xxM" right-aligned inside inner width
        num_pad = 6  # spacing before number glyphs
        gauge_w1 = max(8, inner1 - 2)
        gauge_w2 = max(8, inner2 - 2)
        gauge_w3 = max(8, inner3 - 2)
        spark_w1 = max(8, inner1 - 2)
        spark_w2 = max(8, inner2 - 2)
        spark_w3 = max(8, inner3 - 2)

        # ---------- start composing ----------
        out = Text()

        # Title with timestamp (clamped)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = Text()
        title.append(" DASHBOARD ", style=f"bold {cyan}")
        title.append(" live status of YoY momentum  ", style=fg)
        title.append(f"{ts}", style="#999")
        out += _fit_text(title, width)  # full row
        out.append("\n")
        out.append(_fit_text(Text("═" * width, style=grid), width))
        out.append("\n")

        # Row: Top borders of 3 cards
        out.append(Text("┏" + "━" * (w1 - 2) + "┓"))
        out.append(Text(" "))
        out.append(Text("┏" + "━" * (w2 - 2) + "┓", style=magenta))
        out.append(Text(" "))
        out.append(Text("┏" + "━" * (w3 - 2) + "┓", style=fg))
        out.append("\n")

        # Titles row
        t1 = _fit_str(" GROWERS ↑", inner1)
        t2 = _fit_str(" DECLINERS ↓", inner2)
        t3 = _fit_str(" NET MOMENTUM", inner3)
        out.append(Text("┃" + t1 + "┃", style=green))
        out.append(Text(" "))
        out.append(Text("┃" + t2 + "┃", style=red))
        out.append(Text(" "))
        out.append(Text("┃" + t3 + "┃", style=fg))
        out.append("\n")

        # Numbers row (right aligned)
        n1 = _fit_str(human_money(g_now).rjust(inner1 - 1), inner1)
        n2 = _fit_str(human_money(-d_now).rjust(inner2 - 1), inner2)  # show abs for readability
        n3 = _fit_str(human_money(n_now).rjust(inner3 - 1), inner3)
        out.append(Text("┃" + n1 + "┃", style=green))
        out.append(Text(" "))
        out.append(Text("┃" + n2 + "┃", style=red))
        out.append(Text(" "))
        out.append(Text("┃" + n3 + "┃", style=style_net))
        out.append("\n")

        # Gauges row (hard-clamped)
        gtxt1 = _fit_text(self._gauge(g_now, gauge_w1, green, red), inner1)
        gtxt2 = _fit_text(self._gauge(d_now, gauge_w2, green, red), inner2)
        gtxt3 = _fit_text(self._gauge(n_now, gauge_w3, green, red), inner3)
        out.append(Text("┃"))
        out += gtxt1
        out.append(Text("┃"))
        out.append(Text(" "))
        out.append(Text("┃"))
        out += gtxt2
        out.append(Text("┃"))
        out.append(Text(" "))
        out.append(Text("┃"))
        out += gtxt3
        out.append(Text("┃"))
        out.append("\n")

        # Sparklines row (fixed width)
        out.append(Text("┃" + _fit_str(sparkline(list(self._hist_g), spark_w1), inner1) + "┃", style=green))
        out.append(Text(" "))
        out.append(Text("┃" + _fit_str(sparkline(list(self._hist_d), spark_w2), inner2) + "┃", style=red))
        out.append(Text(" "))
        out.append(Text("┃" + _fit_str(sparkline(list(self._hist_n), spark_w3), inner3) + "┃", style=style_net))
        out.append("\n")

        # Bottom borders
        out.append(Text("┗" + "━" * (w1 - 2) + "┛"))
        out.append(Text(" "))
        out.append(Text("┗" + "━" * (w2 - 2) + "┛", style=magenta))
        out.append(Text(" "))
        out.append(Text("┗" + "━" * (w3 - 2) + "┛"))
        out.append("\n\n")

        # Records row — single full-width box (clamped)
        rows_box_w = width
        out.append(Text("┏" + "━" * (rows_box_w - 2) + "┓", style=grid))
        out.append("\n")
        rec_text = Text()
        total_rows = c_d + c_g
        rec_line = f" Records   Decliners: {c_d:,}   Growers: {c_g:,}   Total: {total_rows:,} "
        rec_text.append(rec_line, style="bold")
        rec_text = _fit_text(rec_text, rows_box_w - 2)
        out.append(Text("┃", style=grid)); out += rec_text; out.append(Text("┃", style=grid))
        out.append("\n")
        out.append(Text("┗" + "━" * (rows_box_w - 2) + "┛", style=grid))
        out.append("\n")

        # Footer hint (clamped)
        hint = _fit_text(Text(" Press ↑/↓ to change views • Enter opens One‑Pager • '/' to search • F formulas • T theme ", style="#667"), width)
        out += hint

        return out

