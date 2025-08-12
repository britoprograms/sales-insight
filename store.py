from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import random

try:
    import clickhouse_connect
except Exception:
    clickhouse_connect = None


@dataclass
class DeclinerRow:
    customer_id: str
    cy_sales: float
    py_sales: float
    yoy_delta: float
    yoy_pct: float
    priority_score: float


@dataclass
class Headline:
    customer_id: str
    cy_sales: float
    py_sales: float
    yoy_sales_pct: float
    cy_gm: float | None = None
    py_gm: float | None = None


class Store:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = None
        self._err = None
        if cfg and getattr(cfg, "has_clickhouse", False) and clickhouse_connect:
            try:
                self.client = clickhouse_connect.get_client(
                    url=cfg.ch_url, username=cfg.ch_user, password=cfg.ch_pass, database=cfg.ch_database
                )
            except Exception as e:
                self.client = None
                self._err = str(e)
        else:
            self._err = "ClickHouse not configured or client unavailable."

    # ---------- SQL templates (for later, when you connect real DB) ----------
    SQL_DECLINERS = """
    WITH by_cust AS (
      SELECT
        CustomerID,
        sum(CY_PurchaseTotal) AS cy_sales,
        sum(PY_PurchaseTotal) AS py_sales
      FROM customer_weekly_sales
      GROUP BY CustomerID
    ),
    scored AS (
      SELECT
        CustomerID,
        cy_sales,
        py_sales,
        (cy_sales - py_sales) AS yoy_delta,
        100 * (cy_sales - py_sales) / NULLIF(py_sales, 0) AS yoy_pct,
        py_sales / NULLIF(max(py_sales) OVER (), 0) AS w_strategic,
        abs(yoy_delta) / NULLIF(max(abs(yoy_delta)) OVER (), 0) AS w_absdrop,
        abs(yoy_pct) / NULLIF(max(abs(yoy_pct)) OVER (), 0) AS w_pctdrop,
        (0.5 * w_absdrop) + (0.3 * w_pctdrop) + (0.2 * w_strategic) AS priority_score
      FROM by_cust
    )
    SELECT CustomerID, cy_sales, py_sales, yoy_delta, yoy_pct, priority_score
    FROM scored
    WHERE yoy_delta < 0
    ORDER BY priority_score DESC
    LIMIT %(limit)s
    """

    SQL_HEADLINE = """
    SELECT
      CustomerID,
      sum(CY_PurchaseTotal) AS cy_sales,
      sum(PY_PurchaseTotal) AS py_sales,
      100 * (sum(CY_PurchaseTotal) - sum(PY_PurchaseTotal)) / NULLIF(sum(PY_PurchaseTotal), 0) AS yoy_sales_pct,
      sum(CY_PurchaseTotal - CY_COGS) AS cy_gm,
      sum(PY_PurchaseTotal - PY_COGS) AS py_gm
    FROM customer_weekly_sales
    WHERE CustomerID = %(cust)s
    GROUP BY CustomerID
    """

    # ---------- Decliners ----------
    def decliners(self, limit: int = 50) -> List[DeclinerRow]:
        if self.client is None:
            # MOCK DATA
            rnd = random.Random(42)
            rows = []
            for i in range(limit):
                py = rnd.uniform(50_000, 250_000)
                drop = rnd.uniform(1_000, py * 0.45)
                cy = max(0.0, py - drop)
                yoy_delta = cy - py
                yoy_pct = 100.0 * (yoy_delta) / (py or 1.0)
                w_abs = min(abs(yoy_delta), 100_000.0)
                w_pct = min(abs(yoy_pct), 60.0)
                score = 0.5 * (w_abs / 100_000.0) + 0.3 * (w_pct / 60.0) + 0.2 * (py / 250_000.0)
                rows.append(DeclinerRow(f"CUST{i:04d}", cy, py, yoy_delta, yoy_pct, score))
            rows.sort(key=lambda r: r.priority_score, reverse=True)
            return rows

        data = self.client.query(self.SQL_DECLINERS, parameters={"limit": limit})
        out = []
        for r in data.result_rows:
            out.append(
                DeclinerRow(
                    customer_id=r[0],
                    cy_sales=float(r[1]),
                    py_sales=float(r[2]),
                    yoy_delta=float(r[3]),
                    yoy_pct=float(r[4]),
                    priority_score=float(r[5]),
                )
            )
        return out

    # ---------- Headline ----------
    def headline(self, customer_id: str) -> Headline | None:
        if self.client is None:
            # Simple MOCK headline (not used by OnePagerView now, but kept for compatibility)
            return Headline(customer_id, cy_sales=125000, py_sales=150000, yoy_sales_pct=-16.7, cy_gm=42000, py_gm=50000)

        data = self.client.query(self.SQL_HEADLINE, parameters={"cust": customer_id})
        if not data.result_rows:
            return None
        r = data.result_rows[0]
        return Headline(r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]))

    # ---------- One-Pager bundle ----------
    def onepager_data(self, customer_id: str) -> dict:
        """
        Returns all sections needed for One-Pager.
        MOCK path returns deterministic numbers so you can demo without DB.
        Real path (when self.client) should run SQL to fill the same structure.
        """
        if self.client is None:
            # MOCK BUNDLE
            rnd = random.Random(hash(customer_id) & 0xFFFFFFFF)
            py = rnd.randint(120_000, 300_000)
            cy = max(0, py - rnd.randint(10_000, 70_000))
            yoy_pct = ((cy - py) / py) * 100 if py else 0.0
            cy_gm = int(cy * rnd.uniform(0.25, 0.35))
            py_gm = int(py * rnd.uniform(0.25, 0.35))

            total_delta = cy - py
            volume_effect = int(total_delta * rnd.uniform(0.4, 0.7))
            price_effect = int(total_delta * rnd.uniform(0.1, 0.3))
            mix_effect = int(total_delta - volume_effect - price_effect)

            cy_ret_qty = rnd.randint(50, 200)
            py_ret_qty = rnd.randint(40, 180)
            returns_value_delta = int((cy_ret_qty - py_ret_qty) * (cy / max(1, rnd.randint(500, 2000))))

            geo = []
            for branch in ["North", "South", "East", "West"]:
                b_py = rnd.randint(20_000, 80_000)
                b_cy = max(0, b_py + rnd.randint(-20_000, 10_000))
                geo.append({"branch": branch, "cy_sales": b_cy, "py_sales": b_py, "yoy_delta": b_cy - b_py})

            cadence = []
            for week in range(1, 7):  # short demo sample
                w_py = rnd.randint(2000, 8000)
                w_cy = max(0, w_py + rnd.randint(-3000, 1500))
                cadence.append({"week": week, "cy_sales": w_cy, "py_sales": w_py, "yoy_delta": w_cy - w_py})

            return {
                "headline": {
                    "customer_id": customer_id,
                    "cy_sales": cy,
                    "py_sales": py,
                    "yoy_pct": yoy_pct,
                    "cy_gm": cy_gm,
                    "py_gm": py_gm,
                },
                "pvm": {
                    "total_delta": total_delta,
                    "volume_effect": volume_effect,
                    "price_effect": price_effect,
                    "mix_effect": mix_effect,
                },
                "returns": {
                    "cy_ret_qty": cy_ret_qty,
                    "py_ret_qty": py_ret_qty,
                    "returns_value_delta": returns_value_delta,
                },
                "geo": geo,
                "cadence": cadence,
            }

        # REAL DB path (fill the same structure with queries)
        # TODO: Run SQL to populate headline, pvm, returns, geo, cadence
        # For now, return empty sections if no implementation yet.
        return {
            "headline": {},
            "pvm": {},
            "returns": {},
            "geo": [],
            "cadence": [],
        }

