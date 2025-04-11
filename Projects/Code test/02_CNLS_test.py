from importlib import reload

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import Methods.CNLS.Circuit as CF
import Methods.CNLS.Utils as Imp
reload(Imp)
reload(CF)

def test_function(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
        return "pass"
    except Exception as e:
        return "fail"

def test_CircuitFunction():
    # Define the frequency range
    f = np.logspace(0, 4, 1000)
    w = 2 * np.pi * f

    # Define the elements in the circuit
    Elements = [
        {'name': 'R1', 'type': 'Resistor', 'Param': [10], 'Ub': [20], 'Lb': [5]},
        {'name': 'L1', 'type': 'Inductor', 'Param': [0.001], 'Ub': [0.002], 'Lb': [0.0005]},
        {'name': 'C1', 'type': 'Capacitor', 'Param': [1e-6], 'Ub': [2e-6], 'Lb': [0.5e-6]},
        {'name': 'RC1', 'type': 'RC', 'Param': [10, 0.001], 'Ub': [20, 0.002], 'Lb': [5, 0.0005]},
        {'name': 'RQ1', 'type': 'RQ', 'Param': [10, 0.001, 0.9], 'Ub': [20, 0.002, 1], 'Lb': [5, 0.0005, 0.8]},
        {'name': 'Ger1', 'type': 'Gerisher', 'Param': [10, 0.001], 'Ub': [20, 0.002], 'Lb': [5, 0.0005]},
        {'name': 'fFLW1', 'type': 'fFLW', 'Param': [10, 0.001, 0.5], 'Ub': [20, 0.002, 0.6], 'Lb': [5, 0.0005, 0.4]},
        {'name': 'FLW1', 'type': 'FLW', 'Param': [10, 0.001], 'Ub': [20, 0.002], 'Lb': [5, 0.0005]},
        {'name': 'RandleC1', 'type': 'RandleC', 'Param': [10, 1e-6, 10, 0.001], 'Ub': [20, 2e-6, 20, 0.002], 'Lb': [5, 0.5e-6, 5, 0.0005]},
        {'name': 'RandleCPE1', 'type': 'RandleCPE', 'Param': [10, 1e-6, 0.9, 10, 0.001], 'Ub': [20, 2e-6, 1, 20, 0.002], 'Lb': [5, 0.5e-6, 0.8, 5, 0.0005]}
    ]

    # Initialize the circuit
    results = {}
    Circuit=CF.EmptyCircuit()
    results['EmptyCircuit'] = test_function(CF.EmptyCircuit)
    Circuit = CF.InitializeCircuit(w, Elements)
    results['InitializeCircuit'] = test_function(CF.InitializeCircuit, w, Elements)

    # Generate synthetic experimental impedance data (Zmes) by evaluating the circuit
    Circuit['Zmes'], _ = CF.EvaluateCircuit(Circuit)
    results['EvaluateCircuit'] = test_function(CF.EvaluateCircuit, Circuit)

    # Add some noise to the synthetic data to simulate experimental data
    noise_level = 0.05
    Circuit['Zmes'] = Circuit['Zmes'] * (1 + noise_level * np.random.randn(len(Circuit['Zmes'])))

    # Fit the circuit to the experimental impedance data
    results['FitCircuit'] = test_function(CF.FitCircuit, Circuit)

    # Plot the impedance data
    results['PlotCircuit'] = test_function(CF.PlotCircuit, Circuit)

    # Show the fit summary
    results['ShowFitSummary'] = test_function(CF.ShowFitSummary,Circuit)

    # Add a new element to the circuit
    new_element = {'name': 'R2', 'type': 'Resistor', 'Param': [5], 'Ub': [10], 'Lb': [1]}
    results['AddElement'] = test_function(CF.AddElement, Circuit, new_element)

    # Print the updated circuit details
    results['PrintCircuit'] = test_function(CF.PrintCircuit, Circuit)

    # Update an existing element in the circuit
    updated_params = [15]
    results['UpdateElement'] = test_function(CF.UpdateElement, Circuit, 'R1', updated_params)

    # Remove an element from the circuit
    results['RemoveElement'] = test_function(CF.RemoveElement, Circuit, 'R2')

    # Get the parameters of an element
    results['GetElementParameters'] = test_function(CF.GetElementParameters, Circuit, 'R1')

    # Get the impedance of an element
    results['GetElementImpedance'] = test_function(CF.GetElementImpedance, Circuit, 'R1')

    # Export the circuit details to an Excel file
    results['ExportCircuit'] = test_function(CF.ExportCircuit, Circuit, 'CircuitDetails.xlsx')
    
    # Import the circuit details from an Excel file
    results['ImportCircuit'] = test_function(CF.ImportCircuit, 'CircuitDetails.xlsx')
    CircuitImp=CF.ImportCircuit('CircuitDetails.xlsx')

    # Plots the impedance of each element in the circuit
    CF.PlotElementImpedance(Circuit)
    results['PlotElementImpedance'] = test_function(CF.PlotElementImpedance, Circuit)

    # Compute the circuit DRT
    Circuit['DRTParameters']={'lambda': 0.001}
    results['EvaluateCircuitDRT'] = test_function(CF.EvaluateCircuitDRT, Circuit)

    # Print results
    for func_name, result in results.items():
        print(f"{func_name}: {result}")
    return Circuit

# Run the test function
Circuit=test_CircuitFunction()