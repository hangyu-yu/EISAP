import numpy as np
import pandas as pd

def DRT_tikhonov(EIS_data, parameters):

    """
    Compute the DRT using Tikhonov regularization based on Priscilla Caliandro's thesis.
    
    Parameters:
    EIS_data (pd.DataFrame): DataFrame containing at least 'f', 'Re', 'Im', 'omega'
                             'Im' should not have been multiplied by -1 (i.e., imag(Z_RC) < 0)
                             Frequency should be ordered from highest to lowest
    parameters (dict): Dictionary containing:
                       'Lambda' = regularization parameter
                                  The lambda used here has to be squared to match that of Priscilla Caliandro's thesis

    Returns:
    dict: A dictionary of DataFrames containing the DRT results
    """

    # Check if tau and omega exist in the DataFrame
    if 'tau' not in EIS_data:
        # Compute tau if it does not exist
        EIS_data['tau'] = 1 / (2 * np.pi * EIS_data['f'])
        # Compute tau if it does not exist
        EIS_data['tau'] = 1 / (2 * np.pi * EIS_data['f'])
    
    if 'omega' not in EIS_data:
        # Compute omega if it does not exist
        EIS_data['omega'] = 2 * np.pi * EIS_data['f']

    # Get Re and Im
    Im = -EIS_data['Im'] # Change the sign of the imaginary part
    Re = EIS_data['Re']

    n_freq = len(EIS_data['omega'])  # number of frequency points

    # Log spacing the RC elements used for the DRT
    log_max_tau = np.log10(max(EIS_data['tau']))
    log_min_tau = np.log10(min(EIS_data['tau']))
    tau = np.logspace(log_min_tau, log_max_tau, n_freq)
    f = 1 / (2 * np.pi * tau)
    dt = np.log(max(EIS_data['tau']) / min(EIS_data['tau'])) / (n_freq - 1)  # quadrature coefficient

    # Initialize A_im and A_re
    A_im = np.zeros((n_freq, n_freq))
    A_re = np.zeros((n_freq, n_freq))

    # Build A1 and A2 matrices column by column
    for j in range(n_freq):
        A_im[:, j] = dt * EIS_data['omega'] * tau[j] / (1 + (EIS_data['omega'] * tau[j]) ** 2)
        A_re[:, j] = dt * 1 / (1 + (EIS_data['omega'] * tau[j]) ** 2)

    # Add serial resistance Z = R (purely real) and inductance Z = jwL (purely imaginary) to A_re and A_im
    A_re = np.hstack([A_re, np.ones((n_freq, 1)), np.zeros((n_freq, 1))])
    A_im = np.hstack([A_im, np.zeros((n_freq, 1)), -EIS_data['omega'].reshape(-1, 1)])

    # Solve linear least square problem A*g(tau)=Z with Tikhonov regularization (ridge regression)
    # Imaginary part only
    DRT_Im = np.linalg.inv(A_im.T @ A_im + parameters['Lambda'] * np.eye(A_im.shape[1])) @ A_im.T @ Im
    Residuals_Im = A_im @ DRT_Im - EIS_data['Im']  # compute the Residuals
    Z_Im = A_re @ DRT_Im + 1j * A_im @ DRT_Im  # Compute Z back from DRT
    Rs_Im = DRT_Im[-2]  # Get R
    L_Im = DRT_Im[-1]  # Get L
    DRT_Im = DRT_Im[:-2]  # Remove R and L from the DRT
    Rp_Im = -np.trapz(DRT_Im, np.log(f))  # Estimated polarization resistance

    # Real part only
    DRT_Re = np.linalg.inv(A_re.T @ A_re + parameters['Lambda'] * np.eye(A_re.shape[1])) @ A_re.T @ Re
    Residuals_Re = A_re @ DRT_Re - EIS_data['Re']  # useful for Lambda optimization
    Z_Re = A_re @ DRT_Re + 1j * A_im @ DRT_Re  # Compute Z back from DRT
    Rs_Re = DRT_Re[-2]  # Get R
    L_Re = DRT_Re[-1]  # Get L
    DRT_Re = DRT_Re[:-2]  # Remove R and L from the DRT
    Rp_Re = -np.trapz(DRT_Re, np.log(f))  # Estimated polarization resistance

    # Combined Imaginary and real parts
    A_im_re = np.vstack([A_im, A_re])
    Im_Re = np.hstack([Im, Re])

    DRT_ImRe = np.linalg.inv(A_im_re.T @ A_im_re + parameters['Lambda'] * np.eye(A_im_re.shape[1])) @ A_im_re.T @ Im_Re
    Residuals_ImRe = A_im_re @ DRT_ImRe - Im_Re  # useful for Lambda optimization
    Z_ImRe = A_re @ DRT_ImRe + 1j * A_im @ DRT_ImRe  # Compute Z back from DRT
    Rs_ImRe = DRT_ImRe[-2]  # Get R
    L_ImRe = DRT_ImRe[-1]  # Get L
    DRT_ImRe = DRT_ImRe[:-2]  # Remove R and L from the DRT
    Rp_ImRe = -np.trapz(DRT_ImRe, np.log(f))  # Estimated polarization resistance

    # Create output structure of DataFrames
    DRT = {
        'Im': {  # Results for the imaginary part only
            'f': f,                  # Frequency array corresponding to tau
            'tau': tau,              # Relaxation times
            'g': DRT_Im,             # Distribution of relaxation times (DRT) for imaginary part
            'Re': np.real(Z_Im),     # Real part of the reconstructed impedance
            'Im': -np.imag(Z_Im),    # Imaginary part of the reconstructed impedance
            'Residuals': Residuals_Im  # Residuals for the imaginary part
        },
        'Re': {  # Results for the real part only
            'f': f,                  # Frequency array corresponding to tau
            'tau': tau,              # Relaxation times
            'g': DRT_Re,             # Distribution of relaxation times (DRT) for real part
            'Re': np.real(Z_Re),     # Real part of the reconstructed impedance
            'Im': -np.imag(Z_Re),    # Imaginary part of the reconstructed impedance
            'Residuals': Residuals_Re  # Residuals for the real part
        },
        'ReIm': {  # Results for the combined imaginary and real parts
            'f': f,                  # Frequency array corresponding to tau
            'tau': tau,              # Relaxation times
            'g': DRT_ImRe,           # Distribution of relaxation times (DRT) for combined parts
            'Re': np.real(Z_ImRe),   # Real part of the reconstructed impedance
            'Im': -np.imag(Z_ImRe)   # Imaginary part of the reconstructed impedance
        },
        'RL': {  # Extracted resistance and inductance values
            'Rs_Im': Rs_Im,          # Series resistance from imaginary part
            'Rp_Im': Rp_Im,          # Polarization resistance from imaginary part
            'L_Im': L_Im,            # Inductance from imaginary part
            'Rs_Re': Rs_Re,          # Series resistance from real part
            'Rp_Re': Rp_Re,          # Polarization resistance from real part
            'L_Re': L_Re,            # Inductance from real part
            'Rs_ImRe': Rs_ImRe,      # Series resistance from combined parts
            'Rp_ImRe': Rp_ImRe,      # Polarization resistance from combined parts
            'L_ImRe': L_ImRe         # Inductance from combined parts
        }
    }

    return DRT
