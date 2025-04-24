import pandas as pd
import numpy as np

def ConvertToASR(EIS_Data, Parameters):
    """
    Convert impedance to area-specific impedance and return a DataFrame
    containing f, Re=Re(Z), Im=Im(Z), omega, and tau associated with f.

    Parameters:
    -----------
    EIS_Data : pd.DataFrame
        A DataFrame containing at least the columns 'f', 'Re', 'Im'.
        'Im' should not have been multiplied by -1 (i.e., imag(Z_RC) < 0).

    Parameters : dict
        A dictionary containing:
            'CellArea': The cell area (usually in cm^2).

    Returns:
    --------
    pd.DataFrame
        A DataFrame containing at least the columns 'f', 'Re', 'Im', 'tau', 'omega',
        where 'Re' and 'Im' are normalized by 'CellArea'.
    """
    EIS_Data['omega'] = 2 * np.pi * EIS_Data['f']
    EIS_Data['tau'] = 1 / (2 * np.pi * EIS_Data['f'])
    EIS_Data['Re'] = Parameters['CellArea'] * EIS_Data['Re']
    EIS_Data['Im'] = Parameters['CellArea'] * EIS_Data['Im']
    
    return EIS_Data