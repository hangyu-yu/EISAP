import numpy as np

def Evaluate_Z_RC_L_C(R_RC, tau_RC, Rs, L, Cinv, omega):
    """
    Evaluate the impedance of a number of R//C elements in series connected in
    series with an inductance L and a capacitor C
    Created by Guillaume Jeanmonod

    Parameters
    ----------
    R_RC : array_like
        Vector of the resistance associated with each R//C element
    tau_RC : array_like
        Vector of the time constant associated with each R//C element
    L : float
        Inductance
    Cinv : float
        Inverse of the capacitance (1/C)
    omega : array_like
        Vector of pulsation at which the impedance Z=Re+i*Im is evaluated

    Returns
    -------
    Re : ndarray
        Vector of the same length as omega containing the real part of the circuit impedance
    Im : ndarray
        Vector of the same length as omega containing the imaginary part of the circuit impedance
    """

    n = len(omega)  # number of frequency points

    Re = np.zeros(n)  # Real part of the circuit impedance
    Im = np.zeros(n)  # Imaginary part of the circuit impedance

    for i in range(n):  # for each frequency
        RealContribution = R_RC / (1 + (omega[i] * tau_RC) ** 2)
        ImaginaryContribution = (omega[i] * tau_RC * R_RC) / (1 + (omega[i] * tau_RC) ** 2)

        Re[i] = np.sum(RealContribution)  # Sum of the real part of the RC element contribution
        Im[i] = -np.sum(ImaginaryContribution)  # Sum of the imaginary part of the RC element contribution, added - sign

    Re = Re + Rs  # add Rs
    Im = Im + omega * L - (Cinv / omega)  # add L and C

    return Re, Im


