import pandas as pd
import numpy as np

def read_zahner_txt_ncepu(file):
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
    with open(file, 'r') as f:
        lines = f.readlines()

    # Save extracted information to a dictionary
    metadata = {}

    # Read the 19th line as the header and the data starting from the 20th line
    header = lines[0].strip().split('\t')
    data_tmp = pd.read_csv(file, skiprows=1, sep=r'\s+', names=header)
    # Sort the data by 'Frequency/Hz' column in descending order
    data_tmp = data_tmp.sort_values(by='frequency (Hz)', ascending=False)

    # Calculate Re and Im columns based on Imp_module and Imp_phase
    data = {}
    data['Frequency/Hz'] = data_tmp["frequency (Hz)"]
    data['Re/Ohm'] = data_tmp.iloc[:, 4]
    data['Im/Ohm'] = data_tmp.iloc[:, 5]
    data['Significance'] = data_tmp.iloc[:, -1]

    return metadata, data