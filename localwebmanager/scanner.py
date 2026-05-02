from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import psutil


LOCAL_HOSTS = {"127.0.0.1", "::1", "0.0.0.0", "::", "localhost"}


@dataclass
class ServiceInfo:
    pid: int | None
    process_name: str
    cmdline: str
    cwd: str | None
    app_name: str
    likely_web: bool
    host: str
    port: int
    status: str
    url: str


def _is_local_address(ip: str | None) -> bool:
    if not ip:
        return True
    if ip in LOCAL_HOSTS:
        return True
    try:
        parsed = socket.getaddrinfo(ip, None)
        for entry in parsed:
            if entry[4][0].startswith("127."):
                return True
    except socket.gaierror:
        return False
    return False


def _is_likely_web_process(cmdline: str, proc_name: str) -> bool:
    haystack = f"{proc_name} {cmdline}".lower()
    markers = (
        "vite",
        "next",
        "astro",
        "webpack",
        "parcel",
        "react-scripts",
        "ng serve",
        "nuxt",
        "svelte",
        "flask",
        "django",
        "uvicorn",
        "gunicorn",
        "http.server",
        "php -s",
        "rails server",
        "hugo",
    )
    return any(marker in haystack for marker in markers)


def _app_name_from_cwd(cwd: str | None) -> str:
    if not cwd:
        return "unknown"
    return Path(cwd).name or cwd


def _is_likely_web_service(process_name: str, cmdline: str, port: int) -> bool:
    if _is_likely_web_process(cmdline, process_name):
        return True
    common_web_ports = {
        3000,
        3001,
        4173,
        4321,
        5000,
        5173,
        5174,
        5180,
        5181,
        5182,
        8000,
        8080,
        8081,
        8088,
        8787,
        8888,
        9000,
    }
    if port in common_web_ports:
        return True
    return 1024 <= port <= 49151 and any(
        token in cmdline.lower() for token in ("server", "dev", "preview", "start")
    )


def _safe_process(pid: int) -> psutil.Process | None:
    try:
        return psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def _iter_listening_connections() -> Iterable[psutil._common.sconn]:
    try:
        conns = psutil.net_connections(kind="inet")
    except psutil.AccessDenied:
        return []
    return (conn for conn in conns if conn.status == psutil.CONN_LISTEN)


def discover_local_web_services() -> list[ServiceInfo]:
    services: dict[tuple[int | None, str, int], ServiceInfo] = {}

    for conn in _iter_listening_connections():
        laddr = conn.laddr
        if not laddr:
            continue

        host = getattr(laddr, "ip", None) or laddr[0]
        port = getattr(laddr, "port", None) or laddr[1]

        if not _is_local_address(host):
            continue

        pid = conn.pid
        process_name = "unknown"
        cmdline = ""
        cwd = None

        if pid:
            proc = _safe_process(pid)
            if proc:
                try:
                    process_name = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process_name = "unknown"

                try:
                    cmdline_parts = proc.cmdline()
                    cmdline = " ".join(cmdline_parts)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    cmdline = ""

                try:
                    cwd = proc.cwd()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    cwd = None

        # LocalWebManager focuses on user-launched local services.
        # Keep all local LISTEN sockets on non-privileged ports to avoid false negatives.
        if port < 1024:
            continue

        url = f"http://localhost:{port}/"
        key = (pid, host, port)
        services[key] = ServiceInfo(
            pid=pid,
            process_name=process_name,
            cmdline=cmdline,
            cwd=cwd,
            app_name=_app_name_from_cwd(cwd),
            likely_web=_is_likely_web_service(process_name, cmdline, port),
            host=host,
            port=port,
            status="LISTEN",
            url=url,
        )

    return sorted(
        services.values(),
        key=lambda s: (s.port, s.process_name.lower(), s.pid or 0),
    )
