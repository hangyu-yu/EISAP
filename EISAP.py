import importlib
import subprocess
import sys
import os
import tempfile
from typing import List, Optional

def check_and_install_dependencies(requirements_file: str = None, 
                                 upgrade: bool = False) -> None:
    """
    Check and install required dependencies
    
    Args:
        requirements_file: Custom path to requirements file (default: looks in src/GUI/requirements.txt)
        upgrade: Whether to upgrade already installed packages
    """
    # Determine requirements file path
    if requirements_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        requirements_file = os.path.join(script_dir, "src", "GUI", "requirements.txt")
    
    try:
        # Try to read requirements file
        with open(requirements_file, 'r', encoding='utf-8') as f:
            required_packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"[Initialization] Requirements file not found: {requirements_file}")
        return

    installed_packages = []
    missing_packages = []
    
    # Check if each dependency is already installed
    for package in required_packages:
        try:
            # Handle package names with version specs
            pkg_name = package.split('==')[0].split('>=')[0].split('<=')[0].strip()
            importlib.import_module(pkg_name)
            installed_packages.append(package)
        except ImportError:
            missing_packages.append(package)

    if not missing_packages:
        print("[Initialization] All dependencies are already installed")
        return

    print(f"[Initialization] Missing {len(missing_packages)} dependencies: {', '.join(missing_packages)}")
    
    # Install missing dependencies
    pip_args = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        pip_args.append("--upgrade")
    
    try:
        subprocess.check_call(pip_args + missing_packages)
        print("[Initialization] Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"[Initialization] Failed to install dependencies: {e}")
        sys.exit(1)

def run_main_program(module_path: str, function_name: Optional[str] = None) -> None:
    """
    Execute the main GUI program
    
    Args:
        module_path: Relative path to main module (e.g., "src.GUI.gui_main")
        function_name: Function to execute (default: looks for main() or run())
    """
    print(f"[Initialization] Starting GUI application: {module_path}")
    try:
        # Add src directory to Python path if needed
        if "src" not in sys.path:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            src_dir = os.path.join(script_dir, "src")
            sys.path.insert(0, src_dir)
            
        module = importlib.import_module(module_path)
        
        # Automatically detect main function if not specified
        if function_name is None:
            for candidate in ["main", "run", "start"]:
                if hasattr(module, candidate):
                    function_name = candidate
                    break
        
        if function_name and hasattr(module, function_name):
            print(f"[Initialization] Executing function: {function_name}()")
            getattr(module, function_name)()
        else:
            print("[Initialization] No entry function found - module imported successfully")
    except ImportError as e:
        print(f"[Initialization] Failed to import GUI module: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# First-run Windows desktop shortcut
# ─────────────────────────────────────────────────────────────────────────────

def _prompt_windows_desktop_shortcut() -> None:
    """On first run under Windows, ask the user whether to create a desktop shortcut.

    The prompt appears exactly once: a sentinel file in %APPDATA%\\SOCEIS is
    written before the dialog is shown so repeated crashes do not re-prompt.
    """
    if sys.platform != 'win32':
        return

    # Sentinel stored in AppData — survives re-installations of the source tree.
    appdata   = os.environ.get('APPDATA', os.path.expanduser('~'))
    soc_dir   = os.path.join(appdata, 'SOCEIS')
    sentinel  = os.path.join(soc_dir, '.shortcut_prompted')

    if os.path.exists(sentinel):
        return  # already asked — skip

    # Write sentinel immediately; worst-case we never ask again if something fails
    try:
        os.makedirs(soc_dir, exist_ok=True)
        open(sentinel, 'w').close()
    except Exception:
        pass  # non-fatal

    # Ask via tkinter (DearPyGui is not yet running at this point)
    try:
        import tkinter as tk
        from tkinter import messagebox
        _root = tk.Tk()
        _root.withdraw()
        _root.attributes('-topmost', True)
        answer = messagebox.askyesno(
            "SOCEIS — Desktop Shortcut",
            "Would you like to add a SOCEIS shortcut to your desktop?\n\n"
            "(This prompt only appears once.)",
        )
        _root.destroy()
    except Exception:
        return  # tkinter unavailable — skip silently

    if answer:
        _create_windows_shortcut()


def _create_windows_shortcut() -> None:
    """Create SOCEIS.lnk on the Windows desktop via a temporary PowerShell script."""
    import ctypes

    script_dir  = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.abspath(__file__)
    icon_path   = os.path.join(script_dir, 'soceis', 'assets', 'icons', 'app_icon.ico')
    working_dir = script_dir

    python_exe = sys.executable

    # Use shell API for reliable Desktop path even when OneDrive redirects it
    try:
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.shell32.SHGetFolderPathW(0, 0x0010, 0, 0, buf)  # CSIDL_DESKTOPDIRECTORY
        desktop = buf.value if buf.value else os.path.join(os.path.expanduser('~'), 'Desktop')
    except Exception:
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')

    shortcut_path = os.path.join(desktop, 'SOCEIS.lnk')

    # Escape single quotes for PowerShell single-quoted string literals
    def _esc(p: str) -> str:
        return p.replace("'", "''")

    # Write the script to a temp file to avoid any shell-quoting issues
    ps_content = (
        "$ws = New-Object -ComObject WScript.Shell\n"
        f"$s = $ws.CreateShortcut('{_esc(shortcut_path)}')\n"
        f"$s.TargetPath       = '{_esc(python_exe)}'\n"
        # Arguments: the script path wrapped in double quotes (handles spaces)
        f"$s.Arguments        = '\"{_esc(script_path)}\"'\n"
        f"$s.WorkingDirectory = '{_esc(working_dir)}'\n"
        f"$s.IconLocation     = '{_esc(icon_path)}'\n"
        "$s.WindowStyle       = 1\n"
        "$s.Save()\n"
    )

    tmp_ps1 = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.ps1', delete=False, encoding='utf-8'
        ) as f:
            f.write(ps_content)
            tmp_ps1 = f.name

        result = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
             '-File', tmp_ps1],
            capture_output=True,
            timeout=15,
        )
        if result.returncode == 0:
            print("[Setup] Desktop shortcut 'SOCEIS' created successfully.")
        else:
            err = result.stderr.decode(errors='replace').strip()
            print(f"[Setup] Shortcut creation failed: {err}")
    except Exception as e:
        print(f"[Setup] Could not create desktop shortcut: {e}")
    finally:
        if tmp_ps1 and os.path.exists(tmp_ps1):
            try:
                os.unlink(tmp_ps1)
            except Exception:
                pass


if __name__ == '__main__':
    # 1. Check and install dependencies
    check_and_install_dependencies(upgrade=False)

    # 2. First-run setup: offer a desktop shortcut on Windows
    _prompt_windows_desktop_shortcut()

    # 3. Run the main GUI program
    run_main_program(
        module_path="src.GUI.gui_main",  # Python module path notation
        function_name=None  # Will auto-detect main(), run(), or start()
    )
