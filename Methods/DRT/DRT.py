"""
DRT Class for Electrochemical Impedance Spectroscopy (EIS) Analysis

Purpose:
    This class is designed to perform EIS data analysis using methods such as Distribution of Relaxation Time (DRT), Kramers-Kronig (KK) analysis, Tikhonov regularization, and Fourier transform-based approaches.

Created by:
    Hangyu Yu, EPFL GEM, Switzerland
    Created date: 2025.02.12
    Last modified: 
"""
import Methods.DRT.Utils as fn
import numpy as np
import matplotlib.pyplot as plt

class DRT:
    def __init__(self, Re_raw=None, Im_raw=None, f_raw=None, cell_area=None, n_cell=None, file_folder=None, filename=None):
        # Test information
        self.file_folder = file_folder # File folder path
        self.filename = filename       # File name
        self.save_name = None          # Save name for results
        self.info = None               # Information for the test
        self.store = None              # Trash can for everything
        
        # Data classification
        self.raw = {
            'Re': Re_raw,               # Real part of raw impedance data [Ω]
            'Im': Im_raw,               # Imaginary part of raw impedance data [Ω]
            'Z': None,                  # Raw impedance data [Ω]
            'frequency': f_raw,         # Raw frequency data
            'significance': None        # Significance values for EIS data, mostly applicable in Zahner data
        }

        self.truncated = {
            'Re': None,                # Truncated real part of impedance data [Ω]
            'Im': None,                # Truncated imaginary part of impedance data
            'Z': None,                 # Truncated impedance data
            'frequency': None          # Truncated frequency data
        }

        self.LCcorrect = {
            'Re': None,                # L/C Corrected real part of impedance data [Ω]
            'Im': None,                # L/C Corrected imaginary part of impedance data
            'Z': None,                 # L/C Corrected impedance data
            'frequency': None          # L/C Corrected frequency data
        }

        self.smooth = {
            'Re': None,                # Smoothed real part of impedance data [Ω]
            'Im': None,                # Smoothed imaginary part of impedance data
            'Z': None,                 # Smoothed impedance data
            'frequency': None,         # Smoothed frequency data
            'points_per_decade': 30    # Points per decade for smoothing
        }

        self.extrapolation = {
            'Re': None,                # Extrapolated real part of impedance data [Ω]
            'Im': None,                # Extrapolated imaginary part of impedance data
            'Z': None,                 # Extrapolated impedance data
            'frequency': None          # Extrapolated frequency data
        }

        # Data structure for KK results
        self.KK_data = {
            'Re': None,                 # Real part of KK analysis
            'Im': None,                 # Imaginary part of KK analysis
            'frequency_kk': None,       # Frequency data for KK analysis
            'tau': None,                # Time constant data for KK analysis
            'omega': None,              # Angular frequency data for KK analysis
            'delta_Re_kk': None,        # KK residual of real part
            'delta_Im_kk': None,        # KK residual of imaginary part
            'res_ohm_kk': None,         # Ohmic resistance based on RC elements fitting
            'res_pol_kk': None,         # Polarization resistance based on RC elements fitting
            'L_kk': None,               # Inductance correction
            'C_kk': None,               # Capacitance correction
            'R_RC': None,               # Resistancs of RC elements
            'tau_RC': None              # Time constants of RC elements
        }

        # Data structure for tikonov methodology
        self.tknv_truncated = {
            'Re': None,                # Tikhonov method with truncated real part data
            'Im': None,                # Tikhonov method with truncated imaginary part data
            'ReIm': None,              # Tikhonov method with truncated real and imaginary part data
            'frequency': None          # Truncated frequency data
        }

        self.tknv_smooth = {
            'Re': None,                # Tikhonov method with smoothed real part data
            'Im': None,                # Tikhonov method with smoothed imaginary part data
            'ReIm': None,              # Tikhonov method with smoothed real and imaginary part data
            'frequency': None          # Smoothed frequency data
        }

        self.tknv_extrapolation = {
            'Re': None,                # Tikhonov method with extrapolated real part data
            'Im': None,                # Tikhonov method with extrapolated imaginary part data
            'ReIm': None,              # Tikhonov method with extrapolated real and imaginary part data
            'frequency': None          # Extrapolated frequency data
        }

        self.tknv_LCcorrect = {
            'Re': None,                # Tikhonov method with LC corrected real part data
            'Im': None,                # Tikhonov method with LC corrected imaginary part data
            'ReIm': None,              # Tikhonov method with LC corrected real and imaginary part data
            'frequency': None          # LC corrected frequency data
        }

        # Data treatment parameters
        self.parameter = {
            # Sample information
            'Sample' : {
                'cell_area': cell_area,  # SOC area [cm^2]
                'n_cell': n_cell,        # Number of cells
                'instrument_type': None  # Zahner or Biologic or others
            },
            # Data preprocessing
            'Preprocessing': {
                'num_cut_upper': 0,    # Number of upper frequency points to be cut
                'num_cut_lower': 0,    # Number of lower frequency points to be cut
                'num_cut_middle': 0,   # Middle frequency cut, index of points in ''original data''
            },
            # Remove points with low significance only for Zahner data
            'RM_significance': {
                'sig_threshold': 0.995,  # Significance threshold for EIS data
                'rm_significance': True # Remove points with low significance
            },
            # Remove outliers
            'Rmoutliers': {
                'mv_window_size': 6,   # Moving window size for outlier removal
                'n_std': 3,            # Number of standard deviations for outlier removal
                'Rmoutliers': True    # Remove outliers from EIS data
            },
            # Self-adaptive KK method
            'KKpreprocess': {
                'nRCmax': 50,           # Maximum RC elements used for Dante's method
                'nlf_cut_min': 0,       # Minimal lower frequency point cut
                'nlf_cut_max': 20,      # Maximal lower frequency point cut
                'nhf_cut_min': 0,       # Minimal upper frequency point cut
                'nhf_cut_max': 10,      # Maximal upper frequency point cut
                'mu_ll': 0,             # Lower limit of mu value
                'mu_ul': 0.9,           # Upper limit of mu value
                'mu_resolution': 0.02,  # Resolution of mu value
                'cut_lf_opt': None,     # Optimal lower frequency point cut
                'cut_hf_opt': None,     # Optimal upper frequency point cut
                'mu_opt': None,         # Optimal mu value
                'Display': True,        # Display the optimal cut and mu value
                'OptimalCut': False     # Switch on self-adaptive KK method or not
            },
            # KK method
            'KK': {
                'nRCmax': 50,           # Maximum RC elements used for mu criterion
                'kk_threshold': 1,      # Threshold for the kk residual
                'mu_threshold': 0.85,   # Threshold for mu criterion
                'KK_type': 'standard',  # KK method applied, including "standard", "Mu_criterion", "Optimal_mu_criterion"
                'nRC': 80,              # Number of RC elements used for KK analysis
                'KK_test': True,       # Perform KK test or not
                'RmNonKK': False        # Remove non-KK points
            },
            # Data smoothing
            'Smoothing': {
                'fmin': None,           # Minimal frequency for smoothing
                'fmax': None,           # Maximal frequency for smoothing
                'PointsPerDecade': 30,  # Number of points per decade for smoothing
            },
            # Data extrapolation
            'Extrapolation': {
                'fmin': 1e-8,           # Minimal frequency for smoothing
                'fmax': 1e10,           # Maximal frequency for smoothing
                'PointsPerDecade': 20,  # Number of points per decade for smoothing
            },
            # Optimal lambda
            'LambdaOpt': {
                'lambda_min': 1e-7,     # Minimal lambda value for Tikhonov regularization
                'lambda_max': 0.2,      # Maximal lambda value for Tikhonov regularization
                'n': 100,               # Number of lambda values to be tested
                'lambda_plot': True,    # Display the lambda plot or not
                'PlotFig': False        # Display the lambda plot or not
            },
            # Tikonov regularization
            'DRT': {
                'Lambda_selection': 'Manual',  # Lambda selection method, including 'Manual' and 'Optimal'
                'Lambda': 0.15,                # Regularization parameter
                'tknv_legend': None            # Legend for Tikhonov regularization plot
            }
        }

    # Functions for data processing
    def rm_hfc_lfc(self):
        """
        Remove high-frequency and low-frequency data points from EIS data and remove outliers
        """
        # Define the cut number of high-frequency and low-frequency points
        Nfh_cut = self.parameter['Preprocessing']['num_cut_upper']
        Nfl_cut = self.parameter['Preprocessing']['num_cut_lower']

        # Cut high-frequency and low-frequency components
        leng = len(self.raw['frequency'])
        self.truncated['frequency'] = self.raw['frequency'][Nfh_cut:leng-Nfl_cut]
        self.truncated['Re'] = self.raw['Re'][Nfh_cut:leng-Nfl_cut]
        self.truncated['Im'] = self.raw['Im'][Nfh_cut:leng-Nfl_cut]
        self.truncated['Z']  = self.raw['Z'][Nfh_cut:leng-Nfl_cut]
        
    def rm_significance(self):
        """
        Remove points with low significance values from EIS data
        """
        if self.raw['significance'] is None:
            print("[Error] Significance values are empty! Check the data import")
        else:
            rm_num = np.where(self.raw['significance'] < self.parameter['RM_significance']['sig_threshold'])[0]
            self.truncated['Re'] = np.delete(self.truncated['Re'], rm_num)
            self.truncated['Im'] = np.delete(self.truncated['Im'], rm_num)
            self.truncated['frequency'] = np.delete(self.truncated['frequency'], rm_num)
            self.truncated['Z'] = np.delete(self.truncated['Z'], rm_num)
            

    def rm_outliers(self):
        # Remove outliers based on the standard deviation
        mv_window_size = self.parameter['Rmoutliers']['mv_window_size']
        n_std = self.parameter['Rmoutliers']['n_std']
        _, Re_outliers = fn.rmoutliers(self.truncated['Re'], mv_window_size, n_std)
        _, Im_outliers = fn.rmoutliers(self.truncated['Im'], mv_window_size, n_std)
        outliers = Re_outliers | Im_outliers

        self.truncated['Re'] = self.truncated['Re'][~outliers]
        self.truncated['Im'] = self.truncated['Im'][~outliers]
        self.truncated['frequency'] = self.truncated['frequency'][~outliers]
        self.truncated['Z'] = self.truncated['Z'][~outliers]

    def KK_test(self):
        """
        Using linear KK method to characterize the data
        """
        self.num_RC = len(self.truncated['frequency']) - 3
        self.store['omega'], self.store['tau'] = DRT.ConvertToASR(self.truncated['frequency'])
        KK_type = self.parameter['KK']['KK_type']
        if KK_type == "standard":
            self.store['EIS_kk'], self.store['RC_kk'], self.store['RsLCinv_kk'] = fn.Linear_KK(self.truncated['Re'], self.truncated['Im'], self.truncated['frequency'], self.store['tau'], self.store['omega'], self.num_RC)
        elif KK_type == "Mu_criterion":
            self.store['EIS_kk'], self.store['RC_kk'], self.store['RsLCinv_kk'] = fn.Linear_KK_mu(self.truncated['Re'], self.truncated['Im'], self.truncated['frequency'], self.store['tau'], self.store['omega'], self.parameter['KK']['nRCmax'], self.parameter['KK']['mu_threshold'])
        else:
            print("[Error] Invalid KK method type specified!")

        self.KK_data['delta_Re_kk'] = self.store['EIS_kk']['dr']
        self.KK_data['delta_Im_kk'] = self.store['EIS_kk']['di']
    
    def rm_auto_KK(self):
        """
        Using linear KK method to automatically remove the values with high residuals
        """
        if 'EIS_kk' in self.store:
            NotKK = (np.abs(self.store['EIS_kk']['di']) > self.parameter['KK']['kk_threshold']) | (np.abs(self.store['EIS_kk']['dr']) > self.parameter['KK']['kk_threshold'])
            NotKK[0] = False
            NotKK[-1] = False
            self.truncated['Re'] = np.delete(self.truncated['Re'], np.where(NotKK))
            self.truncated['Im'] = np.delete(self.truncated['Im'], np.where(NotKK))
            self.truncated['frequency'] = np.delete(self.truncated['frequency'], np.where(NotKK))
        else:
            print("[Error] KK test is not performed yet!")
            return
    
    # Functions for Tiknov regularization
    def lambdaOPT(self):
        parameter = self.parameter['LambdaOpt']
        self.lambda_opt = fn.LambdaOPT(self.truncated['Re'], self.truncated['Im'], self.truncated['frequency'], parameter)
        print(f"Optimal lambda value: {self.lambda_opt}")

    def tknv(self):
        pass
    
    # Functions for data plotting
    def KK_plot(self):
        """
        Plot residuals of KK analysis
        """
        plt.figure('KK_analysis')
        plt.semilogx(self.truncated['frequency'], self.KK_data['delta_Re_kk'], '-ob', label='residual Re')  # Linear KK real
        plt.semilogx(self.truncated['frequency'], self.KK_data['delta_Im_kk'], '-or', label='residual Im')  # Linear KK imag
        plt.xlabel('f [Hz]')
        plt.ylabel('residuals [%]')
        plt.axhline(y=self.parameter['KK']['kk_threshold'], color='k', linestyle='--', linewidth=1.5)  # Line to indicate threshold
        plt.axhline(y=-self.parameter['KK']['kk_threshold'], color='k', linestyle='--', linewidth=1.5)  # Line to indicate threshold
        plt.axhline(y=0, color='k', linewidth=1.5)
        plt.legend()
        plt.grid(True)
        plt.show()

    def EIS_plot(self, EIS_list):
        for plot_type in EIS_list:
            if plot_type == 'ReIm':
                plt.figure('Truncated nyquist')
                plt.plot(self.truncated['Re'], -self.truncated['Im'], '-bo', label='Truncated')
                plt.plot(self.raw['Re'], -self.raw['Im'], '-rx', label='Original')
                plt.xlabel(r"$Z' \, [\Omega*cm^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega*cm^2]$")
                plt.figure('Truncated nyquist')
                plt.plot(self.Re, -self.Im, '-bo', label='Truncated')
                plt.plot(self.Re_raw, -self.Im_raw, '-rx', label='Original')
                plt.xlabel(r"$Z' \, [\Omega*cm^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Re':
                plt.figure('Truncated Bode real')
                plt.semilogx(self.frequency, self.Re, '-bo', label='Truncated')
                plt.semilogx(self.frequency_raw, self.Re_raw, '-rx', label='Original')
                plt.xlabel('f [Hz]')
                plt.semilogx(self.truncated['frequency'], -self.truncated['Im'], '-bo', label='Truncated')
                plt.semilogx(self.raw['frequency'], -self.raw['Im'], '-rx', label='Original')
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'ReIm_LC':
                plt.figure('L/C corrected Nyquist')
                plt.plot(self.truncated['Re'], -self.truncated['Im'], 'ok', self.LCcorrect['Re'], -self.LCcorrect['Im'], 'r', markersize=2, linewidth=1.5)
                plt.xlabel(r"$Z' \, [\Omega*cm^2]$")
                plt.legend()
            elif plot_type == 'ReIm_LC':
                plt.figure('L/C corrected Nyquist')
                plt.plot(self.Re, -self.Im, 'ok', self.Re_crct, -self.Im_crct, 'r', markersize=2, linewidth=1.5)
                plt.xlabel(r"$Z' \, [\Omega*cm^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'Re_LC':
                plt.figure('LC corrected Bode real')
                plt.semilogx(self.frequency, self.Re_crct, '-bo', label='Corrected')
                plt.semilogx(self.frequency_raw, self.Re_raw, '-rx', label='Original')
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega*cm^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Im_LC':
                plt.figure('LC corrected Bode imaginary')
                plt.semilogx(self.frequency, -self.Im_crct, '-bo', label='Corrected')
                plt.semilogx(self.frequency_raw, -self.Im_raw, '-rx', label='Original')
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Re_s':
                plt.figure('Smoothed Re')
                plt.semilogx(self.frequency, self.Re, 'ok', self.frequency_smooth, self.Re_smooth, 'r', markersize=2, linewidth=1.5)
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'Im_s':
                plt.figure('Smoothed Im')
                plt.semilogx(self.frequency, -self.Im, 'ok', self.frequency_smooth, -self.Im_smooth, 'r', markersize=2, linewidth=1.5)
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'ReIm_s':
                plt.figure('Smoothed ReIm')
                plt.plot(self.Re, -self.Im, 'ok', self.Re_smooth, -self.Im_smooth, 'r', markersize=2, linewidth=1.5)
                plt.xlabel(r"$Z' \, [\Omega*cm^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'Re_e':
                plt.figure('Extrapolated Re')
                plt.semilogx(self.frequency, self.Re, 'ok', self.frequency_extra, self.Re_extra, 'r', markersize=2, linewidth=1.5)
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'Im_e':
                plt.figure('Extrapolated Im')
                plt.semilogx(self.frequency, -self.Im, 'ok', self.frequency_extra, -self.Im_extra, 'r', markersize=2, linewidth=1.5)
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
            elif plot_type == 'ReIm_e':
                plt.figure('Extrapolated ReIm')
                plt.plot(self.Re, -self.Im, 'ok', self.Re_extra, -self.Im_extra, 'r', markersize=2, linewidth=1.5)
                plt.xlabel(r"$Z' \, [\Omega*cm^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega*cm^2]$")
                plt.grid(True)
        plt.show()
