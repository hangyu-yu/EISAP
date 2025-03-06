import numpy as np

def ConvertToASR(frequency):
    """
    ConvertToASR converts frequency to angular frequency (omega) and time constant (tau).

    Inputs:
    frequency (numpy array): Frequency.

    Returns:
    omega (numpy array): Angular frequency.
    tau (numpy array): Time constant.
    """
    omega = 2 * np.pi * frequency
    tau = 1 / (2 * np.pi * frequency)
    
    return omega, tau
