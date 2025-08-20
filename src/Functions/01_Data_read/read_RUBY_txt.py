import os
import numpy as np
import pandas as pd

def read_RUBY_txt(file):
    """
    Reads a txt file and extracts metadata and data with the first column as frequency, second column as real part, and third column as imaginary part.

    Parameters:
    -----------
    file : str
        The path to the txt file to be read.

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
        A DataFrame containing the numerical data from the file.

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
    metadata = {
        "file_name": os.path.basename(file),
        "potential": "Unknown",
        "current": "Unknown",
        "ampl": "Unknown"
    }

    # Read the 19th line as the header and the data starting from the 20th line    
    header = lines[0].strip().split()
    if "frequency" in header[0].lower():
        data = pd.read_csv(file, skiprows=1, sep=r'\s+')
    else:
        data = pd.read_csv(file, sep=r'\s+', names=["Frequency", "Impedance"], header=None, skiprows=0)
    # Convert complex numbers in the second column to real and imaginary parts
    data.iloc[:, 1] = data.iloc[:, 1].apply(lambda x: complex(str(x).replace('i', 'j')))
    Real = data.iloc[:, 1].apply(lambda x: x.real)
    Imag = data.iloc[:, 1].apply(lambda x: x.imag)
    data.iloc[:,1] = Real
    data.insert(2, data.columns[0] + '_Imag', Imag)
    # Sort the data by 'Frequency/Hz' column in descending order
    is_ascending = (data.iloc[:, 0].diff().dropna() > 0).all()  # Is strictly ascending
    is_descending = (data.iloc[:, 0].diff().dropna() < 0).all()  # Is strictly descending
    if is_ascending:
        print("---- The data is strictly ascending, no need to remove any rows.")
    elif is_descending:
        print("---- The data is strictly descending, no need to remove any rows.")
    else:
        # Count the number of ascending and descending data points
        ascending_count = (data.iloc[:, 0].diff().dropna() > 0).sum()  # Number of ascending data points
        descending_count = (data.iloc[:, 0].diff().dropna() < 0).sum()  # Number of descending data points
        print(f"---- Number of ascending data points: {ascending_count}")
        print(f"---- Number of descending data points: {descending_count}")
        # Determine and remove the smaller part
        if ascending_count > descending_count:
            # Keep ascending part, remove descending part
            ascending_idx = data.iloc[:, 0].diff().fillna(1) > 0
            if ascending_idx[0] == True and ascending_idx[1] == False:
                ascending_idx[0] = False
                ascending_idx[int(ascending_idx[ascending_idx == False].index[-1])] = True
            data = data[ascending_idx]  # Keep ascending part
            print("---- Removed descending data points, kept ascending data.")
        else:
            # Keep descending part, remove ascending part
            descending_idx = data.iloc[:, 0].diff().fillna(-1) < 0
            if descending_idx[0] == True and descending_idx[1] == False:
                descending_idx[0] = False
                descending_idx[int(descending_idx[descending_idx == False].index[-1])] = True
            data = data[descending_idx]  # Keep descending part
            print("---- Removed ascending data points, kept descending data.")

    data = data.sort_values(by=data.columns[0], ascending=False)

    # Calculate Re and Im columns based on Imp_module and Imp_phase
    data_tmp = pd.DataFrame()
    data_tmp['Frequency/Hz'] = np.float64(data.iloc[:, 0])
    data_tmp['Re/Ohm'] = np.float64(data.iloc[:, 1])
    data_tmp['Im/Ohm'] = np.float64(data.iloc[:, 2])

    return metadata, data_tmp