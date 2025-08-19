import os
import re
import numpy as np
import pandas as pd

def smart_split(line):
    """Split line by any whitespace (tabs or spaces), handling quoted strings if needed."""
    # First try splitting by tabs
    if '\t' in line:
        parts = line.split('\t')
        # If we got at least 2 non-empty parts, return tab-split
        if len([p for p in parts if p.strip()]) >= 2:
            return parts
    # Fall back to splitting by any whitespace
    return re.split(r'\s+', line.strip())

def contains_keyword(line, keywords):
    """Check if a line contains any of the keywords (case insensitive)."""
    line_lower = line.lower()
    return any(keyword.lower() in line_lower for keyword in keywords)

def is_numeric_row(line):
    """Check if a line contains mostly numeric values (potential data row)."""
    parts = line.strip().split()
    if len(parts) < 2:  # Not enough columns to be data
        return False
    numeric_count = 0
    for part in parts:
        try:
            part = part.replace(',', '.')
            float(part)
            numeric_count += 1
        except ValueError:
            pass
    return numeric_count / len(parts) > 0.8  # At least 80% numeric values

def read_general_all(file):
    frequency_search_keywords = ["Freq"]
    real_part_keywords = ["Zreal", "Re(Z)", "Real", "impedance'"]
    imaginary_part_keywords = ["Zimag", "-Im(Z)", "Imag", "impedance''", 'Im(Z)']
    phase_keywords = ["Phase", "Zphz"]
    impedance_keywords = ["impedance", "Zmod", '|Z|']
    
    encodings = ['utf-8', 'ISO-8859-1', 'latin1']
    lines = []
    for encoding in encodings:
        try:
            with open(file, 'r', encoding=encoding) as f:
                lines = [line.strip() for line in f.readlines()]
            break
        except UnicodeDecodeError:
            continue
    
    if not lines:
        raise ValueError(f"---- Cannot read file {file}, none of the attempted encodings worked")

    # Extract metadata (assuming same format as before)
    metadata = {
        "file_name": os.path.basename(file),
        "potential": "",
        "current": "",
        "ampl": ""
    }

    # Find header row
    header_idx = None

    # Change , to . for numeric conversion
    for i in range(len(lines)):
        lines[i] = lines[i].replace(',', '.')
    
    # First try to find the cluster with frequency, real and imaginary parts
    for i, line in enumerate(lines):
        if (contains_keyword(line, frequency_search_keywords) and 
            contains_keyword(line, real_part_keywords) and 
            contains_keyword(line, imaginary_part_keywords)):
            header_idx = i
            break
    
    # If not found, try the second cluster with frequency, phase and impedance
    if header_idx is None:
        for i, line in enumerate(lines):
            if (contains_keyword(line, frequency_search_keywords) and 
                contains_keyword(line, phase_keywords) and 
                contains_keyword(line, impedance_keywords)):
                header_idx = i
                break
    
    if header_idx is None:
        raise ValueError("Could not find valid header row in the file")
    
    # Find where data starts (first numeric row after header)
    data_start_idx = None
    for i in range(header_idx + 1, len(lines)):
        if is_numeric_row(lines[i]):
            data_start_idx = i
            break
    
    if data_start_idx is None:
        raise ValueError("Could not find data rows after header")
    
    # Find where data ends (first non-numeric line after data starts)
    data_end_idx = len(lines)
    for i in range(data_start_idx + 1, len(lines)):
        if not is_numeric_row(lines[i]):
            data_end_idx = i
            break
    
    # Extract data
    header = smart_split(lines[header_idx])
    data_lines = lines[data_start_idx:data_end_idx]
    
    # Create DataFrame
    data = pd.DataFrame([smart_split(line) for line in data_lines], columns=header)
    
    # Convert all columns to numeric where possible
    for col in data.columns:
        data[col] = pd.to_numeric(data[col], errors='ignore')
    
    # Sort data by frequency (assuming it's the first column)
    freq_col = [col for col in data.columns if contains_keyword(col, frequency_search_keywords)][0]
    data = data.sort_values(by=freq_col, ascending=False)
    data['Frequency/Hz'] = data[freq_col].astype(float)
    data = data[data['Frequency/Hz'] != 0]
    
    # If we have phase and impedance, calculate Re and Im
    if (any(contains_keyword(col, phase_keywords) for col in data.columns) and 
        any(contains_keyword(col, impedance_keywords) for col in data.columns)):
        phase_col = [col for col in data.columns if contains_keyword(col, phase_keywords)][0]
        impedance_col = [col for col in data.columns if contains_keyword(col, impedance_keywords)][0]
        
        # Detect phase unit (rad or deg)
        if 'rad' in phase_col.lower():
            # Phase is already in radians
            data['Re/Ohm'] = data[impedance_col] * np.cos(data[phase_col])
            data['Im/Ohm'] = data[impedance_col] * np.sin(data[phase_col])
        elif 'deg' in phase_col.lower():
            # Convert degrees to radians
            data['Re/Ohm'] = data[impedance_col] * np.cos(np.deg2rad(data[phase_col]))
            data['Im/Ohm'] = data[impedance_col] * np.sin(np.deg2rad(data[phase_col]))
        else:
            # Default to degrees if unit not specified
            print(f"Warning: Phase column '{phase_col}' has no unit specified, assuming degrees")
            data['Re/Ohm'] = data[impedance_col] * np.cos(np.deg2rad(data[phase_col]))
            data['Im/Ohm'] = data[impedance_col] * np.sin(np.deg2rad(data[phase_col]))
    
    return metadata, data
