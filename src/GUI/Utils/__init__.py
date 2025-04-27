import os
import importlib.util
import types
from typing import Dict, List, Callable

# Dictionary to store functions grouped by their source files
file_functions: Dict[str, List[Callable]] = {}

# Get the current package path
package_path = os.path.dirname(__file__)

# Iterate through all submodules
for root, dirs, files in os.walk(package_path):
    if "__pycache__" in dirs:
        dirs.remove("__pycache__")
        
    for file in files:
        if file.endswith(".py") and not file.startswith("__"):
            # Get the base filename without extension
            module_name = os.path.splitext(file)[0]
            
            # Skip special files
            if module_name == "gui_main":
                continue
                
            # Create a module-like object for this file's functions
            file_module = types.ModuleType(module_name)
            
            # Construct the module path
            module_path = os.path.join(root, file)

            try:
                # Dynamically load the module
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Copy the module's docstring
                    if module.__doc__:
                        file_module.__doc__ = module.__doc__
                    
                    # Collect all callable functions from the module
                    functions = []
                    for attr_name in dir(module):
                        if attr_name.startswith("__"):
                            continue
                            
                        attr = getattr(module, attr_name)
                        if callable(attr):
                            # Add to global namespace with prefix
                            globals()[f"{module_name}_{attr_name}"] = attr
                            
                            # Add to this file's function list
                            functions.append(attr)
                            
                            # Add to the file module object
                            setattr(file_module, attr_name, attr)
                    
                    # Store the functions list and module object
                    file_functions[module_name] = functions
                    globals()[module_name] = file_module
                    
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")

# Create __all__ to expose all imported functions and modules
__all__ = [
    name for name in globals() 
    if (callable(globals()[name]) or isinstance(globals()[name], types.ModuleType)) 
    and not name.startswith("__")
]
