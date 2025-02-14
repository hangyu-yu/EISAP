import numpy as np

def evaluate_z_rc_l_c(R_RC, tau_RC, Rs, L, Cinv, omega):
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
    Zp : ndarray
        Vector of the same length as omega containing the real part of the circuit impedance
    Zpp : ndarray
        Vector of the same length as omega containing the imaginary part of the circuit impedance
    """

    n = len(omega)  # number of frequency points

    Zp = np.zeros(n)  # Real part of the circuit impedance
    Zpp = np.zeros(n)  # Imaginary part of the circuit impedance

    for i in range(n):  # for each frequency
        RealContribution = R_RC / (1 + (omega[i] * tau_RC) ** 2)
        ImaginaryContribution = (omega[i] * tau_RC * R_RC) / (1 + (omega[i] * tau_RC) ** 2)

        Zp[i] = np.sum(RealContribution)  # Sum of the real part of the RC element contribution
        Zpp[i] = -np.sum(ImaginaryContribution)  # Sum of the imaginary part of the RC element contribution, added - sign

    Zp = Zp + Rs  # add Rs
    Zpp = Zpp + omega * L - (Cinv / omega)  # add L and C

    return Zp, Zpp


