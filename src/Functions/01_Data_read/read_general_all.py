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
    frequency_search_keywords = ["Freq", "Hz"]
    real_part_keywords = ["Zreal", "Re(Z)", "Real", "impedance'", "Zre", "Z\'"]
    imaginary_part_keywords = ["Zimag", "-Im(Z)", "Imag", "impedance''", 'Im(Z)', 'Zim', "-Z\""]
    phase_keywords = ["Phase", "Zphz"]
    impedance_keywords = ["impedance", "Zmod", '|Z|']
    
    encodings = ['utf-8', 'ISO-8859-1', 'latin1']
    lines = []
    if 'xlsx' in file.lower() or 'xls' in file.lower():
        # Read Excel file
        xls = pd.ExcelFile(file)
        sheet_name = xls.sheet_names[0]  # Read the first sheet
        df = pd.read_excel(xls, sheet_name=sheet_name)
        headers_excel = df.columns.tolist()
        lines = df.astype(str).apply(lambda row: '\t'.join(row.dropna().astype(str)), axis=1).tolist()
        lines = ['\t'.join(headers_excel)] + lines  # Add headers as first line
    else:
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
        lines[i] = lines[i].replace(',', ' ').replace(';', ' ').replace('\n', ' ')
    
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
    header = smart_split(lines[header_idx].replace(' (', '('))
    data_lines = lines[data_start_idx:data_end_idx]
    
    # Create DataFrame
    data = pd.DataFrame([smart_split(line)[:len(header)] for line in data_lines], columns=header)
    
    # Convert all columns to numeric where possible
    for col in data.columns:
        data[col] = pd.to_numeric(data[col], errors='ignore')
    
    # Sort data by frequency (assuming it's the first column)
    freq_col = [col for col in data.columns if contains_keyword(col, frequency_search_keywords)][0]
    is_ascending = (data[freq_col].diff().dropna() > 0).all()  # Is strictly ascending
    is_descending = (data[freq_col].diff().dropna() < 0).all()  # Is strictly descending
    if is_ascending:
        print("---- The data is strictly ascending, no need to remove any rows.")
    elif is_descending:
        print("---- The data is strictly descending, no need to remove any rows.")
    else:
        # Count the number of ascending and descending data points
        ascending_count = (data[freq_col].diff().dropna() > 0).sum()  # Number of ascending data points
        descending_count = (data[freq_col].diff().dropna() < 0).sum()  # Number of descending data points
        print(f"---- Number of ascending data points: {ascending_count}")
        print(f"---- Number of descending data points: {descending_count}")
        # Determine and remove the smaller part
        if ascending_count > descending_count:
            # Keep ascending part, remove descending part
            ascending_idx = data[freq_col].diff().fillna(1) > 0
            if ascending_idx[0] == True and ascending_idx[1] == False:
                ascending_idx[0] = False
                ascending_idx[int(ascending_idx[ascending_idx == False].index[-1])] = True
            data = data[ascending_idx]  # Keep ascending part
            print("---- Removed descending data points, kept ascending data.")
        else:
            # Keep descending part, remove ascending part
            descending_idx = data[freq_col].diff().fillna(-1) < 0
            if descending_idx[0] == True and descending_idx[1] == False:
                descending_idx[0] = False
                descending_idx[int(descending_idx[descending_idx == False].index[-1])] = True
            data = data[descending_idx]  # Keep descending part
            print("---- Removed ascending data points, kept descending data.")
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
    elif (any(contains_keyword(col, real_part_keywords) for col in data.columns) and 
        any(contains_keyword(col, imaginary_part_keywords) for col in data.columns)):
        real_col = [col for col in data.columns if contains_keyword(col, real_part_keywords)][0]
        imag_col = [col for col in data.columns if contains_keyword(col, imaginary_part_keywords)][0]
        data['Re/Ohm'] = data[real_col].astype(float)
        data['Im/Ohm'] = data[imag_col].astype(float)

    
    return metadata, data
