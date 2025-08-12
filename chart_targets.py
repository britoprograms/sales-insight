
# chart_targets.py
import json, socket, threading, time, webbrowser
from typing import Any, Dict, Optional

# ---- Browser tab (FastAPI) ----
try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
except Exception:
    FastAPI = None  # type: ignore

ECHARTS_PAGE = """
<!doctype html><html><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Analytics</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>html,body,#chart{margin:0;height:100%;width:100%;background:#0b0f1a;color:#cbd5e1}</style>
</head><body><div id="chart"></div>
<script>
const chart = echarts.init(document.getElementById('chart'));
let ver=-1; async function tick(){
  try{ const r=await fetch('/option?ts='+Date.now());
       const j=await r.json(); if(j.version!==ver){ver=j.version; chart.setOption(j.option,true);} }
  catch(e){} }
tick(); setInterval(tick, 750);
</script></body></html>
"""

class BrowserChart:
    def __init__(self) -> None:
        if FastAPI is None:
            raise RuntimeError("FastAPI/uvicorn not installed. pip install fastapi uvicorn")
        self._app = FastAPI()
        self._latest: Dict[str, Any] = {"title":{"text":"No data yet"},"series":[]}
        self._ver = 0
        self._lock = threading.Lock()
        self._port: Optional[int] = None
        self._started = False

        @self._app.get("/", response_class=HTMLResponse)
        def index(): return HTMLResponse(ECHARTS_PAGE)

        @self._app.get("/option", response_class=JSONResponse)
        def option():
            with self._lock: return JSONResponse({"version": self._ver, "option": self._latest})

    def _free_port(self) -> int:
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]; s.close(); return p

    def _run(self):
        assert self._port is not None
        uvicorn.run(self._app, host="127.0.0.1", port=self._port, log_level="warning")

    def open_or_update(self, option: Dict[str, Any]) -> None:
        with self._lock:
            self._latest = option; self._ver += 1
        if not self._started:
            self._started = True
            self._port = self._free_port()
            threading.Thread(target=self._run, daemon=True).start()
            webbrowser.open_new_tab(f"http://127.0.0.1:{self._port}/")

