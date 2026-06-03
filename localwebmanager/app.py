from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .scanner import discover_local_web_services

app = FastAPI(title="LocalWebManager", version="0.1.0")


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Prevent browsers/iframes from caching static assets."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/static"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(NoCacheMiddleware)

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.delete("/api/services/{pid}")
def kill_service(pid: int) -> JSONResponse:
    """Send SIGTERM to a process by PID. Returns success or error."""
    import os
    import signal

    try:
        os.kill(pid, signal.SIGTERM)
        return JSONResponse({"ok": True, "pid": pid, "signal": "SIGTERM"})
    except ProcessLookupError:
        return JSONResponse(
            {"ok": False, "error": f"Process {pid} not found"}, status_code=404
        )
    except PermissionError:
        return JSONResponse(
            {"ok": False, "error": f"Permission denied killing PID {pid}"}, status_code=403
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
                "framework": svc.framework,
                "friendly_name": svc.friendly_name,
            }
            for svc in services
        ]
    }
    return JSONResponse(payload, headers={"Cache-Control": "no-store, max-age=0"})
