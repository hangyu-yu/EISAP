import platform
import numpy as np
import pandas as pd
import Functions as fn
from Methods.DRT.DRT import DRT
import cmcrameri as cm
import os
import glob

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


# 03 - Data processing
for file in txt_files:
    # 031 - Data load
    if file is None:
        raise FileNotFoundError('The specified file does not exist.')
    else: 
        metadata,data = fn.read_zahner_txt(file)
    
    EIS.raw['Re'] = data['Re/Ohm']
    EIS.raw['Im'] = data['Im/Ohm']
    EIS.raw['Z'] = data['impedance/Ohm']
    EIS.raw['frequency'] = data['Frequency/Hz']
    EIS.raw['significance'] = data['Significance']
    EIS.info = metadata

    # 032 - Data cut based on the significance values
    EIS.rm_hfc_lfc()
    
    if EIS.parameter['Rmoutliers']['RMoutliers']:
        EIS.rm_outliers()
    
    if EIS.parameter['RM_significance']['rm_significance']:
        EIS.rm_significance()