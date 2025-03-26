import numpy as np
import pandas as pd
import Methods.DRT.Utils as fn

def Linear_KK(EIS_Data, Parameters):
    """
    Computed the linear KK according to:
    A Linear Kronig‐Kramers Transform Test for Immittance Data Validation,
    Bernard A. Boukamp, 10.1149/1.2044210
    Some signs had to be modified as they were wrong in the paper.
    Created by Guillaume Jeanmonod.

    Parameters:
        EIS_Data: pandas DataFrame containing at least f, Re, Im, omega.
                  Im should not have been multiplied by -1 (i.e. imag(Z_RC) < 0).
        Parameters: dictionary containing:
                    nRC: the number of RC elements used to compute the linear KK,
                         nRC < #DataPoints - 3.

    Returns:
        EIS_kk: pandas DataFrame containing the linear KK fit results.
        RC_kk: pandas DataFrame containing the resistance and time constant of each R//C element.
        RsLCinv_kk: pandas DataFrame containing the serial resistance, inductance, and inverse capacitance.
    """
    Re = EIS_Data['Re']
    Im = EIS_Data['Im']
    f = EIS_Data['f']
    omega = EIS_Data['omega']
    nRC = Parameters['nRC']

    n = len(f)  # number of data points

    if n < nRC + 3:
        raise ValueError("Error in Linear_KK: Number of elements larger than number of data points, reduce nRC")

    ww = 1 / (Re**2 + Im**2)  # weights for the least square fit
    M = nRC + 3  # Total number of elements M = number of RC + 1xR + 1xL + 1xC
    tau_RC = 1 / (2 * np.pi * np.logspace(np.log10(min(f)), np.log10(max(f)), nRC))  # Logspaced fixed time constants

    b = np.zeros((M, 1))
    A = np.zeros((M, M))

    # Building array of known terms
    b[0, 0] = np.sum(ww * Re)  # dS/dRs
    b[1, 0] = np.sum(ww * Im / omega)  # dS/dX2 where X2 = 1/C
    b[2, 0] = np.sum(ww * Im * omega)  # dS/dL

    for jj in range(nRC):
        b[jj + 3, 0] = np.sum(ww * ((Re - Im * omega * tau_RC[jj]) / (1 + (omega * tau_RC[jj])**2)))

    # Building matrix of coefficients A
    A[0, 0] = np.sum(ww)  # Rs
    A[1, 1] = np.sum(-ww / omega**2)  # X2
    A[1, 2] = np.sum(ww)  # L
    A[2, 1] = np.sum(-ww)  # X2
    A[2, 2] = np.sum(ww * omega**2)  # L

    for jj in range(nRC):
        A[0, jj + 3] = np.sum(ww / (1 + (omega * tau_RC[jj])**2))
        A[1, jj + 3] = -np.sum(ww * tau_RC[jj] / (1 + (omega * tau_RC[jj])**2))
        A[2, jj + 3] = -np.sum((ww * omega**2 * tau_RC[jj]) / (1 + (omega * tau_RC[jj])**2))

        for kk in range(nRC):
            A[kk + 3, 0] = np.sum(ww / (1 + (omega * tau_RC[kk])**2))
            A[kk + 3, 1] = -np.sum(ww * tau_RC[kk] / (1 + (omega * tau_RC[kk])**2))
            A[kk + 3, 2] = -np.sum((ww * omega**2 * tau_RC[kk]) / (1 + (omega * tau_RC[kk])**2))
            A[kk + 3, jj + 3] = np.sum((ww / (1 + (omega * tau_RC[kk])**2)) *
                                       ((1 + omega**2 * tau_RC[kk] * tau_RC[jj]) / (1 + (omega * tau_RC[jj])**2)))

    # Solving the linear system
    U, S, Vt = np.linalg.svd(A)
    X = np.dot(Vt.T, np.dot(U.T, b) / S.reshape(-1,1))

    Rs = X[0, 0]
    Cinv = X[1, 0]
    L = X[2, 0]
    R_RC = X[3:].flatten()

    # Evaluate the real and imaginary part of the fitted impedance (_kk)
    Re_kk, Im_kk = fn.Evaluate_Z_RC_L_C(R_RC, tau_RC, Rs, L, Cinv, omega)

    # Residuals in percent
    Z = Re + 1j * Im
    dr = ((Re - Re_kk) / np.abs(Z)) * 100
    di = ((Im - Im_kk) / np.abs(Z)) * 100

    # Generate output data
    EIS_kk = pd.DataFrame({
        "f": f,
        "Re": Re_kk,
        "Im": Im_kk,
        "tau": EIS_Data['tau'],
        "omega": omega,
        "dr": dr,
        "di": di,
        "Re_LCcorrect": Re_kk,
        "Im_LCcorrect": Im_kk - omega * L + (Cinv / omega)
    })

    RC_kk = pd.DataFrame({
        "R_RC": R_RC,
        "tau_RC": tau_RC
    })

    RsLCinv_kk = pd.DataFrame({
        "Rs": [Rs],
        'Rp': sum(R_RC),
        "L": [L],
        "Cinv": [Cinv]
    })

    return EIS_kk, RC_kk, RsLCinv_kk
