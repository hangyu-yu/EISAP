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
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                
                # Check for the start of data section
                if "Potential" in line and "Current" in line:
                    in_data_section = True
                    data_started = False
                    continue
                
                # Skip empty lines
                if not line:
                    continue
                
                # If we're in data section, parse the data lines
                if in_data_section:
                    # Split line by whitespace
                    parts = line.split()
                    
                    # Check if this is a data line (should have at least 4 parts)
                    if len(parts) >= 4:
                        try:
                            # Extract potential (3rd column) and current (4th column)
                            potential = float(parts[2])
                            current = float(parts[3])
                            
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
    
    print(f"Successfully read {len(potential_array)} data points")
    print(f"Potential range: {potential_array.min():.6f} V to {potential_array.max():.6f} V")
    print(f"Current range: {current_array.min():.6e} A to {current_array.max():.6e} A")
    
    return potential_array, current_array