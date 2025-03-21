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

# 03 - Data processing
for file in txt_files:
    # 031 - Data load
    metadata,data = fn.read_zahner_txt(file)
    EIS.raw['Re'] = data['Re/Ohm']
    EIS.raw['Im'] = data['Im/Ohm']
    EIS.raw['Z'] = data['impedance/Ohm']
    EIS.raw['frequency'] = data['Frequency/Hz']
    EIS.raw['significance'] = data['Significance']