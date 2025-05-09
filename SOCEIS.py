import importlib
import subprocess
import sys
import os
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

if __name__ == "__main__":
    # 1. Check and install dependencies
    check_and_install_dependencies(upgrade=False)
    
    # 2. Run the main GUI program
    run_main_program(
        module_path="src.GUI.gui_main",  # Python module path notation
        function_name=None  # Will auto-detect main(), run(), or start()
    )
