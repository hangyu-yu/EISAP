import os
import importlib.util
import types

# Create an empty ImpedanceFunctions module object
ImpedanceFunctions = types.ModuleType('ImpedanceFunctions')
PeakDerivative = types.ModuleType('PeakDerivative')

# Get the current package path
package_path = os.path.dirname(__file__)

# Iterate through all submodules
for root, dirs, files in os.walk(package_path):
    if "__pycache__" in dirs:
        dirs.remove("__pycache__")
        
    for file in files:
        if file.endswith(".py") and not file.startswith("__"):
            # Construct the module path
            module_path = os.path.join(root, file)
            module_name = os.path.splitext(file)[0]

            try:
                # Dynamically load the module
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Add the functions from the module to the global namespace
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and not attr_name.startswith("__"):
                        globals()[attr_name] = attr
                        
                        # If the function is from ImpedanceFunctions.py, add it to the ImpedanceFunctions module
                        if module_name == 'ImpedanceFunctions':
                            setattr(ImpedanceFunctions, attr_name, attr)
                        if module_name == 'PeakDerivative':
                            setattr(PeakDerivative, attr_name, attr)
                
                # If it is the ImpedanceFunctions module, store the entire module
                if module_name == 'ImpedanceFunctions':
                    # Retain the original module's docstring
                    if module.__doc__:
                        ImpedanceFunctions.__doc__ = module.__doc__
                if module_name == 'PeakDerivative':
                    # Retain the original module's docstring
                    if module.__doc__:
                        PeakDerivative.__doc__ = module.__doc__
            
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")

# Add ImpedanceFunctions to the __all__ list
__all__ = [name for name in globals() if callable(globals()[name]) and not name.startswith("__")]
__all__.append("ImpedanceFunctions")
__all__.append("PeakDerivative")