"""News Radar — FastAPI entry point.

Run from the news_radar/ folder:
    uvicorn app.main:app --host 127.0.0.1 --port 8100
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from .core import Radar
from .models import CATEGORIES
from .sources import REGISTRY

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
STATIC = Path(__file__).resolve().parent.parent / "static"

radar = Radar()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await radar.start()
    yield
    await radar.stop()


app = FastAPI(title="News Radar", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def desk():
    return FileResponse(STATIC / "index.html")


@app.get("/sources")
async def sources_page():
    return FileResponse(STATIC / "sources.html")


# ── news ─────────────────────────────────────────────────────────────────────
@app.get("/api/news")
async def news(limit: int = 300, category: str | None = None, ticker: str | None = None,
               topic: int | None = None, new_only: bool = False):
    return {"items": radar.recent(min(limit, 1000), category, ticker, topic, new_only),
            "categories": CATEGORIES}


@app.post("/api/news/{nid}/seen")
async def mark_seen(nid: str):
    radar.db.execute("UPDATE news SET seen=1 WHERE id=?", (nid,))
    row = radar.db.one("SELECT * FROM news WHERE id=?", (nid,))
    if row:
        await radar.broadcast({"type": "update", "item": radar.view(row)})
    return {"ok": True}


@app.post("/api/news/seen_all")
async def mark_all_seen():
    radar.db.execute("UPDATE news SET seen=1 WHERE seen=0")
    return {"ok": True}


# ── topics ───────────────────────────────────────────────────────────────────
@app.get("/api/topics")
async def topics():
    return {"topics": radar.topic_list()}


@app.post("/api/topics/rebuild")
async def topics_rebuild():
    return {"topics": await radar.refresh_topics()}


# ── ticker panel ─────────────────────────────────────────────────────────────
@app.get("/api/ticker/{sym}")
async def ticker(sym: str, tf: str = "5m", news_ts: float | None = None):
    sym = sym.upper().strip()
    try:
        rep = await radar.market.report(sym, tf, news_ts)
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": f"Alpaca: {e}"}, status_code=502)
    rep["news"] = radar.recent(20, ticker=sym)
    return rep


# ── sources & settings ───────────────────────────────────────────────────────
@app.get("/api/sources")
async def list_sources():
    return {"sources": [radar.source_view(sid) for sid in REGISTRY], "settings": radar.settings()}


@app.put("/api/sources/{sid}")
async def save_source(sid: str, body: dict):
    if sid not in REGISTRY:
        raise HTTPException(404)
    radar.save_source(sid, body)
    radar.restart_source(sid)
    return radar.source_view(sid)


@app.post("/api/sources/{sid}/test")
async def test_source(sid: str):
    if sid not in REGISTRY:
        raise HTTPException(404)
    src = REGISTRY[sid](radar.source_config(sid), radar)
    ok, why = src.ready()
    if not ok:
        return {"ok": False, "message": why}
    try:
        return {"ok": True, "message": await src.test()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": str(e)[:300]}


@app.put("/api/settings")
async def save_settings(body: dict):
    s = radar.update_settings(body)
    for sid in ("sec", "rss", "finnhub", "tickertick"):   # these read the watchlist / UA
        radar.restart_source(sid)
    return s


# ── live push ────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    radar.clients.add(sock)
    try:
        await sock.send_json({"type": "status", "sources": radar.status_list()})
        while True:
            await sock.receive_text()   # keepalive pings from the page
    except WebSocketDisconnect:
        pass
    finally:
        radar.clients.discard(sock)
