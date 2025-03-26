import numpy as np
import pandas as pd
import Methods.DRT.Utils as fn

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
    #                       Re = the real part of the resampled impedance
    #                       Im = the imaginary part of the resampled impedance
    #                       tau = the time constant of the resampled impedance
    #                       omega = the pulsation of the resampled impedance

    lf = np.log10(Parameters['fmin'])
    hf = np.log10(Parameters['fmax'])

    f = np.logspace(hf, lf, int((hf - lf) * Parameters['PointsPerDecade'] + 1))
    omega = 2 * np.pi * f

    Re, Im = fn.Evaluate_Z_RC_L_C(np.array(RC['R_RC']), np.array(RC['tau_RC']), np.array(RsLCinv['Rs']), np.array(RsLCinv['L']), np.array(RsLCinv['Cinv']), omega)

    parameters_dummy = {'CellArea': 1}  # dummy cell area for ConvertToASR
    Z = Re + 1j * Im
    EIS_resampled = pd.DataFrame({'f': f, 'Z': Z, 'Re': Re, 'Im': Im})
    EIS_resampled = fn.ConvertToASR(EIS_resampled, parameters_dummy)  # ConvertToASR only used to add tau and omega

    return EIS_resampled
