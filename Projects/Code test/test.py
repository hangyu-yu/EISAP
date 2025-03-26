import os
import glob
import sys
sys.path.append(os.path.dirname(os.path.dirname(sys.path[0])))
import platform
import numpy as np
import pandas as pd
import Functions as fn                 
from Methods.DRT.DRT import DRT
import matplotlib.pyplot as plt
import mplcursors

# 01 - Initialization
if platform.system() == 'Darwin':  # macOS
    Folder_Path = r'/Users/atlas/Library/CloudStorage/OneDrive-Personal/Experience/01_Projects/19_HydroQuebec/4_Models/IS_analysis_V1/_DataRef/Zahner'
elif platform.system() == 'Windows':  # Windows
    Folder_Path = r'D:\OneDrive\Experience\01_Projects\19_HydroQuebec\4_Models\IS_analysis_V1\_DataRef\Zahner'
fn.figure_initialization(width=1920, height=1080, font_size=24, colormap_name='vik', dpi=100, font_family='Times New Roman', line_width=3, marker_edge_width=3)

txt_files = glob.glob(os.path.join(Folder_Path, '*.txt'))

EIS = DRT(Re_raw=None, Im_raw=None, f_raw=None, CellArea=None, n_cell=None, file_folder=Folder_Path, filename=None)

# 02 - Command window
EIS.parameter['Sample']['CellArea'] = 4*np.pi              # cell area in [cm^2]
EIS.parameter['Sample']['n_cell'] = 1                      # number of cells
EIS.parameter['Preprocessing']['num_cut_upper'] = 15       # high frequency cut
EIS.parameter['Preprocessing']['num_cut_lower'] = 10       # low frequency cut
EIS.parameter['RM_significance']['sig_threshold'] = 0.995  # significance threshold
EIS.parameter['Smoothing']['PointsPerDecade'] = 30         # number of points per decade
EIS.parameter['Extrapolation']['PointsPerDecade'] = 20     # number of points per decade

EIS.parameter['Rmoutliers']['RMoutliers'] = False           # remove outliers
EIS.parameter['RM_significance']['rm_significance'] = False # remove data with low significance
EIS.parameter['KKpreprocess']['OptimalCut'] = False         # remove data based on KK criterion
EIS.parameter['KK']['KK_test'] = True                       # KK test
EIS.parameter['KK']['KK_type'] = 'Mu_criterion'             # KK type

switch_plot_KK = True
switch_plot_EIS = True
plot_EIS_list = {'ReIm', 'ReIm_s', 'ReIm_e', 'ReIm_LC'}

# Data processing
for file in txt_files:
# 03 - EIS Data processing
    if file is None:
        raise FileNotFoundError('The specified file does not exist.')
    else: 
        print('File loaded:', file)
        metadata,data = fn.read_zahner_txt(file)
        filename = os.path.basename(file)
    
    EIS.raw['Re'] = data['Re/Ohm'].to_numpy()
    EIS.raw['Im'] = data['Im/Ohm'].to_numpy()
    EIS.raw['Z'] = data['impedance/Ohm'].to_numpy()
    EIS.raw['f'] = data['Frequency/Hz'].to_numpy()
    EIS.raw['significance'] = data['Significance'].to_numpy()
    EIS.info = metadata
    EIS.raw = EIS.convert2asr(EIS.raw, EIS.parameter['Sample'])

    # 031 - Data cut based on the upper and lower numbers
    EIS.rm_hfc_lfc()

    # 032 - Data cut due to outliers
    if EIS.parameter['Rmoutliers']['RMoutliers']:
        EIS.rm_outliers()

    # 033 - Data cut based on the significance values
    if EIS.parameter['RM_significance']['rm_significance']:
        EIS.rm_significance()

    # 034 - Data cut based on KK criterion
    if EIS.parameter['KKpreprocess']['OptimalCut']:
        EIS.Linear_KK_opt_mu_cut(EIS.truncated, EIS.parameter['KKpreprocess'])

    # 035 - KK test
    if EIS.parameter['KK']['KK_test']:
        EIS.KK_test(EIS.truncated)
    
    # 036 = Get smoothed data, LCcorrected data, and extrapolated data
    EIS.parameter['Smoothing']['fmax'] = max(EIS.truncated['f'])
    EIS.parameter['Smoothing']['fmin'] = min(EIS.truncated['f'])
    EIS.smooth = EIS.ResampleEIS(EIS.truncated, EIS.parameter['Smoothing'])
    EIS.store['RsLCinv_kk']['L'] = 0
    EIS.store['RsLCinv_kk']['Cinv'] = 0
    EIS.LCcorrect = EIS.ResampleEIS(EIS.truncated, EIS.parameter['Smoothing'])
    EIS.extrapolation = EIS.ResampleEIS(EIS.truncated, EIS.parameter['Extrapolation'])

    # Plot KK and EIS data
    if switch_plot_KK:
        EIS.KK_plot(filename)

    EIS.EIS_plot(plot_EIS_list, filename)

# 04 - DRT treatment
    # 041 - Solve the optimum lambda or not
    plt.show()

    break

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