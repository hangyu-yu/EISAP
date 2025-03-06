import numpy as np
import pandas as pd
from scipy.linalg import svd
from Methods.DRT.Utils import Evaluate_Z_RC_L_C

def Linear_KK(Re, Im, f, tau, omega, nRC):
    """
    Computed the linear KK according to 
    A Linear Kronig‐Kramers Transform Test for Immittance Data Validation,
    Bernard A. Boukamp, 10.1149/1.2044210
    Some signs had to be modified as they were wrong in the paper
    Created by Guillaume Jeanmonod in Matlab
    Translated to Python by Hangyu Yu
    Translation date: 2025-02-14
    """

    n = len(f)  # number of data points

    if n < nRC + 3:
        raise ValueError("Error in Linear_KK: Number of elements larger than number of data points, reduce nRC")

    ww = (Re**2 + Im**2)**(-1)  # weights for the least square fit
    M = nRC + 3  # Total number of elements M = number of RC + 1xR+ 1xL+ 1xC+
    tau_RC = 1 / (2 * np.pi * np.logspace(np.log10(max(f)), np.log10(min(f)), nRC))  # Logspaced fixed time constant of for the RC elements

    b = np.zeros((M, 1))
    A = np.zeros((M, M))

    b[0, 0] = np.sum(ww * Re)  # dS/dRs
    b[1, 0] = np.sum(ww * Im / omega)  # ds/dX2 where X2 = 1/C
    b[2, 0] = np.sum(ww * Im * omega)  # dS/dL

    for jj in range(nRC):
        b[jj + 3, 0] = np.sum(ww * ((Re - Im * omega * tau_RC[jj]) / (1 + (omega * tau_RC[jj])**2)))  # dS/dRk

    A[0, 0] = np.sum(ww)  # Rs
    A[0, 1] = 0  # X2
    A[0, 2] = 0  # L

    for jj in range(nRC):  # RC
        A[0, jj + 3] = np.sum(ww / (1 + (omega * tau_RC[jj])**2))

    A[1, 0] = 0  # Rs
    A[1, 1] = np.sum(-ww / (omega**2))  # X2
    A[1, 2] = np.sum(ww)  # L

    for jj in range(nRC):  # RC
        A[1, jj + 3] = -np.sum(ww * tau_RC[jj] / (1 + (omega * tau_RC[jj])**2))

    A[2, 0] = 0  # Rs
    A[2, 1] = np.sum(-ww)  # X2
    A[2, 2] = np.sum(ww * (omega**2))  # L

    for jj in range(nRC):
        A[2, jj + 3] = -np.sum((ww * (omega**2) * tau_RC[jj]) / (1 + (omega * tau_RC[jj])**2))

    for kk in range(nRC):
        A[kk + 3, 0] = np.sum(ww / (1 + (omega * tau_RC[kk])**2))  # Rs
        A[kk + 3, 1] = -np.sum(-ww * tau_RC[kk] / (1 + (omega * tau_RC[kk])**2))  # X2
        A[kk + 3, 2] = -np.sum((ww * (omega**2) * tau_RC[kk]) / (1 + (omega * tau_RC[kk])**2))  # L

        for jj in range(nRC):
            A[kk + 3, jj + 3] = np.sum((ww / (1 + (omega * tau_RC[kk])**2)) * ((1 + (omega**2) * tau_RC[kk] * tau_RC[jj]) / (1 + (omega * tau_RC[jj])**2)))

    U, S, Vt = svd(A)
    X = np.dot(Vt.T, np.dot(U.T, b) / S)

    Rs = X[0, 0]
    Cinv = X[1, 0]
    L = X[2, 0]
    R_RC = X[3:]

    Re_kk, Im_kk = Evaluate_Z_RC_L_C(R_RC, tau_RC, Rs, L, Cinv, omega)

    Z = Re + 1j * Im
    dr = ((Re - Re_kk) / np.abs(Z)) * 100
    di = ((Im - Im_kk) / np.abs(Z)) * 100

    EIS_kk = pd.DataFrame({
        'f': f,
        'Re': Re_kk,
        'Im': Im_kk,
        'tau': tau,
        'omega': omega,
        'dr': dr,
        'di': di
    })

    RC_kk = pd.DataFrame({
        'R_RC': R_RC.flatten(),
        'tau_RC': tau_RC
    })

    RsLCinv_kk = pd.DataFrame({
        'Rs': [Rs],
        'L': [L],
        'Cinv': [Cinv]
    })

    return EIS_kk, RC_kk, RsLCinv_kk
