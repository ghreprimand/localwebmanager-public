from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import time
import webbrowser
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from .scanner import ServiceInfo, discover_local_web_services

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "localwebmanager"
REGISTRY_PATH = CONFIG_DIR / "registered_services.json"
LOG_DIR = CONFIG_DIR / "logs"


@dataclass
class RegisteredService:
    name: str
    cwd: str
    command: str


def load_registry() -> list[RegisteredService]:
    if not REGISTRY_PATH.exists():
        return []
    try:
        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    out: list[RegisteredService] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        cwd = str(item.get("cwd", "")).strip()
        command = str(item.get("command", "")).strip()
        if name and cwd and command:
            out.append(RegisteredService(name=name, cwd=cwd, command=command))
    return out


def save_registry(services: list[RegisteredService]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = [asdict(svc) for svc in services]
    REGISTRY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def detect_launch_command(cwd: str) -> str:
    pkg_json = Path(cwd) / "package.json"
    if not pkg_json.exists():
        return "npm run dev"

    try:
        data = json.loads(pkg_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "npm run dev"

    scripts = data.get("scripts") if isinstance(data, dict) else None
    if not isinstance(scripts, dict):
        return "npm run dev"

    if (Path(cwd) / "pnpm-lock.yaml").exists():
        runner = "pnpm"
    elif (Path(cwd) / "yarn.lock").exists():
        runner = "yarn"
    elif (Path(cwd) / "bun.lockb").exists() or (Path(cwd) / "bun.lock").exists():
        runner = "bun"
    else:
        runner = "npm"

    def run_script(name: str) -> str:
        if runner == "npm":
            return f"npm run {name}"
        if runner == "pnpm":
            return f"pnpm {name}"
        if runner == "yarn":
            return f"yarn {name}"
        return f"bun run {name}"

    def looks_like_web(script_name: str, script_cmd: str) -> bool:
        lower_name = script_name.lower()
        lower_cmd = script_cmd.lower()
        if any(bad in lower_name for bad in ("cli", "research", "test", "lint", "build")):
            return False
        if any(bad in lower_cmd for bad in (" src/cli", "cli.ts", "research", "jest", "vitest")):
            return False
        if "server" in lower_name or "web" in lower_name:
            return True
        web_markers = (
            "vite",
            "next",
            "nuxt",
            "astro",
            "fastify",
            "express",
            "webpack",
            "serve",
            "http.server",
            "uvicorn",
            "django",
            "flask",
            "tsx watch",
            "server.ts",
        )
        return any(marker in lower_cmd for marker in web_markers)

    priority = (
        "dev:server",
        "dev:web",
        "serve",
        "start:server",
        "server:dev",
        "start",
        "dev",
        "preview",
    )
    for key in priority:
        val = scripts.get(key)
        if isinstance(val, str) and looks_like_web(key, val):
            return run_script(key)

    for key, val in scripts.items():
        if isinstance(val, str) and looks_like_web(str(key), val):
            return run_script(str(key))

    if "dev" in scripts:
        return run_script("dev")
    if "start" in scripts:
        return run_script("start")
    return "npm run dev"


def launch_registered_service(svc: RegisteredService) -> tuple[bool, str]:
    cwd_path = Path(svc.cwd)
    if not cwd_path.exists():
        return False, f"Folder does not exist: {svc.cwd}"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{svc.name.replace(' ', '_').lower()}.log"

    shell_cmd = f"cd {shlex.quote(svc.cwd)} && {svc.command}"
    with log_file.open("ab") as out:
        proc = subprocess.Popen(
            ["bash", "-lc", shell_cmd],
            stdout=out,
            stderr=out,
            start_new_session=True,
        )
    time.sleep(1.2)
    exit_code = proc.poll()
    if exit_code is None:
        return True, f"Launched '{svc.name}' with `{svc.command}`"

    log_tail = ""
    try:
        log_tail = log_file.read_text(encoding="utf-8", errors="ignore")[-600:]
    except OSError:
        log_tail = ""
    return (
        False,
        f"Launch failed for '{svc.name}' (exit {exit_code}). Command: `{svc.command}`\n"
        f"Log: {log_file}\n{log_tail}",
    )


class ServiceRow(Gtk.Box):
    def __init__(self, service: ServiceInfo, on_killed: Callable[[], None], on_register: Callable[[ServiceInfo], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(xalign=0)
        title.set_markup(f"<b>{GLib.markup_escape_text(service.url)}</b>")
        title.set_hexpand(True)
        title.set_wrap(True)

        open_btn = Gtk.Button(label="Open")
        open_btn.connect("clicked", self._open_url, service.url)

        register_btn = Gtk.Button(label="Register")
        register_btn.connect("clicked", lambda *_args: on_register(service))

        kill_btn = Gtk.Button(label="Kill")
        kill_btn.set_sensitive(bool(service.pid))
        kill_btn.connect("clicked", self._kill_service, service, on_killed)

        top.append(title)
        top.append(open_btn)
        top.append(register_btn)
        top.append(kill_btn)

        meta = Gtk.Label(xalign=0)
        meta.set_selectable(True)
        meta.set_wrap(True)
        meta.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        meta.set_hexpand(True)
        meta.set_text(
            f"App: {service.app_name}    Process: {service.process_name} (PID: {service.pid or '-'})\n"
            f"Port: {service.port}    Host: {service.host}\n"
            f"Folder: {service.cwd or '-'}"
        )

        cmd = Gtk.Label(xalign=0)
        cmd.set_selectable(True)
        cmd.set_wrap(True)
        cmd.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        cmd.set_hexpand(True)
        cmd.set_text(f"Cmd: {service.cmdline or '-'}")

        self.append(top)
        self.append(meta)
        self.append(cmd)

    @staticmethod
    def _open_url(_button: Gtk.Button, url: str) -> None:
        webbrowser.open(url, new=2)

    def _kill_service(self, _button: Gtk.Button, service: ServiceInfo, on_killed: Callable[[], None]) -> None:
        if not service.pid:
            self._show_info("No PID is available for this service.")
            return

        confirm = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            message_type=Gtk.MessageType.WARNING,
            text=f"Kill process {service.pid}?",
            secondary_text=f"{service.process_name}\n{service.cmdline or service.url}",
        )
        confirm.connect("response", self._on_kill_confirm, service, on_killed)
        confirm.present()

    def _on_kill_confirm(
        self,
        dialog: Gtk.MessageDialog,
        response_id: Gtk.ResponseType,
        service: ServiceInfo,
        on_killed: Callable[[], None],
    ) -> None:
        dialog.close()
        if response_id != Gtk.ResponseType.OK or not service.pid:
            return

        try:
            os.kill(service.pid, signal.SIGTERM)
            self._show_info(f"Sent SIGTERM to PID {service.pid}.")
            on_killed()
        except ProcessLookupError:
            self._show_info(f"Process {service.pid} no longer exists.")
            on_killed()
        except PermissionError:
            self._show_info(f"Permission denied killing PID {service.pid}.")
        except OSError as err:
            self._show_info(f"Failed to kill PID {service.pid}: {err}")

    def _show_info(self, message: str) -> None:
        info = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            buttons=Gtk.ButtonsType.OK,
            message_type=Gtk.MessageType.INFO,
            text=message,
        )
        info.connect("response", lambda dlg, _resp: dlg.close())
        info.present()


class RegisteredRow(Gtk.Box):
    def __init__(
        self,
        svc: RegisteredService,
        on_launch: Callable[[RegisteredService], None],
        on_edit: Callable[[RegisteredService], None],
        on_remove: Callable[[RegisteredService], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(xalign=0)
        title.set_markup(f"<b>{GLib.markup_escape_text(svc.name)}</b>")
        title.set_hexpand(True)

        launch_btn = Gtk.Button(label="Launch")
        launch_btn.connect("clicked", lambda *_args: on_launch(svc))

        edit_btn = Gtk.Button(label="Edit")
        edit_btn.connect("clicked", lambda *_args: on_edit(svc))

        remove_btn = Gtk.Button(label="Remove")
        remove_btn.connect("clicked", lambda *_args: on_remove(svc))

        top.append(title)
        top.append(launch_btn)
        top.append(edit_btn)
        top.append(remove_btn)

        folder = Gtk.Label(xalign=0)
        folder.set_wrap(True)
        folder.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        folder.set_selectable(True)
        folder.set_text(f"Folder: {svc.cwd}")

        cmd = Gtk.Label(xalign=0)
        cmd.set_wrap(True)
        cmd.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        cmd.set_selectable(True)
        cmd.set_text(f"Launch: {svc.command}")

        self.append(top)
        self.append(folder)
        self.append(cmd)


class RegisterDialog(Gtk.Dialog):
    def __init__(
        self,
        parent: Gtk.Window,
        default_name: str = "",
        default_cwd: str = "",
        default_command: str = "",
    ) -> None:
        super().__init__(title="Register Service", transient_for=parent, modal=True)
        self.set_default_size(620, 220)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Save", Gtk.ResponseType.OK)

        box = self.get_content_area()
        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        form.set_margin_top(12)
        form.set_margin_bottom(12)
        form.set_margin_start(12)
        form.set_margin_end(12)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_text(default_name)

        path_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.cwd_entry = Gtk.Entry()
        self.cwd_entry.set_hexpand(True)
        self.cwd_entry.set_text(default_cwd)
        browse_btn = Gtk.Button(label="Browse")
        browse_btn.connect("clicked", self._browse)
        path_row.append(self.cwd_entry)
        path_row.append(browse_btn)

        self.command_entry = Gtk.Entry()
        self.command_entry.set_text(
            default_command or (detect_launch_command(default_cwd) if default_cwd else "npm run dev")
        )

        form.append(Gtk.Label(label="Name", xalign=0))
        form.append(self.name_entry)
        form.append(Gtk.Label(label="Working folder", xalign=0))
        form.append(path_row)
        form.append(Gtk.Label(label="Launch command", xalign=0))
        form.append(self.command_entry)

        box.append(form)

    def _browse(self, _button: Gtk.Button) -> None:
        chooser = Gtk.FileChooserNative(
            title="Select working directory",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="Select",
            cancel_label="Cancel",
        )
        chooser.connect("response", self._on_browse_response)
        chooser.show()

    def _on_browse_response(self, chooser: Gtk.FileChooserNative, response_id: int) -> None:
        if response_id == Gtk.ResponseType.ACCEPT:
            file_obj = chooser.get_file()
            if file_obj:
                path = file_obj.get_path()
                if path:
                    self.cwd_entry.set_text(path)
                    if not self.name_entry.get_text().strip():
                        self.name_entry.set_text(Path(path).name)
                    self.command_entry.set_text(detect_launch_command(path))
        chooser.destroy()

    def values(self) -> RegisteredService | None:
        name = self.name_entry.get_text().strip()
        cwd = self.cwd_entry.get_text().strip()
        command = self.command_entry.get_text().strip()
        if not name or not cwd or not command:
            return None
        return RegisteredService(name=name, cwd=cwd, command=command)


class LocalWebManagerWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app)
        self.set_title("LocalWebManager")
        self.set_default_size(1020, 760)

        self.registry = load_registry()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)

        self.notebook = Gtk.Notebook()

        self.active_tab = self._build_active_tab()
        self.registered_tab = self._build_registered_tab()

        self.notebook.append_page(self.active_tab, Gtk.Label(label="Active"))
        self.notebook.append_page(self.registered_tab, Gtk.Label(label="Registered"))

        root.append(self.notebook)
        self.set_child(root)

        self._refresh_active()
        self._refresh_registered()
        GLib.timeout_add_seconds(5, self._auto_refresh)

    def _build_active_tab(self) -> Gtk.Widget:
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.active_meta = Gtk.Label(xalign=0)
        self.active_meta.set_hexpand(True)

        self.web_only = Gtk.CheckButton(label="Likely web apps only")
        self.web_only.set_active(True)
        self.web_only.connect("toggled", lambda *_args: self._refresh_active())

        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", lambda *_args: self._refresh_active())

        header.append(self.active_meta)
        header.append(self.web_only)
        header.append(refresh_btn)

        self.active_list = Gtk.ListBox()
        self.active_list.set_selection_mode(Gtk.SelectionMode.NONE)

        scroller = Gtk.ScrolledWindow()
        scroller.set_child(self.active_list)
        scroller.set_vexpand(True)

        container.append(header)
        container.append(scroller)
        return container

    def _build_registered_tab(self) -> Gtk.Widget:
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.reg_meta = Gtk.Label(xalign=0)
        self.reg_meta.set_hexpand(True)

        add_btn = Gtk.Button(label="Add")
        add_btn.connect("clicked", lambda *_args: self._open_register_dialog())

        header.append(self.reg_meta)
        header.append(add_btn)

        self.reg_list = Gtk.ListBox()
        self.reg_list.set_selection_mode(Gtk.SelectionMode.NONE)

        scroller = Gtk.ScrolledWindow()
        scroller.set_child(self.reg_list)
        scroller.set_vexpand(True)

        container.append(header)
        container.append(scroller)
        return container

    def _auto_refresh(self) -> bool:
        self._refresh_active()
        return True

    def _refresh_active(self) -> None:
        services = discover_local_web_services()
        shown = [svc for svc in services if svc.likely_web] if self.web_only.get_active() else services

        self._clear_listbox(self.active_list)

        if not shown:
            self.active_list.append(Gtk.Label(label="No matching services detected.", xalign=0))
            self.active_meta.set_text(f"0 shown ({len(services)} total local services)")
            return

        for service in shown:
            self.active_list.append(ServiceRow(service, self._refresh_active, self._register_from_active))

        self.active_meta.set_text(f"{len(shown)} shown ({len(services)} total local services)")

    def _refresh_registered(self) -> None:
        self._clear_listbox(self.reg_list)
        if not self.registry:
            self.reg_list.append(Gtk.Label(label="No registered services.", xalign=0))
            self.reg_meta.set_text("0 registered")
            return

        for svc in self.registry:
            self.reg_list.append(
                RegisteredRow(svc, self._launch_registered, self._edit_registered, self._remove_registered)
            )

        self.reg_meta.set_text(f"{len(self.registry)} registered")

    @staticmethod
    def _clear_listbox(listbox: Gtk.ListBox) -> None:
        while True:
            child = listbox.get_first_child()
            if child is None:
                break
            listbox.remove(child)

    def _register_from_active(self, service: ServiceInfo) -> None:
        default_name = service.app_name if service.app_name != "unknown" else f"service-{service.port}"
        default_cwd = service.cwd or ""
        self._open_register_dialog(default_name=default_name, default_cwd=default_cwd)

    def _open_register_dialog(
        self,
        default_name: str = "",
        default_cwd: str = "",
        default_command: str = "",
    ) -> None:
        dialog = RegisterDialog(
            self,
            default_name=default_name,
            default_cwd=default_cwd,
            default_command=default_command,
        )
        dialog.connect("response", self._on_register_response)
        dialog.present()

    def _on_register_response(self, dialog: RegisterDialog, response_id: Gtk.ResponseType) -> None:
        if response_id != Gtk.ResponseType.OK:
            dialog.close()
            return

        values = dialog.values()
        dialog.close()
        if not values:
            self._show_info("Name, folder, and command are required.")
            return

        # Upsert by cwd path.
        updated = False
        for idx, existing in enumerate(self.registry):
            if Path(existing.cwd) == Path(values.cwd):
                self.registry[idx] = values
                updated = True
                break
        if not updated:
            self.registry.append(values)

        save_registry(self.registry)
        self._refresh_registered()
        self._show_info(f"Registered: {values.name}")

    def _launch_registered(self, svc: RegisteredService) -> None:
        ok, message = launch_registered_service(svc)
        self._show_info(message)
        if ok:
            GLib.timeout_add_seconds(2, self._post_launch_refresh)

    def _edit_registered(self, svc: RegisteredService) -> None:
        self._open_register_dialog(
            default_name=svc.name,
            default_cwd=svc.cwd,
            default_command=svc.command,
        )

    def _post_launch_refresh(self) -> bool:
        self._refresh_active()
        return False

    def _remove_registered(self, svc: RegisteredService) -> None:
        self.registry = [item for item in self.registry if not (item.cwd == svc.cwd and item.command == svc.command)]
        save_registry(self.registry)
        self._refresh_registered()

    def _show_info(self, message: str) -> None:
        info = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            buttons=Gtk.ButtonsType.OK,
            message_type=Gtk.MessageType.INFO,
            text=message,
        )
        info.connect("response", lambda dlg, _resp: dlg.close())
        info.present()


class LocalWebManagerApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="com.localwebmanager.app")

    def do_activate(self) -> None:
        window = self.props.active_window
        if not window:
            window = LocalWebManagerWindow(self)
        window.present()


def main() -> int:
    app = LocalWebManagerApp()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
