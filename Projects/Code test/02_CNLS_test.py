from importlib import reload
import platform
import os
import glob
import sys
sys.path.append(os.path.dirname(os.path.dirname(sys.path[0])))
import numpy as np
import pandas as pd
import Functions as fn
import matplotlib.pyplot as plt
from Methods.CNLS.Circuit import Circuit
from Methods.DRT.DRT import DRT


# 01 - Initialization
if platform.system() == 'Darwin':  # macOS
    Folder_Path = r'/Users/atlas/Library/CloudStorage/OneDrive-Personal/Experience/01_Projects/19_HydroQuebec/4_Models/IS_analysis_V1/_DataRef/Zahner'
elif platform.system() == 'Windows':  # Windows
    Folder_Path = r'D:\OneDrive\Experience\01_Projects\19_HydroQuebec\4_Models\IS_analysis_V1\_DataRef\Zahner'
fn.figure_initialization(width=1920, height=1080, font_size=24, colormap_name='vik', dpi=100, font_family='Times New Roman', line_width=3, marker_edge_width=3)

txt_files = glob.glob(os.path.join(Folder_Path, '*.txt'))

EIS = DRT(Re_raw=None, Im_raw=None, f_raw=None, CellArea=None, n_cell=None, file_folder=Folder_Path, filename=None)

# 02 - Command window
Plot_data = True
Save_data = False

Data_type = 'truncated' # 'raw', 'truncated', 'LCcorrected', 'smooth', 'extrapolation'

# 03 - Data processing
for file in txt_files:
    if file is None:
        raise FileNotFoundError('The specified file does not exist.')
    else:
        filename = os.path.basename(file)
        EIS.filename = filename
        print('---- File loaded:', file)
        print('-- File name:', filename)
        EIS.import_data()
    # Initiate the CNLS fit class
    CNLS = Circuit(file_folder=Folder_Path, filename=filename, Elements = None, EIS = EIS, data_type = Data_type)

    # Get the initial guess based on the Gaussian fit
    f_fixed = np.array([1e5, 1.3e3, 2e2, 3e1, 3e0, 3e-1])
    R_est, freq_est, alpha_est, nbr_peaks, tau_est = CNLS.PeakDerivative('fixed', f_fixed=f_fixed, nbr_peaks_fixed=len(f_fixed))
    R_est = R_est*EIS['tknv_' + Data_type]['RL']['Rp_ReIm']/np.sum(R_est)

    # Define the elements based on the Gaussian fit results
    CNLS.Elements = [
        {'name': 'L1', 'type': 'Inductor', 'Param': [EIS['tknv_' + Data_type]['RL']['L_ReIm']], 'Ub': [], 'Lb': []},
        {'name': 'R2', 'type': 'Resistor', 'Param': [EIS['tknv_' + Data_type]['RL']['Rs_ReIm']], 'Ub': [], 'Lb': []},
        {'name': 'RQ3', 'type': 'RQ', 'Param': [R_est[0], tau_est[0], alpha_est[0]], 'Ub': [], 'Lb': []},
        {'name': 'RQ4', 'type': 'RQ', 'Param': [R_est[1], tau_est[1], alpha_est[1]], 'Ub': [], 'Lb': []},
        {'name': 'RQ5', 'type': 'RQ', 'Param': [R_est[2], tau_est[2], alpha_est[2]], 'Ub': [], 'Lb': []},
        {'name': 'RQ6', 'type': 'RQ', 'Param': [R_est[3], tau_est[3], alpha_est[3]], 'Ub': [], 'Lb': []},
        {'name': 'RQ7', 'type': 'RQ', 'Param': [R_est[4], tau_est[4], alpha_est[4]], 'Ub': [], 'Lb': []},
        {'name': 'RQ8', 'type': 'RQ', 'Param': [R_est[5], tau_est[5], alpha_est[5]], 'Ub': [], 'Lb': []},
    ]

    # Initialize the elements
    CNLS.initialize_elements('segment')

    # Fit the circuit
    for i in range(0,5):
        CNLS.FitCircuit()
    # Evaluate the DRT results of the Circuit
    CNLS.EvaluateCircuitDRT()

    # Plot the results
    if Plot_data:
        CNLS.PlotResiduals()
        CNLS.PlotElementImpedance()
        CNLS.PlotCircuit()
    
    breakpoint