"""
DRT Class for Electrochemical Impedance Spectroscopy (EIS) Analysis

Purpose:
    This class is designed to perform EIS data analysis using methods such as Distribution of Relaxation Time (DRT), Kramers-Kronig (KK) analysis, Tikhonov regularization, and Fourier transform-based approaches.

Created by:
    Hangyu Yu, EPFL GEM, Switzerland
    Created date: 2025.02.12
    Last modified: 
"""
from Methods.DRT.Utils import rmoutliers
from Methods.DRT.Utils import ConvertToASR
from Methods.DRT.Utils import Linear_KK
from Methods.DRT.Utils import Linear_KK_mu
from Methods.DRT.Utils import Linear_KK_opt_mu_cut
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class DRT:
    def __init__(self, Re_raw=None, Im_raw=None, f_raw=None, cell_area=None, n_cell=None, file_folder=None, filename=None):
        # Test information
        self.cell_area = cell_area     # SOC area [cm^2]
        self.n_cell = n_cell           # Number of cells
        self.file_folder = file_folder # File folder path
        self.filename = filename       # File name
        self.instrument_type = None    # Zahner or Biologic or others
        self.save_name = None          # Save name for results
        self.store = None              # Trash can for everything
        
        # Data classification
        self.Re_raw = Re_raw             # Real part of raw impedance data [Ω]
        self.Im_raw = Im_raw             # Imaginary part of raw impedance data [Ω]
        self.Z_raw = None              # Raw impedance data [Ω]
        self.frequency_raw = f_raw      # Raw frequency data
        self.significance = None       # Significance values for EIS data, mostly applicable in Zahner data

        self.Re_trunc = None           # Truncated real part of impedance data [Ω]
        self.Im_trunc = None           # Truncated imaginary part of impedance data
        self.Z_trunc = None            # Truncated impedance data
        self.frequency_trunc = None    # Truncated frequency data

        self.Re_crct = None            # L/C Corrected real part of impedance data
        self.Im_crct = None            # L/C Corrected imaginary part of impedance data
        self.Z_crct = None             # L/C Corrected impedance data
        self.frequency_crct = None     # L/C Corrected frequency data

        self.Re_smooth = None          # Smoothed real part of impedance data
        self.Im_smooth = None          # Smoothed imaginary part of impedance data
        self.Z_smooth = None           # Smoothed impedance data
        self.frequency_smooth = None   # Smoothed frequency data
        self.points_per_decade = 30    # Points per decade for smoothing

        self.Re_extra = None            # Extrapolated real part of impedance data
        self.Im_extra = None            # Extrapolated imaginary part of impedance data
        self.Z_extra = None             # Extrapolated impedance data
        self.frequency_extra = None     # Extrapolated frequency data

        # Data treatment parameters
        self.freq_log_min = -10        # 10^min frequency for extended spectra
        self.freq_log_max =  10        # 10^max frequency for extended spectra
        self.num_cut_upper = None      # Number of upper frequency points to be cut
        self.num_cut_lower = None      # Number of lower frequency points to be cut
        self.num_cut_middle = None     # middle frequency cut, index of points in original data

        self.sig_threshold = 0.995     # Significance threshold for EIS data, specifically for Zahner data
        self.mu_threshold = 0.85       # Threshold for Dante's method
        self.nRCmax = 50              # Maximum RC elements used for Dante's method
        self.kk_threshold = 1          # Threshold for the kk residual, used for auto-kk cut

        # Parameters and variables for Kronig-Kramers method
        self.delta_Re_kk = None        # KK residual of real part
        self.delta_Im_kk = None        # KK residual of imaginary part
        self.frequency_kk = None       # Frequency data for KK analysis
        self.res_ohm_kk = None         # Ohmic resistance based on RC elements fitting
        self.res_pol_kk = None         # Polarization resistance based on RC elements fitting
        self.L_kk = None               # Inductance correction
        self.C_kk = None               # Capacitance correction
        self.num_RC = None             # Number of RC elements applied
        self.KK_type = "standard"      # KK method applied, including "standard", "Mu_criterion", "Optimal_mu_criterion"

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
        self.lambda_tknv = 0.15        # Regularization parameter
        self.lambda_opt  = None        # Optimal regularization parameter
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

        if self.Re_raw is None:
            print("[Error] Real part of impedance data is empty!")
            return
        elif self.Im_raw is None:
            print("[Error] Imaginary part of impedance data is empty!")
            return
        elif self.frequency_raw is None:
            print("[Error] Frequency data is empty!")
            return
        else:
            if len(self.frequency_raw) != len(np.unique(self.frequency_raw)):
                print("[Error] Duplicate frequency points found! Check the data import")
                return
            if self.cell_area is None:
                print("[Error] Cell area is empty!")
                return
            elif self.n_cell is None:
                print("[Error] Number of cells is empty!")
                return
            else:
                sort_idx = np.argsort(self.frequency_raw)[::-1]
                self.Re_raw = self.Re_raw[sort_idx] * self.cell_area / self.n_cell
                self.Im_raw = self.Im_raw[sort_idx] * self.cell_area / self.n_cell
                self.Re_trunc = self.Re_raw
                self.Im_trunc = self.Im_raw
                self.frequency_trunc = self.frequency_raw[sort_idx]
                if self.Z_raw is None:
                    self.Z_raw = self.Re_raw + 1j * self.Im_raw
                self.Z_trunc = self.Z_raw
                if self.significance is not None:
                    self.significance = self.significance[sort_idx]
                print("[Info] DRT code initialized successfully!")

    # Functions for data processing
    def rm_significance(self):
        """
        Remove points with low significance values from EIS data
        """
        if self.significance is None:
            print("[Error] Significance values are empty! Check the data import")
        else:
            rm_num = np.where(self.significance < self.sig_threshold)[0]
            self.Re_trunc = np.delete(self.Re_trunc, rm_num)
            self.Im_trunc = np.delete(self.Im_trunc, rm_num)
            self.frequency_trunc = np.delete(self.frequency_trunc, rm_num)
            self.Z_trunc = np.delete(self.Z_trunc, rm_num)
            
    def rm_hfc_lfc(self):
        """
        Remove high-frequency and low-frequency data points from EIS data and remove outliers
        """
        # Define the cut number of high-frequency and low-frequency points
        Nfh_cut = self.num_cut_upper
        Nfl_cut = self.num_cut_lower

        # Cut high-frequency and low-frequency components
        leng = len(self.frequency_trunc)
        self.frequency_trunc = self.frequency_trunc[Nfh_cut:leng-Nfl_cut]
        self.Re_trunc = self.Re_trunc[Nfh_cut:leng-Nfl_cut]
        self.Im_trunc = self.Im_trunc[Nfh_cut:leng-Nfl_cut]
        self.Z_trunc  = self.Z_trunc[Nfh_cut:leng-Nfl_cut]

    def rm_outliers(self, mv_window_size=6, n_std=3):
        # Remove outliers based on the standard deviation
        _, Re_outliers = rmoutliers(self.Re_trunc, mv_window_size, n_std)
        _, Im_outliers = rmoutliers(self.Im_trunc, mv_window_size, n_std)
        outliers = Re_outliers | Im_outliers

        self.Re_trunc = self.Re_trunc[~outliers]
        self.Im_trunc = self.Im_trunc[~outliers]
        self.frequency_trunc = self.frequency_trunc[~outliers]
        self.Z_trunc = self.Z_trunc[~outliers]

    def KK_test(self):
        """
        Using linear KK method to characterize the data
        """
        self.num_RC = len(self.frequency_trunc) - 3
        self.store['omega'], self.store['tau'] = ConvertToASR(self.frequency_trunc)
        if self.KK_type == "standard":
            self.store['EIS_kk'], self.store['RC_kk'], self.store['RsLCinv_kk'] = Linear_KK(self.Re_trunc, self.Im_trunc, self.frequency_trunc, self.store['tau'], self.store['omega'], self.num_RC)
        elif self.KK_type == "Mu_criterion":
            self.store['EIS_kk'], self.store['RC_kk'], self.store['RsLCinv_kk'] = Linear_KK_mu(self.Re_trunc, self.Im_trunc, self.frequency_trunc, self.store['tau'], self.store['omega'], self.nRCmax, self.mu_threshold)
        else:
            print("[Error] Invalid KK method type specified!")

        self.delta_Re_kk = self.store['EIS_kk']['dr']
        self.delta_Im_kk = self.store['EIS_kk']['di']
    
    def rm_auto_KK(self):
        """
        Using linear KK method to automatically remove the values with high residuals
        """
        if 'EIS_kk' in self.store is not None:
            NotKK = (np.abs(self.store['EIS_kk']['di']) > self.kk_threshold) | (np.abs(self.store['EIS_kk']['dr']) > self.kk_threshold)
            NotKK[0] = False
            NotKK[-1] = False
            self.Re_trunc        = np.delete(self.Re_trunc, np.where(NotKK))
            self.Im_trunc        = np.delete(self.Im_trunc, np.where(NotKK))
            self.frequency_trunc = np.delete(self.frequency_trunc, np.where(NotKK))
        else:
            print("[Error] KK test is not performed yet!")
            return
    
    # Functions for data plotting
    def KK_plot(self):
        """
        Plot residuals of KK analysis
        """
        plt.figure('KK_analysis')
        plt.semilogx(self.frequency_kk, self.delta_Re_kk, '-ob', label='residual Re')  # Linear KK real
        plt.semilogx(self.frequency_kk, self.delta_Im_kk, '-or', label='residual Im')  # Linear KK imag
        plt.xlabel('f [Hz]')
        plt.ylabel('residuals [%]')
        plt.axhline(y=self.kk_threshold, color='k', linestyle='--', linewidth=1.5)  # Line to indicate threshold
        plt.axhline(y=-self.kk_threshold, color='k', linestyle='--', linewidth=1.5)  # Line to indicate threshold
        plt.axhline(y=0, color='k', linewidth=1.5)
        plt.legend()
        plt.grid(True)
        plt.show()

    def EIS_plot(self, EIS_list):
        for plot_type in EIS_list:
            if plot_type == 'ReIm':
                plt.figure('Truncated nyquist')
                plt.plot(self.Re, -self.Im, '-bo', label='Truncated')
                plt.plot(self.Re_raw, -self.Im_raw, '-rx', label='Original')
                plt.xlabel("$Z' \, [\Omega*cm^2]$")
                plt.ylabel("$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Re':
                plt.figure('Truncated Bode real')
                plt.semilogx(self.frequency, self.Re, '-bo', label='Truncated')
                plt.semilogx(self.frequency_raw, self.Re_raw, '-rx', label='Original')
                plt.xlabel('f [Hz]')
                plt.ylabel("$Z' \, [\Omega*cm^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Im':
                plt.figure('Truncated Bode imaginary')
                plt.semilogx(self.frequency, -self.Im, '-bo', label='Truncated')
                plt.semilogx(self.frequency_raw, -self.Im_raw, '-rx', label='Original')
                plt.xlabel('f [Hz]')
                plt.ylabel("$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'ReIm_LC':
                plt.figure('L/C corrected Nyquist')
                plt.plot(self.Re, -self.Im, 'ok', self.Re_crct, -self.Im_crct, 'r', markersize=2, linewidth=1.5)
                plt.xlabel("$Z' \, [\Omega*cm^2]$")
                plt.ylabel("$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'Re_LC':
                plt.figure('LC corrected Bode real')
                plt.semilogx(self.frequency, self.Re_crct, '-bo', label='Corrected')
                plt.semilogx(self.frequency_raw, self.Re_raw, '-rx', label='Original')
                plt.xlabel('f [Hz]')
                plt.ylabel("$Z' \, [\Omega*cm^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Im_LC':
                plt.figure('LC corrected Bode imaginary')
                plt.semilogx(self.frequency, -self.Im_crct, '-bo', label='Corrected')
                plt.semilogx(self.frequency_raw, -self.Im_raw, '-rx', label='Original')
                plt.xlabel('f [Hz]')
                plt.ylabel("$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Re_s':
                plt.figure('Smoothed Re')
                plt.semilogx(self.frequency, self.Re, 'ok', self.frequency_smooth, self.Re_smooth, 'r', markersize=2, linewidth=1.5)
                plt.xlabel('f [Hz]')
                plt.ylabel("$Z' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'Im_s':
                plt.figure('Smoothed Im')
                plt.semilogx(self.frequency, -self.Im, 'ok', self.frequency_smooth, -self.Im_smooth, 'r', markersize=2, linewidth=1.5)
                plt.xlabel('f [Hz]')
                plt.ylabel("$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'ReIm_s':
                plt.figure('Smoothed ReIm')
                plt.plot(self.Re, -self.Im, 'ok', self.Re_smooth, -self.Im_smooth, 'r', markersize=2, linewidth=1.5)
                plt.xlabel("$Z' \, [\Omega*cm^2]$")
                plt.ylabel("$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'Re_e':
                plt.figure('Extrapolated Re')
                plt.semilogx(self.frequency, self.Re, 'ok', self.frequency_extra, self.Re_extra, 'r', markersize=2, linewidth=1.5)
                plt.xlabel('f [Hz]')
                plt.ylabel("$Z' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'Im_e':
                plt.figure('Extrapolated Im')
                plt.semilogx(self.frequency, -self.Im, 'ok', self.frequency_extra, -self.Im_extra, 'r', markersize=2, linewidth=1.5)
                plt.xlabel('f [Hz]')
                plt.ylabel("$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'ReIm_e':
                plt.figure('Extrapolated ReIm')
                plt.plot(self.Re, -self.Im, 'ok', self.Re_extra, -self.Im_extra, 'r', markersize=2, linewidth=1.5)
                plt.xlabel("$Z' \, [\Omega*cm^2]$")
                plt.ylabel("$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
        plt.show()
