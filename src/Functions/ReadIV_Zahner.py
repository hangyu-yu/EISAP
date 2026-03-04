import numpy as np

def ReadIV_Zahner(filepath):
    """
    Read Current and Potential data from the electrochemical measurement file.
    
    Parameters:
    -----------
    filepath : str
        Path to the data file
        
    Returns:
    --------
    tuple : (potential, current)
        potential : numpy array of potential values (V)
        current : numpy array of current values (A)
    """
    
    # Initialize lists to store data
    potential_list = []
    current_list = []
    
    # Flags to track when we're in the data section
    in_data_section = False
    data_started = False
    potential_idx = None
    current_idx = None
    delimiter = None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                
                # Check for the start of data section
                if "Potential" in line and "Current" in line:
                    in_data_section = True
                    data_started = False

                    if ',' in line:
                        delimiter = ','
                        header_parts = [part.strip() for part in line.split(',')]
                    else:
                        delimiter = None
                        header_parts = line.split()

                    for idx, header in enumerate(header_parts):
                        header_lower = header.lower()
                        if 'potential' in header_lower and potential_idx is None:
                            potential_idx = idx
                        if 'current' in header_lower and current_idx is None:
                            current_idx = idx
                    continue
                
                # Skip empty lines
                if not line:
                    continue
                
                # If we're in data section, parse the data lines
                if in_data_section:
                    if delimiter == ',':
                        parts = [part.strip() for part in line.split(',')]
                    else:
                        parts = line.split()

                    if potential_idx is None or current_idx is None:
                        continue
                    
                    required_len = max(potential_idx, current_idx) + 1
                    if len(parts) >= required_len:
                        try:
                            potential = float(parts[potential_idx])
                            current = float(parts[current_idx])
                            
                            potential_list.append(potential)
                            current_list.append(current)
                            data_started = True
                        except (ValueError, IndexError):
                            # If we can't parse as floats, this might not be a data line
                            # but if we already started reading data, this might be the end
                            if data_started:
                                break
                    elif data_started:
                        # If we've started reading data and encounter a non-data line, stop
                        break
    
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None, None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None, None
    
    # Convert lists to numpy arrays
    potential_array = np.array(potential_list)
    current_array = np.array(current_list)

    if len(potential_array) == 0 or len(current_array) == 0:
        print(f"No IV data parsed from: {filepath}")
        return potential_array, current_array
    
    print(f"Successfully read {len(potential_array)} data points")
    print(f"Potential range: {potential_array.min():.6f} V to {potential_array.max():.6f} V")
    print(f"Current range: {current_array.min():.6e} A to {current_array.max():.6e} A")
    
    return potential_array, current_array