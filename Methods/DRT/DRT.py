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
import time
import os
import pandas as pd

class DRT:
    def __init__(self, Re_raw=None, Im_raw=None, f_raw=None, CellArea=None, n_cell=None, file_folder=None, filename=None):
        # Test information
        self.file_folder = file_folder # File folder path
        self.filename = filename       # File name
        self.save_name = filename      # Save name for results
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
        self.tknv_truncated = None

        self.tknv_smooth = None

        self.tknv_extrapolation = None

        self.tknv_LCcorrect = None

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
                'lampda_opt': True,     # Perform optimal lambda selection or not
                'PlotFig': True,        # Plot the L-curve or not
            },
            # Tikonov regularization
            'DRT': {
                'Lambda_selection': 'Manual',  # Lambda selection method, including 'Manual' and 'Optimal'
                'Lambda': 5e-5,                # Regularization parameter
                'tknv_legend': None,           # Legend for Tikhonov regularization plot
                'DRT_switch': True,            # Switch on Tikhonov regularization or not
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
    def lambdaOPT(self, EIS_data):
        parameter = self.parameter['LambdaOpt']
        self.lambda_opt = fn.LambdaOPT(EIS_data, parameter)
        print(f"---- Optimal lambda value: {self.lambda_opt}")

    def tknv(self):
        # Start timing the Tikhonov regularization process
        start_time = time.time()

        # Perform Tikhonov regularization on truncated data
        self.tknv_truncated = fn.DRT_tikhonov(self.truncated, self.parameter['DRT'])

        # Perform Tikhonov regularization on smoothed data
        self.tknv_smooth = fn.DRT_tikhonov(self.smooth, self.parameter['DRT'])

        # Perform Tikhonov regularization on extrapolated data
        self.tknv_extrapolation = fn.DRT_tikhonov(self.extrapolation, self.parameter['DRT'])

        # Perform Tikhonov regularization on L/C corrected data
        self.tknv_LCcorrect = fn.DRT_tikhonov(self.LCcorrect, self.parameter['DRT'])

        # Calculate and print the total execution time
        elapsed_time = time.time() - start_time
        print(f"---- Tikhonov regularization completed in {elapsed_time:.2f} seconds.")
    
    # Functions for data plotting
    def KK_plot(self, figure_name = ''):
        """
        Plot residuals of KK analysis
        """
        cmap = plt.cm.get_cmap(plt.rcParams['image.cmap'])
        plt.figure('KK_results -- '+figure_name)
        plt.semilogx(self.KK_data['f'], self.KK_data['delta_Re_kk'], '-o', label='Residual Re', color=cmap(0.2))  # Linear KK real
        plt.semilogx(self.KK_data['f'], self.KK_data['delta_Im_kk'], '-o', label='Residual Im', color=cmap(0.8))  # Linear KK imag
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
                plt.plot(self.truncated['Re'], -self.truncated['Im'], '-', label='Truncated', color=cmap(0.2))
                plt.plot(self.raw['Re'], -self.raw['Im'], 'o', markerfacecolor='none', label='Original', color=cmap(0.8))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Re':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.truncated['f'], self.truncated['Re'], '-', label='Truncated', color=cmap(0.2))
                plt.semilogx(self.raw['f'], self.raw['Re'], 'o', markerfacecolor='none', label='Original', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Im':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.truncated['f'], -self.truncated['Im'], '-', label='Truncated', color=cmap(0.2))
                plt.semilogx(self.raw['f'], -self.raw['Im'], 'o', markerfacecolor='none', label='Original', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'ReIm_LC':
                plt.figure(plot_type + '--' + figure_name)
                plt.plot(self.LCcorrect['Re'], -self.LCcorrect['Im'], '-', label='Corrected', color=cmap(0.2))
                plt.plot(self.truncated['Re'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Re_LC':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.LCcorrect['f'], self.LCcorrect['Re'], '-', label='Corrected', color=cmap(0.2))
                plt.semilogx(self.truncated['f'], self.truncated['Re'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Im_LC':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.LCcorrect['f'], -self.LCcorrect['Im'], '-', label='Corrected', color=cmap(0.2))
                plt.semilogx(self.truncated['f'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Re_s':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.smooth['f'], self.smooth['Re'], '-', label='Smoothed', color=cmap(0.2))
                plt.semilogx(self.truncated['f'], self.truncated['Re'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Im_s':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.smooth['f'], -self.smooth['Im'], '-', label='Smoothed', color=cmap(0.2))
                plt.semilogx(self.truncated['f'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'ReIm_s':
                plt.figure(plot_type + '--' + figure_name)
                plt.plot(self.smooth['Re'], -self.smooth['Im'], '-', label='Smoothed', color=cmap(0.2))
                plt.plot(self.truncated['Re'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Re_e':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.extrapolation['f'], self.extrapolation['Re'], '-', label='Extrapolated', color=cmap(0.2))
                plt.semilogx(self.truncated['f'], self.truncated['Re'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Im_e':
                plt.figure(plot_type + '--' + figure_name)
                plt.semilogx(self.extrapolation['f'], -self.extrapolation['Im'], '-', label='Extrapolated', color=cmap(0.2))
                plt.semilogx(self.truncated['f'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'ReIm_e':
                plt.figure(plot_type + '--' + figure_name)
                plt.plot(self.extrapolation['Re'], -self.extrapolation['Im'], '-', label='Extrapolated', color=cmap(0.2))
                plt.plot(self.truncated['Re'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop

    def DRT_plot(self, plot_type, figure_name = ''):
        """
        Plot Tikhonov regularization results based on the specified type.
        """
        cmap = plt.cm.get_cmap(plt.rcParams['image.cmap'])
        plt.figure(plot_type)
        if plot_type == 'Im':
            plt.semilogx(self.tknv_truncated['Im']['f'], self.tknv_truncated['Im']['g'], linewidth=3, label=f"TKNV_Im - {figure_name.replace('_', ' ')}")
        elif plot_type == 'Im_s':
            plt.semilogx(self.tknv_smooth['Im']['f'], self.tknv_smooth['Im']['g'], linewidth=3, label=f"TKNV_Im_s - {figure_name.replace('_', ' ')}")
        elif plot_type == 'Im_e':
            plt.semilogx(self.tknv_extrapolation['Im']['f'], self.tknv_extrapolation['Im']['g'], linewidth=3, label=f"TKNV_Im_e - {figure_name.replace('_', ' ')}")
        elif plot_type == 'Im_crct':
            plt.semilogx(self.tknv_LCcorrect['Im']['f'], self.tknv_LCcorrect['Im']['g'], linewidth=3, label=f"TKNV_Im_crct - {figure_name.replace('_', ' ')}")
        elif plot_type == 'Re':
            plt.semilogx(self.tknv_truncated['Re']['f'], self.tknv_truncated['Re']['g'], linewidth=3, label=f"TKNV_Re - {figure_name.replace('_', ' ')}")
        elif plot_type == 'Re_s':
            plt.semilogx(self.tknv_smooth['Re']['f'], self.tknv_smooth['Re']['g'], linewidth=3, label=f"TKNV_Re_s - {figure_name.replace('_', ' ')}")
        elif plot_type == 'Re_e':
            plt.semilogx(self.tknv_extrapolation['Re']['f'], self.tknv_extrapolation['Re']['g'], linewidth=3, label=f"TKNV_Re_e - {figure_name.replace('_', ' ')}")
        elif plot_type == 'Re_crct':
            plt.semilogx(self.tknv_LCcorrect['Re']['f'], self.tknv_LCcorrect['Re']['g'], linewidth=3, label=f"TKNV_Re_crct - {figure_name.replace('_', ' ')}")
        elif plot_type == 'ReIm':
            plt.semilogx(self.tknv_truncated['ReIm']['f'], self.tknv_truncated['ReIm']['g'], linewidth=3, label=f"TKNV_ReIm - {figure_name.replace('_', ' ')}")
        elif plot_type == 'ReIm_s':
            plt.semilogx(self.tknv_smooth['ReIm']['f'], self.tknv_smooth['ReIm']['g'], linewidth=3, label=f"TKNV_ReIm_s - {figure_name.replace('_', ' ')}")
        elif plot_type == 'ReIm_e':
            plt.semilogx(self.tknv_extrapolation['ReIm']['f'], self.tknv_extrapolation['ReIm']['g'], linewidth=3, label=f"TKNV_ReIm_e - {figure_name.replace('_', ' ')}")
        elif plot_type == 'ReIm_crct':
            plt.semilogx(self.tknv_LCcorrect['ReIm']['f'], self.tknv_LCcorrect['ReIm']['g'], linewidth=3, label=f"TKNV_ReIm_crct - {figure_name.replace('_', ' ')}")
        else:
            print("[Error] Invalid TKNV type specified!")
            return

        plt.xlabel('Frequency [Hz]')
        plt.ylabel(r'$\gamma \, [\Omega \cdot cm^2 \cdot s]$')
        plt.legend()
        plt.xlim([1e-2, 1e6])
        plt.ylim(bottom=0)  # Set y-axis to start from 0
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)  # Add subgrid for each decade
        plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop

    def DRT_EIS_plot(self, EIS_list, figure_name = ''):
        cmap = plt.cm.get_cmap(plt.rcParams['image.cmap'])
        for plot_type in EIS_list:
            if plot_type == 'ReIm':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.plot(self.tknv_truncated['Re']['Re'], -self.tknv_truncated['Re']['Im'], '-', label='DRT-Truncated', color=cmap(0.2))
                plt.plot(self.truncated['Re'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Re':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.semilogx(self.tknv_truncated['Re']['f'], self.tknv_truncated['Re']['Re'], '-', label='DRT-Truncated', color=cmap(0.2))
                plt.semilogx(self.truncated['f'], self.truncated['Re'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Im':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.semilogx(self.tknv_truncated['Im']['f'], -self.tknv_truncated['Im']['Im'], '-', label='DRT-Truncated', color=cmap(0.2))
                plt.semilogx(self.truncated['f'], -self.truncated['Im'], 'o', markerfacecolor='none', label='Truncated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'ReIm_LC':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.plot(self.tknv_LCcorrect['Re']['Re'], -self.tknv_LCcorrect['Re']['Im'], '-', label='DRT-Corrected', color=cmap(0.2))
                plt.plot(self.LCcorrect['Re'], -self.LCcorrect['Im'], 'o', markerfacecolor='none', label='Corrected', color=cmap(0.8))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Re_LC':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.semilogx(self.tknv_LCcorrect['Re']['f'], self.tknv_LCcorrect['Re']['Re'], '-', label='DRT-Corrected', color=cmap(0.2))
                plt.semilogx(self.LCcorrect['f'], self.LCcorrect['Re'], 'o', markerfacecolor='none', label='Corrected', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Im_LC':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.semilogx(self.tknv_LCcorrect['Im']['f'], -self.tknv_LCcorrect['Im']['Im'], '-', label='DRT-Corrected', color=cmap(0.2))
                plt.semilogx(self.LCcorrect['f'], -self.LCcorrect['Im'], 'o', markerfacecolor='none', label='Corrected', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Re_s':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.semilogx(self.tknv_smooth['Re']['f'], self.tknv_smooth['Re']['Re'], '-', label='DRT-Smoothed', color=cmap(0.2))
                plt.semilogx(self.smooth['f'], self.smooth['Re'], 'o', markerfacecolor='none', label='Smoothed', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Im_s':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.semilogx(self.tknv_smooth['Im']['f'], -self.tknv_smooth['Im']['Im'], '-', label='DRT-Smoothed', color=cmap(0.2))
                plt.semilogx(self.smooth['f'], -self.smooth['Im'], 'o', markerfacecolor='none', label='Smoothed', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'ReIm_s':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.plot(self.tknv_smooth['Re']['Re'], -self.tknv_smooth['Re']['Im'], '-', label='DRT-Smoothed', color=cmap(0.2))
                plt.plot(self.smooth['Re'], -self.smooth['Im'], 'o', markerfacecolor='none', label='Smoothed', color=cmap(0.8))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Re_e':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.semilogx(self.tknv_extrapolation['Re']['f'], self.tknv_extrapolation['Re']['Re'], '-', label='DRT-Extrapolated', color=cmap(0.2))
                plt.semilogx(self.extrapolation['f'], self.extrapolation['Re'], 'o', markerfacecolor='none', label='Extrapolated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'Im_e':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.semilogx(self.tknv_extrapolation['Im']['f'], -self.tknv_extrapolation['Im']['Im'], '-', label='DRT-Extrapolated', color=cmap(0.2))
                plt.semilogx(self.extrapolation['f'], -self.extrapolation['Im'], 'o', markerfacecolor='none', label='Extrapolated', color=cmap(0.8))
                plt.xlabel('f [Hz]')
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop
            elif plot_type == 'ReIm_e':
                plt.figure('DRT' + plot_type + '--' + figure_name)
                plt.plot(self.tknv_extrapolation['Re']['Re'], -self.tknv_extrapolation['Re']['Im'], '-', label='DRT-Extrapolated', color=cmap(0.2))
                plt.plot(self.extrapolation['Re'], -self.extrapolation['Im'], 'o', markerfacecolor='none', label='Extrapolated', color=cmap(0.8))
                plt.xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.grid(True)
                plt.legend()
                plt.gca().set_aspect('equal', adjustable='box')
                plt.gcf().canvas.draw()  # Ensure the plot updates when called in a loop

    # Functions for saving data
    def save_data(self):
        """
        Save EIS and DRT data to Excel files.

        Parameters:
        - EIS: An object containing EIS and DRT data, following the structure defined in DRT.py.
        """
        # Define file paths
        ext_save = '.xlsx'
        folder_eis = os.path.join(self.file_folder, 'EIS')
        folder_drt = os.path.join(self.file_folder, 'DRT')
        eis_file = os.path.join(folder_eis, f"{self.filename}{ext_save}")
        drt_file = os.path.join(folder_drt, f"{self.filename}{ext_save}")

        # Ensure directories exist
        os.makedirs(folder_eis, exist_ok=True)
        os.makedirs(folder_drt, exist_ok=True)

        # Remove existing files
        if os.path.exists(eis_file):
            os.remove(eis_file)
            print(f"---- {eis_file}: already existed, deleted and created a new one.")
        if os.path.exists(drt_file):
            os.remove(drt_file)
            print(f"---- {drt_file}: already existed, deleted and created a new one.")

        # Save EIS data
        print("---- Saving EIS data...")
        with pd.ExcelWriter(eis_file, engine='openpyxl') as writer:
            # Info of measurement
            if self.info is not None:
                # Convert self.info to a DataFrame if it's not already
                if not isinstance(self.info, pd.DataFrame):
                    self.info = pd.DataFrame([self.info])
                self.info.to_excel(writer, sheet_name='Info of measurement', index=False)

            # Original data
            pd.DataFrame({
                'Frequency/Hz': self.raw['f'],
                'Re/ohm·cm2': self.raw['Re'],
                'Im/ohm·cm2': self.raw['Im'],
            }).to_excel(writer, sheet_name='Original', index=False)

            # Truncated data
            pd.DataFrame({
                'Frequency/Hz': self.truncated['f'],
                'Re/ohm·cm2': self.truncated['Re'],
                'Im/ohm·cm2': self.truncated['Im']
            }).to_excel(writer, sheet_name='Truncated', index=False)

            # LC corrected data
            pd.DataFrame({
                'Frequency/Hz': self.LCcorrect['f'],
                'Re/ohm·cm2': self.LCcorrect['Re'],
                'Im/ohm·cm2': self.LCcorrect['Im']
            }).to_excel(writer, sheet_name='LC corrected', index=False)

            # Linear Kramers-Kronig data
            pd.DataFrame({
                'Frequency/Hz': self.KK_data['f'],
                'Re/ohm·cm2': self.KK_data['Re'],
                'Im/ohm·cm2': self.KK_data['Im'],
                'dr_kkl': self.KK_data['delta_Re_kk'],
                'di_kkl': self.KK_data['delta_Im_kk']
            }).to_excel(writer, sheet_name='Linear Kramers-Kroning', index=False)

            # Smoothed data
            pd.DataFrame({
                'Frequency/Hz': self.smooth['f'],
                'Re/ohm·cm2': self.smooth['Re'],
                'Im/ohm·cm2': self.smooth['Im']
            }).to_excel(writer, sheet_name='Smooth', index=False)

            # Extrapolated data
            pd.DataFrame({
                'Frequency/Hz': self.extrapolation['f'],
                'Re/ohm·cm2': self.extrapolation['Re'],
                'Im/ohm·cm2': self.extrapolation['Im']
            }).to_excel(writer, sheet_name='Extended', index=False)

            # Resistance data
            pd.DataFrame({
                'Rohm/ohm·cm2 - KK': self.KK_data['res_ohm_kk'],
                'Rp/ohm·cm2 - KK': self.KK_data['res_pol_kk'],
                'L/ohm·cm2 - DRT_Re': self.tknv_truncated['RL']['L_Re'],
                'Rohm/ohm·cm2 - DRT_Re': self.tknv_truncated['RL']['Rs_Re'],
                'Rp/ohm·cm2 - DRT_Re': self.tknv_truncated['RL']['Rp_Re'],
                'L/ohm·cm2 - DRT_Im': self.tknv_truncated['RL']['L_Im'],
                'Rohm/ohm·cm2 - DRT_Im': self.tknv_truncated['RL']['Rs_Im'],
                'Rp/ohm·cm2 - DRT_Im': self.tknv_truncated['RL']['Rp_Im'],
                'L/ohm·cm2 - DRT_ReIm': self.tknv_truncated['RL']['L_ReIm'],
                'Rohm/ohm·cm2 - DRT_ReIm': self.tknv_truncated['RL']['Rs_ReIm'],
                'Rp/ohm·cm2 - DRT_ReIm': self.tknv_truncated['RL']['Rp_ReIm']
            }).to_excel(writer, sheet_name='Resistance', index=False)

        print("-- EIS data saved.")

        # Save DRT data
        print("---- Saving DRT data...")
        with pd.ExcelWriter(drt_file, engine='openpyxl') as writer:
            # Info of measurement
            if self.info is not None:
                # Convert self.info to a DataFrame if it's not already
                if not isinstance(self.info, pd.DataFrame):
                    self.info = pd.DataFrame([self.info])
                self.info.to_excel(writer, sheet_name='Info of measurement', index=False)

            # DRT parameters
            pd.DataFrame({
                'Nfh_cut': [self.parameter['Preprocessing']['num_cut_upper']],
                'Nfl_cut': [self.parameter['Preprocessing']['num_cut_lower']],
                'fl': [min(self.truncated['f'])],
                'fh': [max(self.truncated['f'])],
                'lambda': [self.parameter['DRT']['Lambda']],
                'CellArea/cm2': [self.parameter['Sample']['CellArea']]
            }).to_excel(writer, sheet_name='DRT_Parameters', index=False)

            # Tikhonov regularization data
            if hasattr(self, 'tknv_truncated') and self.tknv_truncated is not None:
                pd.DataFrame({
                    'Frequency/Hz': self.tknv_truncated['Re']['f'],
                    'gamma/ohm·s·cm2': self.tknv_truncated['Re']['g'],
                    'Re/ohm·cm2': self.tknv_truncated['Re']['Re'],
                    'Im/ohm·cm2': self.tknv_truncated['Re']['Im'],
                    'Residuals': self.tknv_truncated['Re']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_Re', index=False)

                pd.DataFrame({
                    'Frequency/Hz': self.tknv_truncated['Im']['f'],
                    'gamma/ohm·s·cm2': self.tknv_truncated['Im']['g'],
                    'Re/ohm·cm2': self.tknv_truncated['Im']['Re'],
                    'Im/ohm·cm2': self.tknv_truncated['Im']['Im'],
                    'Residuals': self.tknv_truncated['Im']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_Im', index=False)

                pd.DataFrame({
                    'Frequency/Hz': self.tknv_truncated['ReIm']['f'],
                    'gamma/ohm·s·cm2': self.tknv_truncated['ReIm']['g'],
                    'Re/ohm·cm2': self.tknv_truncated['ReIm']['Re'],
                    'Im/ohm·cm2': self.tknv_truncated['ReIm']['Im'],
                    'Residuals': self.tknv_truncated['ReIm']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_ReIm', index=False)

            # Smoothed Tikhonov regularization data
            if hasattr(self, 'tknv_smooth') and self.tknv_smooth is not None:
                pd.DataFrame({
                    'Frequency/Hz': self.tknv_smooth['Re']['f'],
                    'gamma/ohm·s·cm2': self.tknv_smooth['Re']['g'],
                    'Re/ohm·cm2': self.tknv_smooth['Re']['Re'],
                    'Im/ohm·cm2': self.tknv_smooth['Re']['Im'],
                    'Residuals': self.tknv_smooth['Re']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_Re_s', index=False)

                pd.DataFrame({
                    'Frequency/Hz': self.tknv_smooth['Im']['f'],
                    'gamma/ohm·s·cm2': self.tknv_smooth['Im']['g'],
                    'Re/ohm·cm2': self.tknv_smooth['Im']['Re'],
                    'Im/ohm·cm2': self.tknv_smooth['Im']['Im'],
                    'Residuals': self.tknv_smooth['Im']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_Im_s', index=False)

                pd.DataFrame({
                    'Frequency/Hz': self.tknv_smooth['ReIm']['f'],
                    'gamma/ohm·s·cm2': self.tknv_smooth['ReIm']['g'],
                    'Re/ohm·cm2': self.tknv_smooth['ReIm']['Re'],
                    'Im/ohm·cm2': self.tknv_smooth['ReIm']['Im'],
                    'Residuals': self.tknv_smooth['ReIm']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_ReIm_s', index=False)

            # Extrapolated Tikhonov regularization data
            if hasattr(self, 'tknv_extrapolation') and self.tknv_extrapolation is not None:
                pd.DataFrame({
                    'Frequency/Hz': self.tknv_extrapolation['Re']['f'],
                    'gamma/ohm·s·cm2': self.tknv_extrapolation['Re']['g'],
                    'Re/ohm·cm2': self.tknv_extrapolation['Re']['Re'],
                    'Im/ohm·cm2': self.tknv_extrapolation['Re']['Im'],
                    'Residuals': self.tknv_extrapolation['Re']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_Re_e', index=False)

                pd.DataFrame({
                    'Frequency/Hz': self.tknv_extrapolation['Im']['f'],
                    'gamma/ohm·s·cm2': self.tknv_extrapolation['Im']['g'],
                    'Re/ohm·cm2': self.tknv_extrapolation['Im']['Re'],
                    'Im/ohm·cm2': self.tknv_extrapolation['Im']['Im'],
                    'Residuals': self.tknv_extrapolation['Im']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_Im_e', index=False)

                pd.DataFrame({
                    'Frequency/Hz': self.tknv_extrapolation['ReIm']['f'],
                    'gamma/ohm·s·cm2': self.tknv_extrapolation['ReIm']['g'],
                    'Re/ohm·cm2': self.tknv_extrapolation['ReIm']['Re'],
                    'Im/ohm·cm2': self.tknv_extrapolation['ReIm']['Im'],
                    'Residuals': self.tknv_extrapolation['ReIm']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_ReIm_e', index=False)

            # L/C corrected Tikhonov regularization data
            if hasattr(self, 'tknv_LCcorrect') and self.tknv_LCcorrect is not None:
                pd.DataFrame({
                    'Frequency/Hz': self.tknv_LCcorrect['Re']['f'],
                    'gamma/ohm·s·cm2': self.tknv_LCcorrect['Re']['g'],
                    'Re/ohm·cm2': self.tknv_LCcorrect['Re']['Re'],
                    'Im/ohm·cm2': self.tknv_LCcorrect['Re']['Im'],
                    'Residuals': self.tknv_LCcorrect['Re']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_Re_crct', index=False)

                pd.DataFrame({
                    'Frequency/Hz': self.tknv_LCcorrect['Im']['f'],
                    'gamma/ohm·s·cm2': self.tknv_LCcorrect['Im']['g'],
                    'Re/ohm·cm2': self.tknv_LCcorrect['Im']['Re'],
                    'Im/ohm·cm2': self.tknv_LCcorrect['Im']['Im'],
                    'Residuals': self.tknv_LCcorrect['Im']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_Im_crct', index=False)

                pd.DataFrame({
                    'Frequency/Hz': self.tknv_LCcorrect['ReIm']['f'],
                    'gamma/ohm·s·cm2': self.tknv_LCcorrect['ReIm']['g'],
                    'Re/ohm·cm2': self.tknv_LCcorrect['ReIm']['Re'],
                    'Im/ohm·cm2': self.tknv_LCcorrect['ReIm']['Im'],
                    'Residuals': self.tknv_LCcorrect['ReIm']['Residuals']
                }).to_excel(writer, sheet_name='Tknv_ReIm_crct', index=False)
        print("-- DRT data saved.")