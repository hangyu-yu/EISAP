import os
import glob
import sys
sys.path.append(os.path.dirname(os.path.dirname(sys.path[0])))
import platform
import numpy as np
import pandas as pd
import Functions as fn
from Methods.DRT.DRT import DRT
import cmcrameri as cm
import matplotlib.pyplot as plt
import mplcursors

# 01 - Initialization
if platform.system() == 'Darwin':  # macOS
    Folder_Path = r'/Users/atlas/Library/CloudStorage/OneDrive-Personal/Experience/01_Projects/19_HydroQuebec/4_Models/IS_analysis_V1/_DataRef/Zahner'
elif platform.system() == 'Windows':  # Windows
    Folder_Path = r'D:\OneDrive\Experience\01_Projects\19_HydroQuebec\4_Models\IS_analysis_V1\_DataRef\Zahner'

txt_files = glob.glob(os.path.join(Folder_Path, '*.txt'))

EIS = DRT(Re_raw=None, Im_raw=None, f_raw=None, cell_area=None, n_cell=None, file_folder=Folder_Path, filename=None)

# 02 - Command window
EIS.parameter['Sample']['cell_area'] = 4*np.pi             # cell area in [cm^2]
EIS.parameter['Sample']['n_cell'] = 1                      # number of cells
EIS.parameter['Preprocessing']['num_cut_upper'] = 15       # high frequency cut
EIS.parameter['Preprocessing']['num_cut_lower'] = 10       # low frequency cut
EIS.parameter['RM_significance']['sig_threshold'] = 0.995  # significance threshold

EIS.parameter['Rmoutliers']['RMoutliers'] = True           # remove outliers
EIS.parameter['RM_significance']['rm_significance'] = True # remove data with low significance
EIS.parameter['KKpreprocess']['OptimalCut'] = True        # remove data based on KK criterion

# Data processing
for file in txt_files:
    # 03 - Data load
    if file is None:
        raise FileNotFoundError('The specified file does not exist.')
    else: 
        metadata,data = fn.read_zahner_txt(file)
    
    EIS.raw['Re'] = data['Re/Ohm'].to_numpy()
    EIS.raw['Im'] = data['Im/Ohm'].to_numpy()
    EIS.raw['Z'] = data['impedance/Ohm'].to_numpy()
    EIS.raw['frequency'] = data['Frequency/Hz'].to_numpy()
    EIS.raw['significance'] = data['Significance'].to_numpy()
    EIS.info = metadata

    # 04 - Data cut based on the upper and lower numbers
    EIS.rm_hfc_lfc()

    # 05 - Data cut due to outliers
    if EIS.parameter['Rmoutliers']['RMoutliers']:
        EIS.rm_outliers()
    # 06 - Data cut based on the significance values
    if EIS.parameter['RM_significance']['rm_significance']:
        EIS.rm_significance()

    # 07 - Data cut based on KK criterion
    if EIS.parameter['KKpreprocess']['OptimalCut']:
        EIS.Linear_KK_opt_mu_cut()
    
    # plt.figure(figsize=(8, 6))
    # plt.plot(EIS.raw['Re'], -EIS.raw['Im'], 'o-', label='Original Data')
    # plt.plot(EIS.truncated['Re'], -EIS.truncated['Im'], 'o-', label='Cleaned Data')  
    # plt.xlabel(r"$Z' \, [\Omega]$", fontsize=14)
    # plt.ylabel(r"$-Z'' \, [\Omega]$", fontsize=14)
    # plt.title("Nyquist Plot", fontsize=16)
    # plt.grid(True)
    # plt.legend()
    # cursor = mplcursors.cursor(hover=True)
    # cursor.connect("add", lambda sel: sel.annotation.set_text(
    #     f"Re: {sel.target[0]:.5f}\n-Im: {sel.target[1]:.5f}"))
    # plt.show()