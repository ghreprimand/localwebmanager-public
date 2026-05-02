# LocalWebManager

LocalWebManager is a small native desktop utility for finding, opening, launching, and stopping local web development servers.

It is meant for developers who regularly have several localhost services running at once and want a fast desktop view of what is listening on which port.

## Features

- Native GTK 4 desktop app.
- Active tab for detected localhost services.
- Registered tab for saved project folders and launch commands.
- One-click open, register, launch, edit, remove, and SIGTERM actions.
- Auto-detect launch commands from `package.json` and lockfiles.
- Works with common npm, pnpm, yarn, and bun project layouts.
- Localhost web dashboard for quick browser-based inspection.
- Auto-refresh every 5 seconds plus manual refresh.

## Install Requirements

LocalWebManager needs Python 3, GTK 4 Python bindings, and `psutil`.

Arch:

```bash
sudo pacman -S python python-gobject gtk4
```

Debian/Ubuntu:

```bash
sudo apt install python3 python3-gi gir1.2-gtk-4.0
```

`run-desktop.sh` will install `psutil` for the current user if it is missing.

## Run The Desktop App

```bash
./run-desktop.sh
```

## Run The Browser Dashboard

```bash
./run.sh
```

Then open:

```text
http://127.0.0.1:8000/
```

The browser dashboard is intentionally read-only. Use the desktop app for register, launch, and kill actions.

## Install A Desktop Launcher

```bash
./scripts/install-desktop-entry.sh
```

This installs a `.desktop` entry and icon under your user data directory.

## How Detection Works

LocalWebManager scans local listening TCP sockets with `psutil`, keeps non-privileged localhost listeners, and labels likely web services using process names, command lines, common development ports, and common web framework commands.

The detector is intentionally heuristic. It may miss unusual setups and may show non-web local services if they look like development servers.

## Registered Services

Registered services are stored in:

```text
~/.config/localwebmanager/registered_services.json
```

Launch logs are written to:

```text
~/.config/localwebmanager/logs/
```

## Safety Model

- LocalWebManager only scans local listening sockets.
- The browser dashboard binds to `127.0.0.1`.
- Registered launch commands are user-controlled shell commands.
- The Kill action sends `SIGTERM` only after confirmation.
- Some process command lines or working directories may be hidden by OS permissions.

Do not register commands you would not run manually in a terminal.

## License

MIT. See [LICENSE](LICENSE).
