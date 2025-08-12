from textual.widgets import Static
from textual.screen import ModalScreen

# Registry: context_key -> markdown text
FORMULAS = {
    "decliners": """# Decliner Priority Score

Formulas:
- YoY Δ $ = Σ(CY_Sales) − Σ(PY_Sales)
- YoY %  = 100 × (Σ(CY_Sales) − Σ(PY_Sales)) / Σ(PY_Sales)
- w_absdrop = |YoY Δ $| ÷ max(|YoY Δ $|)
- w_pctdrop = |YoY %| ÷ max(|YoY %|)
- w_strategic = PY ÷ max(PY)
- priority_score = 0.5*w_absdrop + 0.3*w_pctdrop + 0.2*w_strategic

Sample SQL (ClickHouse):
WITH by_cust AS (
  SELECT CustomerID,
         sum(CY_PurchaseTotal) AS cy_sales,
         sum(PY_PurchaseTotal) AS py_sales
  FROM customer_weekly_sales
  GROUP BY CustomerID
),
scored AS (
  SELECT
    CustomerID, cy_sales, py_sales,
    (cy_sales - py_sales) AS yoy_delta,
    100 * (cy_sales - py_sales) / NULLIF(py_sales, 0) AS yoy_pct,
    py_sales / NULLIF(max(py_sales) OVER (), 0) AS w_strategic,
    abs(yoy_delta) / NULLIF(max(abs(yoy_delta)) OVER (), 0) AS w_absdrop,
    abs(yoy_pct)  / NULLIF(max(abs(yoy_pct))  OVER (), 0) AS w_pctdrop,
    (0.5*w_absdrop + 0.3*w_pctdrop + 0.2*w_strategic) AS priority_score
  FROM by_cust
)
SELECT CustomerID, cy_sales, py_sales, yoy_delta, yoy_pct, priority_score
FROM scored
WHERE yoy_delta < 0
ORDER BY priority_score DESC
LIMIT 200;
""",

    "onepager_headline": """# One-Pager — Headline Metrics

Formulas:
- CY Sales = Σ(CY_PurchaseTotal)
- PY Sales = Σ(PY_PurchaseTotal)
- YoY %    = 100 × (Σ(CY_PurchaseTotal) − Σ(PY_PurchaseTotal)) / Σ(PY_PurchaseTotal)
- CY GM    = Σ(CY_PurchaseTotal − CY_COGS)
- PY GM    = Σ(PY_PurchaseTotal − PY_COGS)

Sample SQL:
SELECT
  CustomerID,
  sum(CY_PurchaseTotal) AS cy_sales,
  sum(PY_PurchaseTotal) AS py_sales,
  100 * (sum(CY_PurchaseTotal) - sum(PY_PurchaseTotal))
      / NULLIF(sum(PY_PurchaseTotal), 0) AS yoy_sales_pct,
  sum(CY_PurchaseTotal - CY_COGS) AS cy_gm,
  sum(PY_PurchaseTotal - PY_COGS) AS py_gm
FROM customer_weekly_sales
WHERE CustomerID = {customer_id:String}
GROUP BY CustomerID;
""",

    "onepager_pvm": """# One-Pager — PVM (Price–Volume–Mix)

Definitions:
- Total Δ       = Σ(cy_sales − py_sales)
- Volume Effect = Σ( (CY_Qty − PY_Qty) × PY_Price )
- Price Effect  = Σ( (CY_Price − PY_Price) × CY_Qty )
- Mix Effect    = Total Δ − Volume Effect − Price Effect

Sample SQL:
WITH base AS (
  SELECT
    FullSubCommCode,
    sum(CY_PurchaseTotal) AS cy_sales,
    sum(PY_PurchaseTotal) AS py_sales,
    sum(CY_QtySold) AS cy_qty,
    sum(PY_QtySold) AS py_qty,
    (cy_sales / NULLIF(cy_qty, 0)) AS cy_price,
    (py_sales / NULLIF(py_qty, 0)) AS py_price
  FROM customer_weekly_sales
  WHERE CustomerID = {customer_id:String}
  GROUP BY FullSubCommCode
)
SELECT
  sum(cy_sales - py_sales) AS total_delta,
  sum( (cy_qty - py_qty) * py_price ) AS volume_effect,
  sum( (cy_price - py_price) * cy_qty ) AS price_effect,
  (total_delta - volume_effect - price_effect) AS mix_effect
FROM base;
""",

    "onepager_returns": """# One-Pager — Returns Impact

Formulas:
- CY Unit Price = Σ(CY_PurchaseTotal) / Σ(CY_QtySold)
- Δ Returns Qty = Σ(CY_ReturnQty) − Σ(PY_ReturnQty)
- Returns $ Δ   = Δ Returns Qty × CY Unit Price

Sample SQL:
SELECT
  sum(CY_ReturnQty) AS cy_ret_qty,
  sum(PY_ReturnQty) AS py_ret_qty,
  (sum(CY_PurchaseTotal) / NULLIF(sum(CY_QtySold), 0)) AS cy_unit_price,
  (sum(CY_ReturnQty) - sum(PY_ReturnQty)) *
    (sum(CY_PurchaseTotal) / NULLIF(sum(CY_QtySold), 0)) AS returns_value_delta
FROM customer_weekly_sales
WHERE CustomerID = {customer_id:String};
""",

    "onepager_geo": """# One-Pager — Geographic Redistribution

Measures:
- Branch YoY Δ = Σ(CY_PurchaseTotal) − Σ(PY_PurchaseTotal) per Branch
- Best/Worst Branch = max/min Branch YoY Δ for the customer
- Net Flow = Σ(positive deltas) vs Σ(negative deltas)

Sample SQL:
SELECT
  Branch,
  sum(CY_PurchaseTotal) AS cy_sales,
  sum(PY_PurchaseTotal) AS py_sales,
  (sum(CY_PurchaseTotal) - sum(PY_PurchaseTotal)) AS yoy_delta
FROM customer_weekly_sales
WHERE CustomerID = {customer_id:String}
GROUP BY Branch
ORDER BY yoy_delta ASC;
""",

    "onepager_cadence": """# One-Pager — Seasonal Cadence

Approach:
- Group sales by ISO week number (or month) for CY and PY
- Compare peaks/troughs to detect shifts in seasonal buying patterns

Sample SQL:
SELECT
  toISOWeek(CY_WeekDate) AS iso_week,
  sum(CY_PurchaseTotal) AS cy_sales,
  sum(PY_PurchaseTotal) AS py_sales,
  (sum(CY_PurchaseTotal) - sum(PY_PurchaseTotal)) AS yoy_delta
FROM customer_weekly_sales
WHERE CustomerID = {customer_id:String}
GROUP BY iso_week
ORDER BY iso_week;
"""
}




class FormulaModal(ModalScreen[str]):
    """Modal window for displaying formulas/queries."""
    # Capture keys inside the modal so they don't bubble to the app
    BINDINGS = [
        ("q", "close", "Close formulas"),
        ("enter", "close", "Close formulas"),
        ("space", "close", "Close formulas"),
        ("escape", "close", "Close formulas"),
    ]

    def __init__(self, text: str):
        super().__init__()
        self._text = text

    def compose(self):
        help_line = "\n\n[Press q, Enter, Space, or Esc to close]"
        yield Static(self._text + help_line, id="formula", expand=True)

    def action_close(self):
        # Close the modal only (never the app)
        self.dismiss("close")
