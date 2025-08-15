# charts.py — ECharts option builders for Sales Insight TUI

from typing import List, Dict, Any


def option_from_sales(records: List[Dict[str, Any]], *, theme: str = "mono", title: str = "Weekly Sales"):
    """
    Build a simple line chart for weekly sales.
    records: [{"week": "W01", "sales": 1234, "subcommodity": "X"}, ...]
    """
    weeks = [r.get("week") for r in records]
    sales = [r.get("sales") for r in records]

    def fg_for(t: str) -> str:
        return "#111111" if t == "light" else "#ffffff"

    return {
        "backgroundColor": "transparent",
        "title": {"text": title, "left": "center", "textStyle": {"color": fg_for(theme)}},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": weeks, "axisLabel": {"color": fg_for(theme)}},
        "yAxis": {"type": "value", "axisLabel": {"color": fg_for(theme)}, "splitLine": {"show": False}},
        "grid": {"left": 50, "right": 20, "top": 60, "bottom": 40},
        "series": [
            {"type": "line", "smooth": True, "data": sales}
        ],
        "animationDuration": 300,
    }


def option_compare_decliners_growers(
    stats: Dict[str, Dict[str, float]],
    *,
    theme: str = "mono",
    title: str = "Decliners vs Growers"
):
    """
    Build an ECharts option that compares decliners vs growers.

    stats = {
      "decliners": {"count": int, "sum_delta": float},
      "growers":   {"count": int, "sum_delta": float},
    }
    """
    def palette(t: str):
        if t == "light":
            return {"fg": "#111111", "decl": "#0ea5e9", "grow": "#22c55e"}
        if t == "matrix":
            return {"fg": "#00ff7f", "decl": "#22d3ee", "grow": "#86efac"}
        return {"fg": "#ffffff", "decl": "#60a5fa", "grow": "#34d399"}  # mono

    p = palette(theme)

    categories = ["Count", "Σ YoY Δ ($)"]
    d_vals = [int(stats["decliners"]["count"]), round(float(stats["decliners"]["sum_delta"]), 2)]
    g_vals = [int(stats["growers"]["count"]),   round(float(stats["growers"]["sum_delta"]), 2)]

    return {
        "backgroundColor": "transparent",
        "title": {"text": title, "left": "center", "textStyle": {"color": p["fg"]}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"data": ["Decliners", "Growers"], "top": 24, "textStyle": {"color": p["fg"]}},
        "xAxis": {"type": "category", "data": categories, "axisLabel": {"color": p["fg"]}},
        "yAxis": {"type": "value", "axisLabel": {"color": p["fg"]}, "splitLine": {"show": False}},
        "series": [
            {"name": "Decliners", "type": "bar", "data": d_vals, "barGap": "10%", "itemStyle": {"color": p["decl"]}},
            {"name": "Growers",   "type": "bar", "data": g_vals, "itemStyle": {"color": p["grow"]}},
        ],
        "grid": {"left": 50, "right": 20, "top": 60, "bottom": 40},
        "animationDuration": 250,
    }

