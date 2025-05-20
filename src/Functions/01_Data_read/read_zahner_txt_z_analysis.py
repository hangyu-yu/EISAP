import pandas as pd
import numpy as np
import os

def read_zahner_txt_z_analysis(file):
    """
    Reads a Zahner TXT file and extracts metadata and data.

    Parameters:
    -----------
    file : str
        The path to the Zahner TXT file to be read.

    Returns:
    --------
    metadata : dict
        A dictionary containing the extracted metadata:
        - "file_name" : str
            The name of the file extracted from the first line.
        - "potential" : str
            The potential value extracted from the fourth line.
        - "current" : str
            The current value extracted from the fifth line.
        - "ampl" : str
            The ampl value extracted from the fifth line.
    data : pandas.DataFrame
        A DataFrame containing the numerical data from the file, with the 19th line used as the header.

    Notes:
    ------
    - The function assumes the file follows a specific format where:
        - The first line contains the file name in the format "File Name: <name>".
        - The fourth line contains the potential value in the format "Potential: <value>".
        - The fifth line contains the current and ampl values in the format "Current: <value>, Ampl: <value>".
        - The 19th line contains the column headers for the data section.
        - The data section starts from the 20th line and is delimited by whitespace.
    - Ensure the file exists and is accessible before calling this function.

    Raises:
    -------
    FileNotFoundError
        If the specified file does not exist.
    ValueError
        If the file format does not match the expected structure.
    """
    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Extract file name (first line)
    file_name = os.path.basename(lines[0].split(':', 1)[1].strip())

    # Extract Potential value (fourth line)
    if 'Ampl' in lines[4].split(':', 1)[1].strip():
        Ampl_line = lines[4].split(': ', 1)[1].strip()
        potential, ampl = Ampl_line.split(', Ampl: ')
        potential = potential.strip()
        current_line = lines[5].split(': ', 1)[1].strip()
        current = current_line.split(', Ampl: ')[0].strip()
    elif 'Ampl' in lines[5].split(': ', 1)[1].strip():
        Ampl_line = lines[5].split(': ', 1)[1].strip()
        current, ampl = Ampl_line.split(', Ampl: ')
        current = current.strip()
        potential_line = lines[4].split(':', 1)[1].strip()
        potential = potential_line.split(', Ampl: ')[0].strip()
    ampl = ampl.strip()

    # Save extracted information to a dictionary
    metadata = {
        "file_name": file_name,
        "potential": potential,
        "current": current,
        "ampl": ampl
    }

    # Read the 19th line as the header and the data starting from the 20th line
    header = lines[15].strip().split('\t')
    data = pd.read_csv(file, skiprows=16, sep=r'\t+', names=header)
    
    is_ascending = (data['frequency (Hz)'].diff().dropna() > 0).all()  # Is strictly ascending
    is_descending = (data['frequency (Hz)'].diff().dropna() < 0).all()  # Is strictly descending
    if is_ascending:
        print("---- The data is strictly ascending, no need to remove any rows.")
    elif is_descending:
        print("---- The data is strictly descending, no need to remove any rows.")
    else:
        # Count the number of ascending and descending data points
        ascending_count = (data['frequency (Hz)'].diff().dropna() > 0).sum()  # Number of ascending data points
        descending_count = (data['frequency (Hz)'].diff().dropna() < 0).sum()  # Number of descending data points
        print(f"---- Number of ascending data points: {ascending_count}")
        print(f"---- Number of descending data points: {descending_count}")
        # Determine and remove the smaller part
        if ascending_count > descending_count:
            # Keep ascending part, remove descending part
            ascending_idx = data['frequency (Hz)'].diff().fillna(1) > 0
            if ascending_idx[0] == True and ascending_idx[1] == False:
                ascending_idx[0] = False
                ascending_idx[int(ascending_idx[ascending_idx == False].index[-1])] = True
            data = data[ascending_idx]  # Keep ascending part
            print("---- Removed descending data points, kept ascending data.")
        else:
            # Keep descending part, remove ascending part
            descending_idx = data['frequency (Hz)'].diff().fillna(-1) < 0
            if descending_idx[0] == True and descending_idx[1] == False:
                descending_idx[0] = False
                descending_idx[int(descending_idx[descending_idx == False].index[-1])] = True
            data = data[descending_idx]  # Keep descending part
            print("---- Removed ascending data points, kept descending data.")
    
    # Sort the data by 'frequency (Hz)' column in descending order
    data = data.sort_values(by='frequency (Hz)', ascending=False)
    data = data.rename(columns={'frequency (Hz)': 'Frequency/Hz'})
    data = data.rename(columns={'significance': 'Significance'})
    # Calculate Re and Im columns based on Imp_module and Imp_phase
    data['Re/Ohm'] = data['impedance (Ω)'] * np.cos(np.deg2rad(data['phase / deg (°)']))
    data['Im/Ohm'] = data['impedance (Ω)'] * np.sin(np.deg2rad(data['phase / deg (°)']))

    return metadata, data