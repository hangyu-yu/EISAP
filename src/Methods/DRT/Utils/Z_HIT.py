import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.integrate import cumulative_trapezoid


def Z_HIT(EIS_Data, Parameters):
    """
    Z-HIT algorithm: reconstruct the impedance modulus from the phase angle.

    Based on:
        Ehm et al., "Z-HIT - A Simple Relation Between Impedance Modulus and
        Phase Angle, Providing a New Way to the Validation of Electrochemical
        Impedance Spectra", Electrochemical Society Proceedings Volume 2000-24.

    Core formula (Eq. [2]):
        ln|Z(ω₀)| ≈ C + (2/π) ∫[ω_s→ω₀] φ(ω) d(ln ω)  +  γ · dφ/d(ln ω)|ω₀
    with  γ = -π/6  (exact factor from Riemann Zeta function, Eq.[4] k=1 term)

    Processing steps (mirror of Fig. 4 in the paper):
        [1] Smooth the measured phase with a Savitzky-Golay polynomial
        [2] Numerically integrate the smoothed phase  → dominant PI term
        [3] Analytically differentiate the SG polynomial → correction term
        [4] Fit the single additive constant C by least-squares to measured |Z|

    Parameters
    ----------
    EIS_Data : pandas DataFrame
        Must contain the following columns:
            f       – frequency in Hz
            omega   – angular frequency (2π·f)
            Z_mod   – impedance modulus in Ohm
            phi     – phase angle in degrees (negative = capacitive)

    Parameters : dict
        Optional keys:
            poly_order   (int)   – Savitzky-Golay polynomial order  [default: 3]
            window_frac  (float) – SG window size as fraction of N  [default: 0.25]

    Returns
    -------
    EIS_zhit : pandas DataFrame
        f               – frequency / Hz
        omega           – angular frequency / rad s⁻¹
        Z_mod_meas      – original measured modulus / Ω
        Z_mod_zhit      – Z-HIT reconstructed modulus / Ω
        phi_deg         – original phase / °
        phi_smooth_deg  – Savitzky-Golay smoothed phase / °
        phase_integral  – (2/π) ∫ φ d(ln ω)  cumulative integral
        correction      – γ · dφ/d(ln ω)  correction term
        delta_lnZ       – ln|Z_meas| − ln|Z_zhit|  (log residual)
        delta_lnZ_pct   – delta_lnZ × 100  (≈ % error in |Z|)

    zhit_info : dict
        const         – fitted additive constant C
        gamma         – correction factor (always -π/6)
        window_length – actual SG window length used (odd integer)
        poly_order    – SG polynomial order used
    """
    f       = EIS_Data['f'].values.copy()
    Z_mod   = EIS_Data['Z_mod'].values.copy()
    phi_deg = EIS_Data['phi'].values.copy()
    omega   = EIS_Data['omega'].values.copy()

    poly_order  = Parameters.get('poly_order', 3)
    window_frac = Parameters.get('window_frac', 0.25)

    # γ = -π/6  (second coefficient of the Riemann Zeta expansion, Eq.[4] k=1)
    gamma = -np.pi / 6.0
    n     = len(f)

    # ── Sort ascending in frequency for integration ──────────────────────────
    idx_asc    = np.argsort(omega)
    omega_s    = omega[idx_asc]
    phi_deg_s  = phi_deg[idx_asc]
    Z_mod_s    = Z_mod[idx_asc]
    ln_omega_s = np.log(omega_s)
    phi_rad_s  = np.deg2rad(phi_deg_s)

    # ── [1] Savitzky-Golay smoothing of phase ─────────────────────────────────
    win = int(window_frac * n)
    win = win if win % 2 == 1 else win + 1       # must be odd
    win = max(win, poly_order + 2)
    win = win if win % 2 == 1 else win + 1
    win = min(win, n if n % 2 == 1 else n - 1)   # cannot exceed data length

    phi_smooth_s = savgol_filter(phi_rad_s, window_length=win, polyorder=poly_order)

    # ── [2] Numerical integration: (2/π) ∫ φ d(ln ω) ─────────────────────────
    phase_integral_s = (2.0 / np.pi) * cumulative_trapezoid(
        phi_smooth_s, ln_omega_s, initial=0.0)

    # ── [3] Analytical derivative: γ · dφ/d(ln ω) ────────────────────────────
    delta_ln = np.mean(np.diff(ln_omega_s))
    dphi_dlnomega_s = savgol_filter(
        phi_rad_s, window_length=win, polyorder=poly_order,
        deriv=1, delta=delta_ln)
    correction_s = gamma * dphi_dlnomega_s

    # ── [4] Fit additive constant via least-squares mean ─────────────────────
    ln_Z_no_const_s = phase_integral_s + correction_s
    ln_Z_meas_s     = np.log(Z_mod_s)
    const           = np.mean(ln_Z_meas_s - ln_Z_no_const_s)

    ln_Z_zhit_s  = const + ln_Z_no_const_s
    Z_mod_zhit_s = np.exp(ln_Z_zhit_s)

    # ── Residuals ─────────────────────────────────────────────────────────────
    delta_lnZ_s     = ln_Z_meas_s - ln_Z_zhit_s
    delta_lnZ_pct_s = delta_lnZ_s * 100.0

    # ── Map back to original frequency order ─────────────────────────────────
    idx_orig = np.argsort(idx_asc)

    EIS_zhit = pd.DataFrame({
        'f'             : f,
        'omega'         : omega,
        'Z_mod_meas'    : Z_mod,
        'Z_mod_zhit'    : Z_mod_zhit_s[idx_orig],
        'phi_deg'       : phi_deg,
        'phi_smooth_deg': np.rad2deg(phi_smooth_s)[idx_orig],
        'phase_integral': phase_integral_s[idx_orig],
        'correction'    : correction_s[idx_orig],
        'delta_lnZ'     : delta_lnZ_s[idx_orig],
        'delta_lnZ_pct' : delta_lnZ_pct_s[idx_orig],
    })

    zhit_info = {
        'const'        : const,
        'gamma'        : gamma,
        'window_length': win,
        'poly_order'   : poly_order,
    }
    return EIS_zhit, zhit_info
