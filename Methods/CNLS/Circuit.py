import numpy as np
import pandas as pd
import Methods.CNLS.Utils.ImpedanceFunctions as Imp
import scipy.optimize as opt
from scipy.stats import t
import matplotlib.pyplot as plt
import Methods.DRT.DRT as DRT

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont

class Circuit:
    def __init__(self,file_folder=None, filename=None, Zmes = None, DRTmes = None, w = None, Elements = None):
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
        self.Zmes  = Zmes # Measured impedance data
        self.DRTmes = DRTmes # Measured DRT data
        self.Ztot0 = None # Initial total impedance
        self.Z0    = None # Initial impedance for each angular frequency
        self.Ztot  = None # Total impedance of the circuit
        self.Z     = None # Impedance values for each angular frequency
        self.w     = w    # Angular frequency array
        self.f     = w/(2*np.pi) # Frequency array
        self.DRT   = None # DRT data
        self.DRTparameters = None # DRT parameters
        
        # Initialize lists to store circuit elements configuration
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
            'RandleCPE': ['_R', '_Q', '_alpha_Q', '_R_W', '_tau0_W']
        }

        # Check for duplicate element names
        self.display_name = set()
        for element in Elements:
            if 'name' in element and element['name'] in self.display_name:
                raise ValueError(f"Duplicate element name found: {element['name']}")
            self.display_name.add(element.get('name', ''))

        # Iterate over the elements and assign parameter names
        for element in Elements:
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
            if 'Lb' not in element or element['Lb'] == []:
                element['Lb'] = [-np.inf] * len(element['Param'])

            self.UpperBound.extend(element['Ub'])
            self.LowerBound.extend(element['Lb'])

            #update loop increment
            StartIndex+=len(element['Param'])
            counter+=1

        self.initiate['Ztot0'], self.initiate['Z0']=self.EvaluateCircuit()

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
            'Resistor': Imp.Resistor,
            'Inductor': Imp.Inductor,
            'Inductor_a': Imp.Inductor_a,
            'Capacitor': Imp.Capacitor,
            'RC': Imp.RC,
            'RQ': Imp.RQ,
            'Gerisher': Imp.Gerisher,
            'fFLW': Imp.fFLW,
            'FLW': Imp.FLW,
            'RandleC': Imp.RandleC,
            'RandleCPE': Imp.RandleCPE
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
        result = opt.least_squares(residuals, initial_params,
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
        fit_summary_df = pd.DataFrame(fit_summary_data, index=Circuit['ElementsParamNames']).T
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

        # Plot |Z| vs Frequency
        ax[0, 0].plot(self.f, np.abs(self.Zmes), 'o', label='Experimental Impedance')
        ax[0, 0].plot(self.f, np.abs(Ztot), label='Total Impedance')
        ax[0, 0].set_xscale('log')
        ax[0, 0].set_yscale('log')
        ax[0, 0].set_xlabel('Frequency [Hz]')
        ax[0, 0].set_ylabel('|Z| (Ohmcm2)')
        ax[0, 0].legend()

        # Plot Phase vs Frequency
        ax[0, 1].plot(self.f, np.angle(self.Zmes, deg=True), 'o', label='Experimental Impedance')
        ax[0, 1].plot(self.f, np.angle(Ztot, deg=True), label='Total Impedance')
        ax[0, 1].set_xscale('log')
        ax[0, 1].set_xlabel('Frequency [Hz]')
        ax[0, 1].set_ylabel('Phase (degrees)')
        ax[0, 1].legend()

        # Plot -Imag(Z) vs Frequency
        ax[1, 0].plot(self.f, -np.imag(self.Zmes), 'o', label='Experimental Impedance')
        ax[1, 0].plot(self.f, -np.imag(Ztot), label='Total Impedance')
        ax[1, 0].set_xscale('log')
        ax[1, 0].set_xlabel('Frequency [Hz]')
        ax[1, 0].set_ylabel('-Imag(Z) (Ohmcm2)')
        ax[1, 0].legend()

        # Plot Real(Z) vs Frequency
        ax[1, 1].plot(self.f, np.real(self.Zmes), 'o', label='Experimental Impedance')
        ax[1, 1].plot(self.f, np.real(Ztot), label='Total Impedance')
        ax[1, 1].set_xscale('log')
        ax[1, 1].set_xlabel('Frequency [Hz]')
        ax[1, 1].set_ylabel('Real(Z) (Ohmcm2)')
        ax[1, 1].legend()

        # Plot Nyquist plot (Real(Z) vs -Imag(Z))
        ax[2, 0].plot(np.real(self.Zmes), -np.imag(self.Zmes), 'o', label='Experimental Impedance')
        ax[2, 0].plot(np.real(Ztot), -np.imag(Ztot), label='Total Impedance')
        ax[2, 0].set_xlabel('Real(Z) (Ohmcm2)')
        ax[2, 0].set_ylabel('-Imag(Z) (Ohmcm2)')
        ax[2, 0].set_aspect('equal', 'box')
        ax[2, 0].legend()

        if 'DRT' in self:
            if self['DRT'] is not None:
                # Plot DRT
                ax[2, 1].plot(self.f, self.DRTmes, label='Experimental DRT')
                ax[2, 1].plot(self.f, self.DRT['ReIm']['g'], label='DRT')
                ax[2, 1].set_xscale('log')
                ax[2, 1].set_xlabel('Frequency [Hz]')
                ax[2, 1].sylabel(r'$\gamma \, [\Omega \cdot cm^2 \cdot s]$')
                ax[2, 1].legend()
            else:
                ax[2, 1].axis('off')
        else:
            ax[2, 1].axis('off')
        
        # Hide the empty subplot (bottom right)
        #fig.delaxes(ax[2, 1])
        

        plt.tight_layout()
        plt.show()

    def PlotElementImpedance(self):
        """
        Plots the impedance of each element in the circuit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        """

        # Evaluate the circuit
        _, Z = self.EvaluateCircuit()

        fig, ax = plt.subplots(figsize=(10, 8))

        # Plot -Imag(Z) vs Frequency for each element
        for element in Z.columns:
            ax.plot(self.f, -np.imag(Z[element]), label=f'{element} (Impedance)')
        ax.plot(self.f, -np.imag(self.Zmes), 'o', label='Experimental Impedance')

        ax.set_xscale('log')
        ax.set_xlabel('Frequency [Hz]')
        ax.set_ylabel(r"$-Z'' \, [\Omega\cdot \mathrm{cm}^2]$")
        ax.legend()
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)

        plt.tight_layout()
        plt.show()

    def PlotResiduals(self):
        """
        Plots the residuals of the circuit fit.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        """

        # Create subplots
        fig, ax = plt.subplots(2, 1, figsize=(10, 8))

        # Plot Real(Residuals) vs Frequency
        ax[0].plot(self.f, 100*self.ResidualsReal/np.abs(self.Ztot), 'o', label='Real(Residuals)')
        ax[0].set_xscale('log')
        ax[0].set_xlabel('Frequency [Hz]')
        ax[0].set_ylabel('Real(Residuals) [%]')
        ax[0].legend()

        # Plot Imag(Residuals) vs Frequency
        ax[1].plot(self.f, 100*self.ResidualsImag/np.abs(self.Ztot), 'o', label='Imag(Residuals)')
        ax[1].set_xscale('log')
        ax[1].set_xlabel('Frequency [Hz]')
        ax[1].set_ylabel('Imag(Residuals) [%]')
        ax[1].legend()

        plt.tight_layout()
        plt.show()

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

    def ExportCircuit(self, filename):
        """
        Exports the circuit details into an Excel file. Each element of the Circuit dictionary is saved on a different sheet.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        filename (str): The name of the Excel file to save the circuit details.
        """
        with pd.ExcelWriter(filename) as writer:
            for key, value in Circuit.items():
                if isinstance(value, list):
                    # Convert list to DataFrame
                    df = pd.DataFrame(value, columns=[key])
                elif isinstance(value, np.ndarray):
                    # Convert ndarray to DataFrame
                    df = pd.DataFrame(value, columns=[key])
                elif isinstance(value, (pd.DataFrame, pd.Series)):
                    # Use DataFrame or Series directly
                    df = value
                else:
                    # Convert other types to DataFrame
                    df = pd.DataFrame([value], columns=[key])
                
                
                # Write DataFrame to Excel sheet
                df.to_excel(writer, sheet_name=key, index=False)

    def ImportCircuit(self,filename): 
        """
        Imports the circuit details from an Excel file.

        Parameters:
        filename (str): The name of the Excel file containing the circuit details.

        Returns:
        dict: A dictionary representing the circuit details.
        """
        with pd.ExcelFile(filename) as xls:
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name)
                if df.shape[1] == 1:
                    # Check if the first element is a string
                    if isinstance(df.iloc[0, 0], str):
                        self[sheet_name] = df.values.flatten().tolist()
                    else:
                        self[sheet_name] = np.array(df.values.flatten().tolist())
                else:
                    self[sheet_name] = df

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

    def EvaluateCircuitDRT(self):

        """
        Evaluates the circuit with the fitted parameters and computes the DRT.

        Parameters:
        Circuit (dict): A dictionary representing the initialized circuit.
        DRTParameters (dict): A dictionary containing the DRT parameters.

        Returns:
        dict: A dictionary containing the DRT results.
        """
        # Evaluate the circuit with the fitted parameters
        self.Ztot, _ = self.EvaluateCircuit()

        # Compute the DRT
        EIS = {
            'Re': np.real(self.Ztot),
            'Im': np.imag(self.Ztot),
            'f': self.f,
        }
        EIS=pd.DataFrame(EIS)

        self.DRT = DRT.drt_tikonov(EIS, self.DRTparameters)
