import pandas as pd
import numpy as np

def read_gamry_dta(file):
    """
    Reads a Gamry DTA file and extracts metadata and data.

    Parameters:
    -----------
    file : str
        The path to the Gamry DTA file to be read.

    Returns:
    --------
    metadata : dict
        A dictionary containing the extracted metadata:
        - "file_name" : str
            The name of the file extracted from the first line.
        - "potential" : str
            The potential value extracted from the appropriate line.
        - "current" : str
            The current value extracted from the appropriate line.
        - "ampl" : str
            The ampl value extracted from the appropriate line.
    data : pandas.DataFrame
        A DataFrame containing the numerical data from the file.

    Notes:
    ------
    - This function assumes the .DTA file is in the format used by Zahner software.
    - Header information is parsed until a line starting with 'ZCURVE' is found.
    - The data section follows this keyword.
    """

    with open(file, 'r', encoding='latin1') as f:
        lines = f.readlines()

    # Parse header
    file_name = file.split("/")[-1]
    potential = current = ampl = None
    data_start = None
    headers = []
    for idx, line in enumerate(lines):
        if line.startswith('ZCURVE'):
            data_start = idx + 1
            headers = line.strip().split()[1:]  # Skip 'ZCURVE', get column names
            break
        elif 'Potential' in line:
            potential = line.split('=')[1].strip()
        elif 'Current' in line:
            current = line.split('=')[1].strip()
        elif 'Amplitude' in line or 'Ampl' in line:
            ampl = line.split('=')[1].strip()

    if data_start is None:
        raise ValueError("Data section not found in the file.")

    # Read numerical data
    data = pd.read_csv(file, skiprows=data_start, sep=r'\s+', names=headers)

    # Construct metadata
    metadata = {
        "file_name": file_name,
        "potential": potential,
        "current": current,
        "ampl": ampl
    }

    # Optional: calculate Re/Ohm and Im/Ohm if impedance and phase columns exist
    imp_col = next((col for col in data.columns if 'Z' in col), None)
    phase_col = next((col for col in data.columns if 'PHI' in col or 'Phase' in col), None)

    if imp_col and phase_col:
        data['Re/Ohm'] = data[imp_col] * np.cos(np.deg2rad(data[phase_col]))
        data['Im/Ohm'] = data[imp_col] * np.sin(np.deg2rad(data[phase_col]))

    return metadata, data
