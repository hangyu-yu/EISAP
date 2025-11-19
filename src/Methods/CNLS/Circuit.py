import numpy as np
import pandas as pd
import scipy.optimize as opt
from scipy.stats import t
import matplotlib.pyplot as plt
import src.Methods.DRT.Utils as DRT_fn
import src.Methods.CNLS.Utils as CNLS_fn

import tkinter as tk
from tkinter import ttk
import os
import tkinter.font as tkFont

class Circuit:
    def __init__(self,file_folder=None, filename=None, Elements = None, EIS = None, data_type = None):
        """
        Initializes a new Circuit object with the specified elements and parameters.
        
        Parameters:
        ----------
        file_folder : str, optional
            Path to the folder containing the circuit data files.
        filename : str, optional
            Name of the file containing circuit data.
        Elements : list of dict, optional
            List of circuit elements, where each element is a dictionary containing:
                - 'name': str, identifier for the element
                - 'type': str, type of the element (e.g., 'Resistor', 'Capacitor')
                - 'Param': list, parameter values for the element
                - 'Ub': list, optional, upper bounds for parameters
                - 'Lb': list, optional, lower bounds for parameters
        
        Notes:
        ------
        Each element in the circuit is processed and stored with its parameters,
        bounds, and metadata for subsequent circuit evaluation and analysis.
        """
        self.file_folder = file_folder
        self.filename = filename

        # Initialize the circuit details
        if data_type is None:
            print('---- Data type not provided, data_type by default set as truncated.')
            self.data_type = 'truncated'
        else:
            self.data_type = data_type # Data type, smooth, truncated, extrapolation, etc.

        if EIS is None:
            self.DRTparameters = None # DRT parameters
            self.Zmes  = None # Measured impedance data
            self.DRTmes = None # Measured DRT data
            self.f = None # Frequency array
            self.w = None # Angular frequency array
            print('---- DRT parameters not provided, please define f, w, DRTmes, Zmes, and DRTparameters.')
        else:
            self.DRTparameters = EIS.parameter['DRT'] # DRT parameters
            if self.data_type == 'smooth_DRT':
                self.Zmes  = EIS['tknv_truncated']['ReIm']['Re'] + EIS['tknv_truncated']['ReIm']['Im']*1j # Measured impedance data
                self.DRTmes = EIS['tknv_truncated']['ReIm']['g'] # Measured DRT data
                self.f = EIS['tknv_truncated']['ReIm']['f'] # Frequency array
                self.w = self.f*(2*np.pi)    # Angular frequency array
            else:
                self.Zmes  = EIS[self.data_type.replace('_KK', '')]['Z'] # Measured impedance data
                self.DRTmes = EIS['tknv_' + self.data_type.replace('_KK', '')]['ReIm']['g'] # Measured DRT data
                self.f = EIS[self.data_type.replace('_KK', '')]['f'] # Frequency array
                self.w = self.f*(2*np.pi)    # Angular frequency array
        self.Ztot0 = None # Initial total impedance
        self.Z0    = None # Initial impedance for each angular frequency
        self.Ztot  = None # Total impedance of the circuit
        self.Z     = None # Impedance values for each angular frequency
        self.DRT   = None # DRT data
        self.ElementDRTs = None # DRT for each element
        self.store = {} # Store all the mess
        self.iteration = 5 # Number of iterations for the fit
        self.f_fixed = None # Fixed frequencies for peak identification
        self.f_mode = 'fixed'
        self.constraint_type = 'segment'
        
        # Initialize lists to store circuit elements configuration
        self.Elements = Elements     # List to store circuit elements
        self.ElementsNames = []      # List to store names of the circuit elements
        self.ElementsType = []       # List to store types of circuit elements (e.g., Resistor, Capacitor)
        self.ElementsStartIndex = [] # List to store starting indices of each element's parameters
        self.ElementsEndIndex = []   # List to store ending indices of each element's parameters
        self.ElementsNparam = []     # List to store number of parameters for each element

        # Initialize lists to store parameter information
        self.ElementsParamNames = [] # List to store parameter names for all elements
        self.ElementsParamValues = [] # List to store parameter values for all elements
        self.UpperBound = []         # List to store upper bounds for all parameters
        self.LowerBound = []         # List to store lower bounds for all parameters

        # Residual values and variance analysis
        self.ResidualsReal = None    # Residuals for the real part of the impedance
        self.ResidualsImag = None    # Residuals for the imaginary part of the impedance
        self.SumNormResiduals = None # Sum of the normalized residuals
        self.dof = None              # Degrees of freedom for the fit
        self.ElementsParamVariance = [] # List to store variance of parameters (for uncertainty quantification)
        self.ElementsParamStandardErrors = [] # List to store standard errors of parameters
        self.ElementsParamPValues = [] # List to store p-values for parameters (for statistical significance)
        self.FitSummary = None # DataFrame to store the fit summary

    # Function to initialize the circuit elements
    def initialize_elements(self, change_UBLB=True):
        # Initialize tracking indices for parameter positions
        StartIndex = 0              # Keeps track of the current parameter index
        counter = 0                 # Counter for element counting/naming

        # Define a mapping from element types to their corresponding parameter names
        element_param_map = {
            'Resistor': ['_R'],
            'Inductor': ['_L'],
            'Inductor_a': ['_L', '_alpha'],
            'Capacitor': ['_C'],
            'RC': ['_R', '_tau0'],
            'RQ': ['_R', '_tau0', '_alpha'],
            'Gerisher': ['_R', '_tau0'],
            'fFLW': ['_R', '_tau0', '_alpha'],
            'FLW': ['_R', '_tau0'],
            'RandleC': ['_R', '_C', '_R_W', '_tau0_W'],
            'RandleCPE': ['_R', '_Q', '_alpha_Q', '_R_W', '_tau0_W'],
            'RandleCPEfFLW': ['_R', '_Q', '_alpha_Q', '_R_W', '_tau0_W', 'alpha_W'],
            'RandleCfFLW': ['_R', '_C', '_R_W', '_tau0_W', 'alpha_W']
        }

        # Check for duplicate element names
        self.display_name = set()
        for element in self.Elements:
            if 'name' in element and element['name'] in self.display_name:
                raise ValueError(f"Duplicate element name found: {element['name']}")
            self.display_name.add(element.get('name', ''))
        
        # Check if the elements are imported
        if len(self.Elements) != 0:
            self.ElementsType = []
        if len(self.ElementsParamValues) != 0:
            self.ElementsParamValues = []
        if len(self.ElementsParamVariance) != 0:
            self.ElementsParamVariance = []
        if len(self.ElementsParamNames) != 0:
            self.ElementsParamNames = []
            self.ElementsNparam = []
        if len(self.LowerBound) != 0:
            self.LowerBound = []
            self.UpperBound = []
            self.ElementsStartIndex = []
            self.ElementsEndIndex = []

        # Iterate over the elements and assign parameter names
        for idx, element in enumerate(self.Elements):
            element_type = element['type']
            if element_type in element_param_map:
                param_suffixes = element_param_map[element_type]
                if 'name' not in element or element['name'] == '':
                    element['name'] = element_type + str(counter)
                for suffix in param_suffixes:
                    self.ElementsParamNames.append(element['name'] + suffix)
            else:
                print('Element not recognized')
            counter += 1

            self.ElementsNames.append(element['name'])
            self.ElementsType.append(element['type'])
            self.ElementsNparam.append(len(element['Param']))
            self.ElementsStartIndex.append(StartIndex)
            self.ElementsEndIndex.append(StartIndex+len(element['Param'])-1)
            self.ElementsParamValues.extend(element['Param'])
            self.ElementsParamVariance.extend([0] * len(element['Param']))  # Initialize variances to zero
            
            # Check if upper and lower bounds are provided
            if 'Ub' not in element or element['Ub'] == []:
                element['Ub'] = [np.inf] * len(element['Param'])
            if 'Lb' not in element or element['Lb'] == [] or any(lb == -np.inf for lb in element['Lb']):
                element['Lb'] = [1e-10] * len(element['Param'])
            self.UpperBound.extend(element['Ub'])
            self.LowerBound.extend(element['Lb'])

            #update loop increment
            StartIndex+=len(element['Param'])
            counter+=1
        
        self.UpperBound = np.array(self.UpperBound)
        self.LowerBound = np.array(self.LowerBound)

        self.Ztot0, self.Z0=self.EvaluateCircuit()
        
        AlphaIndex = [i for i, name in enumerate(self.ElementsParamNames) if 'alpha' in name]
        for i in AlphaIndex:
            if self.UpperBound[i] == np.inf or self.LowerBound[i] == 1e-10:
                self.UpperBound[i] = 1.0
                self.LowerBound[i] = 0.4

        TauIndex = [i for i, name in enumerate(self.ElementsParamNames) if 'tau' in name]
        if self.constraint_type == 'segment' and change_UBLB:
            # Set the segment as bounds
            tau = np.array(self.ElementsParamValues)[TauIndex]
            # self.UpperBound[TauIndex] = np.concatenate([(tau[:-1] + tau[1:]) / 2, [10 * tau[-1]]])
            # self.LowerBound[TauIndex] = np.concatenate([[0.1 * tau[0]], (tau[:-1] + tau[1:]) / 2])
            log_tau = np.log(tau)
            log_upper_midpoints = (log_tau[:-1] + log_tau[1:]) / 2
            log_lower_midpoints = (log_tau[:-1] + log_tau[1:]) / 2
            self.UpperBound[TauIndex] = np.concatenate([
                np.exp(log_upper_midpoints),
                [10 * tau[-1]]
            ])
            self.LowerBound[TauIndex] = np.concatenate([
                [0.1 * tau[0]], 
                np.exp(log_lower_midpoints)
            ])
        else:
            pass
            
        for idx, element in enumerate(self.Elements):
            start_idx = self.ElementsStartIndex[idx]
            end_idx = self.ElementsEndIndex[idx] + 1
            self.Elements[idx]['Param'] = self.ElementsParamValues[start_idx:end_idx]
            self.Elements[idx]['Ub'] = self.UpperBound[start_idx:end_idx].tolist()
            self.Elements[idx]['Lb'] = self.LowerBound[start_idx:end_idx].tolist()

    def PeakDerivative(self, mode, nbr_peaks_fixed=None, f_fixed=None):
        """
        Calculates derivative-based peak identification for DRT analysis.
        This method identifies peaks in the distribution of relaxation times (DRT) using 
        derivative-based techniques.
        Parameters
        ----------
        mode : str 'manual', 'fixed' or 'auto'
            Mode for peak identification algorithm. Specifies how peaks should be identified.
        nbr_peaks_fixed : int, optional
            If provided, forces the algorithm to identify exactly this number of peaks.
        f_fixed : array-like, optional
            If provided, uses these specific frequencies for peak identification instead of
            automatically determining them.
        Returns
        -------
        r_est : array-like
            Estimated resistance values for each identified peak.
        freq_est : array-like
            Estimated characteristic frequencies for each identified peak.
        alpha_est : array-like
            Estimated shape parameters (alpha) for each identified peak.
        nbr_peaks : int
            Total number of peaks identified.
        tau_est : array-like
            Estimated time constants (tau = 1/(2π*freq)) for each identified peak.
        """
        if mode is None:
            raise ValueError("Mode must be specified as 'maund', 'fixed', or 'auto'.")
        elif mode == 'fixed' and (nbr_peaks_fixed is None or f_fixed is None):
            raise ValueError("For 'fixed' mode, both nbr_peaks_fixed and f_fixed must be provided.")
        else:
            R_est, freq_est, alpha_est, nbr_peaks, tau_est = CNLS_fn.PeakDerivative.peak_derivative(self.DRTmes, self.f, mode, nbr_peaks_fixed, f_fixed)
        
        return R_est, freq_est, alpha_est, nbr_peaks, tau_est

    def EvaluateCircuit(self):
        """
        Evaluates the impedance of the circuit for each element and computes the total impedance.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit. It should contain the following keys:
            - 'w': (array) Array of angular frequencies.
            - 'ElementsNames': (list) List of element names.
            - 'ElementsParamValues': (list) List of parameter values for each element.
            - 'ElementsType': (list) List of element types.
            - 'ElementsStartIndex': (list) List of start indices for the parameters of each element.
            - 'ElementsEndIndex': (list) List of end indices for the parameters of each element.

        Returns:
        tuple: A tuple containing:
            - Ztot (array): Total impedance of the circuit.
            - Z (DataFrame): Impedance values for each element.
        """

        # Initialize the impedance matrix and the counter
        Z = pd.DataFrame()
        counter=0

        # Define a mapping from element types to their corresponding functions
        element_function_map = {
            'Resistor': CNLS_fn.ImpedanceFunctions.Resistor,
            'Inductor': CNLS_fn.ImpedanceFunctions.Inductor,
            'Inductor_a': CNLS_fn.ImpedanceFunctions.Inductor_a,
            'Capacitor': CNLS_fn.ImpedanceFunctions.Capacitor,
            'RC': CNLS_fn.ImpedanceFunctions.RC,
            'RQ': CNLS_fn.ImpedanceFunctions.RQ,
            'Gerisher': CNLS_fn.ImpedanceFunctions.Gerisher,
            'fFLW': CNLS_fn.ImpedanceFunctions.fFLW,
            'FLW': CNLS_fn.ImpedanceFunctions.FLW,
            'RandleC': CNLS_fn.ImpedanceFunctions.RandleC,
            'RandleCPE': CNLS_fn.ImpedanceFunctions.RandleCPE,
            'RandleCPEfFLW': CNLS_fn.ImpedanceFunctions.RandleCPEfFLW,
            'RandleCfFLW': CNLS_fn.ImpedanceFunctions.RandleCfFLW
        }
        
        # Iterate over the elements and compute their impedances
        for counter, type in enumerate(self.ElementsType):
            if type in element_function_map:
                func = element_function_map[type]
                start_idx = self.ElementsStartIndex[counter]
                end_idx = self.ElementsEndIndex[counter] + 1
                params = self.ElementsParamValues[start_idx:end_idx]
                Z[self.ElementsNames[counter]] = func(self.w, params)
            else:
                print(f'Element type {type} not recognized')
        
        # Compute the total impedance
        Ztot=np.array(np.sum(Z,axis=1))

        return Ztot, Z

    def FitCircuit(self):
        """
        Fits the circuit to experimental impedance data.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.

        Returns:
        dict: A dictionary containing the fitted circuit parameters and their variances.
            - ElementsParamValues (list): The fitted parameter values for each element in the circuit.
            - Residuals (numpy array): The residuals from the optimization process, representing the differences between the observed data (Zmes) and the model predictions (Ztot), weighted by the magnitude of the experimental impedance.
            - ResidualsReal (numpy array): The real part of the residuals.
            - ResidualsImag (numpy array): The imaginary part of the residuals.
            - SumResiduals (float): The sum of the residuals, providing a measure of the overall fit quality.
            - ElementsParamVariance (numpy array): The variances of the fitted parameters, computed from the covariance matrix.
            - ElementsParamStandardErrors (numpy array): The standard errors of the fitted parameters, computed as the square root of the variances.
            - ElementsParamPValues (numpy array): The p-values for the fitted parameters, computed using the t-distribution, indicating the statistical significance of the fitted parameters.
        """

        # Define the residuals function
        def residuals(params):
            # Update the circuit parameters
            self.ElementsParamValues = params
            # Evaluate the circuit with the updated parameters
            Ztot, _ = self.EvaluateCircuit()
            # Compute the residuals (weighted by the magnitude of the experimental impedance)
            weights = 1 / np.abs(self.Zmes)
            res = weights * (Ztot - self.Zmes)
            res = np.array(res)  # Ensure res is a numpy array
            return np.concatenate([res.real, res.imag])

        # Flatten the initial parameter values
        initial_params = np.array(self.ElementsParamValues)

        # Perform the weighted least squares fit
        adjusted_x0 = np.where(
            initial_params < self.LowerBound,
            self.LowerBound * 1.001,  # 低于下界 → 设为下界的 110%
            np.where(
                initial_params > self.UpperBound,
                self.UpperBound * 0.9999,  # 高于上界 → 设为上界的 90%
                initial_params  # 否则保持原值
            )
        )
        result = opt.least_squares(residuals, adjusted_x0,
                        bounds=(self.LowerBound, self.UpperBound))

        # Update the circuit with the fitted parameters
        self.ElementsParamValues = list(result.x)

        # Evaluate the circuit with the fitted parameters
        self.Ztot, self.Z = self.EvaluateCircuit()

        # Add residuals to the circuit dictionary
        residuals = result.fun
        self.ResidualsReal = residuals[:len(residuals)//2]
        self.ResidualsImag = residuals[len(residuals)//2:]
        self.SumNormResiduals = np.sum(residuals**2)
        print('---- Sum of normalized residuals:', self.SumNormResiduals)
        # Compute the covariance matrix
        self.dof = 2*len(self.Zmes) - len(result.x)  # Degrees of freedom
        J = result.jac
        cov = (self.SumNormResiduals/self.dof)*np.linalg.pinv(J.T @ J)  # Pseudo-inverse to handle singular matrices
        self.ElementsParamVariance = np.diag(cov)

        # Compute the standard error of the parameter estimates
        se = np.sqrt(self.ElementsParamVariance)
        self.ElementsParamStandardErrors =se

        # Compute the t-values
        t_values = result.x / se

        # Compute the p-values using the t-distribution
        p_values = 2 * (1 - t.cdf(np.abs(t_values), self.dof))
        #p_values = 2 * (t.cdf(-np.abs(t_values), self.dof)) # both formulations are equivalent

        # Add p-values to the circuit dictionary
        self.ElementsParamPValues = p_values

        # Create FitSummary DataFrame
        fit_summary_data = {
            'Value': self.ElementsParamValues,
            'SE': self.ElementsParamStandardErrors,
            'Pvalue': self.ElementsParamPValues
        }
        fit_summary_df = pd.DataFrame(fit_summary_data, index=self.ElementsParamNames).T
        fit_summary_df.index.name = 'Index'

        self.FitSummary = fit_summary_df

    def PrintCircuit(self):
        """
        Prints the details of the circuit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        """

        print("Circuit Details:")
        print("Elements Names:", self.ElementsNames)
        print("Elements Types:", self.ElementsNames)
        print("Elements Param Values:", self.ElementsParamValues)
        print("Elements Upper Bound:", self.UpperBound)
        print("Elements Lower Bound:", self.LowerBound)
        print("Elements Param Variance:", self.ElementsParamVariance)

    def PlotResiduals(self):
        """
        Plots the residuals of the circuit fit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        """

        # Create subplots
        plt.figure('Residual')

        # Plot Real(Residuals) vs Frequency
        plt.plot(self.f, 100 * self.ResidualsReal / np.abs(self.Ztot), 'o', label='Real', markerfacecolor='none', color='blue')
        plt.plot(self.f, 100 * self.ResidualsImag / np.abs(self.Ztot), 'o', label='Imag', markerfacecolor='none', color='red')
        plt.xscale('log')
        plt.xlabel('Frequency [Hz]')
        plt.ylabel('Residuals [%]')
        plt.legend()
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)

        plt.tight_layout()

    def PlotCircuit(self):
        """
        Plots the impedance of the circuit and the experimental impedance data.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        """

        # Evaluate the circuit
        Ztot, _ = self.EvaluateCircuit()
        #EIS4DRT=pd.DataFrame({'f':self.f,'Re':Ztot.real,'Im':Ztot.imag})
        #DRTtot=DRT.drt_tikonov(EIS4DRT, Circuit['lambda']);

        # Create subplots
        fig, ax = plt.subplots(3, 2, figsize=(15, 12))
        fig.canvas.manager.set_window_title('Fit results')

        # Plot |Z| vs Frequency
        ax[0, 0].plot(self.f, np.abs(self.Zmes), 'o', markerfacecolor='none', label='Experimental Impedance')
        ax[0, 0].plot(self.f, np.abs(Ztot), label='Total Impedance')
        ax[0, 0].set_xscale('log')
        ax[0, 0].set_xlabel('Frequency [Hz]')
        ax[0, 0].set_ylabel(r'|Z| [$\Omega\cdot \mathrm{cm}^2$]')
        ax[0, 0].grid(True, which='both', linestyle='--', linewidth=0.5)
        ax[0, 0].legend()

        # Plot Phase vs Frequency
        ax[0, 1].plot(self.f, np.angle(self.Zmes, deg=True), 'o', markerfacecolor='none', label='Experimental Impedance')
        ax[0, 1].plot(self.f, np.angle(Ztot, deg=True), label='Total Impedance')
        ax[0, 1].set_xscale('log')
        ax[0, 1].set_xlabel('Frequency [Hz]')
        ax[0, 1].set_ylabel('Phase [degree]')
        ax[0, 1].grid(True, which='both', linestyle='--', linewidth=0.5)
        # ax[0, 1].legend()

        # Plot -Imag(Z) vs Frequency
        ax[1, 0].plot(self.f, -np.imag(self.Zmes), 'o', markerfacecolor='none', label='Experimental Impedance')
        ax[1, 0].plot(self.f, -np.imag(Ztot), label='Total Impedance')
        ax[1, 0].set_xscale('log')
        ax[1, 0].set_xlabel('Frequency [Hz]')
        ax[1, 0].set_ylabel(r"$\mathrm{-Z}'' \, [\Omega\cdot \mathrm{cm}^2]$")
        ax[1, 0].grid(True, which='both', linestyle='--', linewidth=0.5)
        # ax[1, 0].legend()

        # Plot Real(Z) vs Frequency
        ax[1, 1].plot(self.f, np.real(self.Zmes), 'o', markerfacecolor='none', label='Experimental Impedance')
        ax[1, 1].plot(self.f, np.real(Ztot), label='Total Impedance')
        ax[1, 1].set_xscale('log')
        ax[1, 1].set_xlabel('Frequency [Hz]')
        ax[1, 1].set_ylabel(r"$\mathrm{Z}' \, [\Omega\cdot \mathrm{cm}^2]$")
        ax[1, 1].grid(True, which='both', linestyle='--', linewidth=0.5)
        # ax[1, 1].legend()

        # Plot Nyquist plot (Real(Z) vs -Imag(Z))
        ax[2, 0].plot(np.real(self.Zmes), -np.imag(self.Zmes), 'o', markerfacecolor='none', label='Experimental Impedance')
        ax[2, 0].plot(np.real(Ztot), -np.imag(Ztot), label='Total Impedance')
        ax[2, 0].set_xlabel(r"$\mathrm{Z}' \, [\Omega\cdot \mathrm{cm}^2]$")
        ax[2, 0].set_ylabel(r"$\mathrm{-Z}'' \, [\Omega\cdot \mathrm{cm}^2]$")
        ax[2, 0].set_aspect('equal', 'box')
        ax[2, 0].grid(True, which='both', linestyle='--', linewidth=0.5)
        # ax[2, 0].legend()

        if self.DRT is not None:
            # Plot DRT
            ax[2, 1].plot(self.f, self.DRTmes, label='Experimental DRT')
            ax[2, 1].plot(self.f, self.DRT['ReIm']['g'], label='DRT')
            ax[2, 1].set_xscale('log')
            ax[2, 1].set_xlabel('Frequency [Hz]')
            ax[2, 1].set_ylabel(r'$\gamma \, [\Omega \cdot cm^2 \cdot s]$')
            ax[2, 1].grid(True, which='both', linestyle='--', linewidth=0.5)
            ax[2, 1].set_ylim(0, 1.2 * np.max([self.DRTmes, self.DRT['ReIm']['g']]))
            # ax[2, 1].legend()
        else:
            ax[2, 1].axis('off')
        
        plt.tight_layout()

    def PlotElements(self):
        """
        Plots the impedance of each element in the circuit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        """

        # Evaluate the circuit
        _, Z = self.EvaluateCircuit()

        fig, ax = plt.subplots(2, 2, figsize=(12, 10))
        fig.canvas.manager.set_window_title('Individual elements')

        # Plot -Imag(Z) vs Frequency for each element
        ax[0, 0].plot(self.f, -np.imag(self.Zmes), 'o', markerfacecolor='none', label='Experimental Impedance')
        for element in Z.columns:
            ax[0, 0].semilogx(self.f, -np.imag(Z[element]), label=f'{element}')
        ax[0, 0].set_xlabel('Frequency [Hz]')
        ax[0, 0].set_ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
        ax[0, 0].legend()
        ax[0, 0].grid(True, which='both', linestyle='--', linewidth=0.5)

        # Plot Real(Z) vs Frequency for each element (cumulative)
        ax[0, 1].plot(self.f, np.real(self.Zmes), 'o', markerfacecolor='none', label='Experimental Impedance')
        for idx, element in enumerate(Z.columns):
            cumulative_real = sum(np.real(Z[element].iloc[-1]) for element in Z.columns[:idx])
            ax[0, 1].semilogx(self.f, np.real(Z[element])+cumulative_real, label=f'{element}')
        ax[0, 1].set_xlabel('Frequency [Hz]')
        ax[0, 1].set_ylabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
        # ax[0, 1].legend()
        ax[0, 1].grid(True, which='both', linestyle='--', linewidth=0.5)

        # Nyquist plot (Real(Z) vs -Imag(Z) for each element)
        ax[1, 0].plot(np.real(self.Zmes), -np.imag(self.Zmes), 'o', markerfacecolor='none', label='Experimental Impedance')
        for idx, element in enumerate(Z.columns):
            cumulative_real = sum(np.real(Z[element].iloc[-1]) for element in Z.columns[:idx])
            if 'L' in element:
                cumulative_real = sum(
                    np.real(Z[col][0]) for col in Z.columns
                    if 'R' in col and not any(excluded in col for excluded in ['RQ', 'RC', 'Randle'])
                )
            ax[1, 0].plot(np.real(Z[element])+cumulative_real, -np.imag(Z[element]), label=f'{element}')
        ax[1, 0].set_xlabel(r"$Z' \, [\Omega\cdot \mathrm{cm}^2]$")
        ax[1, 0].set_ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
        ax[1, 0].set_aspect('equal', 'box')
        # ax[1, 0].legend()
        ax[1, 0].grid(True, which='both', linestyle='--', linewidth=0.5)

        # DRT plot
        if self.DRT is not None:
            ax[1, 1].plot(self.f, self.DRTmes, label='Experimental DRT')
            for element in self.ElementDRTs:
                if 'L' in element or ('R' in element and not any(excluded in element for excluded in ['RQ', 'RC', 'Randle'])):
                    continue
                ax[1, 1].plot(self.f, self.ElementDRTs[element]['ReIm']['g'], label=f'{element}')
            ax[1, 1].set_xscale('log')
            ax[1, 1].set_xlabel('Frequency [Hz]')
            ax[1, 1].set_ylabel(r'$\gamma \, [\Omega \cdot cm^2 \cdot s]$')
            ax[1, 1].legend()
            ax[1, 1].grid(True, which='both', linestyle='--', linewidth=0.5)
            ax[1, 1].set_ylim(0, 1.2 * np.max([self.DRTmes, self.DRT['ReIm']['g']]))
        else:
            ax[1, 1].axis('off')

        plt.tight_layout()

    def EvaluateCircuitDRT(self):
        """
        Computes the DRT for the total impedance and for each individual circuit element
        using the existing impedance data (self.Ztot and self.Z).

        Returns:
        dict: A dictionary containing the DRT results for the total impedance and each element.
        
        Raises:
        ValueError: If self.Ztot or self.Z is None or empty.
        """
        # Check if impedance data exists
        if self.Ztot is None or self.Z is None:
            raise ValueError("Circuit impedance data not available. Run EvaluateCircuit() first.")
        
        if len(self.Ztot) == 0 or self.Z.empty:
            raise ValueError("Circuit impedance data is empty. Check your circuit configuration.")

        # Compute the DRT for the total impedance
        EIS_total = {
            'Re': np.real(self.Ztot),
            'Im': np.imag(self.Ztot),
            'f': self.f,
        }
        
        self.DRT = DRT_fn.DRT_tikhonov(EIS_total, self.DRTparameters)
        
        # Compute DRT for each individual element
        self.ElementDRTs = {}
        for element_name in self.Z.columns:
            element_impedance = self.Z[element_name]
            EIS_element = {
                'Re': np.real(element_impedance),
                'Im': np.imag(element_impedance),
                'f': self.f,
            }

            # Store the DRT for this element
            self.ElementDRTs[element_name] = DRT_fn.DRT_tikhonov(EIS_element, self.DRTparameters)

    def _reconstruct_elements(self):
        """
        Reconstructs the Elements list by directly checking for type keywords (e.g., RQ, RC, fFLW) in parameter names.
        """
        # Element type and name
        TYPE_KEYWORDS = {
            'RQ': ['RQ'],
            'RC': ['RC'],
            'fFLW': ['fFLW'],
            'FLW': ['FLW'],
            'Gerisher': ['Gerisher'],
            'RandleC': ['RandleC'],
            'RandleCPE': ['RandleCPE'],
            'RandleCPEfFLW': ['RandleCPEfFLW'],
            'RandleCfFLW': ['RandleCfFLW'],
            'Resistor': ['R'],
            'Capacitor': ['C'],
            'Inductor': ['L'],
            'Inducotr_a': ['La'],
            'CPE': ['Q']
        }

        elements = []
        current_element = None
        param_index = 0

        while param_index < len(self.ElementsParamNames):
            param_name = self.ElementsParamNames[param_index]
            
            # Get element name（e.g., "RQ1" -> "RQ"）
            element_type = None
            element_name = None

            # Check the element type based on keywords in the parameter name
            for type_name, keywords in TYPE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in param_name:
                        element_type = type_name
                        # Extract element name (e.g., "RQ1" -> "RQ")
                        element_name = param_name.split('_')[0]
                        break
                if element_type is not None:
                    break

            if element_type is None:
                print(f"Warning: Unrecognized parameter {param_name}")
                param_index += 1
                continue

            # Create or update the current element
            if current_element is None or current_element['name'] != element_name:
                if current_element is not None:
                    elements.append(current_element)
                current_element = {
                    'name': element_name,
                    'type': element_type,
                    'Param': [],
                    'Ub': [],
                    'Lb': []
                }

            # Add the parameter to the current element
            current_element['Param'].append(self.ElementsParamValues[param_index])
            current_element['Ub'].append(self.UpperBound[param_index])
            current_element['Lb'].append(self.LowerBound[param_index])
            param_index += 1

        # Add the last element if it exists
        if current_element is not None:
            elements.append(current_element)

        return elements

    def ExportCircuit(self):
        """
        Exports the circuit details into an Excel file. Each element of the Circuit dictionary is saved on a different sheet.

        The file is saved in a folder named 'CNLS' inside self.file_folder, with the filename being self.filename
        (without its original extension) and an '.xlsx' extension added.
        """

        # Ensure the CNLS folder exists
        export_folder = os.path.join(self.file_folder, "CNLS")
        os.makedirs(export_folder, exist_ok=True)

        # Define the export file path
        export_file = os.path.join(export_folder, os.path.splitext(self.filename)[0] + ".xlsx")

        # Create a Pandas Excel writer
        with pd.ExcelWriter(export_file, engine='openpyxl') as writer:
            # Sheet - Summary
            summary_data = {
                "ElementsNames": [self.ElementsNames],
                "ElementsType": [self.ElementsType],
                "SumNormResiduals": [self.SumNormResiduals],
                "dof": [self.dof],
                "data_type": [self.data_type],
                "fixed_frequencies": [self.f_fixed if self.f_fixed is not None else None],
                "constraint_type": [self.constraint_type],
                "f_mode": [self.f_mode],
                "ElementsEndIndex": [self.ElementsEndIndex],
                "ElementsStartIndex": [self.ElementsStartIndex],
                "ElementsNparam": [self.ElementsNparam],
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

            # Sheet - Elements
            elements_data = {
                "ElementsParamNames": self.ElementsParamNames,
                "ElementsParamValues": self.ElementsParamValues,
                "UpperBound": self.UpperBound,
                "LowerBound": self.LowerBound,
                "ElementsParamVariance": self.ElementsParamVariance,
                "ElementsParamStandardErrors": self.ElementsParamStandardErrors,
                "ElementsParamPValues": self.ElementsParamPValues,
            }
            elements_df = pd.DataFrame(elements_data)
            elements_df.to_excel(writer, sheet_name="Elements", index=False)

            # Sheet - Z
            z_data = {
                "Frequency/Hz": self.f,
                "Zmes_Re/ohm·cm2": np.real(self.Zmes),
                "Zmes_Im/ohm·cm2": np.imag(self.Zmes),
                "Ztot_Re/ohm·cm2": np.real(self.Ztot),
                "Ztot_Im/ohm·cm2": np.imag(self.Ztot),
                "Ztot0_Re/ohm·cm2": np.real(self.Ztot0),
                "Ztot0_Im/ohm·cm2": np.imag(self.Ztot0),
                "Residuals_Re": self.ResidualsReal,
                "Residuals_Im": self.ResidualsImag,
            }
            z_df = pd.DataFrame(z_data)
            z_df.to_excel(writer, sheet_name="Z", index=False)

            # Add individual element impedances to the Z sheet
            for element_name in self.Z.columns:
                z_df[element_name + "_Re" + "/ohm·cm2"] = np.real(self.Z[element_name])
                z_df[element_name + "_Im" + "/ohm·cm2"] = np.imag(self.Z[element_name])
            z_df.to_excel(writer, sheet_name="Z", index=False)

            # Sheet - DRT
            drt_data = {
                "f": self.f,
                "DRTmes/ohm·s·cm2": self.DRTmes,
            }
            if self.DRT is not None:
                drt_data.update({
                    "DRT": self.DRT["ReIm"]["g"],
                })
            drt_df = pd.DataFrame(drt_data)
            drt_df.to_excel(writer, sheet_name="DRT", index=False)

            # Add individual element DRTs to the DRT sheet
            for element_name, drt in self.ElementDRTs.items():
                drt_df["DRT" + element_name + "/ohm·s·cm2"] = drt["ReIm"]["g"]
            drt_df.to_excel(writer, sheet_name="DRT", index=False)

        print(f"-- Circuit details exported to {export_file}")


    def ImportCircuit(self):
        """
        Imports the circuit details from an Excel file.

        The file is expected to be located in a folder named 'CNLS' inside self.file_folder,
        with the filename being self.filename (without its original extension) and an '.xlsx' extension added.

        Returns:
        None: Updates the Circuit object with the imported data.
        """
        # Define the import file path
        import_folder = os.path.join(self.file_folder, "CNLS")
        import_file = os.path.join(import_folder, os.path.splitext(self.filename)[0] + ".xlsx")

        # Check if the file exists
        if not os.path.exists(import_file):
            raise FileNotFoundError(f"File not found: {import_file}")
        else:
            print(f"-- Importing CNLS data from {import_file}")

        # Read the Excel file
        with pd.ExcelFile(import_file) as xls:
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name)
                if sheet_name == "Summary":
                    # Convert the Summary sheet to a dictionary
                    self.data_type = df["data_type"].iloc[0]
                    self.constraint_type = df["constraint_type"].iloc[0]
                    self.f_mode = df["f_mode"].iloc[0]
                    self.SumNormResiduals = df["SumNormResiduals"].iloc[0]
                    self.dof = df["dof"].iloc[0]
                    self.ElementsNames = eval(df["ElementsNames"].iloc[0])
                    self.ElementsType = eval(df["ElementsType"].iloc[0])
                    self.f_fixed = eval(df["fixed_frequencies"].iloc[0])
                    self.ElementsEndIndex = eval(df["ElementsEndIndex"].iloc[0])
                    self.ElementsStartIndex = eval(df["ElementsStartIndex"].iloc[0])
                    self.ElementsNparam = eval(df["ElementsNparam"].iloc[0])
                elif sheet_name == "Elements":
                    # Extract elements-related data
                    self.ElementsParamNames = df["ElementsParamNames"].tolist()
                    self.ElementsParamValues = df["ElementsParamValues"].tolist()
                    self.UpperBound = df["UpperBound"].tolist()
                    self.LowerBound = df["LowerBound"].tolist()
                    self.ElementsParamVariance = df["ElementsParamVariance"].tolist()
                    self.ElementsParamStandardErrors = df["ElementsParamStandardErrors"].tolist()
                    self.ElementsParamPValues = df["ElementsParamPValues"].tolist()
                elif sheet_name == "Z":
                    # Extract impedance-related data
                    self.f = df["Frequency/Hz"].to_numpy()
                    self.Zmes = df["Zmes_Re/ohm·cm2"].to_numpy() + 1j * df["Zmes_Im/ohm·cm2"].to_numpy()
                    self.Ztot = df["Ztot_Re/ohm·cm2"].to_numpy() + 1j * df["Ztot_Im/ohm·cm2"].to_numpy()
                    self.Ztot0 = df["Ztot0_Re/ohm·cm2"].to_numpy() + 1j * df["Ztot0_Im/ohm·cm2"].to_numpy()
                    self.ResidualsReal = df["Residuals_Re"].to_numpy()
                    self.ResidualsImag = df["Residuals_Im"].to_numpy()
                    # Extract individual element impedances
                    self.Z = pd.DataFrame()
                    for col in df.columns:
                        if "_Re/ohm·cm2" in col:
                            element_name = col.split("_Re")[0]
                            self.Z[element_name] = df[col].to_numpy() + 1j * df[element_name + "_Im/ohm·cm2"].to_numpy()
                elif sheet_name == "DRT":
                    # Extract DRT-related data
                    self.DRTmes = df["DRTmes/ohm·s·cm2"].to_numpy()
                    if "DRT" in df.columns:
                        self.DRT = {"ReIm": {"g": df["DRT"].to_numpy()}}
                    # Extract individual element DRTs
                    self.ElementDRTs = {}
                    for col in df.columns:
                        if "DRT" in col and col != "DRT":
                            element_name = col.replace("DRT", "").replace("/ohm·s·cm2", "")
                            self.ElementDRTs[element_name] = {"ReIm": {"g": df[col].to_numpy()}}
        self.Elements = self._reconstruct_elements()
        print(f"-- Circuit data imported successfully")

    # Software functions
    def AddElement(self, Element):
        """
        Adds a new element to the circuit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        Element (dict): A dictionary representing the new element to be added. It should have the following keys:
            - 'name': (str) Name of the element.
            - 'type': (str) Type of the element (e.g., 'Resistor', 'Inductor', 'Capacitor', etc.).
            - 'Param': (list) List of parameters for the element.
            - 'Ub': (list) Upper bounds for the parameters.
            - 'Lb': (list) Lower bounds for the parameters.

        Returns:
        dict: A dictionary representing the updated circuit with the new element added.
        """

        # Update the circuit details
        self.ElementsNames.append(Element['name'])
        self.ElementsNames.append(Element['type'])
        self.ElementsParamValues.extend(Element['Param'])

        # Check if upper and lower bounds are provided
        if 'Ub' not in Element or Element['Ub'] == []:
            Element['Ub'] = [np.inf] * len(Element['Param'])
        if 'Lb' not in Element or Element['Lb'] == []:
            Element['Lb'] = [-np.inf] * len(Element['Param'])

        self.UpperBound.extend(Element['Ub'])
        self.LowerBound.extend(Element['Lb'])

        # Update the start and end indices
        self.ElementsStartIndex.append(self.ElementsEndIndex[-1] + 1)
        self.ElementsEndIndex.append(self.ElementsEndIndex[-1] + len(Element['Param']))
        self.ElementsNparam.append(len(Element['Param']))

        # Evaluate the circuit
        self.Ztot0, self.Z0 = self.EvaluateCircuit()

    def RemoveElement(self, ElementName):
        """
        Removes an element from the circuit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        ElementName (str): Name of the element to be removed.

        Returns:
        dict: A dictionary representing the updated circuit with the element removed.
        """

        # Find the index of the element to be removed
        idx = self.ElementsNames.index(ElementName)

        # Update the circuit details
        self.ElementsNames.pop(idx)
        self.ElementsNames.pop(idx)
        self.ElementsParamValues = self.ElementsParamValues[:self.ElementsStartIndex[idx]] + self.ElementsParamValues[self.ElementsEndIndex[idx] + 1:]
        self.UpperBound = self.UpperBound[:self.ElementsStartIndex[idx]] + self.UpperBound[self.ElementsEndIndex[idx] + 1:]
        self.LowerBound = self.LowerBound[:self.ElementsStartIndex[idx]] + self.LowerBound[self.ElementsEndIndex[idx] + 1:]
        self.ElementsStartIndex.pop(idx)
        self.ElementsEndIndex.pop(idx)
        self.ElementsNparam.pop(idx)

        # Evaluate the circuit
        self.Ztot0, self.Z0 = self.EvaluateCircuit()

    def UpdateElement(self, ElementName, NewParams): 
        """
        Updates the parameters of an element in the circuit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        ElementName (str): Name of the element to be updated.
        NewParams (list): List of new parameters for the element.

        Returns:
        dict: A dictionary representing the updated circuit with the element parameters updated.
        """

        # Find the index of the element to be updated
        idx = self.ElementsNames.index(ElementName)

        # Update the circuit details
        start_idx = self.ElementsStartIndex[idx]
        end_idx = self.ElementsEndIndex[idx] + 1
        self.ElementsParamValues[start_idx:end_idx] = NewParams

        # Evaluate the circuit
        self.Ztot0, self.Z0 = self.EvaluateCircuit()

    def GetElementParameters(self, ElementName): 
        """
        Gets the parameters of an element in the circuit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        ElementName (str): Name of the element.

        Returns:
        list: A list of parameters for the specified element.
        """

        # Find the index of the element
        idx = self.ElementsNames.index(ElementName)

        # Get the parameters of the element
        start_idx = self.ElementsStartIndex[idx]
        end_idx = self.ElementsEndIndex[idx] + 1
        params = self.ElementsParamValues[start_idx:end_idx]

        return params

    def GetElementImpedance(self, ElementName):
        """
        Gets the impedance of an element in the circuit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        ElementName (str): Name of the element.

        Returns:
        DataFrame: Impedance values for the specified element.
        """

        # Evaluate the circuit
        _, Z = self.EvaluateCircuit()

        # Get the impedance of the specified element
        Z_element = Z[ElementName]

        return Z_element
    
    def ShowFitSummary(self):
        """
        Displays the Fit Summary table in an external window using tkinter.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        """
        fit_summary_df = self.FitSummary.round(4)  # Round the numbers to 4 decimal places

        # Create a new tkinter window
        root = tk.Tk()
        root.title("Fit Summary")

        # Get screen width and height
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # Set window size to be slightly smaller than the screen size
        window_width = min(screen_width - 100, 1000)
        window_height = min(screen_height - 100, 350)
        root.geometry(f"{window_width}x{window_height}")

        # Create a frame for the DataFrame
        frame = ttk.Frame(root)
        frame.pack(fill='both', expand=True)

        # Create a Canvas widget
        canvas = tk.Canvas(frame)
        canvas.pack(side='left', fill='both', expand=True)

        # Add vertical scrollbar to the canvas
        v_scrollbar = ttk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        v_scrollbar.pack(side='right', fill='y')
        canvas.configure(yscrollcommand=v_scrollbar.set)

        # Add horizontal scrollbar to the canvas
        h_scrollbar = ttk.Scrollbar(root, orient='horizontal', command=canvas.xview)
        h_scrollbar.pack(side='bottom', fill='x')
        canvas.configure(xscrollcommand=h_scrollbar.set)

        # Create another frame inside the canvas
        inner_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor='nw')

        # Add the index as a separate column
        fit_summary_df.reset_index(inplace=True)

        # Create a Treeview widget
        tree = ttk.Treeview(inner_frame, columns=list(fit_summary_df.columns), show='headings')
        tree.pack(fill='both', expand=True)

        # Define headings and adjust column widths
        font = tkFont.Font()
        for col in fit_summary_df.columns:
            tree.heading(col, text=col)
            tree.column(col, anchor='center', width=font.measure(col) + 1)  # Set a minimum width for columns

        # Insert data into the Treeview
        for row in fit_summary_df.itertuples(index=False):
            tree.insert('', 'end', values=row)
            for i, val in enumerate(row):
                col_width = font.measure(str(val))+1
                if tree.column(f'#{i+1}', width=None) < col_width:
                    tree.column(f'#{i+1}', width=col_width)

        # Update the inner frame's size to fit the Treeview
        inner_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        # Ensure the Treeview widget expands horizontally
        tree.pack(side='left', fill='both', expand=True)

        # Create a new window to print the DataFrame
        def print_dataframe():
            print_window = tk.Toplevel(root)
            print_window.title("Fit Summary - Print View")
            print_window.geometry(f"{window_width}x{window_height}")

            text_widget = tk.Text(print_window)
            text_widget.pack(fill='both', expand=True)

            text_widget.insert(tk.END, fit_summary_df.to_string())

        # Add a button to print the DataFrame in a new window
        print_button = ttk.Button(root, text="Print Fit Summary", command=print_dataframe)
        print_button.pack(side='bottom')

        # Start the tkinter main loop
        root.mainloop()