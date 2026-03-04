"""
DRT Class for Electrochemical Impedance Spectroscopy (EIS) Analysis

Purpose:
    This class is designed to perform EIS data analysis using methods such as Distribution of Relaxation Time (DRT), Kramers-Kronig (KK) analysis, Tikhonov regularization, and Fourier transform-based approaches.

Created by:
    Hangyu Yu, EPFL GEM, Switzerland
    Created date: 2025.02.12
    Last modified: 
"""
import src.Methods.DRT.Utils as fn
import numpy as np
import matplotlib.pyplot as plt
import time
import os
import zipfile
import pandas as pd
import traceback
from datetime import datetime

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
            'omega': None,             # Angular frequency data [rad/s]
            'tau': None                # Time constant data [s]
        }

        self.smooth = {
            'f': None,                 # Smoothed frequency data [Hz]
            'Z': None,                 # Smoothed impedance data [Ω*cm2]
            'Re': None,                # Smoothed real part of impedance data [Ω*cm2]
            'Im': None,                # Smoothed imaginary part of impedance data [Ω*cm2]
            'omega': None,             # Angular frequency data [rad/s]
            'tau': None,               # Time constant data [s]
        }

        self.extrapolation = {
            'f': None,                 # Extrapolated frequency data [Hz]
            'Z': None,                 # Extrapolated impedance data
            'Re': None,                # Extrapolated real part of impedance data [Ω*cm2]
            'Im': None,                # Extrapolated imaginary part of impedance data
            'omega': None,             # Angular frequency data [rad/s]
            'tau': None                # Time constant data [s]
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

        self.lambda_opt = None

        # Data treatment parameters
        self.parameter = {
            # Sample information
            'Sample' : {
                'CellArea': CellArea,  # SOC area [\mathrm{cm}^2]
                'n_cell': n_cell,        # Number of cells
                'instrument_type': "Zahner"  # Zahner or Biologic or others
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
                'rm_significance': False # Remove points with low significance
            },
            # Remove outliers
            'Rmoutliers': {
                'mv_window_size': 5,   # Moving window size for outlier removal
                'n_std': 5,            # Number of standard deviations for outlier removal
                'Rmoutliers': False    # Remove outliers from EIS data
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
                'lampda_opt': False,     # Perform optimal lambda selection or not
                'PlotFig': False,        # Plot the L-curve or not
            },
            # Tikonov regularization
            'DRT': {
                'Lambda_selection': 'Manual',  # Lambda selection method, including 'Manual' and 'Optimal'
                'tknv_pos': False,          # Tikhonov positive method, including 'Manual' and 'Optimal'
                'lambda': 5e-4,                # Regularization parameter
                'tknv_legend': None,           # Legend for Tikhonov regularization plot
                'DRT_switch': True,            # Switch on Tikhonov regularization or not
            },
            # Manual cut
            'ManualRemoval': {
                'enable': False,              # Enable manual removal of data points
                'indices': []                 # Indices of data points to be removed (1-based)
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
        print("---- Cutting finished. Raw data points -", len(self.raw['f']), ", truncated data points -", len(self.truncated['f']))
        
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
            NotKK.iloc[0] = False
            NotKK.iloc[-1] = False
            for i in self.truncated.keys():
                if self.truncated[i] is not None and self.truncated[i] is not []:
                    self.truncated[i] = np.delete(self.truncated[i], np.where(NotKK))
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

    def tknv_pos(self):
        # Start timing the Tikhonov regularization process
        start_time = time.time()

        # Perform Tikhonov regularization on truncated data
        self.tknv_truncated = fn.DRT_tknv_pos(self.truncated, self.parameter['DRT'])

        # Perform Tikhonov regularization on smoothed data
        self.tknv_smooth = fn.DRT_tknv_pos(self.smooth, self.parameter['DRT'])

        # Perform Tikhonov regularization on extrapolated data
        self.tknv_extrapolation = fn.DRT_tknv_pos(self.extrapolation, self.parameter['DRT'])

        # Perform Tikhonov regularization on L/C corrected data
        self.tknv_LCcorrect = fn.DRT_tknv_pos(self.LCcorrect, self.parameter['DRT'])

        # Calculate and print the total execution time
        elapsed_time = time.time() - start_time
        print(f"---- Tikhonov positive regularization completed in {elapsed_time:.2f} seconds.")
    
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
                plt.xlabel(r"$\mathrm{Z}' \, [\Omega\cdot \mathrm{cm}^2]$")
                plt.ylabel(r"$\mathrm{-Z}'' \, [\Omega\cdot \mathrm{cm}^2]$")
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
    def backup_folder_to_temp_zip(self, folder_name, zip_name):
        """
        Backup one target folder as a zip file into temp folder.
        """
        if self.file_folder is None:
            print("[Warning] file_folder is None, skip folder backup.")
            return None

        base_folder = os.path.abspath(self.file_folder)
        folder_path = os.path.join(base_folder, folder_name)
        if not os.path.isdir(folder_path):
            print(f"---- {folder_name} folder not found, skip backup.")
            return None

        temp_folder = os.path.join(base_folder, 'temp')
        os.makedirs(temp_folder, exist_ok=True)
        
        # Delete old backup files with the same prefix
        name_without_ext, ext = os.path.splitext(zip_name)
        pattern = f"{name_without_ext}_*{ext}"
        old_backups = [f for f in os.listdir(temp_folder) if f.startswith(f"{name_without_ext}_") and f.endswith(ext)]
        for old_backup in old_backups:
            old_backup_path = os.path.join(temp_folder, old_backup)
            try:
                os.remove(old_backup_path)
                print(f"---- Deleted old backup: {old_backup}")
            except Exception as e:
                print(f"[Warning] Failed to delete {old_backup}: {e}")
        
        # Add timestamp to zip filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name_with_timestamp = f"{name_without_ext}_{timestamp}{ext}"
        zip_path = os.path.join(temp_folder, zip_name_with_timestamp)

        with zipfile.ZipFile(zip_path, mode='w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(folder_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    rel_path = os.path.relpath(file_path, start=folder_path)
                    arcname = os.path.join(folder_name, rel_path)
                    zipf.write(file_path, arcname=arcname)

        print(f"---- Backup created: {zip_path}")
        return zip_path

    def save_data_EIS(self):
        """
        Save EIS data to an Excel file.
        """

        # Define file path
        ext_save = '.xlsx'
        folder_eis = os.path.join(self.file_folder, 'EIS')
        eis_file = os.path.join(folder_eis, f"{os.path.splitext(self.filename)[0]}{ext_save}")

        # Ensure directory exists
        os.makedirs(folder_eis, exist_ok=True)

        # Remove existing file
        if os.path.exists(eis_file):
            os.remove(eis_file)
            print(f"---- {eis_file}: already existed, deleted and created a new one.")

        # Save EIS data
        print("---- Saving EIS data...")
        with pd.ExcelWriter(eis_file, engine='openpyxl') as writer:
            # Info of measurement
            if self.info is not None:
                # Convert self.info to a DataFrame if it's not already
                if not isinstance(self.info, pd.DataFrame):
                    self.info = pd.DataFrame([self.info])
                self.info.to_excel(writer, sheet_name='Info of measurement', index=False)

            # EIS parameters
            pd.DataFrame({
                'Nfh_cut': [self.parameter['Preprocessing']['num_cut_upper']],
                'Nfl_cut': [self.parameter['Preprocessing']['num_cut_lower']],
                'num_cut_middle': [self.parameter['Preprocessing']['num_cut_middle']],
                'sig_threshold': [self.parameter['RM_significance']['sig_threshold']],
                'rm_significance': [self.parameter['RM_significance']['rm_significance']],
                'mv_window_size': [self.parameter['Rmoutliers']['mv_window_size']],
                'n_std': [self.parameter['Rmoutliers']['n_std']],
                'Rmoutliers': [self.parameter['Rmoutliers']['Rmoutliers']],
                'nRCmax': [self.parameter['KK']['nRCmax']],
                'kk_threshold': [self.parameter['KK']['kk_threshold']],
                'mu_threshold': [self.parameter['KK']['mu_threshold']],
                'KK_type': [self.parameter['KK']['KK_type']],
                'nRC': [self.parameter['KK']['nRC']],
                'KK_test': [self.parameter['KK']['KK_test']],
                'RmNonKK': [self.parameter['KK']['RmNonKK']],
                'fmin_smoothing': [self.parameter['Smoothing']['fmin']],
                'fmax_smoothing': [self.parameter['Smoothing']['fmax']],
                'PointsPerDecade_smoothing': [self.parameter['Smoothing']['PointsPerDecade']],
                'fmin_extrapolation': [self.parameter['Extrapolation']['fmin']],
                'fmax_extrapolation': [self.parameter['Extrapolation']['fmax']],
                'PointsPerDecade_extrapolation': [self.parameter['Extrapolation']['PointsPerDecade']],
                'lambda_min': [self.parameter['LambdaOpt']['lambda_min']],
                'lambda_max': [self.parameter['LambdaOpt']['lambda_max']],
                'lambda_n': [self.parameter['LambdaOpt']['n']],
                'lampda_opt': [self.parameter['LambdaOpt']['lampda_opt']],
                'PlotFig': [self.parameter['LambdaOpt']['PlotFig']],
                'Lambda_selection': [self.parameter['DRT']['Lambda_selection']],
                'lambda': [self.parameter['DRT']['lambda']],
                'tknv_legend': [self.parameter['DRT']['tknv_legend']],
                'DRT_switch': [self.parameter['DRT']['DRT_switch']],
                'CellArea/cm2': [self.parameter['Sample']['CellArea']],
                'n_cell': [self.parameter['Sample']['n_cell']],
                'instrument_type': [self.parameter['Sample']['instrument_type']],
                'ManualRemoval': [self.parameter['ManualRemoval']['enable']],
                'ManualRemoval_Indices': [','.join(map(str, [i+1 for i in self.parameter['ManualRemoval']['indices']])) if self.parameter['ManualRemoval']['indices'] else '']
            }).to_excel(writer, sheet_name='EIS_Parameters', index=False)

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
                'L/H·cm2 - KK': self.KK_data['L_kk'],
                'C/C·cm-2 - KK': self.KK_data['C_kk'],
                'Rohm/ohm·cm2 - KK': self.KK_data['res_ohm_kk'],
                'Rp/ohm·cm2 - KK': self.KK_data['res_pol_kk'],
            }).to_excel(writer, sheet_name='Resistance', index=False)

        print(f"-- EIS data saved for {self.filename}.")

    def save_data_DRT(self):
        """
        Save DRT data to an Excel file.
        """
        self.backup_folder_to_temp_zip('DRT', 'DRT_old.zip')

        # Define file path
        ext_save = '.xlsx'
        folder_drt = os.path.join(self.file_folder, 'DRT')
        drt_file = os.path.join(folder_drt, f"{os.path.splitext(self.filename)[0]}{ext_save}")

        # Ensure directory exists
        os.makedirs(folder_drt, exist_ok=True)

        # Remove existing file
        if os.path.exists(drt_file):
            os.remove(drt_file)
            print(f"---- {drt_file}: already existed, deleted and created a new one.")

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
                'lambda': [self.parameter['DRT']['lambda']],
                'tknv_pos': [self.parameter['DRT']['tknv_pos']],
                'Lambda_selection': [self.parameter['DRT']['Lambda_selection']],
                'tknv_legend': [self.parameter['DRT']['tknv_legend']],
                'DRT_switch': [self.parameter['DRT']['DRT_switch']],
                'lambda_min': [self.parameter['LambdaOpt']['lambda_min']],
                'lambda_max': [self.parameter['LambdaOpt']['lambda_max']],
                'lambda_n': [self.parameter['LambdaOpt']['n']],
                'lampda_opt': [self.parameter['LambdaOpt']['lampda_opt']],
                'PlotFig': [self.parameter['LambdaOpt']['PlotFig']]
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

                for data_cat in ['truncated', 'smooth', 'extrapolation', 'LCcorrect']:
                    pd.DataFrame({
                        'L/ohm·cm2 - DRT_Re': [self['tknv_'+data_cat]['RL']['L_Re']],
                        'Rohm/ohm·cm2 - DRT_Re': [self['tknv_'+data_cat]['RL']['Rs_Re']],
                        'Rp/ohm·cm2 - DRT_Re': [self['tknv_'+data_cat]['RL']['Rp_Re']],
                        'L/ohm·cm2 - DRT_Im': [self['tknv_'+data_cat]['RL']['L_Im']],
                        'Rohm/ohm·cm2 - DRT_Im': [self['tknv_'+data_cat]['RL']['Rs_Im']],
                        'Rp/ohm·cm2 - DRT_Im': [self['tknv_'+data_cat]['RL']['Rp_Im']],
                        'L/ohm·cm2 - DRT_ReIm': [self['tknv_'+data_cat]['RL']['L_ReIm']],
                        'Rohm/ohm·cm2 - DRT_ReIm': [self['tknv_'+data_cat]['RL']['Rs_ReIm']],
                        'Rp/ohm·cm2 - DRT_ReIm': [self['tknv_'+data_cat]['RL']['Rp_ReIm']]
                    }).to_excel(writer, sheet_name='Resistance_'+data_cat, index=False)

        print(f"-- DRT data saved for {self.filename}.")

    # Function for import data
    def import_data_EIS(self):
        """
        Import EIS data from Excel file.
        
        Returns:
        - True if import was successful, False otherwise
        """
        if self.filename is None:
            print("[Error] No filename specified!")
            return False
            
        file_to_import = os.path.splitext(self.filename)[0]
        folder_eis = os.path.join(self.file_folder, 'EIS')
        eis_file = os.path.join(folder_eis, f"{file_to_import}.xlsx")
        
        if not os.path.exists(eis_file):
            print(f"[Error] EIS file not found: {eis_file}")
            return False
        
        try:
            print(f"-- Importing EIS data from {eis_file}...")
            
            # Import info of measurement
            try:
                self.info = pd.read_excel(eis_file, sheet_name='Info of measurement')
            except:
                print("---- No 'Info of measurement' sheet found")

            # Import EIS parameters with default values for missing/empty fields
            try:
                eis_params = pd.read_excel(eis_file, sheet_name='EIS_Parameters')
                
                # Helper function to safely get values with defaults
                def safe_get(column_name, default_value, dtype_func):
                    try:
                        value = eis_params[column_name].values[0]
                        # Check if value is NaN, None, or empty string
                        if pd.isna(value) or value is None or value == '':
                            return default_value
                        return dtype_func(value)
                    except (KeyError, IndexError):
                        return default_value
                
                # Apply safe_get for each parameter
                self.parameter['Preprocessing']['num_cut_upper'] = safe_get('Nfh_cut', 0, int)
                self.parameter['Preprocessing']['num_cut_lower'] = safe_get('Nfl_cut', 0, int)
                self.parameter['Preprocessing']['num_cut_middle'] = safe_get('num_cut_middle', 0, int)
                self.parameter['RM_significance']['sig_threshold'] = safe_get('sig_threshold', 0.995, float)
                self.parameter['RM_significance']['rm_significance'] = safe_get('rm_significance', True, bool)
                self.parameter['Rmoutliers']['mv_window_size'] = safe_get('mv_window_size', 5, int)
                self.parameter['Rmoutliers']['n_std'] = safe_get('n_std', 5, int)
                self.parameter['Rmoutliers']['Rmoutliers'] = safe_get('Rmoutliers', False, bool)
                self.parameter['KK']['nRCmax'] = safe_get('nRCmax', 50, int)
                self.parameter['KK']['kk_threshold'] = safe_get('kk_threshold', 1.0, float)
                self.parameter['KK']['mu_threshold'] = safe_get('mu_threshold', 0.85, float)
                self.parameter['KK']['KK_type'] = safe_get('KK_type', 'standard', str)
                self.parameter['KK']['nRC'] = safe_get('nRC', 80, int)
                self.parameter['KK']['KK_test'] = safe_get('KK_test', True, bool)
                self.parameter['KK']['RmNonKK'] = safe_get('RmNonKK', False, bool)
                self.parameter['Smoothing']['fmin'] = safe_get('fmin_smoothing', None, float)
                self.parameter['Smoothing']['fmax'] = safe_get('fmax_smoothing', None, float)
                self.parameter['Smoothing']['PointsPerDecade'] = safe_get('PointsPerDecade_smoothing', 30, int)
                self.parameter['Extrapolation']['fmin'] = safe_get('fmin_extrapolation', 1e-8, float)
                self.parameter['Extrapolation']['fmax'] = safe_get('fmax_extrapolation', 1e10, float)
                self.parameter['Extrapolation']['PointsPerDecade'] = safe_get('PointsPerDecade_extrapolation', 20, int)
                self.parameter['LambdaOpt']['lambda_min'] = safe_get('lambda_min', 1e-7, float)
                self.parameter['LambdaOpt']['lambda_max'] = safe_get('lambda_max', 0.2, float)
                self.parameter['LambdaOpt']['n'] = safe_get('lambda_n', 100, int)
                self.parameter['LambdaOpt']['lampda_opt'] = safe_get('lampda_opt', True, bool)
                self.parameter['LambdaOpt']['PlotFig'] = safe_get('PlotFig', False, bool)
                self.parameter['DRT']['Lambda_selection'] = safe_get('Lambda_selection', 'Manual', str)
                self.parameter['DRT']['tknv_pos'] = safe_get('tknv_pos', False, bool)
                self.parameter['DRT']['lambda'] = safe_get('lambda', 5e-4, float)
                self.parameter['DRT']['tknv_legend'] = safe_get('tknv_legend', None, str)
                self.parameter['DRT']['DRT_switch'] = safe_get('DRT_switch', True, bool)
                self.parameter['Sample']['CellArea'] = safe_get('CellArea/cm2', None, float)
                self.parameter['Sample']['n_cell'] = safe_get('n_cell', None, int)
                self.parameter['Sample']['instrument_type'] = safe_get('instrument_type', "Zahner", str)
                self.parameter['ManualRemoval']['enable'] = safe_get('ManualRemoval', False, bool)
                indices_str = safe_get('ManualRemoval_Indices', '', str)
                if indices_str and indices_str.strip():
                    try:
                        self.parameter['ManualRemoval']['indices'] = [int(x)-1 for x in indices_str.split(',') if x.strip()]
                    except ValueError:
                        self.parameter['ManualRemoval']['indices'] = []
                else:
                    self.parameter['ManualRemoval']['indices'] = []
                
            except Exception as e:
                print(f"---- No 'EIS_Parameters' sheet found or error reading parameters: {str(e)}")
            
            # 其余的数据导入代码保持不变...
            # Define all data import operations in a list for cleaner code
            import_operations = [
                ('Original', self.raw),
                ('Truncated', self.truncated),
                ('LC corrected', self.LCcorrect),
                ('Smooth', self.smooth),
                ('Extended', self.extrapolation)
            ]
            
            for sheet_name, target_dict in import_operations:
                try:
                    data = pd.read_excel(eis_file, sheet_name=sheet_name)
                    target_dict['f'] = data['Frequency/Hz'].values
                    target_dict['Re'] = data['Re/ohm·cm2'].values
                    target_dict['Im'] = data['Im/ohm·cm2'].values
                    target_dict['Z'] = target_dict['Re'] + 1j * target_dict['Im']
                    target_dict['omega'] = 2 * np.pi * target_dict['f']
                    target_dict['tau'] = 1 / target_dict['omega']
                except Exception as e:
                    print(f"---- Failed to import {sheet_name} sheet: {str(e)}")
            
            # Import KK data (has additional fields)
            try:
                kk_data = pd.read_excel(eis_file, sheet_name='Linear Kramers-Kroning')
                self.KK_data['f'] = kk_data['Frequency/Hz'].values
                self.KK_data['Re'] = kk_data['Re/ohm·cm2'].values
                self.KK_data['Im'] = kk_data['Im/ohm·cm2'].values
                self.KK_data['delta_Re_kk'] = kk_data['dr_kkl'].values
                self.KK_data['delta_Im_kk'] = kk_data['di_kkl'].values
                self.KK_data['omega'] = 2 * np.pi * self.KK_data['f']
                self.KK_data['tau'] = 1 / self.KK_data['omega']
            except Exception as e:
                print(f"---- Failed to import KK data: {str(e)}")
            
            # Import Resistance data
            try:
                resistance_data = pd.read_excel(eis_file, sheet_name='Resistance')
                self.KK_data['L_kk'] = resistance_data['L/H·cm2 - KK'].values if 'L/H·cm2 - KK' in resistance_data.columns else None
                self.KK_data['C_kk'] = resistance_data['C/C·cm-2 - KK'].values if 'C/C·cm-2 - KK' in resistance_data.columns else None
                self.KK_data['res_ohm_kk'] = resistance_data['Rohm/ohm·cm2 - KK'].values
                self.KK_data['res_pol_kk'] = resistance_data['Rp/ohm·cm2 - KK'].values
            except Exception as e:
                print(f"---- Failed to import resistance data: {str(e)}")
            
            print("---- EIS data import successful!")
            return True
            
        except Exception as e:
            print(f"[Error] Failed to import EIS data: {str(e)}")
            traceback.print_exc()
            return False

    def import_data_DRT(self):
        """Import DRT data from Excel in a single function."""
        try:
            # 1. Validate input file
            if self.filename is None:
                raise ValueError("No filename specified")
                
            file_to_import = os.path.splitext(self.filename)[0]
            folder_drt = os.path.join(self.file_folder, 'DRT')
            drt_file = os.path.join(folder_drt, f"{file_to_import}.xlsx")
            
            if not os.path.exists(drt_file):
                print(f"[Warning] DRT file not found: {drt_file}")

            print(f"-- Importing DRT data from {drt_file}...")
            
            # 2. Initialize data structure
            self.tknv_truncated = {'RL': {
                'Rs_Re': None, 'Rp_Re': None, 'L_Re': None,
                'Rs_Im': None, 'Rp_Im': None, 'L_Im': None,
                'Rs_ReIm': None, 'Rp_ReIm': None, 'L_ReIm': None
            }}
            self.tknv_smooth = {'RL': dict(self.tknv_truncated['RL'])}
            self.tknv_extrapolation = {'RL': dict(self.tknv_truncated['RL'])}
            self.tknv_LCcorrect = {'RL': dict(self.tknv_truncated['RL'])}
            
            # 3. Import parameter table
            try:
                drt_params = pd.read_excel(drt_file, sheet_name='DRT_Parameters')
                def safe_get(column_name, default_value, dtype_func):
                    try:
                        value = drt_params[column_name].values[0]
                        # Check if value is NaN, None, or empty string
                        if pd.isna(value) or value is None or value == '':
                            return default_value
                        return dtype_func(value)
                    except (KeyError, IndexError):
                        return default_value
                
                # Apply safe_get for each DRT parameter
                self.parameter['DRT']['lambda'] = safe_get('lambda', 5e-4, float)
                self.parameter['DRT']['tknv_pos'] = safe_get('tknv_pos', False, bool)
                self.parameter['DRT']['Lambda_selection'] = safe_get('Lambda_selection', 'Manual', str)
                self.parameter['DRT']['tknv_legend'] = safe_get('tknv_legend', None, str)  # 处理tknv_legend为空的情况
                self.parameter['DRT']['DRT_switch'] = safe_get('DRT_switch', True, bool)
                self.parameter['LambdaOpt']['lambda_min'] = safe_get('lambda_min', 1e-7, float)
                self.parameter['LambdaOpt']['lambda_max'] = safe_get('lambda_max', 0.2, float)
                self.parameter['LambdaOpt']['n'] = safe_get('lambda_n', 100, int)
                self.parameter['LambdaOpt']['lampda_opt'] = safe_get('lampda_opt', True, bool)
                self.parameter['LambdaOpt']['PlotFig'] = safe_get('PlotFig', False, bool)
            except Exception as e:
                print(f"---- Failed to import parameters: {str(e)}")
            
            # 4. Define data table mapping
            sheet_map = {
                ('Re', ''): ('Tknv_Re', 'truncated'),
                ('Im', ''): ('Tknv_Im', 'truncated'),
                ('ReIm', ''): ('Tknv_ReIm', 'truncated'),
                ('Re', 's'): ('Tknv_Re_s', 'smooth'),
                ('Im', 's'): ('Tknv_Im_s', 'smooth'),
                ('ReIm', 's'): ('Tknv_ReIm_s', 'smooth'),
                ('Re', 'e'): ('Tknv_Re_e', 'extrapolation'),
                ('Im', 'e'): ('Tknv_Im_e', 'extrapolation'),
                ('ReIm', 'e'): ('Tknv_ReIm_e', 'extrapolation'),
                ('Re', 'crct'): ('Tknv_Re_crct', 'LCcorrect'),
                ('Im', 'crct'): ('Tknv_Im_crct', 'LCcorrect'),
                ('ReIm', 'crct'): ('Tknv_ReIm_crct', 'LCcorrect')
            }
            
            # 5. Import all data tables
            for (data_type, suffix), (sheet_name, data_cat) in sheet_map.items():
                try:
                    # Get target dictionary
                    target_dict = getattr(self, f'tknv_{data_cat}')
                    
                    # Read data
                    tknv_data = pd.read_excel(drt_file, sheet_name=sheet_name)
                    
                    # Store data
                    if data_type not in target_dict:
                        target_dict[data_type] = {}
                    
                    target_dict[data_type]['f'] = tknv_data['Frequency/Hz'].values
                    target_dict[data_type]['g'] = tknv_data['gamma/ohm·s·cm2'].values
                    target_dict[data_type]['Re'] = tknv_data['Re/ohm·cm2'].values
                    target_dict[data_type]['Im'] = tknv_data['Im/ohm·cm2'].values
                    target_dict[data_type]['Residuals'] = tknv_data['Residuals'].values
                    
                    # Import resistance data
                    res_sheet = f'Resistance_{data_cat}'
                    resistance_data = pd.read_excel(drt_file, sheet_name=res_sheet)
                    prefix = data_type.replace('Im', 'Im').replace('ReIm', 'ReIm')
                    target_dict['RL'][f'L_{prefix}'] = resistance_data[f'L/ohm·cm2 - DRT_{prefix}'].values[0]
                    target_dict['RL'][f'Rs_{prefix}'] = resistance_data[f'Rohm/ohm·cm2 - DRT_{prefix}'].values[0]
                    target_dict['RL'][f'Rp_{prefix}'] = resistance_data[f'Rp/ohm·cm2 - DRT_{prefix}'].values[0]
                        
                except Exception as e:
                    print(f"---- Failed to import {sheet_name}: {str(e)}")

            print("---- DRT data import successful!")
            return True
            
        except Exception as e:
            print(f"[Error] DRT import failed: {str(e)}")
            traceback.print_exc()
            return False

        
    # Function to get data
    def __getitem__(self, key):
        """
        Get the data from the DRT class using the key
        """
        if key == 'raw':
            return self.raw
        elif key == 'truncated':
            return self.truncated
        elif key == 'LCcorrect':
            return self.LCcorrect
        elif key == 'smooth':
            return self.smooth
        elif key == 'extrapolation':
            return self.extrapolation
        elif key == 'KK_data':
            return self.KK_data
        elif key == 'tknv_truncated':
            return self.tknv_truncated
        elif key == 'tknv_smooth':
            return self.tknv_smooth
        elif key == 'tknv_extrapolation':
            return self.tknv_extrapolation
        elif key == 'tknv_LCcorrect':
            return self.tknv_LCcorrect
        elif key == 'parameter':
            return self.parameter
        else:
            raise KeyError(f"Key '{key}' not found in DRT class.")

