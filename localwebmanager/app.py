from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .scanner import discover_local_web_services

app = FastAPI(title="LocalWebManager", version="0.1.0")

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/api/services")
def get_services() -> dict[str, list[dict[str, str | int | None]]]:
    services = discover_local_web_services()
    payload = {
        "services": [
            {
                "pid": svc.pid,
                "process_name": svc.process_name,
                "cmdline": svc.cmdline,
                "cwd": svc.cwd,
                "app_name": svc.app_name,
                "likely_web": svc.likely_web,
                "host": svc.host,
                "port": svc.port,
                "status": svc.status,
                "url": svc.url,
            }
            for svc in services
        ]
    }
    return JSONResponse(payload, headers={"Cache-Control": "no-store, max-age=0"})
