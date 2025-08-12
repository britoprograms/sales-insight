Sales Insight TUI
Sales Insight TUI is a Python-based full-screen terminal application for analyzing year-over-year (YoY) sales performance, powered by Textual.
It provides a fast, keyboard-driven interface for business analysts, buyers, sales, finance, and ops teams to spot declining customers, dig into root causes, and visualize trends.

✨ Features
📊 Decliners Report
Quickly identify top YoY sales decliners, ranked by a custom priority score based on:

Absolute dollar decline

Percentage decline

Strategic importance (prior-year sales share)

📝 Customer One-Pager
View a single customer’s summary including:

Headline YoY performance

Price–Volume–Mix (PVM) breakdown

Returns impact

Geographic redistribution (branch deltas)

Weekly cadence chart data

📈 Browser-based ECharts Integration (b key)
Launch interactive weekly sales charts directly in your browser.

🔍 Formula Reference (f key)
Pop-up modal showing the exact formulas & calculations used for each metric.

🎨 Multiple Themes (t key)
Switch between mono, light, and matrix themes.

⌨️ Fully Keyboard-Driven Navigation

↑/↓ — Navigate sidebar

Enter — Open view

b — Open browser chart

f — Show formulas

Esc — Quit

🛠 Architecture
Python
Core application logic & analytics.

Textual
Rich terminal UI framework.

FastAPI + ECharts
Serves interactive charts to a browser.

Mock/ClickHouse Data Store
Switch between offline mock mode and live ClickHouse queries (via raw SQL).

📂 Project Structure
bash
Copy
Edit
sales-insight/
│
├── app.py                  # Main application entry point
├── config.py               # Environment/config loader
├── store.py                # Data access layer (mock or ClickHouse)
├── themes.py               # Theme definitions
├── charts.py               # ECharts option builder
├── chart_targets.py        # Chart rendering (browser)
│
└── views/                  # UI components
    ├── decliners.py        # Decliners report view
    ├── onepager.py         # One-Pager view
    ├── formulas.py         # Formulas modal content
🚀 Running Locally
1. Install dependencies

bash
Copy
Edit
pip install -r requirements.txt
2. (Optional) Set up .env for ClickHouse & AI API

bash
Copy
Edit
CH_URL=http://your-clickhouse-host:8123
CH_USER=default
CH_PASS=yourpassword
CH_DATABASE=default
AI_PROVIDER=openai
AI_API_KEY=sk-...
3. Run the app

bash
Copy
Edit
python app.py
🔮 Future Enhancements
ClickHouse live data integration

Automated root cause tagging (AI-powered)

External market/news feeds for sales impact analysis

Exportable PDF reports
