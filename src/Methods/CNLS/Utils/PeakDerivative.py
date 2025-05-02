import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

import matplotlib.pyplot as plt

# Define a Gaussian function for curve fitting
def gaussian(x, *params):
    y = np.zeros_like(x)
    for i in range(0, len(params), 3):
        amp = params[i]  # Amplitude of the Gaussian
        pos = params[i + 1]  # Position (log10 of frequency)
        width = params[i + 2]  # Width of the Gaussian
        y += amp * np.exp(-((np.log10(x) - pos) / width) ** 2)
    return y

# Function to analyze peaks in the derivative of a signal
def peak_derivative(drt, f, mode, nbr_peaks_fixed=5, f_fixed=None):
    fmin = np.min(f)  # Minimum frequency
    fmax = np.max(f)  # Maximum frequency

    # Compute first and second derivatives of the signal
    d_drt = np.gradient(drt)
    dd_drt = np.gradient(d_drt)

    # Find peaks in the absolute value of the first derivative
    peak_valley_shoulder_loc,_  = find_peaks(-np.abs(d_drt))
    m = dd_drt[peak_valley_shoulder_loc] < 0.00001  # Filter based on second derivative

    # Extract peak and shoulder locations
    peak_shoulder_loc = peak_valley_shoulder_loc[m]
    f_peak_shoulder = f[peak_shoulder_loc]
    x_peak_shoulder = drt[peak_shoulder_loc]

    # Filter peaks and shoulders within the frequency range
    in_freq_range = (fmin < f_peak_shoulder) & (f_peak_shoulder < fmax)
    f_peak_shoulder = f_peak_shoulder[in_freq_range]
    x_peak_shoulder = x_peak_shoulder[in_freq_range]

    # Peak selection based on the specified mode
    if mode == 'manual':
        nbr_peaks = nbr_peaks_fixed
        
        # Plot the graph
        plt.semilogx(f, drt, '-b', f_peak_shoulder, x_peak_shoulder, 'r*')
        plt.xlim([0.1 * fmin, 10 * fmax])
        plt.axvline(fmin, linestyle=':', color='k', linewidth=1.5)
        plt.axvline(fmax, linestyle=':', color='k', linewidth=1.5)

        # Get user-selected points
        points = plt.ginput(nbr_peaks, timeout=0)  # This returns a list of (x, y) tuples
        plt.show()
        
        # Extract x and y coordinates into separate arrays
        f_input = np.array([p[0] for p in points])  # Extract all x-coordinates
        y_input = np.array([p[1] for p in points])  # Extract all y-coordinates


    elif mode == 'auto':
        # Automatically use detected peaks and shoulders
        nbr_peaks = len(f_peak_shoulder)
        f_input = f_peak_shoulder
        y_input = x_peak_shoulder

    elif mode == 'fixed':
        # Use fixed frequency and number of peaks
        f_input = f_fixed
        nbr_peaks = nbr_peaks_fixed
        y_input = 0.1 * np.ones_like(f_input)  # Default amplitude for fixed mode

    # Prepare parameters and bounds for Gaussian fitting
    params = []
    bounds_lower = []
    bounds_upper = []
    for i in range(nbr_peaks):
        bounds_lower.extend([0, np.log10(0.1 * f_input[i]), 0])  # Lower bounds
        bounds_upper.extend([np.inf, np.log10(10 * f_input[i]), 1])  # Upper bounds
        params.extend([y_input[i], np.log10(f_input[i]), 0.5])  # Initial guesses

    # Perform Gaussian fitting
    popt, _ = curve_fit(gaussian, f, drt, p0=params, bounds=(bounds_lower, bounds_upper))

    # Extract results from the fitted parameters
    r_est = []  # Resistance estimates
    freq_est = []  # Frequency estimates
    widths = []  # Widths of the peaks
    for k in range(nbr_peaks):
        kk = 3 * k
        amp = popt[kk]  # Amplitude
        pos = popt[kk + 1]  # Position (log10 of frequency)
        width = popt[kk + 2]  # Width

        # Calculate resistance estimate
        r_est.append(amp * width / 0.3989)

        # Calculate frequency estimate
        freq_est.append(10 ** pos)

        # Calculate full width at half maximum (FWHM)
        sigma = width / 2
        widths.append(sigma * (2 * np.sqrt(2 * np.log(2))))

    # Calculate alpha estimates based on widths
    widths = np.array(widths)
    alpha_est = -0.0032 * widths ** 3 + 0.0525 * widths ** 2 - 0.3209 * widths + 0.9847

    # Sort results from highest to lowest frequency
    freq_est = np.array(freq_est)
    r_est = np.array(r_est)
    alpha_est = np.array(alpha_est)
    sorted_indices = np.argsort(freq_est)[::-1]
    freq_est = freq_est[sorted_indices]
    r_est = r_est[sorted_indices]
    alpha_est = alpha_est[sorted_indices]
    tau_est = 1 / 2 / np.pi / freq_est  # Calculate tau estimates

    return r_est, freq_est, alpha_est, nbr_peaks, tau_est
