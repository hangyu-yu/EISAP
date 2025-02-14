import numpy as np

def ConvertToASR(EIS_Data, CellArea=1):
    """
    ConvertToASR convert impedance to area specific impedance and return a DataFrame
    containing f, Zp=Re(Z), Zpp=Im(Z), and omega and tau associated to f

    Parameters:
    EIS_Data (pd.DataFrame): DataFrame containing at least 'f', 'Zp', 'Zpp'
                             'Zpp' should not have been multiplied by -1 (i.e. imag(Z_RC)<0)
    Parameters (dict): Dictionary containing 'CellArea' which is the cell area (usually in cm2)

    Returns:
    pd.DataFrame: DataFrame containing at least 'f', 'Zp', 'Zpp', 'tau', 'omega', where 'Zp' and 'Zpp' are normalized by 'CellArea'
    """
    EIS_Data['omega'] = 2 * np.pi * EIS_Data['f']
    EIS_Data['tau'] = 1 / (2 * np.pi * EIS_Data['f'])
    EIS_Data['Zp'] = CellArea * EIS_Data['Zp']
    EIS_Data['Zpp'] = CellArea * EIS_Data['Zpp']
    
    return EIS_Data
