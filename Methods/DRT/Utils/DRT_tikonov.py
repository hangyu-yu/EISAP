import numpy as np
import pandas as pd

def DRT_tikonov(EIS_Data, Parameters):
    """
    Computed the DRT using tikonov regularization
    Based on Priscilla Caliandro thesis
    Created by Guilaume Jeanmonod
    Translated to Python by Hangyu Yu

    Parameters:
    EIS_Data (pd.DataFrame): A dataframe containing at least f, Zp, Zpp, omega
    Parameters (dict): A dictionary containing lambda (regularization parameter)

    Returns:
    dict: A dictionary containing DRT results
    """

    # Change the sign of the imaginary part
    EIS_Data['Zpp'] = -EIS_Data['Zpp']

    nFreq = len(EIS_Data['omega'])  # number of frequency points

    # Log spacing the RC elements use for the DRT
    log_MaxTau = np.log10(max(EIS_Data['tau']))
    log_MinTau = np.log10(min(EIS_Data['tau']))
    tau = np.logspace(log_MinTau, log_MaxTau, nFreq)
    f = 1 / (2 * np.pi * tau)
    dt = np.log(max(EIS_Data['tau']) / min(EIS_Data['tau'])) / (nFreq - 1)

    # Initialize A_im and A_re
    A_im = np.zeros((nFreq, nFreq))
    A_re = np.zeros((nFreq, nFreq))

    # Build A1 and A2 matrices column by column
    for j in range(nFreq):
        A_im[:, j] = dt * EIS_Data['omega'] * tau[j] / (1 + (EIS_Data['omega'] * tau[j]) ** 2)
        A_re[:, j] = dt / (1 + (EIS_Data['omega'] * tau[j]) ** 2)

    # Add serial resistance and inductance to A_re and A_im
    A_re = np.hstack([A_re, np.ones((nFreq, 1)), np.zeros((nFreq, 1))])
    A_im = np.hstack([A_im, np.zeros((nFreq, 1)), -EIS_Data['omega'].values.reshape(-1, 1)])

    # Solve linear least square problem A*g(tau)=Z with tikonov regularization (ridge regression)
    lambda_param = Parameters['lambda']

    # Imaginary part only
    DRT_Im = np.linalg.inv(A_im.T @ A_im + lambda_param * np.eye(A_im.shape[1])) @ A_im.T @ EIS_Data['Zpp']
    Residuals_Im = A_im @ DRT_Im - EIS_Data['Zpp']
    Z_Im = A_re @ DRT_Im + 1j * A_im @ DRT_Im
    Rs_Im = DRT_Im[-2]
    L_Im = DRT_Im[-1]
    DRT_Im = DRT_Im[:-2]
    Rp_Im = -np.trapz(DRT_Im, np.log(f))

    # Real part only
    DRT_Re = np.linalg.inv(A_re.T @ A_re + lambda_param * np.eye(A_re.shape[1])) @ A_re.T @ EIS_Data['Zp']
    Residuals_Re = A_re @ DRT_Re - EIS_Data['Zp']
    Z_Re = A_re @ DRT_Re + 1j * A_im @ DRT_Re
    Rs_Re = DRT_Re[-2]
    L_Re = DRT_Re[-1]
    DRT_Re = DRT_Re[:-2]
    Rp_Re = -np.trapz(DRT_Re, np.log(f))

    # Combined Imaginary and real parts
    A_im_re = np.vstack([A_im, A_re])
    Im_Re = np.hstack([EIS_Data['Zpp'], EIS_Data['Zp']])

    DRT_ImRe = np.linalg.inv(A_im_re.T @ A_im_re + lambda_param * np.eye(A_im_re.shape[1])) @ A_im_re.T @ Im_Re
    Residuals_ImRe = A_im_re @ DRT_ImRe - Im_Re
    Z_ImRe = A_re @ DRT_ImRe + 1j * A_im @ DRT_ImRe
    Rs_ImRe = DRT_ImRe[-2]
    L_ImRe = DRT_ImRe[-1]
    DRT_ImRe = DRT_ImRe[:-2]
    Rp_ImRe = -np.trapz(DRT_ImRe, np.log(f))

    # Create output structure of tables
    DRT = {
        'Im': pd.DataFrame({
            'f': f,
            'tau': tau,
            'g': DRT_Im,
            'Zp': np.real(Z_Im),
            'Zpp': -np.imag(Z_Im),
            'Residuals': Residuals_Im
        }),
        'Re': pd.DataFrame({
            'f': f,
            'tau': tau,
            'g': DRT_Re,
            'Zp': np.real(Z_Re),
            'Zpp': -np.imag(Z_Re),
            'Residuals': Residuals_Re
        }),
        'ImRe': pd.DataFrame({
            'f': f,
            'tau': tau,
            'g': DRT_ImRe,
            'Zp': np.real(Z_ImRe),
            'Zpp': -np.imag(Z_ImRe)
        }),
        'RL': pd.DataFrame({
            'Rs_Im': [Rs_Im],
            'Rp_Im': [Rp_Im],
            'L_Im': [L_Im],
            'Rs_Re': [Rs_Re],
            'Rp_Re': [Rp_Re],
            'L_Re': [L_Re],
            'Rs_ImRe': [Rs_ImRe],
            'Rp_ImRe': [Rp_ImRe],
            'L_ImRe': [L_ImRe]
        })
    }

    return DRT
