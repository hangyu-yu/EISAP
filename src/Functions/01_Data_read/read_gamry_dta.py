import os
import pandas as pd
import numpy as np

def read_gamry_dta(file):
    """
    Reads a Gamry DTA file and extracts specific metadata and impedance data with sorting and duplicate removal.

    Parameters:
    -----------
    file : str
        The path to the Gamry DTA file to be read.

    Returns:
    --------
    metadata : dict
        A dictionary containing the extracted metadata:
        - "file_name" : str
            The name of the file.
        - "potential" : str
            The potential value (EOC from file).
        - "current" : str
            The DC current value (IDCREQ from file).
        - "ampl" : str
            The AC current value (IACREQ from file).
    data : pandas.DataFrame
        A DataFrame containing the impedance data with columns:
        - 'Frequency/Hz': Frequency in Hz
        - 'Im/Ohm': Imaginary impedance in Ohm
        - 'Re/Ohm': Real impedance in Ohm
        - 'impedance/Ohm': Impedance magnitude in Ohm
        - 'Phase/deg': Phase angle in degrees
        Sorted by frequency in descending order with duplicates removed.
    """
    with open(file, 'r') as f:
        lines = f.readlines()

    metadata = {
        "file_name": os.path.basename(file),  # Extract filename from path
        "potential": "",
        "current": "",
        "ampl": ""
    }
    
    data_start = None
    data_end = None
    
    # Parse required metadata
    for line in lines:
        if line.startswith('EOC'):
            parts = line.split('\t')
            metadata["potential"] = parts[2].strip() if len(parts) > 2 else ""
        elif line.startswith('IDCREQ'):
            parts = line.split('\t')
            metadata["current"] = parts[2].strip() if len(parts) > 2 else ""
        elif line.startswith('IACREQ'):
            parts = line.split('\t')
            metadata["ampl"] = parts[2].strip() if len(parts) > 2 else ""
        elif line.startswith('ZCURVE'):
            data_start = lines.index(line) + 2  # Skip header line and units line
        elif line.startswith('EXPERIMENTABORTED') and data_start is not None:
            data_end = lines.index(line)
            break
    
    # Extract and process data table
    if data_start is not None and data_end is not None:
        data_lines = lines[data_start:data_end]
        data = []
        for line in data_lines:
            parts = line.strip().split('\t')
            if len(parts) >= 13:  # Ensure we have all columns
                try:
                    freq = float(parts[2])
                    z_real = float(parts[3])
                    z_imag = float(parts[4])
                    z_mod = float(parts[6])
                    z_phase = float(parts[7])
                    
                    # Calculate phase if not available (using atan2 for correct quadrant)
                    if np.isnan(z_phase):
                        z_phase = np.rad2deg(np.arctan2(z_imag, z_real))
                    
                    # Calculate impedance magnitude if not available
                    if np.isnan(z_mod):
                        z_mod = np.sqrt(z_real**2 + z_imag**2)
                    
                    row = {
                        'Frequency/Hz': freq,
                        'Im/Ohm': z_imag,
                        'Re/Ohm': z_real,
                        'impedance/Ohm': z_mod,
                        'Phase/deg': z_phase
                    }
                    data.append(row)
                except (ValueError, IndexError):
                    continue
        
        df = pd.DataFrame(data)
        
        # Remove duplicate frequencies (keep first occurrence)
        df = df.drop_duplicates(subset=['Frequency/Hz'], keep='first')
        
        # Sort by frequency and check direction
        df = df.sort_values('Frequency/Hz')
        
        # Determine if data is ascending or descending
        freq_diff = df['Frequency/Hz'].diff().dropna()
        is_ascending = (freq_diff > 0).all()
        is_descending = (freq_diff < 0).all()
        
        if is_ascending:
            print("---- The data is strictly ascending, sorting in descending order.")
            df = df.sort_values('Frequency/Hz', ascending=False)
        elif is_descending:
            print("---- The data is strictly descending, no need to change order.")
        else:
            # Count ascending and descending segments
            ascending_count = (freq_diff > 0).sum()
            descending_count = (freq_diff < 0).sum()
            print(f"---- Mixed frequency order: {ascending_count} ascending, {descending_count} descending points")
            
            # Keep the dominant trend
            if ascending_count > descending_count:
                print("---- Keeping ascending segment and converting to descending order")
                df = df.sort_values('Frequency/Hz', ascending=False)
            else:
                print("---- Keeping descending order")
        
        df.reset_index(drop=True, inplace=True)
        
        # Ensure all required columns exist
        required_columns = ['Frequency/Hz', 'Im/Ohm', 'Re/Ohm', 'impedance/Ohm', 'Phase/deg']
        for col in required_columns:
            if col not in df.columns:
                df[col] = np.nan
    else:
        df = pd.DataFrame(columns=['Frequency/Hz', 'Im/Ohm', 'Re/Ohm', 'impedance/Ohm', 'Phase/deg'])
    
    return metadata, df
