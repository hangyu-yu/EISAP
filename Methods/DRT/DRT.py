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
from cmcrameri import cm

class DRT:
    def __init__(self, Re_raw=None, Im_raw=None, f_raw=None, CellArea=None, n_cell=None, file_folder=None, filename=None):
        # Test information
        self.file_folder = file_folder # File folder path
        self.filename = filename       # File name
        self.save_name = None          # Save name for results
        self.info = None               # Information for the test
        self.store = {}                # Trash can for everything
        
        # Data classification
        self.raw = {
            'f': f_raw,                 # Raw frequency data [Hz]
            'Z': None,                  # Raw impedance data [Ω*cm2]
            'Re': Re_raw,               # Real part of raw impedance data [Ω*cm2]
            'Im': Im_raw,               # Imaginary part of raw impedance data [Ω*cm2]
            'significance': None,       # Significance values for EIS data, mostly applicable in Zahner data
            'omega': None,               # Angular frequency data [rad/s]
            'tau': None                 # Time constant data [s]
        }

        self.truncated = {
            'f': None,                 # Truncated frequency data [Hz]
            'Z': None,                 # Truncated impedance data [Ω*cm2]
            'Re': None,                # Truncated real part of impedance data [Ω*cm2]
            'Im': None,                # Truncated imaginary part of impedance data [Ω*cm2]
            'significance': None,      # Truncated significance values for EIS data
            'omega': None,               # Angular frequency data [rad/s]
            'tau': None                 # Time constant data [s]
        }

        self.LCcorrect = {
            'f': None,                 # L/C Corrected frequency data [Hz]
            'Z': None,                 # L/C Corrected impedance data [Ω*cm2]
            'Re': None,                # L/C Corrected real part of impedance data [Ω*cm2]
            'Im': None,                # L/C Corrected imaginary part of impedance data [Ω*cm2]
            'omega': None,               # Angular frequency data [rad/s]
            'tau': None                 # Time constant data [s]
        }

        self.smooth = {
            'f': None,                 # Smoothed frequency data [Hz]
            'Z': None,                 # Smoothed impedance data [Ω*cm2]
            'Re': None,                # Smoothed real part of impedance data [Ω*cm2]
            'Im': None,                # Smoothed imaginary part of impedance data [Ω*cm2]
            'omega': None,               # Angular frequency data [rad/s]
            'tau': None,               # Time constant data [s]
        }

        self.extrapolation = {
            'f': None,                 # Extrapolated frequency data [Hz]
            'Z': None,                 # Extrapolated impedance data
            'Re': None,                # Extrapolated real part of impedance data [Ω*cm2]
            'Im': None,                # Extrapolated imaginary part of impedance data
            'omega': None,               # Angular frequency data [rad/s]
            'tau': None                 # Time constant data [s]
        }

        # Data structure for KK results
        self.KK_data = {
            'Re': None,                 # Real part of KK analysis
            'Im': None,                 # Imaginary part of KK analysis
            'f': None,                  # Frequency data for KK analysis
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
            'f': None                  # Truncated frequency data
        }

        self.tknv_smooth = {
            'Re': None,                # Tikhonov method with smoothed real part data
            'Im': None,                # Tikhonov method with smoothed imaginary part data
            'ReIm': None,              # Tikhonov method with smoothed real and imaginary part data
            'f': None                  # Smoothed frequency data
        }

        self.tknv_extrapolation = {
            'Re': None,                # Tikhonov method with extrapolated real part data
            'Im': None,                # Tikhonov method with extrapolated imaginary part data
            'ReIm': None,              # Tikhonov method with extrapolated real and imaginary part data
            'f': None          # Extrapolated frequency data
        }

        self.tknv_LCcorrect = {
            'Re': None,                # Tikhonov method with LC corrected real part data
            'Im': None,                # Tikhonov method with LC corrected imaginary part data
            'ReIm': None,              # Tikhonov method with LC corrected real and imaginary part data
            'f': None                  # LC corrected frequency data
        }

        # Data treatment parameters
        self.parameter = {
            # Sample information
            'Sample' : {
                'CellArea': CellArea,  # SOC area [\mathrm{cm}^2]
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
                'mv_window_size': 5,   # Moving window size for outlier removal
                'n_std': 5,            # Number of standard deviations for outlier removal
                'Rmoutliers': True    # Remove outliers from EIS data
            },
            # Self-adaptive KK method
            'KKpreprocess': {
                'nRCmax': 30,           # Maximum RC elements used for Dante's method
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
                'KK_test': True,        # Perform KK test or not
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
        leng = len(self.raw['f'])
        self.truncated['f'] = self.raw['f'][Nfh_cut:leng-Nfl_cut]
        self.truncated['Re'] = self.raw['Re'][Nfh_cut:leng-Nfl_cut]
        self.truncated['Im'] = self.raw['Im'][Nfh_cut:leng-Nfl_cut]
        self.truncated['Z'] = self.raw['Z'][Nfh_cut:leng-Nfl_cut]
        if self.raw['significance'] is not None:
            self.truncated['significance'] = self.raw['significance'][Nfh_cut:leng-Nfl_cut]
        
    def rm_significance(self):
        """
        Remove points with low significance values from EIS data
        """
        if self.raw['significance'] is None:
            print("[Error] Significance values are empty! Check the data import")
        elif self.truncated['significance'] is None:
            print("[Error] Significance values are empty! Check the data import")
        else:
            rm_num = np.where(self.truncated['significance'] < self.parameter['RM_significance']['sig_threshold'])[0]
            self.truncated['Re'] = np.delete(self.truncated['Re'], rm_num)
            self.truncated['Im'] = np.delete(self.truncated['Im'], rm_num)
            self.truncated['f'] = np.delete(self.truncated['f'], rm_num)
            self.truncated['Z'] = np.delete(self.truncated['Z'], rm_num)
            self.truncated['significance'] = np.delete(self.truncated['significance'], rm_num)
            
    def rm_outliers(self):
        # Remove outliers based on the standard deviation
        mv_window_size = self.parameter['Rmoutliers']['mv_window_size']
        n_std = self.parameter['Rmoutliers']['n_std']
        _, Re_outliers = fn.rmoutliers(self.truncated['Re'], mv_window_size, n_std)
        _, Im_outliers = fn.rmoutliers(self.truncated['Im'], mv_window_size, n_std)
        outliers = Re_outliers | Im_outliers

        self.truncated['Re'] = self.truncated['Re'][~outliers]
        self.truncated['Im'] = self.truncated['Im'][~outliers]
        self.truncated['f'] = self.truncated['f'][~outliers]
        self.truncated['Z'] = self.truncated['Z'][~outliers]
        if self.raw['significance'] is not None:
            self.truncated['significance'] = self.truncated['significance'][~outliers]

    def Linear_KK_opt_mu_cut(self, EIS_data, parameter):
        # Automatic determine the optimal cut based on mu criterion
        self.store['EIS_Processed'], self.store['EIS_kk_opt'], self.store['RC_kk_opt'], self.store['RsLCinv_kk_opt'], self.store['Parameters_opt'] = fn.Linear_KK_opt_mu_cut(EIS_data, parameter)
        self.KK_data['Re'] = self.store['EIS_kk_opt']['Re'].to_numpy()
        self.KK_data['Im'] = self.store['EIS_kk_opt']['Im'].to_numpy()
        self.KK_data['f'] = self.store['EIS_kk_opt']['f'].to_numpy()
        self.KK_data['tau'] = self.store['EIS_kk_opt']['tau'].to_numpy()
        self.KK_data['omega'] = self.store['EIS_kk_opt']['omega'].to_numpy()
        self.KK_data['delta_Re_kk'] = self.store['EIS_kk_opt']['dr'].to_numpy()
        self.KK_data['delta_Im_kk'] = self.store['EIS_kk_opt']['di'].to_numpy()
        self.KK_data['res_ohm_kk'] = self.store['RsLCinv_kk_opt']['Rs'].to_numpy()
        self.KK_data['res_pol_kk'] = self.store['RsLCinv_kk_opt']['Rp'].to_numpy()
        self.KK_data['L_kk'] = self.store['RsLCinv_kk_opt']['L'].to_numpy()
        self.KK_data['C_kk'] = 1 / self.store['RsLCinv_kk_opt']['Cinv'].to_numpy()
        self.KK_data['R_RC'] = self.store['RC_kk_opt']['R_RC'].to_numpy()
        self.KK_data['tau_RC'] = self.store['RC_kk_opt']['tau_RC'].to_numpy()

    def KK_test(self, EIS_data):
        """
        Using linear KK method to characterize the data
        """
        self.parameter['KK']['nRC'] = len(EIS_data['f']) - 3
        parameters_dummy = {'CellArea': 1}  # dummy cell area for ConvertToASR
        EIS_data = self.convert2asr(EIS_data,parameters_dummy)
        KK_type = self.parameter['KK']['KK_type']
        if KK_type == "standard":
            self.store['EIS_kk'], self.store['RC_kk'], self.store['RsLCinv_kk'] = fn.Linear_KK(EIS_data, self.parameter['KK'])
        elif KK_type == "Mu_criterion":
            self.store['EIS_kk'], self.store['RC_kk'], self.store['RsLCinv_kk'] = fn.Linear_KK_mu(EIS_data, self.parameter['KK'])
        else:
            print("[Error] Invalid KK method type specified!")
        self.KK_data['Re'] = self.store['EIS_kk']['Re'].to_numpy()
        self.KK_data['Im'] = self.store['EIS_kk']['Im'].to_numpy()
        self.KK_data['f'] = self.store['EIS_kk']['f'].to_numpy()
        self.KK_data['tau'] = self.store['EIS_kk']['tau'].to_numpy()
        self.KK_data['omega'] = self.store['EIS_kk']['omega'].to_numpy()
        self.KK_data['delta_Re_kk'] = self.store['EIS_kk']['dr'].to_numpy()
        self.KK_data['delta_Im_kk'] = self.store['EIS_kk']['di'].to_numpy()
        self.KK_data['res_ohm_kk'] = self.store['RsLCinv_kk']['Rs'].to_numpy()
        self.KK_data['res_pol_kk'] = self.store['RsLCinv_kk']['Rp'].to_numpy()
        self.KK_data['L_kk'] = self.store['RsLCinv_kk']['L'].to_numpy()
        self.KK_data['C_kk'] = 1 / self.store['RsLCinv_kk']['Cinv'].to_numpy()
        self.KK_data['R_RC'] = self.store['RC_kk']['R_RC'].to_numpy()
        self.KK_data['tau_RC'] = self.store['RC_kk']['tau_RC'].to_numpy()

    def ResampleEIS(self, EIS_data, parameter):
        if self.parameter['Smoothing']['fmax'] is None:
            self.parameter['Smoothing']['fmax'] = max(EIS_data['f'])
            self.parameter['Smoothing']['fmin'] = min(EIS_data['f'])
        EIS_data_processed = fn.ResampleEIS(self.store['RC_kk'], self.store['RsLCinv_kk'], parameter)
        return EIS_data_processed
    
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
            self.truncated['f'] = np.delete(self.truncated['f'], np.where(NotKK))
        else:
            print("[Error] KK test is not performed yet!")
            return
        
    def convert2asr(self, EIS_data, parameter):
        """
        Convert the EIS data to the ASR data
        """
        EIS_data = fn.ConvertToASR(EIS_data,parameter)
        return EIS_data
    
    # Functions for Tiknov regularization
    def lambdaOPT(self):
        parameter = self.parameter['LambdaOpt']
        self.lambda_opt = fn.LambdaOPT(self.truncated['Re'], self.truncated['Im'], self.truncated['f'], parameter)
        print(f"Optimal lambda value: {self.lambda_opt}")

    def tknv(self):
        pass
    
    # Functions for data plotting
    def KK_plot(self, figure_name = ''):
        """
        Plot residuals of KK analysis
        """
        cmap = plt.cm.get_cmap(plt.rcParams['image.cmap'])
        plt.figure('KK_results -- '+figure_name)
        plt.semilogx(self.KK_data['f'], self.KK_data['delta_Re_kk'], '-o', label='Residual Re', color=cmap(0.3))  # Linear KK real
        plt.semilogx(self.KK_data['f'], self.KK_data['delta_Im_kk'], '-o', label='Residual Im', color=cmap(0.7))  # Linear KK imag
        plt.xlabel('frequency [Hz]')
        plt.ylabel('Residuals [%]')
        plt.axhline(y=self.parameter['KK']['kk_threshold'], linestyle='--', linewidth=1.5)  # Line to indicate threshold
        plt.axhline(y=-self.parameter['KK']['kk_threshold'], linestyle='--', linewidth=1.5)  # Line to indicate threshold
        plt.axhline(y=0, color='k', linewidth=1.5)
        plt.legend()
        plt.grid(True)
        # plt.show()

    def EIS_plot(self, EIS_list, figure_name = ''):
        cmap = plt.cm.get_cmap(plt.rcParams['image.cmap'])
        for plot_type in EIS_list:
            if plot_type == 'ReIm':
                plt.figure(plot_type + '--' + figure_name)
                plt.plot(self.truncated['Re'], -self.truncated['Im'], '-', label='Truncated', color=cmap(0.3))
                plt.plot(self.raw['Re'], -self.raw['Im'], 'o', markerfacecolor='none', label='Original', color=cmap(0.7))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
            elif plot_type == 'Re':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.truncated['f'], self.truncated['Re'], '-', label='Truncated', color=cmap(0.3))
                plt.semilogx(self.raw['f'], self.raw['Re'], 'o', markerfacecolor='none', label='Original', color=cmap(0.7))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Im':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.truncated['f'], -self.truncated['Im'], '-', label='Truncated', color=cmap(0.3))
                plt.semilogx(self.raw['f'], -self.raw['Im'], 'o', markerfacecolor='none', label='Original', color=cmap(0.7))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'ReIm_LC':
                plt.figure(plot_type + '--' + figure_name)
                plt.plot(self.LCcorrect['Re'], -self.LCcorrect['Im'], '-', label='Corrected', color=cmap(0.3))
                plt.plot(self.truncated['Re'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.7))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
            elif plot_type == 'Re_LC':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.LCcorrect['f'], self.LCcorrect['Re'], '-', label='Corrected', color=cmap(0.3))
                plt.semilogx(self.truncated['f'], self.truncated['Re'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.7))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Im_LC':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.LCcorrect['f'], -self.LCcorrect['Im'], '-', label='Corrected', color=cmap(0.3))
                plt.semilogx(self.truncated['f'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.7))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Re_s':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.smooth['f'], self.smooth['Re'], '-', label='Smoothed', color=cmap(0.3))
                plt.semilogx(self.truncated['f'], self.truncated['Re'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.7))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Im_s':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.smooth['f'], -self.smooth['Im'], '-', label='Smoothed', color=cmap(0.3))
                plt.semilogx(self.truncated['f'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.7))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'ReIm_s':
                plt.figure(plot_type + '--' + figure_name)
                plt.plot(self.smooth['Re'], -self.smooth['Im'], '-', label='Smoothed', color=cmap(0.3))
                plt.plot(self.truncated['Re'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.7))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
            elif plot_type == 'Re_e':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.extrapolation['f'], self.extrapolation['Re'], '-', label='Extrapolated', color=cmap(0.3))
                plt.semilogx(self.truncated['f'], self.truncated['Re'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.7))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'Im_e':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.extrapolation['f'], -self.extrapolation['Im'], '-', label='Extrapolated', color=cmap(0.3))
                plt.semilogx(self.truncated['f'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.7))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
            elif plot_type == 'ReIm_e':
                plt.figure(plot_type + '--' + figure_name)
                plt.plot(self.extrapolation['Re'], -self.extrapolation['Im'], '-', label='Extrapolated', color=cmap(0.3))
                plt.plot(self.truncated['Re'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.7))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
        # plt.show()
