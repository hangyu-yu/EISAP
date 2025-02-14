import numpy as np
import pandas as pd
from Methods.DRT.Utils import Evaluate_Z_RC_L_C, ConvertToASR

def ResampleEIS(RC, RsLCinv, Parameters):
    """
    ResampleEIS uses the results of the Linear KK transform to smooth and/or
    extrapolate the EIS data.

    The resampling/smoothing is performed by evaluating the contribution of
    each RC elements defined in the Linear KK test and also adds the 
    contribution of a serial resistance, an inductance and a capacitance.
    The resampled point are logarithmically spaced between a user defined 
    minimum and maximum frequency with a user defined number of point per
    decade.

    Created by Guillaume Jeanmonod
    """

    # Input
    # RC            is a table containing:
    #                   R_RC : the resistance of each R//C elements used for resampling
    #                   tau_RC : the time constant of each R//C elements used for resampling
    # 
    # RsLCinv       is a table containing:
    #                   Rs: the serial resistance used
    #                   L : an inductance
    #                   Cinv : the inverse of the capacitance used in the linear KK fit
    #
    # Parameters    is a table containing:
    #                   fmin : minimum frequency used for the resampling
    #                   fmax : maximum frequency used for the resampling
    #                   PointsPerDecade : number of points per decade used for
    #                                     the resampling

    # Output
    # EIS_resampled     is a table containing: 
    #                       f = frequency of the resampled impedance
    #                       Zp = the real part of the resampled impedance
    #                       Zpp = the imaginary part of the resampled impedance
    #                       tau = the time constant of the resampled impedance
    #                       omega = the pulsation of the resampled impedance

    lf = np.log10(min(Parameters['fmin']))
    hf = np.log10(max(Parameters['fmax']))

    f = np.logspace(hf, lf, int((hf - lf) * Parameters['PointsPerDecade'] + 1))
    omega = 2 * np.pi * f

    Zp, Zpp = Evaluate_Z_RC_L_C(RC['R_RC'], RC['tau_RC'], RsLCinv['Rs'], RsLCinv['L'], RsLCinv['Cinv'], omega)

    EIS_resampled = pd.DataFrame({'f': f, 'Zp': Zp, 'Zpp': Zpp})
    EIS_resampled = ConvertToASR(EIS_resampled, 1)  # ConvertToASR only used to add tau and omega

    return EIS_resampled
