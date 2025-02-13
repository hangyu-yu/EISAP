"""
DRT Class for Electrochemical Impedance Spectroscopy (EIS) Analysis

Purpose:
    This class is designed to perform EIS data analysis using methods such as Distribution of Relaxation Time (DRT), Kramers-Kronig (KK) analysis, Tikhonov regularization, and Fourier transform-based approaches.

Created by:
    Hangyu Yu, EPFL GEM, Switzerland
    Created date: 2025.02.12
    Last modified: 
"""
from Methods.DRT.Utils import *
import numpy as np
import pandas as pd

class DRT:
    def __init__(self, cell_area=None, n_cell=None, file_folder=None, filename=None):
        # Test information
        self.cell_area = cell_area     # SOC area [cm^2]
        self.n_cell = n_cell           # Number of cells
        self.file_folder = file_folder # File folder path
        self.filename = filename       # File name
        self.instrument_type = None    # Zahner or Biologic or others
        self.save_name = None          # Save name for results
        
        # Data classification
        self.Re_raw = None             # Real part of raw impedance data
        self.Im_raw = None             # Imaginary part of raw impedance data
        self.Z_raw = None              # Raw impedance data
        self.frequency_raw = None      # Raw frequency data
        self.significance = None       # Significance values for EIS data, mostly applicable in Zahner data

        self.Re_orig = None             # Real part of original impedance data for further treatment
        self.Im_orig = None             # Imaginary part of original impedance data for further treatment
        self.Z_orig = None              # Original impedance data for further treatment
        self.frequency_orig = None      # Original frequency data for further treatment

        self.Re_trunc = None           # Truncated real part of impedance data
        self.Im_trunc = None           # Truncated imaginary part of impedance data
        self.Z_trunc = None            # Truncated impedance data
        self.frequency_trunc = None    # Truncated frequency data

        self.Re_crct = None            # L/C Corrected real part of impedance data
        self.Im_crct = None            # L/C Corrected imaginary part of impedance data
        self.Z_crct = None             # L/C Corrected impedance data
        self.frequency_crct = None     # L/C Corrected frequency data

        self.Re_kk = None              # Linear Kramers-Kronig fitted real part of impedance data
        self.Im_kk = None              # Linear Kramers-Kronig fitted imaginary part of impedance data
        self.Z_kk = None               # Linear Kramers-Kronig fitted impedance data
        self.frequency_kk = None       # Linear Kramers-Kronig fitted frequency data

        self.Re_smooth = None          # Smoothed real part of impedance data
        self.Im_smooth = None          # Smoothed imaginary part of impedance data
        self.Z_smooth = None           # Smoothed impedance data
        self.frequency_smooth = None   # Smoothed frequency data

        self.Re_extr = None            # Extrapolated real part of impedance data
        self.Im_extr = None            # Extrapolated imaginary part of impedance data
        self.Z_extr = None             # Extrapolated impedance data
        self.frequency_extr = None     # Extrapolated frequency data

        # Data treatment parameters
        self.freq_log_min = -10        # 10^min frequency for extended spectra
        self.freq_log_max =  10        # 10^max frequency for extended spectra
        self.num_cut_upper = None      # Number of upper frequency points to be cut
        self.num_cut_lower = None      # Number of lower frequency points to be cut
        self.num_cut_middle = None     # middle frequency cut, index of points in original data

        self.sig_threshold = 0.995     # Significance threshold for EIS data, specifically for Zahner data
        self.mu_threshold = 0.85       # Threshold for Dante's method
        self.RC_max = 100              # Maximum RC elements used for Dante's method
        self.kk_threshold = 1          # Threshold for the kk residual, used for auto-kk cut

        # Parameters and variables for Kronig-Kramers method
        self.delta_Im_kk = None        # KK residual of imaginary part
        self.delta_Re_kk = None        # KK residual of real part
        self.res_pol_kk = None         # Polarization resistance based on RC elements fitting
        self.res_ohm_kk = None         # Ohmic resistance based on RC elements fitting
        self.L_kk = None               # Inductance correction
        self.C_kk = None               # Capacitance correction
        self.num_RC = None             # Number of RC elements applied

        # Parameters for self-adaptive KK method
        self.ini_cut_low = 0           # Initial lower frequency point cut
        self.end_cut_low = 15          # Maximal lower frequency point cut
        self.ini_cut_up = 5            # Initial upper frequency point cut
        self.end_cut_up = 15           # Maximal upper frequency point cut
        self.mu_ll = 0.5               # Lower limit of mu value
        self.mu_ul = 0.5               # Upper limit of mu value
        self.cut_low_opt = None        # Optimal lower frequency point cut
        self.cut_up_opt = None         # Optimal upper frequency point cut
        self.mu_opt = None             # Optimal mu value

        # Parameters and variables for Tikhonov regularization
        self.lambda_tik = 0.15         # Regularization parameter
        self.lambda_opt = None         # Optimal regularization parameter
        self.tknv_legend = None        # Legend for Tikhonov regularization plot

        self.tknv_Im_f = None          # Tikhonov method with truncated imaginary part data
        self.tknv_Im_drt = None
        self.tknv_Re_f = None          # Tikhonov method with truncated real part data
        self.tknv_Re_drt = None
        self.tknv_ReIm_f = None        # Tikhonov method with truncated real and imaginary part data
        self.tknv_ReIm_drt = None
        self.tknv_Im_s_f = None        # Tikhonov method with smoothed imaginary part data
        self.tknv_Im_s_drt = None
        self.tknv_Re_s_f = None        # Tikhonov method with smoothed real part data
        self.tknv_Re_s_drt = None
        self.tknv_ReIm_s_f = None      # Tikhonov method with smoothed imaginary and real part data
        self.tknv_ReIm_s_drt = None
        self.tknv_Im_e_f = None        # Tikhonov method with extrapolated imaginary part data
        self.tknv_Im_e_drt = None
        self.tknv_Re_e_f = None        # Tikhonov method with extrapolated real part data
        self.tknv_Re_e_drt = None
        self.tknv_ReIm_e_f = None      # Tikhonov method with extrapolated imaginary and real part data
        self.tknv_ReIm_e_drt = None
        self.tknv_Im_crct_f = None     # Tikhonov method with LC corrected imaginary part data
        self.tknv_Im_crct_drt = None
        self.tknv_Re_crct_f = None     # Tikhonov method with LC corrected real part data
        self.tknv_Re_crct_drt = None
        self.tknv_ReIm_crct_f = None   # Tikhonov method with LC corrected real and imaginary part data
        self.tknv_ReIm_crct_drt = None

        self.tknvNeg_Im_f = None       # TikhonovNeg method with truncated imaginary part data
        self.tknvNeg_Im_drt = None
        self.tknvNeg_Re_f = None       # TikhonovNeg method with truncated real part data
        self.tknvNeg_Re_drt = None
        self.tknvNeg_ReIm_f = None     # TikhonovNeg method with truncated imaginary and real part data
        self.tknvNeg_ReIm_drt = None
        self.tknvNeg_Im_s_f = None     # TikhonovNeg method with smoothed imaginary part data
        self.tknvNeg_Im_s_drt = None
        self.tknvNeg_Re_s_f = None     # TikhonovNeg method with smoothed real part data
        self.tknvNeg_Re_s_drt = None
        self.tknvNeg_ReIm_s_f = None   # TikhonovNeg method with smoothed imaginary and real part data
        self.tknvNeg_ReIm_s_drt = None
        self.tknvNeg_Im_e_f = None     # TikhonovNeg method with extrapolated imaginary part data
        self.tknvNeg_Im_e_drt = None
        self.tknvNeg_Re_e_f = None     # TikhonovNeg method with extrapolated real part data
        self.tknvNeg_Re_e_drt = None
        self.tknvNeg_ReIm_e_f = None   # TikhonovNeg method with extrapolated imaginary and real part data
        self.tknvNeg_ReIm_e_drt = None

    def rm_significance(self):
        """
        Remove points with low significance values from EIS data
        """
        if self.significance is None:
            print("[Error] Significance values are empty! Check the data import")
        else:
            self.Re0 = self.Re_orig
            self.Im0 = self.Im_orig
            self.f0 = self.frequency_orig
            self.Z0 = self.Z_orig
            rm_num = np.where(self.significance < self.sig_threshold)[0]
            self.Re_orig = np.delete(self.Re_orig, rm_num)
            self.Im_orig = np.delete(self.Im_orig, rm_num)
            self.frequency_orig = np.delete(self.frequency_orig, rm_num)
            self.Z_orig = np.delete(self.Z_orig, rm_num)
            
    def rm_hfc_lfc(self, Nfh_cut, Nfl_cut):
        """
        Remove high-frequency and low-frequency data points from EIS data and remove outliers
        """
        if self.frequency_orig is None or self.Re_orig is None or self.Im_orig is None:
            print("[Error] Original data for data treatment is empty! Check the data import")
            return

        # Check if each frequency point is unique
        if len(self.frequency_orig) != len(np.unique(self.frequency_orig)):
            print("[Error] Duplicate frequency points found! Check the data import")
            return

        idx = np.argsort(self.frequency_orig)[::-1]
        f = self.frequency_orig[idx]
        Re = self.Re_orig[idx]
        Im = self.Im_orig[idx]

        # Cut high-frequency and low-frequency components
        leng = len(f)
        self.frequency_trunc = f[Nfh_cut:leng-Nfl_cut]
        self.Re_trunc = Re[Nfh_cut:leng-Nfl_cut]
        self.Im_trunc = Im[Nfh_cut:leng-Nfl_cut]
        self.Z_trunc = self.Re_trunc + 1j * self.Im_trunc

        # Remove outliers based on the standard deviation
        mv_window_size = 6
        Re_mean = pd.Series(self.Re_trunc).rolling(window=mv_window_size, center=True).mean()
        Re_mean.iloc[0]  = self.Re_trunc[0:mv_window_size].mean()
        Re_mean.iloc[-1] = self.Re_trunc[-mv_window_size:].mean()
        Re_residuals = np.abs(pd.Series(self.Re_trunc) - Re_mean)
        Re_threshold = 2 * np.std(Re_residuals)
        Re_outliers = Re
        Re_outliers = np.abs(self.Re_trunc - pd.Series(self.Re_trunc).rolling(window=6, center=True).mean()) > 3 * pd.Series(self.Re_trunc).rolling(window=6, center=True).std()
        Im_outliers = np.abs(self.Im_trunc - pd.Series(self.Im_trunc).rolling(window=6, center=True).mean()) > 3 * pd.Series(self.Im_trunc).rolling(window=6, center=True).std()
        outliers = Re_outliers | Im_outliers

        self.Re_trunc = self.Re_trunc[~outliers]
        self.Im_trunc = self.Im_trunc[~outliers]
        self.frequency_trunc = self.frequency_trunc[~outliers]
        self.Z_trunc = self.Z_trunc[~outliers]