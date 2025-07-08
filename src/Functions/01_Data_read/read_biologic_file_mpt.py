import os
import numpy as np
import pandas as pd
from datetime import datetime

def read_biologic_file_mpt(file_path):
    """
    This function reads and concatenates EIS data from Biologic .mpt files.

    Parameters:
    path_folder (str): Path to the directory containing the EIS .mpt files
    file_name (str): Name of the mpt file to be read

    Returns:
    tuple: A tuple containing EIS_Data (pd.DataFrame) and Info (pd.DataFrame)
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Get the number of header
    index_header = [i for i, line in enumerate(lines) if "header" in line][0]
    number_of_header = int(lines[index_header].split(':')[1].strip())

    # Get the start time of the acquisition
    index_start_time = [i for i, line in enumerate(lines) if "Acquisition started on" in line]
    if index_start_time:
        start_sequence = datetime.strptime(lines[index_start_time[0]].split('on : ')[1].split('.')[0], "%m/%d/%Y %H:%M:%S")
        skip_date_time = False
    else:
        start_sequence = 0
        skip_date_time = True

    # Skip the specified number of rows
    lines = lines[number_of_header-1:]

    # Split each line by the delimiter and create a list of lists
    data = [line.strip().split('\t') for line in lines]

    # Convert the list of lists into a DataFrame
    data_table = pd.DataFrame(data[1:], columns=data[0])  # Assuming the first row is the header

    # Convert DataFrame values to float
    columns_to_convert = [data[0][i] for i in [0,1,2,6,7]]  # Adjust column names as needed
    # Convert specified columns to float
    for column in columns_to_convert:
        if column in data_table.columns:
            data_table[column] = data_table[column].astype(float)

    # Drop any rows with NaN values
    #data_table = pd.read_csv(file_path, delimiter='\t', skiprows=number_of_header)
    data_table.dropna(inplace=True)

    # Check if the file is not empty
    if not data_table.empty:
        f = data_table.iloc[:, 0].astype(float)  # freq
        Zp = data_table.iloc[:, 1].astype(float)  # Re
        Zpp = -data_table.iloc[:, 2].astype(float)  # Im and change from -Im to Im
        eis_data = pd.DataFrame({'Frequency/Hz': f, 'Re/Ohm': Zp, 'Im/Ohm': Zpp})

        # Store the measurement information
        potential_v = data_table.iloc[:, 6].mean()  # Average voltage
        if "mA" in data_table.columns[7]:
            current_a = data_table.iloc[:, 7].mean() / 1000  # convert to A if mA
        else:
            current_a = data_table.iloc[:, 7].mean()

        if skip_date_time:
            end_time = 0
            start_time = 0
        else:
            try:
                start_time = start_sequence + pd.to_timedelta(data_table.iloc[0, 5], unit='s')  # Start time
                end_time = start_sequence + pd.to_timedelta(data_table.iloc[-1, 5], unit='s')  # End time
            except:
                if isinstance(data_table.iloc[0, 5], datetime):
                    start_time = pd.to_datetime(data_table.iloc[0, 5], format="%m/%d/%Y %H:%M:%S.%f")
                    end_time = pd.to_datetime(data_table.iloc[-1, 5], format="%m/%d/%Y %H:%M:%S.%f")
                else:
                    start_time = pd.to_datetime(data_table.iloc[0, 5].strip().replace('-', '/'), format="%m/%d/%Y %H:%M:%S.%f")
                    end_time = pd.to_datetime(data_table.iloc[-1, 5].strip().replace('-', '/'), format="%m/%d/%Y %H:%M:%S.%f")

        info = {'file_name': [os.path.basename(file_path)], 'potential': [potential_v], 'current': [current_a]}

    return info, eis_data