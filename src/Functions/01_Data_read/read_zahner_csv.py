import pandas as pd
import numpy as np

def read_zahner_csv(file):
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

    # Pre-check if the file is with ;
    if 'File' not in lines[1]:
        lines.insert(0, 'sep=,\n')
        for i, line in enumerate(lines):
            while ';;' in lines[i]:
                lines[i] = lines[i].replace(';;', ';')
            lines[i] = lines[i].replace('"', '')
            if i > 18:
                lines[i] = lines[i].replace(';', ',')

    # Extract file name (first line)
    file_name = lines[1].split(':', 1)[1].strip()

    # Extract Potential value (fourth line)
    if 'Ampl' in lines[4].split(':', 1)[1].strip():
        Ampl_line = lines[4].split(':', 1)[1].strip()
        potential, ampl = Ampl_line.split('; Ampl:')
        potential = potential.strip()
        current = lines[5].split(':', 1)[1].strip()
    elif 'Ampl' in lines[5].split(':', 1)[1].strip():
        Ampl_line = lines[5].split(':', 1)[1].strip()
        current, ampl = Ampl_line.split('; Ampl:')
        current = current.strip()
        potential = lines[4].split(':', 1)[1].strip()
    ampl = ampl.strip()

    # Save extracted information to a dictionary
    metadata = {
        "file_name": file_name,
        "potential": potential,
        "current": current,
        "ampl": ampl
    }

    # Read the 19th line as the header and the data starting from the 20th line
    lines[19] = lines[19].replace(',\n', '\n')  # Ensure the header line uses commas
    header = lines[19].split(',')
    data_lines = [line.split(',')[:len(header)] for line in lines[20:] if line]
    data = pd.DataFrame(data_lines, columns=header)
    data['Frequency/Hz'] = pd.to_numeric(data['Frequency/Hz'], errors='coerce')
    data['impedance/Ohm'] = pd.to_numeric(data['impedance/Ohm'], errors='coerce')
    data['Phase/deg'] = pd.to_numeric(data['Phase/deg'], errors='coerce')
    # Sort the data by 'Frequency/Hz' column in descending order
    data = data.sort_values(by='Frequency/Hz', ascending=False)

    # Calculate Re and Im columns based on Imp_module and Imp_phase
    data['Re/Ohm'] = data['impedance/Ohm'] * np.cos(np.deg2rad(data['Phase/deg']))
    data['Im/Ohm'] = data['impedance/Ohm'] * np.sin(np.deg2rad(data['Phase/deg']))

    return metadata, data