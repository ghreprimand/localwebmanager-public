# LocalWebManager

LocalWebManager is a lightweight browser-based dashboard for discovering, inspecting, and stopping local web development servers.

It scans your machine's listening TCP sockets, identifies dev servers by process name and command line, and presents them in a polished dark UI — with one-click open, URL copy, process kill, and pinning.

## Features

- Auto-detect running dev servers: Vite, Next.js, Nuxt, Astro, SvelteKit, Flask, Django, FastAPI, Rails, Bun, Deno, and more.
- Friendly display names derived from project folder + detected framework (e.g. "My App · Vite").
- Pin services to a persistent top section (stored in `localStorage`); pinned-but-offline services remain visible as greyed cards.
- Kill any process with SIGTERM directly from the UI.
- Copy URL to clipboard with visual feedback.
- Live refresh with keyed DOM reconciliation — cards update in-place without flashing.
- "Web apps only" filter toggle.
- Responsive dark theme with Inter font.

## Requirements

Python 3.9+ and the packages in `requirements.txt` (fastapi, uvicorn, psutil). `starlette` ships with fastapi.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

### Quick start

```bash
./run-desktop.sh
```

Starts the uvicorn server on port 8000 and opens the dashboard in your default browser. If the server is already running it just opens the browser.

### Launcher script (start / stop / status / logs)

```bash
./scripts/localwebmanager start
./scripts/localwebmanager stop
./scripts/localwebmanager restart
./scripts/localwebmanager status
./scripts/localwebmanager logs
```

The launcher manages a PID file under `~/.cache/localwebmanager/`, handles port conflicts, and sends desktop notifications via `notify-send` when available.

The port defaults to 8000. Override with the `LWM_PORT` environment variable.

### Direct uvicorn

```bash
uvicorn localwebmanager.app:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000/`.

## Install a Desktop Launcher

```bash
./scripts/install-desktop-entry.sh
```

Installs a `.desktop` entry and icon under your user data directory so LocalWebManager appears in your application launcher.

## How Detection Works

LocalWebManager calls `psutil` to enumerate local listening TCP sockets, filters out privileged and non-local addresses, then scores each process against a list of framework signatures (command line keywords, process names, common ports). Matching services get a framework label and emoji badge.

Detection is heuristic. It may miss unusual setups or surface non-web local listeners that look like dev servers.

## Safety Model

- Only local listening sockets are scanned (`127.0.0.1`, `0.0.0.0`, `::1`).
- The server binds to `127.0.0.1` only.
- Kill sends `SIGTERM` with a browser confirmation prompt; it does not force-kill.
- Some process command lines or working directories may be hidden by OS permissions.

## License

MIT. See [LICENSE](LICENSE).
