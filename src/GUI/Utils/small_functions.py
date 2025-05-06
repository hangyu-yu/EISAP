import importlib
import subprocess
import sys

def string_abbreviation(string, begin=0, end=0):
    """
    Abbreviate a string by removing the first and last 'n' characters.
    
    Parameters:
        string (str): The input string to be abbreviated.
        begin (int): The number of characters to remove from the beginning of the string. Default is 0.
        end (int): The number of characters to remove from the end of the string. Default is 0.
    
    Returns:
        str: The abbreviated string.
    """
    return f"{string[:begin]}...{string[-end:]}" if len(string) > begin+end else string

def install_and_check_dependencies():
    """
    Check if the required dependencies are installed, and install them if they are not.
    Dependencies: scipy, pandas, numpy, matplotlib, dearpygui
    """
    dependencies = ['scipy', 'pandas', 'numpy', 'matplotlib', 'dearpygui', 'openpyxl']
    for package in dependencies:
        try:
            importlib.import_module(package)
        except ImportError:
            print(f"{package} not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])