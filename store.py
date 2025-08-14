
# store.py — shared mock data source for decliners & growers, ClickHouse-ready
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Any, Dict
import random
import math

try:
    from clickhouse_connect import get_client  # optional; only used when creds present
except Exception:
    get_client = None  # type: ignore


@dataclass
class Row:
    customer_id: str
    cy_sales: float
    py_sales: float
    yoy_delta: float
    yoy_pct: float
    priority_score: float


class Store:
    """
    Data access layer.
    - In MOCK mode (no ClickHouse client), uses deterministic synthetic data.
    - In DB mode (future), replace _db_* methods with real ClickHouse SQL.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.client = None
        if (
            get_client is not None
            and cfg.ch_url
            and cfg.ch_user is not None
        ):
            try:
                self.client = get_client(
                    host=cfg.ch_url.replace("http://", "").replace("https://", "").split(":")[0],
                    port=int(cfg.ch_url.rsplit(":", 1)[-1]) if ":" in cfg.ch_url else 8123,
                    username=cfg.ch_user,
                    password=cfg.ch_pass or "",
                    database=cfg.ch_database or "default",
                    secure=cfg.ch_url.startswith("https://"),
                )
            except Exception:
                # Stay in MOCK mode if connection fails
                self.client = None

    # ---------------- MOCK GENERATOR (shared) ----------------
    def _mock_rows_source(self, n: int = 300) -> List[Row]:
        """
        Deterministic mock customers with CY/PY, YoY deltas (positive and negative),
        and a priority score aligned with your earlier formula:
          priority = 0.5 * w_absdrop + 0.3 * w_pctdrop + 0.2 * w_strategic
        For growers, we keep the same 'priority_score' to rank by absolute movement + pct + strategic weight.
        """
        rnd = random.Random(42)  # deterministic
        rows: List[Row] = []

        # create a bell curve around 0 so we get both decliners and growers
        for i in range(n):
            cust_num = i + 1
            customer_id = f"CUST{cust_num:04d}"
            py_sales = max(1_000.0, rnd.uniform(10_000, 250_000))
            # movement factor in [-0.45, +0.45], roughly normal-ish
            movement = rnd.gauss(0, 0.18)
            movement = max(-0.55, min(0.55, movement))
            cy_sales = max(500.0, py_sales * (1.0 + movement))

            yoy_delta = cy_sales - py_sales
            yoy_pct = (yoy_delta / py_sales) * 100.0 if py_sales else 0.0
            rows.append(Row(customer_id, cy_sales, py_sales, yoy_delta, yoy_pct, 0.0))

        # compute weights across the whole set
        max_py = max(r.py_sales for r in rows) or 1.0
        max_absdelta = max(abs(r.yoy_delta) for r in rows) or 1.0
        max_abspct = max(abs(r.yoy_pct) for r in rows) or 1.0

        for r in rows:
            w_strategic = r.py_sales / max_py if max_py else 0.0
            w_absdrop = abs(r.yoy_delta) / max_absdelta if max_absdelta else 0.0
            w_pctdrop = abs(r.yoy_pct) / max_abspct if max_abspct else 0.0
            r.priority_score = (0.5 * w_absdrop) + (0.3 * w_pctdrop) + (0.2 * w_strategic)

        return rows

    # ---------------- PUBLIC APIS ----------------
    def decliners(self, limit: int = 50) -> List[Row]:
        """
        Top negative YoY movers (decliners), sorted by priority_score desc.
        """
        if self.client:
            rows = self._db_decliners(limit=limit)  # TODO: replace stub with real SQL
        else:
            rows = self._mock_rows_source(n=500)
        decliners = [r for r in rows if r.yoy_delta < 0]
        decliners.sort(key=lambda r: r.priority_score, reverse=True)
        return decliners[:limit]

    def growers(self, limit: int = 50) -> List[Row]:
        """
        Top positive YoY movers (growers), sorted by priority_score desc.
        """
        if self.client:
            rows = self._db_growers(limit=limit)  # TODO: replace stub with real SQL
        else:
            rows = self._mock_rows_source(n=500)
        growers = [r for r in rows if r.yoy_delta > 0]
        growers.sort(key=lambda r: r.priority_score, reverse=True)
        return growers[:limit]

    def onepager_data(self, customer_id: str) -> Dict[str, Any]:
        """
        Return a bundle used by One‑Pager (headline, pvm, returns, geo, cadence).
        In MOCK mode we synthesize this from the same seed so it's stable per customer.
        """
        if self.client:
            return self._db_onepager_data(customer_id)
        return self._mock_onepager(customer_id)

    # ---------------- DB STUBS (fill when you wire ClickHouse) ----------------
    def _db_decliners(self, limit: int = 50) -> List[Row]:
        # TODO: Implement with ClickHouse SQL:
        #  - aggregate CY vs PY by CustomerID
        #  - compute yoy_delta, yoy_pct, weights and priority_score
        #  - WHERE yoy_delta < 0 ORDER BY priority_score DESC LIMIT {limit}
        return self._mock_rows_source(n=500)

    def _db_growers(self, limit: int = 50) -> List[Row]:
        # TODO: Implement with ClickHouse SQL:
        #  - same as decliners but yoy_delta > 0
        return self._mock_rows_source(n=500)

    def _db_onepager_data(self, customer_id: str) -> Dict[str, Any]:
        # TODO: Implement detailed per-customer bundles from ClickHouse
        return self._mock_onepager(customer_id)

    # ---------------- MOCK ONE-PAGER ----------------
    def _mock_onepager(self, customer_id: str) -> Dict[str, Any]:
        """
        Generate a stable (per-customer) one-pager bundle.
        """
        # stable seed per customer
        seed = sum(ord(c) for c in customer_id)
        rnd = random.Random(seed)

        py_sales = rnd.uniform(20_000, 200_000)
        # +/- up to ~35%
        cy_sales = py_sales * (1.0 + rnd.uniform(-0.35, 0.45))
        yoy_pct = ((cy_sales - py_sales) / py_sales) * 100.0 if py_sales else 0.0

        # headline
        headline = {
            "cy_sales": round(cy_sales, 2),
            "py_sales": round(py_sales, 2),
            "yoy_pct": round(yoy_pct, 2),
            "cy_gm": round(cy_sales * rnd.uniform(0.14, 0.24), 2),
            "py_gm": round(py_sales * rnd.uniform(0.14, 0.24), 2),
        }

        # PVM
        total_delta = cy_sales - py_sales
        vol = total_delta * rnd.uniform(0.35, 0.6)
        price = total_delta * rnd.uniform(-0.1, 0.4)
        mix = total_delta - vol - price
        pvm = {
            "total_delta": round(total_delta, 2),
            "volume_effect": round(vol, 2),
            "price_effect": round(price, 2),
            "mix_effect": round(mix, 2),
        }

        # returns
        py_ret = rnd.randint(5, 80)
        cy_ret = max(0, int(py_ret + rnd.randint(-15, 25)))
        returns = {
            "cy_ret_qty": cy_ret,
            "py_ret_qty": py_ret,
            "returns_value_delta": round((cy_ret - py_ret) * rnd.uniform(20, 80), 2),
        }

        # geo branches
        branches = ["NORTH", "SOUTH", "EAST", "WEST", "CENTRAL", "NE", "NW", "SE", "SW"]
        geo = []
        for b in branches[: rnd.randint(3, 6)]:
            b_py = rnd.uniform(2_000, 40_000)
            b_cy = b_py * (1.0 + rnd.uniform(-0.45, 0.55))
            geo.append(
                {
                    "branch": b,
                    "py_sales": int(b_py),
                    "cy_sales": int(b_cy),
                    "yoy_delta": int(b_cy - b_py),
                }
            )

        # cadence: 13 recent weeks
        cadence = []
        base = cy_sales / 13.0
        for wk in range(1, 14):
            # wavy seasonality
            factor = 1.0 + 0.25 * math.sin(wk / 2.8)
            noise = rnd.uniform(0.85, 1.15)
            cadence.append(
                {
                    "week": f"W{wk:02d}",
                    "cy_sales": int(base * factor * noise),
                }
            )

        return {
            "headline": headline,
            "pvm": pvm,
            "returns": returns,
            "geo": geo,
            "cadence": cadence,
        }
