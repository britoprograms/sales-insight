# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
python app.py
```

### Dependencies
```bash
pip install -r requirements.txt
```

### Environment Setup
Create a `.env` file for optional ClickHouse and AI integration:
```
CH_URL=http://your-clickhouse-host:8123
CH_USER=default
CH_PASS=yourpassword  
CH_DATABASE=default
AI_PROVIDER=openai
AI_API_KEY=sk-...
```

## Architecture Overview

This is a **Textual-based TUI application** for year-over-year sales analysis with AI integration and browser-based charting capabilities.

### Core Architecture Pattern
- **Data Layer**: `store.py` - Dual-mode data access (mock data + ClickHouse-ready stubs)
- **TUI Framework**: Built on Textual with reactive widgets and keyboard-driven navigation
- **Chart Integration**: FastAPI server (`chart_targets.py`) serves ECharts to browser via `uvicorn`
- **AI Services**: OpenAI-compatible API client in `services/ai.py` and `services/ai_client.py`

### Key Application Structure
- `app.py`: Main TUI application with permanent dashboard (top) + tabbed content (bottom)
- `views/`: UI components for different report types
  - `dashboard.py`: Live metrics dashboard with sparklines and gauges
  - `decliners.py` / `growers.py`: Data tables with search functionality
  - `onepager.py`: Detailed customer analysis view
  - `ai_modal.py` / `prompt_modal.py`: AI interaction interfaces
- `config.py`: Environment configuration with `.env` support
- `themes.py`: Theme definitions (mono, matrix, light)

### Data Flow
1. **Store Layer**: Handles both mock data generation (deterministic via seed) and ClickHouse connection
2. **Priority Scoring**: Custom formula combining absolute dollar decline, percentage decline, and strategic importance
3. **Real-time Updates**: Dashboard refreshes every 1.5 seconds (configurable via `LIVE_DASH_INTERVAL`)
4. **Chart Export**: One-pager data can be visualized in browser via 'b' key

### Key Navigation Patterns
- Fully keyboard-driven interface
- Only ESC quits (not 'q')  
- Enter opens One-Pager from decliners/growers tables
- '/' for search, 'f' for formulas, 't' for theme cycling, 'r' for refresh
- 'a' opens AI modal for analysis

### Data Models
The `Row` dataclass in `store.py` represents core sales metrics:
- `customer_id`, `cy_sales`, `py_sales` 
- `yoy_delta`, `yoy_pct`, `priority_score`

### Mock vs Production Data
- **Mock Mode**: Deterministic synthetic data using `random.Random(42)`
- **DB Mode**: ClickHouse integration (stubs in place, ready for SQL implementation)
- Mode detection: `store.client` indicates active database connection

### AI Integration Details  
- Configurable AI provider via environment variables
- Local server support with default endpoint `http://10.8.29.155:8000/v1`
- OpenAI-compatible API interface for sales analysis

### Hard Development Rules
- Never use .Git; I will take care of all version control. 
- Ask question if you do not know how to proceed; NEVER delete a file in full.
- Ask for permission every time you are about to push a breaking update. NEVER do so without asking for permission.
- Test to make sure it compiles before asking permission for an update. 
