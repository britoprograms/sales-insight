# charts.py
from typing import Any, Dict, Iterable, List, Sequence, Union, Optional
try:
    import pandas as pd  # optional
except Exception:
    pd = None  # type: ignore

Palette = Dict[str, Any]

THEMES: Dict[str, Palette] = {
    "dark":   {"bg":"#0b0f1a", "fg":"#cbd5e1", "axis":"#334155", "grid":"#1f2937",
               "colors":["#60a5fa","#34d399","#f472b6","#fbbf24","#a78bfa"]},
    "bright": {"bg":"#ffffff", "fg":"#111827", "axis":"#9ca3af", "grid":"#e5e7eb",
               "colors":["#2563eb","#059669","#dc2626","#7c3aed","#0ea5e9"]},
    "tokyo":  {"bg":"#1a1b26", "fg":"#c0caf5", "axis":"#565f89", "grid":"#2a2f44",
               "colors":["#7aa2f7","#bb9af7","#9ece6a","#f7768e","#e0af68"]},
    "barbie": {"bg":"#fff0f6", "fg":"#6b7280", "axis":"#f472b6", "grid":"#fde2e8",
               "colors":["#ec4899","#f472b6","#fb7185","#fbbf24","#60a5fa"]},
}

Records = Union["pd.DataFrame", Iterable[Dict[str, Any]]]

def option_from_sales(
    data: Records,
    category_col: str = "week",           # x-axis (e.g., "W1","W2",...)
    value_col: str = "sales",             # y values
    split_col: Optional[str] = "subcommodity",  # series split (None => single series)
    theme: str = "dark",
    title: str = "Sales",
) -> Dict[str, Any]:
    pal = THEMES.get(theme, THEMES["dark"])

    # Normalize to list-of-dicts if pandas isn't present
    if pd is not None and hasattr(data, "to_dict"):
        records: List[Dict[str, Any]] = list(data.to_dict(orient="records"))  # type: ignore
    else:
        records = list(data)  # assume iterable of dicts

    # Build axes + series
    cats = sorted({r[category_col] for r in records})
    if split_col:
        series_keys = sorted({r[split_col] for r in records})
    else:
        series_keys = ["Series"]

    # Map values
    series: List[Dict[str, Any]] = []
    for key in series_keys:
        points = []
        for c in cats:
            v = 0
            for r in records:
                if r.get(category_col) == c and (not split_col or r.get(split_col) == key):
                    v = r.get(value_col, 0) or 0
                    break
            points.append(v)
        series.append({"type": "line", "name": str(key), "data": points, "smooth": True})

    option = {
        "backgroundColor": pal["bg"],
        "color": pal["colors"],
        "title": {"text": title, "left": "center", "textStyle": {"color": pal["fg"]}},
        "tooltip": {"trigger": "axis"},
        "legend": {"bottom": 0, "textStyle": {"color": pal["fg"]}},
        "grid": {"left": 50, "right": 30, "top": 60, "bottom": 60},
        "xAxis": {"type": "category", "data": cats,
                  "axisLabel":{"color": pal["fg"]}, "axisLine":{"lineStyle":{"color": pal["axis"]}}},
        "yAxis": {"type": "value",
                  "axisLabel":{"color": pal["fg"]}, "splitLine":{"lineStyle":{"color": pal["grid"]}}},
        "series": series,
    }
    return option

