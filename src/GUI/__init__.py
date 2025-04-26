import os
import importlib.util
from typing import Dict, Callable

# Get the current package path
package_path = os.path.dirname(__file__)

# Dictionary to store imported functions
_imported_functions: Dict[str, Callable] = {}

# Traverse all submodules
for root, dirs, files in os.walk(package_path):
    # Skip cache directories
    if "__pycache__" in dirs:
        dirs.remove("__pycache__")
        
    for file in files:
        # Skip non-Python files and __init__.py
        if not file.endswith('.py') or file == "__init__.py":
            continue
            
        # Get the base filename without extension
        module_name = os.path.splitext(file)[0]
        
        # Skip gui_main.py as requested
        if module_name == "gui_main" or module_name == "config":
            continue
            
        # Construct the module path
        module_path = os.path.join(root, file)

        try:
            # Dynamically load the module
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Get the function that matches the filename
                if hasattr(module, module_name) and callable(getattr(module, module_name)):
                    _imported_functions[module_name] = getattr(module, module_name)
                    
        except Exception as e:
            print(f"Failed to import from {file}: {str(e)}")
            continue

# Add the imported functions to globals
globals().update(_imported_functions)

# Define __all__ to explicitly expose the imported functions
__all__ = list(_imported_functions.keys())
