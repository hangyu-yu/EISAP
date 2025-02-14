import numpy as np
from Methods.DRT.Utils.Linear_KK import Linear_KK

def Linear_KK_mu(EIS_Data, Parameters):
    """
    Optimized linear KK based on
    M. Schönleber, 10.1016/j.electacta.2014.01.034

    Created by Dante Fronterotta in Matlab
    Modified by Guillaume Jeanmonod
    Translated by Hangyu Yu

    Parameters
    ----------
    EIS_Data : pd.DataFrame
        A table containing at least f, Zp, Zpp, omega.
        Im should not have been multiplied by -1 (i.e. imag(Z_RC) < 0).

    Parameters : dict
        A dictionary containing:
        mu_threshold : float
            The threshold used for the optimization of the number of RC elements
            used for the linear KK estimation according to Schönleber et. al.
            A good estimate is 0.85.
        nRCmax : int
            The maximum number of RC elements used to evaluate the linear KK.

    Returns
    -------
    EIS_kk : pd.DataFrame
        A table containing:
            f : frequency of the linear KK fit
            Zp : the real part of the linear KK fit
            Zpp : the imaginary part of the linear KK fit
            tau : the time constant of the linear KK fit
            omega : the pulsation of the linear KK fit
            dr : the relative error of the real part of linear KK fit in %
            di : the relative error of the imaginary part of linear KK fit in %

    RC_kk : pd.DataFrame
        A table containing the resistance and time constant of each R//C elements
        used in the linear KK fit.

    RsLCinv_kk : pd.DataFrame
        A table containing the serial resistance, the inductance and the inverse
        of the capacitance used in the linear KK fit.
    """
    
    for nRC in range(5, Parameters['nRCmax'] + 1):  # Add RC element until the mu criterion is satisfied
        Parameters['nRC'] = nRC
        EIS_kk, RC_kk, RsLCinv_kk = Linear_KK(EIS_Data, Parameters)
        Rk = RC_kk['R_RC']

        # Mu criterion M. Schönleber
        mu = 1 - np.sum(np.abs(Rk[Rk < 0])) / np.sum(Rk[Rk >= 0])
        if mu <= Parameters['mu_threshold']:
            break

    return EIS_kk, RC_kk, RsLCinv_kk
