import os
import importlib.util

# Get the current package path
package_path = os.path.dirname(__file__)

# Traverse all submodules
for root, dirs, files in os.walk(package_path):
    if "__pycache__" in dirs:
        dirs.remove("__pycache__")
        
    for file in files:
        if file == "gui_tab_soceis.py":  # Only process gui_tab_soceis.py
            # Construct the module path
            module_path = os.path.join(root, file)
            module_name = os.path.splitext(file)[0]

            # Dynamically load the module
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Add only the gui_tab_soceis function to the global namespace
            if hasattr(module, "gui_tab_soceis") and callable(getattr(module, "gui_tab_soceis")):
                globals()["gui_tab_soceis"] = getattr(module, "gui_tab_soceis")

# Define __all__ to explicitly expose the gui_tab_soceis function
__all__ = ["gui_tab_soceis"] if "gui_tab_soceis" in globals() else []
