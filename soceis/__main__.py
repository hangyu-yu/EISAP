"""
soceis.__main__
───────────────
Entry point for the `eisap` / `soceis` console scripts and module launchers.

Workflow
--------
1. Check / install runtime dependencies (reads src/GUI/requirements.txt).
2. On first run under Windows, offer a desktop shortcut (asks the user).
3. Launch the DearPyGui application (src.GUI.gui_main).
"""

import importlib
import os
import subprocess
import sys
import tempfile
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Dependency bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def _check_and_install_dependencies() -> None:
    """Verify all entries in requirements.txt are importable; install any that are missing."""
    try:
        import importlib.resources as _ir
        req_text = (_ir.files("src") / "GUI" / "requirements.txt").read_text(encoding="utf-8")
    except Exception:
        # Fallback: find requirements.txt relative to this file's installed location
        _here = os.path.dirname(os.path.abspath(__file__))
        req_path = os.path.join(_here, "..", "src", "GUI", "requirements.txt")
        try:
            with open(os.path.normpath(req_path), encoding="utf-8") as fh:
                req_text = fh.read()
        except Exception:
            print("[SOCEIS] requirements.txt not found — skipping dependency check.")
            return

    required = [
        line.strip() for line in req_text.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    missing = []
    for pkg in required:
        name = pkg.split("==")[0].split(">=")[0].split("<=")[0].strip()
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(pkg)

    if not missing:
        print("[SOCEIS] All dependencies satisfied.")
        return

    print(f"[SOCEIS] Installing missing packages: {', '.join(missing)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("[SOCEIS] Missing packages installed successfully.")
    except subprocess.CalledProcessError as exc:
        print(f"[SOCEIS] Could not install dependencies: {exc}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Windows desktop shortcut (first-run, Windows only, asks the user)
# ─────────────────────────────────────────────────────────────────────────────

def _prompt_windows_desktop_shortcut() -> None:
    """Ask once whether to create a desktop shortcut (Windows only)."""
    if sys.platform != "win32":
        return

    appdata  = os.environ.get("APPDATA", os.path.expanduser("~"))
    soc_dir  = os.path.join(appdata, "SOCEIS")
    sentinel = os.path.join(soc_dir, ".shortcut_prompted")

    if os.path.exists(sentinel):
        return  # already asked; never prompt again

    # Write the sentinel before showing the dialog so a crash doesn't re-prompt.
    try:
        os.makedirs(soc_dir, exist_ok=True)
        open(sentinel, "w").close()
    except Exception:
        pass

    try:
        import tkinter as tk
        from tkinter import messagebox
        _root = tk.Tk()
        _root.withdraw()
        _root.attributes("-topmost", True)
        answer = messagebox.askyesno(
            "SOCEIS — Desktop Shortcut",
            "Would you like to create a SOCEIS shortcut on your desktop?\n\n"
            "(This prompt appears only once.)",
        )
        _root.destroy()
    except Exception:
        return  # tkinter unavailable — skip silently

    if answer:
        _create_windows_shortcut()


def _create_windows_shortcut() -> None:
    """Create SOCEIS.lnk on the Windows desktop via a temporary PowerShell script.

    The shortcut runs `python -m eisap`, so it works regardless of whether the
    user installed via pip or cloned the repo.
    """
    import ctypes

    python_exe = sys.executable

    # Find the app_icon.ico from the installed package if available.
    icon_path = ""
    try:
        import importlib.resources as _ir
        _ico = _ir.files("src") / "assets" / "icons" / "app_icon.ico"
        icon_path = str(_ico)
    except Exception:
        pass

    # Resolve the Desktop folder (handles OneDrive redirection on Windows).
    try:
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.shell32.SHGetFolderPathW(0, 0x0010, 0, 0, buf)  # CSIDL_DESKTOPDIRECTORY
        desktop = buf.value or os.path.join(os.path.expanduser("~"), "Desktop")
    except Exception:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")

    shortcut_path = os.path.join(desktop, "SOCEIS.lnk")

    def _esc(s: str) -> str:
        return s.replace("'", "''")

    ps_lines = [
        "$ws = New-Object -ComObject WScript.Shell",
        f"$s = $ws.CreateShortcut('{_esc(shortcut_path)}')",
        f"$s.TargetPath    = '{_esc(python_exe)}'",
        "$s.Arguments     = '-m eisap'",
        "$s.WindowStyle   = 1",
    ]
    if icon_path:
        ps_lines.append(f"$s.IconLocation = '{_esc(icon_path)}'")
    ps_lines.append("$s.Save()")
    ps_content = "\n".join(ps_lines) + "\n"

    tmp_ps1 = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ps1", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(ps_content)
            tmp_ps1 = fh.name

        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-File", tmp_ps1,
            ],
            capture_output=True,
            timeout=15,
        )
        if result.returncode == 0:
            print("[SOCEIS] Desktop shortcut 'SOCEIS' created successfully.")
        else:
            err = result.stderr.decode(errors="replace").strip()
            print(f"[SOCEIS] Shortcut creation failed: {err}")
    except Exception as exc:
        print(f"[SOCEIS] Could not create desktop shortcut: {exc}")
    finally:
        if tmp_ps1 and os.path.exists(tmp_ps1):
            try:
                os.unlink(tmp_ps1)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point invoked by the `eisap` / `soceis` console scripts."""
    _check_and_install_dependencies()
    _prompt_windows_desktop_shortcut()

    # Import and run the GUI.  `src` is installed as a top-level package, so
    # `import src.GUI.gui_main` works from any directory after `pip install eisap`.
    try:
        gui_main = importlib.import_module("src.GUI.gui_main")
    except ImportError as exc:
        print(f"[SOCEIS] Cannot import GUI module: {exc}")
        sys.exit(1)

    for fn_name in ("main", "run", "start"):
        if hasattr(gui_main, fn_name):
            getattr(gui_main, fn_name)()
            return

    print("[SOCEIS] No entry function found in src.GUI.gui_main.")


if __name__ == "__main__":
    main()
