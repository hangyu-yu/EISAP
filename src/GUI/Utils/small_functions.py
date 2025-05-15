import os
import io
import numpy as np
import pandas as pd
from pathlib import Path
import src.GUI.Utils as gui_utils

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

def separate_multichannel_zahner_csv(config, EIS, CNLS):
    """
    Process multi-channel Zahner CSV files by splitting them into individual measurements
    based on the 'Lines' metadata and save them as separate files.
    
    Parameters:
    -----------
    config : object
        Configuration object containing folder_path
    EIS : object
        EIS data object
    CNLS : object
        CNLS data object
        
    Returns:
    --------
    None (creates 'Individual' folder with processed files)
    """
    directory = config.folder_path
    individual_dir = os.path.join(directory, "Individual")
    os.makedirs(individual_dir, exist_ok=True)
    
    # Get all CSV files in directory
    csv_files = [f for f in os.listdir(directory) if f.lower().endswith('.csv')]
    
    for csv_file in csv_files:
        file_path = os.path.join(directory, csv_file)
        
        try:
            # Read the entire file to extract metadata
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            Line_idx = []
            for i in range(len(lines)):
                if "Lines:" in lines[i]:
                    Line_idx.append(i)
            
            current_line = lines[5]
            current = current_line.split(': ', 1)[1].split(';', 1)[0].strip()
            ampl = current_line.split('Ampl: ', 1)[1].strip()
            
            for num, idx in enumerate(Line_idx):
                file_name = csv_file.split('.csv')[0] + f"_{str(num).zfill(2)}.csv"
                if num == 0:
                    potential = lines[4].split(': ', 1)[1].strip()
                    data_num = int(lines[idx].split(': ', 1)[1].strip())
                else:
                    potential = lines[idx-4].split(':,', 1)[1].strip()
                    data_num = int(lines[idx].split(':,', 1)[1].strip())
                
                header = lines[idx+3].strip().split(',')
                data = [line.strip().split(',') for line in lines[idx+4:idx+data_num+4]]
                data = pd.DataFrame(data, columns=header)
                metadata = {
                    "file_name": file_name,
                    "potential": potential,
                    "current": current,
                    "ampl": ampl
                }
                # Save metadata and data to a new CSV file
                output_path = os.path.join(individual_dir, file_name)
                with open(output_path, 'w', encoding='utf-8') as out_f:
                    # Write metadata as comments
                    for key, value in metadata.items():
                        out_f.write(f"# {key}: {value}\n")
                    # Write header and data

                    data.to_csv(out_f, index=False)
            
            # Update the file list in the GUI
            config.folder_path = individual_dir
            config.data_import_function = "/Users/atlas/Desktop/Git/SOCEIS/src/Functions/01_Data_read/read_zahner_csv_multichannel.py"
            gui_utils.file_list.update_file_list(config, "child_window_file_list_soceis", EIS, CNLS)
            
        except Exception as e:
            print(f"Error processing file {csv_file}: {str(e)}")
