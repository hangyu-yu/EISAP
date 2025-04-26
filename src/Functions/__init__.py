import os
import importlib.util

# Get the current package path
package_path = os.path.dirname(__file__)

# Traverse all submodules
for root, dirs, files in os.walk(package_path):
    if "__pycache__" in dirs:
        dirs.remove("__pycache__")
        
    for file in files:
        if file.endswith(".py") and not file.startswith("__"):
            # Construct the module path
            module_path = os.path.join(root, file)
            module_name = os.path.splitext(file)[0]

            # Dynamically load the module
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Add functions from the module to the global namespace
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and not attr_name.startswith("__"):
                    globals()[attr_name] = attr

# Optional: Define __all__ to explicitly expose functions
__all__ = [name for name in globals() if callable(globals()[name]) and not name.startswith("__")]