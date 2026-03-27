"""
DRT_rbf.py  ─  Python port of DRTtools (Ciucci lab, MATLAB)
============================================================
Faithfully reproduces the core algorithms from:
  DRTtools-master/src/  (assemble_A_re.m, assemble_A_im.m,
                          assemble_M_1.m, assemble_M_2.m,
                          compute_epsilon.m, g_i.m, g_ii.m,
                          inner_prod_rbf_1.m, inner_prod_rbf_2.m,
                          quad_format.m, quad_format_combined.m,
                          NMLL_fct.m, HT_single_est.m, HMC_exact.m)

Reference:
  Wan, T. H., Saccoccio, M., Chen, C., & Ciucci, F. (2015).
  Influence of the discretization methods on the distribution of
  relaxation times deconvolution: implementing radial basis
  functions with DRTtools. Electrochimica Acta, 184, 483-499.

  Ciucci, F., & Chen, C. (2015). Analysis of electrochemical
  impedance spectroscopy data using the distribution of relaxation
  times: a Bayesian and hierarchical Bayesian approach.
  Electrochimica Acta, 167, 439-454.

Three inversion modes (matching DRT_tikhonov.py output structure):
  'Im'   – imaginary part only
  'Re'   – real part only
  'ReIm' – combined (default, recommended)

Two regularization strategies:
  'ridge' – manual lambda
  'bayes' – automatic lambda via empirical Bayes (NMLL optimisation)

Supported RBF types (same names as DRTtools):
  'Gaussian', 'C0 Matern', 'C2 Matern', 'C4 Matern', 'C6 Matern',
  'Inverse quadratic', 'Cauchy', 'Piecewise linear'
"""

import numpy as np
import pandas as pd
from collections import OrderedDict
from functools import lru_cache
from scipy import integrate, optimize
from scipy.linalg import toeplitz

try:
    from cvxopt import matrix, solvers

    HAS_CVXOPT = True
    solvers.options["show_progress"] = False
except ImportError:
    HAS_CVXOPT = False


_RBF_MATRIX_CACHE = OrderedDict()
_RBF_MATRIX_CACHE_MAX = 64


def _matrix_cache_key(freq, epsilon, rbf_type, der_used):
    freq_arr = np.ascontiguousarray(np.asarray(freq, dtype=np.float64).reshape(-1))
    return (
        int(freq_arr.size),
        freq_arr.tobytes(),
        float(epsilon),
        str(rbf_type),
        str(der_used),
    )


def _get_or_build_rbf_matrices(freq, omega, epsilon, rbf_type, der_used):
    key = _matrix_cache_key(freq, epsilon, rbf_type, der_used)
    cached = _RBF_MATRIX_CACHE.get(key)
    if cached is not None:
        _RBF_MATRIX_CACHE.move_to_end(key)
        return cached

    N = len(freq)
    A_re_drt = assemble_A_re(freq, epsilon, rbf_type)
    A_im_drt = assemble_A_im(freq, epsilon, rbf_type)
    M_core = assemble_M(freq, epsilon, rbf_type=rbf_type, der_used=der_used)

    A_re = np.zeros((N, N + 2))
    A_re[:, 1] = 1.0
    A_re[:, 2:] = A_re_drt

    A_im = np.zeros((N, N + 2))
    A_im[:, 0] = omega
    A_im[:, 2:] = A_im_drt

    M_ext = np.zeros((N + 2, N + 2))
    M_ext[:N, :N] = M_core

    result = (A_re, A_im, M_ext)
    _RBF_MATRIX_CACHE[key] = result
    _RBF_MATRIX_CACHE.move_to_end(key)

    if len(_RBF_MATRIX_CACHE) > _RBF_MATRIX_CACHE_MAX:
        _RBF_MATRIX_CACHE.popitem(last=False)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# 1.  compute_epsilon  (port of compute_epsilon.m)
# ══════════════════════════════════════════════════════════════════════════════
@lru_cache(maxsize=16)
def _rbf_fwhm_coeff(rbf_type):
    """Return 2×half-width at half-maximum for each RBF (in ε-normalised units)."""
    if rbf_type == "Gaussian":
        return 2.0 * np.sqrt(np.log(2.0))
    elif rbf_type == "C0 Matern":
        return 2.0 * np.log(2.0)
    elif rbf_type == "C2 Matern":
        return 2.0 * optimize.brentq(
            lambda x: np.exp(-abs(x)) * (1 + abs(x)) - 0.5, 0.1, 10.0
        )
    elif rbf_type == "C4 Matern":
        return 2.0 * optimize.brentq(
            lambda x: 1 / 3 * np.exp(-abs(x)) * (3 + 3 * abs(x) + x**2) - 0.5, 0.1, 10.0
        )
    elif rbf_type == "C6 Matern":
        return 2.0 * optimize.brentq(
            lambda x: (
                1 / 15 * np.exp(-abs(x)) * (15 + 15 * abs(x) + 6 * x**2 + abs(x) ** 3)
                - 0.5
            ),
            0.1,
            10.0,
        )
    elif rbf_type == "Inverse quadratic":
        return 2.0 * optimize.brentq(lambda x: 1 / (1 + x**2) - 0.5, 0.1, 10.0)
    elif rbf_type == "Cauchy":
        return 2.0 * optimize.brentq(lambda x: 1 / (1 + abs(x)) - 0.5, 0.1, 10.0)
    elif rbf_type == "Piecewise linear":
        return 0.0
    else:
        raise ValueError(f"Unknown rbf_type: {rbf_type}")


def compute_epsilon(
    freq, coeff=0.5, rbf_type="Gaussian", shape_control="FWHM Coefficient"
):
    """
    Compute RBF shape parameter ε  (port of compute_epsilon.m).

    'FWHM Coefficient': ε = coeff × FWHM_coeff / Δ(ln τ)
    'Shape Factor':     ε = coeff  (direct)
    """
    if shape_control == "FWHM Coefficient":
        # DRTtools expects freq descending (high→low), so tau = 1/f is ascending
        # Use abs() to be robust to either ordering
        delta = abs(np.mean(np.diff(np.log(1.0 / freq))))
        return coeff * _rbf_fwhm_coeff(rbf_type) / delta
    elif shape_control == "Shape Factor":
        return float(coeff)
    else:
        raise ValueError(f"Unknown shape_control: {shape_control}")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  RBF kernel  φ(x)
# ══════════════════════════════════════════════════════════════════════════════
def _rbf(x, epsilon, rbf_type):
    ax = np.abs(epsilon * x)
    if rbf_type == "Gaussian":
        return np.exp(-((epsilon * x) ** 2))
    elif rbf_type == "C0 Matern":
        return np.exp(-ax)
    elif rbf_type == "C2 Matern":
        return np.exp(-ax) * (1 + ax)
    elif rbf_type == "C4 Matern":
        return 1 / 3 * np.exp(-ax) * (3 + 3 * ax + ax**2)
    elif rbf_type == "C6 Matern":
        return 1 / 15 * np.exp(-ax) * (15 + 15 * ax + 6 * ax**2 + ax**3)
    elif rbf_type == "Inverse quadratic":
        return 1.0 / (1 + (epsilon * x) ** 2)
    elif rbf_type == "Cauchy":
        return 1.0 / (1 + ax)
    else:
        raise ValueError(f"RBF {rbf_type} not supported")


# ══════════════════════════════════════════════════════════════════════════════
# 3.  g_i, g_ii  ─  exact A-matrix element integrals (port of g_i.m / g_ii.m)
#     x = ln(τ) − ln(τ_m),  α = 2π f_n / f_m
#     g_i  = ∫ φ(x) / (1 + α² e^{2x}) dx
#     g_ii = ∫ φ(x) · α e^x / (1 + α² e^{2x}) dx
# ══════════════════════════════════════════════════════════════════════════════
def g_i(freq_n, freq_m, epsilon, rbf_type):
    alpha = 2.0 * np.pi * freq_n / freq_m
    # Limit integration range to where RBF is non-negligible (avoid overflow)
    x_range = max(10.0 / (epsilon + 1e-10), 30.0)

    def integrand(x):
        with np.errstate(over="ignore", invalid="ignore"):
            rbf_val = _rbf(x, epsilon, rbf_type)
            denom = 1.0 + alpha**2 * np.exp(2 * x)
            return np.where(rbf_val < 1e-300, 0.0, rbf_val / denom)

    val, _ = integrate.quad(
        integrand, -x_range, x_range, limit=300, epsrel=1e-8, epsabs=1e-12
    )
    return val


def g_ii(freq_n, freq_m, epsilon, rbf_type):
    alpha = 2.0 * np.pi * freq_n / freq_m
    x_range = max(10.0 / (epsilon + 1e-10), 30.0)

    def integrand(x):
        with np.errstate(over="ignore", invalid="ignore"):
            rbf_val = _rbf(x, epsilon, rbf_type)
            ex = np.exp(np.clip(x, -700, 700))
            denom = 1.0 + alpha**2 * ex**2
            return np.where(rbf_val < 1e-300, 0.0, rbf_val * alpha * ex / denom)

    val, _ = integrate.quad(
        integrand, -x_range, x_range, limit=300, epsrel=1e-8, epsabs=1e-12
    )
    return val


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Assemble A matrices  (port of assemble_A_re.m / assemble_A_im.m)
#     Toeplitz trick when frequencies are evenly log-spaced (tol < 1 %).
# ══════════════════════════════════════════════════════════════════════════════
def _is_log_spaced(freq, tol=0.01):
    # Use abs(mean) so ascending frequencies are handled correctly.
    # Without abs, a non-uniform ascending sequence gives std/mean < 0,
    # which is always < tol → Toeplitz incorrectly enabled.
    d = np.diff(np.log(1.0 / freq))
    return np.std(d) / abs(np.mean(d)) < tol


def assemble_A_re(freq, epsilon, rbf_type="Gaussian"):
    """A_re matrix (N×N), DRT part only (no Rs/L columns)."""
    N = len(freq)
    if rbf_type == "Piecewise linear":
        A = np.zeros((N, N))
        lt = np.log(1.0 / freq)
        for n in range(N):
            for m in range(N):
                dt = (
                    lt[m + 1] - lt[m]
                    if m == 0
                    else lt[m] - lt[m - 1]
                    if m == N - 1
                    else lt[m + 1] - lt[m - 1]
                )
                A[n, m] = 0.5 / (1 + (2 * np.pi * freq[n] / freq[m]) ** 2) * dt
        return A
    if _is_log_spaced(freq):
        C = np.array([g_i(freq[n], freq[0], epsilon, rbf_type) for n in range(N)])
        R = np.array([g_i(freq[0], freq[m], epsilon, rbf_type) for m in range(N)])
        return toeplitz(C, R)
    A = np.zeros((N, N))
    for n in range(N):
        for m in range(N):
            A[n, m] = g_i(freq[n], freq[m], epsilon, rbf_type)
    return A


def assemble_A_im(freq, epsilon, rbf_type="Gaussian"):
    """A_im matrix (N×N), DRT part only.  Element = −g_ii (DRTtools sign)."""
    N = len(freq)
    if rbf_type == "Piecewise linear":
        A = np.zeros((N, N))
        lt = np.log(1.0 / freq)
        for n in range(N):
            for m in range(N):
                dt = (
                    lt[m + 1] - lt[m]
                    if m == 0
                    else lt[m] - lt[m - 1]
                    if m == N - 1
                    else lt[m + 1] - lt[m - 1]
                )
                alpha = 2 * np.pi * freq[n] / freq[m]
                A[n, m] = -0.5 * alpha / (1 + alpha**2) * dt
        return A
    if _is_log_spaced(freq):
        C = np.array([-g_ii(freq[n], freq[0], epsilon, rbf_type) for n in range(N)])
        R = np.array([-g_ii(freq[0], freq[m], epsilon, rbf_type) for m in range(N)])
        return toeplitz(C, R)
    A = np.zeros((N, N))
    for n in range(N):
        for m in range(N):
            A[n, m] = -g_ii(freq[n], freq[m], epsilon, rbf_type)
    return A


# ══════════════════════════════════════════════════════════════════════════════
# 5.  inner_prod_rbf_1/2  ─  analytical ∫ dφ_n/dy · dφ_m/dy dy
#     (port of inner_prod_rbf_1.m / inner_prod_rbf_2.m)
# ══════════════════════════════════════════════════════════════════════════════
def inner_prod_rbf_1(freq_n, freq_m, epsilon, rbf_type):
    a = epsilon * np.log(freq_n / freq_m)
    if rbf_type == "Gaussian":
        return -epsilon * (-1 + a**2) * np.exp(-(a**2) / 2) * np.sqrt(np.pi / 2)
    elif rbf_type == "C0 Matern":
        return epsilon * (1 - abs(a)) * np.exp(-abs(a))
    elif rbf_type == "C2 Matern":
        return epsilon / 6 * (3 + 3 * abs(a) - abs(a) ** 3) * np.exp(-abs(a))
    elif rbf_type == "C4 Matern":
        return (
            epsilon
            / 30
            * (
                105
                + 105 * abs(a)
                + 30 * abs(a) ** 2
                - 5 * abs(a) ** 3
                - 5 * abs(a) ** 4
                - abs(a) ** 5
            )
            * np.exp(-abs(a))
        )
    elif rbf_type == "C6 Matern":
        return (
            epsilon
            / 140
            * (
                10395
                + 10395 * abs(a)
                + 3780 * abs(a) ** 2
                + 315 * abs(a) ** 3
                - 210 * abs(a) ** 4
                - 84 * abs(a) ** 5
                - 14 * abs(a) ** 6
                - abs(a) ** 7
            )
            * np.exp(-abs(a))
        )
    elif rbf_type == "Inverse quadratic":
        return 4 * epsilon * (4 - 3 * a**2) * np.pi / (4 + a**2) ** 3
    elif rbf_type == "Cauchy":
        if a == 0:
            return 2 / 3 * epsilon
        num = abs(a) * (2 + abs(a)) * (4 + 3 * abs(a) * (2 + abs(a))) - 2 * (
            1 + abs(a)
        ) ** 2 * (4 + abs(a) * (2 + abs(a))) * np.log(1 + abs(a))
        den = abs(a) ** 3 * (1 + abs(a)) * (2 + abs(a)) ** 3
        return 4 * epsilon * num / den
    else:
        raise ValueError(f"inner_prod_rbf_1 not implemented for {rbf_type}")


def inner_prod_rbf_2(freq_n, freq_m, epsilon, rbf_type):
    a = epsilon * np.log(freq_n / freq_m)
    if rbf_type == "Gaussian":
        return (
            epsilon**3
            * (3 - 6 * a**2 + a**4)
            * np.exp(-(a**2) / 2)
            * np.sqrt(np.pi / 2)
        )
    elif rbf_type == "C0 Matern":
        return epsilon**3 * (1 + abs(a)) * np.exp(-abs(a))
    elif rbf_type == "C2 Matern":
        return (
            epsilon**3
            / 6
            * (3 + 3 * abs(a) - 6 * abs(a) ** 2 + abs(a) ** 3)
            * np.exp(-abs(a))
        )
    elif rbf_type == "C4 Matern":
        return (
            epsilon**3
            / 30
            * (45 + 45 * abs(a) - 15 * abs(a) ** 3 - 5 * abs(a) ** 4 + abs(a) ** 5)
            * np.exp(-abs(a))
        )
    elif rbf_type == "C6 Matern":
        return (
            epsilon**3
            / 140
            * (
                2835
                + 2835 * abs(a)
                + 630 * abs(a) ** 2
                - 315 * abs(a) ** 3
                - 210 * abs(a) ** 4
                - 42 * abs(a) ** 5
                + abs(a) ** 7
            )
            * np.exp(-abs(a))
        )
    elif rbf_type == "Inverse quadratic":
        return 48 * (16 + 5 * a**2 * (-8 + a**2)) * np.pi * epsilon**3 / (4 + a**2) ** 5
    elif rbf_type == "Cauchy":
        if a == 0:
            return 8 / 5 * epsilon**3
        num = abs(a) * (2 + abs(a)) * (
            -96
            + abs(a)
            * (2 + abs(a))
            * (-30 + abs(a) * (2 + abs(a)) * (4 + abs(a) * (2 + abs(a))))
        ) + 12 * (1 + abs(a)) ** 2 * (
            16 + abs(a) * (2 + abs(a)) * (12 + abs(a) * (2 + abs(a)))
        ) * np.log(1 + abs(a))
        den = abs(a) ** 5 * (1 + abs(a)) * (2 + abs(a)) ** 5
        return 8 * epsilon**3 * num / den
    else:
        raise ValueError(f"inner_prod_rbf_2 not implemented for {rbf_type}")


# ══════════════════════════════════════════════════════════════════════════════
# 6.  assemble_M  (port of assemble_M_1.m / assemble_M_2.m)
# ══════════════════════════════════════════════════════════════════════════════
def assemble_M(freq, epsilon, rbf_type="Gaussian", der_used="1st order"):
    """Derivative regularization matrix M (N×N core block)."""
    N = len(freq)
    ip = inner_prod_rbf_1 if der_used == "1st order" else inner_prod_rbf_2

    if rbf_type == "Piecewise linear":
        lt = np.log(1.0 / freq)
        L = np.zeros((N - 1, N))
        for k in range(N - 1):
            d = lt[k + 1] - lt[k]
            L[k, k] = -1 / d
            L[k, k + 1] = 1 / d
        return L.T @ L

    if _is_log_spaced(freq):
        C = np.array([ip(freq[n], freq[0], epsilon, rbf_type) for n in range(N)])
        R = np.array([ip(freq[0], freq[m], epsilon, rbf_type) for m in range(N)])
        return toeplitz(C, R)

    M = np.zeros((N, N))
    for n in range(N):
        for m in range(N):
            M[n, m] = ip(freq[n], freq[m], epsilon, rbf_type)
    return M


# ══════════════════════════════════════════════════════════════════════════════
# 7.  map_array_to_gamma  (port of map_array_to_gamma.m)
# ══════════════════════════════════════════════════════════════════════════════
def map_array_to_gamma(tau_fine, tau_colloc, x, epsilon, rbf_type):
    """γ(τ_fine) = Σ_j x_j · φ(ln(τ_fine) − ln(τ_j))"""
    if rbf_type == "Piecewise linear":
        return x.copy()
    y_fine = -np.log(tau_fine)
    y_c = -np.log(tau_colloc)
    gamma = np.array([np.dot(x, _rbf(yf - y_c, epsilon, rbf_type)) for yf in y_fine])
    return gamma


# ══════════════════════════════════════════════════════════════════════════════
# 8.  NMLL_fct  (port of NMLL_fct.m)
#     Negative Marginal Log-Likelihood for Bayesian hyperparameter selection.
#
#     Bayesian model:
#       Prior on γ:   p(γ) ∝ exp(−½ γ^T W γ)
#                     W = σ_β^{-2} I + σ_λ^{-2} M
#       Likelihood:   Z | γ ~ N(A γ, σ_n² I)
#       Posterior:    γ | Z ~ N(μ_γ, Σ_γ)
#                     K_agm = σ_n^{-2} A^T A + W
#                     μ_γ   = σ_n^{-2} K_agm^{-1} A^T Z
#                     Σ_γ   = K_agm^{-1}
# ══════════════════════════════════════════════════════════════════════════════
def NMLL_fct(log_theta, Z, A, M, N_freqs, N_taus):
    sigma_n = np.exp(log_theta[0])
    sigma_beta = np.exp(log_theta[1])
    sigma_lambda = np.exp(log_theta[2])

    W = (1 / sigma_beta**2) * np.eye(N_taus + 1) + (1 / sigma_lambda**2) * M
    W = 0.5 * (W + W.T)
    K_agm = (1 / sigma_n**2) * (A.T @ A) + W
    K_agm = 0.5 * (K_agm + K_agm.T)

    try:
        L_W = np.linalg.cholesky(W)
        L_agm = np.linalg.cholesky(K_agm)
    except np.linalg.LinAlgError:
        return 1e20

    u = np.linalg.solve(L_agm.T, np.linalg.solve(L_agm, A.T @ Z))
    mu_x = (1 / sigma_n**2) * u
    E_mu = 0.5 / sigma_n**2 * np.dot(A @ mu_x - Z, A @ mu_x - Z) + 0.5 * mu_x @ (
        W @ mu_x
    )

    nmll = -(
        np.sum(np.log(np.diag(L_W)))
        - np.sum(np.log(np.diag(L_agm)))
        - 0.5 * N_freqs * np.log(sigma_n**2)
        - E_mu
        - 0.5 * N_freqs * np.log(2 * np.pi)
    )
    return nmll


# ══════════════════════════════════════════════════════════════════════════════
# 9.  HMC_exact  (port of HMC_exact.m — Pakman & Paninski, arXiv 1208.4118)
#     Sample from truncated Gaussian N(μ, Σ) subject to F x + g > 0.
# ══════════════════════════════════════════════════════════════════════════════
def HMC_exact(F, g, M_mat, mu_r, cov, n_samples, initial_X):
    if cov:
        mu = mu_r.copy()
        g = g + F @ mu
        R = np.linalg.cholesky(M_mat).T
        F = F @ R.T
        initial_X = np.linalg.solve(R.T, initial_X - mu)
    else:
        r = mu_r.copy()
        R = np.linalg.cholesky(M_mat).T
        mu = np.linalg.solve(R, np.linalg.solve(R.T, r))
        g = g + F @ mu
        F = F @ np.linalg.inv(R)
        initial_X = R @ (initial_X - mu)

    d = len(initial_X)
    nearzero = 1e4 * np.finfo(float).eps
    Xs = np.zeros((d, n_samples))
    Xs[:, 0] = initial_X
    last_X = initial_X.copy()
    F2 = np.sum(F**2, axis=1)
    Ft = F.T
    i = 1
    while i < n_samples:
        V0 = np.random.randn(d)
        X = last_X.copy()
        T = np.pi / 2
        tt = 0.0
        j = -1
        while True:
            a = V0.copy()
            b = X.copy()
            fa = F @ a
            fb = F @ b
            U = np.sqrt(fa**2 + fb**2)
            phi = np.arctan2(-fa, fb)
            pn = np.abs(g / (U + 1e-300)) <= 1
            inds = np.where(pn)[0]
            if len(inds) > 0:
                t1 = -phi[pn] + np.arccos(-g[pn] / (U[pn] + 1e-300))
                t1 = np.where(t1 < 0, t1 + 2 * np.pi, t1)
                if j >= 0 and pn[j]:
                    cs = np.cumsum(pn)
                    idx = int(cs[j]) - 1
                    if idx < len(t1):
                        if (
                            abs(t1[idx]) < nearzero
                            or abs(t1[idx] - 2 * np.pi) < nearzero
                        ):
                            t1[idx] = np.inf
                mt = np.min(t1)
                m_ind = inds[np.argmin(t1)]
                j = int(m_ind)
            else:
                mt = T
            tt += mt
            if tt >= T:
                mt -= tt - T
                stop = True
            else:
                stop = False
            X = a * np.sin(mt) + b * np.cos(mt)
            V = a * np.cos(mt) - b * np.sin(mt)
            if stop:
                break
            qj = F[j, :] @ V / F2[j]
            V0 = V - 2 * qj * Ft[:, j]
        if np.all(F @ X + g > 0):
            Xs[:, i] = X
            last_X = X.copy()
            i += 1

    return R.T @ Xs + mu[:, None] if cov else np.linalg.solve(R, Xs) + mu[:, None]


# ══════════════════════════════════════════════════════════════════════════════
# 10.  Main function  DRT_rbf
# ══════════════════════════════════════════════════════════════════════════════
def DRT_rbf(EIS_data, parameters):
    """
    DRT via Gaussian RBF discretization with ridge or Bayesian regularization.
    Full Python port of DRTtools (Ciucci lab).

    Parameters
    ----------
    EIS_data : dict or pd.DataFrame
               Required fields: f, Re, Im (or f, Zre, Zim).
               Im NOT sign-flipped (Im of RC < 0).  Freq highest→lowest.
    parameters : dict
        'lambda'        – regularization parameter
        'rbf_type'      – default 'Gaussian'
        'coeff'         – FWHM coefficient, default 0.5
        'shape_control' – 'FWHM Coefficient' (default) or 'Shape Factor'
        'der_used'      – '1st order' (default) or '2nd order'
        'method'        – 'ridge' (default) or 'bayes'
        'fit_inductance'– whether to fit inductance term L (default False)
        'theta0'        – initial [σ_n, σ_β, σ_λ] for Bayes
        'n_samples'     – HMC samples for credible interval (default 0 = skip)

    Returns
    -------
    dict with same keys as DRT_tikhonov:
        'Im', 'Re', 'ReIm' → {'f','tau','g','g_coeff','Re','Im','Residuals'}
        'RL'               → scalar parameters + epsilon + lambda_eff
    Bayesian mode adds: 'g_mean','g_std','g_lower','g_upper','theta_opt'
    """
    verbose = bool(parameters.get("verbose", False))

    def _log(msg):
        if verbose:
            print(msg)

    def _normalize_eis_input(eis_data):
        """Accept dict or DataFrame and return a sanitized DataFrame with f/Re/Im/omega/tau."""
        if isinstance(eis_data, pd.DataFrame):
            data_local = eis_data.copy()
        elif isinstance(eis_data, dict):
            if "f" not in eis_data:
                raise ValueError("EIS_data is missing required key 'f'.")

            re_key = "Re" if "Re" in eis_data else "Zre" if "Zre" in eis_data else None
            im_key = "Im" if "Im" in eis_data else "Zim" if "Zim" in eis_data else None
            if re_key is None or im_key is None:
                raise ValueError("EIS_data must contain Re/Im (or Zre/Zim).")

            f_arr = np.asarray(eis_data["f"], dtype=float).reshape(-1)
            re_arr = np.asarray(eis_data[re_key], dtype=float).reshape(-1)
            im_arr = np.asarray(eis_data[im_key], dtype=float).reshape(-1)

            n = min(len(f_arr), len(re_arr), len(im_arr))
            if n < 2:
                raise ValueError("EIS_data must contain at least two valid points.")

            data_local = pd.DataFrame(
                {
                    "f": f_arr[:n],
                    "Re": re_arr[:n],
                    "Im": im_arr[:n],
                }
            )
        else:
            raise TypeError("EIS_data must be a dict or pandas.DataFrame.")

        required_cols = {"f", "Re", "Im"}
        if not required_cols.issubset(set(data_local.columns)):
            missing = sorted(required_cols - set(data_local.columns))
            raise ValueError(f"EIS_data is missing required columns: {missing}")

        # Keep numeric/finite rows and positive frequencies only.
        data_local = data_local.copy()
        data_local["f"] = pd.to_numeric(data_local["f"], errors="coerce")
        data_local["Re"] = pd.to_numeric(data_local["Re"], errors="coerce")
        data_local["Im"] = pd.to_numeric(data_local["Im"], errors="coerce")
        data_local = data_local[np.isfinite(data_local["f"]) & np.isfinite(data_local["Re"]) & np.isfinite(data_local["Im"]) & (data_local["f"] > 0)]

        if len(data_local) < 2:
            raise ValueError("EIS_data has fewer than two valid data points after filtering.")

        # DRTtools convention: descending frequency.
        data_local = data_local.sort_values("f", ascending=False).reset_index(drop=True)

        if "tau" not in data_local.columns:
            data_local["tau"] = 1 / (2 * np.pi * data_local["f"])
        if "omega" not in data_local.columns:
            data_local["omega"] = 2 * np.pi * data_local["f"]

        return data_local

    data = _normalize_eis_input(EIS_data)

    freq = data["f"].values
    omega = data["omega"].values
    b_re = data["Re"].values
    b_im = data["Im"].values  # Z'' from EIS data (MATLAB convention, negative for RC)
    N = len(freq)

    rbf_type = parameters.get("rbf_type", "Gaussian")
    coeff = parameters.get("coeff", 0.5)
    shape_control = parameters.get("shape_control", "FWHM Coefficient")
    der_used = parameters.get("der_used", "1st order")
    method = parameters.get("method", "ridge")
    fit_inductance = bool(parameters.get("fit_inductance", False))
    lam = parameters["lambda"]
    n_samples = parameters.get("n_samples", 0)

    tau_c = 1.0 / (2 * np.pi * freq)

    # ── ε ──────────────────────────────────────────────────────────────────
    epsilon = compute_epsilon(
        freq, coeff=coeff, rbf_type=rbf_type, shape_control=shape_control
    )
    _log(f"  ε = {epsilon:.4f}  rbf = {rbf_type}")

    # ── A/M matrices (cached by frequency grid and RBF settings) ───────────
    A_re, A_im, M_ext = _get_or_build_rbf_matrices(
        freq, omega, epsilon, rbf_type, der_used
    )

    # ── Bayesian mode: DRTtools exact method ─────────────────────────────────
    # DRTtools bayesian_button_Callback:
    #   1. Run ridge regression → x_ridge
    #   2. sigma_n = std(residuals)
    #   3. Sigma_inv = (1/sigma_n^2)(A^T A + lambda * M)
    #      mu       = Sigma_inv^{-1} * (1/sigma_n^2) * A^T b  [posterior mean]
    #   4. HMC samples gamma ONLY (not Rs/L), with x_ridge as initial point
    # Note: NMLL_fct is only for the BHT validation mode, not used here.
    lam_use = lam
    sigma_n_bayes = None
    Sigma_gamma = None
    mu_gamma_bayes = None

    # ── Solve: port of DRTtools quadprog ─────────────────────────────────────
    # min (1/2)*x'*H*x + f'*x   s.t. G*x <= h, x >= 0
    # DRTtools: G=-I, h=0
    def solve(A_use, b_use, lam_s=None, active_idx=None):
        if lam_s is None:
            lam_s = lam_use
        n_full = A_use.shape[1]

        if active_idx is None:
            active_idx = np.arange(n_full)
        active_idx = np.asarray(active_idx, dtype=int).reshape(-1)
        if active_idx.size == 0:
            return np.zeros(n_full, dtype=float)

        A_red = A_use[:, active_idx]
        M_red = M_ext[np.ix_(active_idx, active_idx)]
        n_vars = A_red.shape[1]

        # quad_format_combined: H = 2*(A'A + lambda*M), c = -2*A'b
        H_matlab = 2 * (A_red.T @ A_red + lam_s * M_red)
        H_matlab = 0.5 * (H_matlab + H_matlab.T)
        c_matlab = -2 * (b_use @ A_red)

        if HAS_CVXOPT:
            # Use cvxopt for accurate QP solution (matches MATLAB quadprog)
            G = matrix(-np.eye(n_vars))
            h = matrix(np.zeros(n_vars))
            sol = solvers.qp(matrix(H_matlab), matrix(c_matlab), G, h)
            x_red = np.array(sol["x"]).flatten()
        else:
            # Fallback to scipy L-BFGS-B
            def obj(x):
                return 0.5 * x @ H_matlab @ x + c_matlab @ x

            def grad(x):
                return H_matlab @ x + c_matlab

            bounds = [(0, None)] * n_vars
            r = optimize.minimize(
                obj,
                np.ones(n_vars),
                jac=grad,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 10000, "ftol": 1e-15},
            )
            x_red = r.x

        x_full = np.zeros(n_full, dtype=float)
        x_full[active_idx] = x_red
        return x_full

    # x order: [L, Rs, g_1...g_N].
    # Re-only fit cannot identify L (A_re[:,0] == 0) -> fix L=0.
    # Im-only fit cannot identify Rs (A_im[:,1] == 0) -> fix Rs=0.
    # Optional DRTtools-like setting: disable inductance fitting by fixing L=0.
    idx_re_active = np.r_[1, np.arange(2, N + 2)]
    idx_im_active = np.r_[0, np.arange(2, N + 2)] if fit_inductance else np.arange(2, N + 2)
    idx_reim_active = np.arange(N + 2) if fit_inductance else np.r_[1, np.arange(2, N + 2)]

    x_Im = solve(A_im, b_im, active_idx=idx_im_active)
    x_Re = solve(A_re, b_re, active_idx=idx_re_active)
    x_ReIm = solve(
        np.vstack([A_im, A_re]),
        np.hstack([b_im, b_re]),
        active_idx=idx_reim_active,
    )

    if method == "bayes":
        # ── DRTtools Bayesian: x_ridge = DRT result; mu/Sigma for HMC only ──
        # gamma_ridge_fine (plotted DRT) = x_ridge[2:] = x_ReIm[:N]
        # mu (posterior mean for HMC distribution) is computed separately
        # HMC initial_X = x_ridge_gamma (NOT mu)
        A_comb = np.vstack([A_im, A_re])
        b_comb = np.hstack([b_im, b_re])
        res_ridge = A_comb @ x_ReIm - b_comb
        sigma_n_b = max(float(np.std(res_ridge)), 1e-12)
        # Posterior precision (full N+2 x N+2):
        # Sigma_inv = (1/sigma_n²)(A'A + lambda*M)
        Sigma_inv_full = (1 / sigma_n_b**2) * (A_comb.T @ A_comb + lam_use * M_ext)
        Sigma_inv_full = 0.5 * (Sigma_inv_full + Sigma_inv_full.T)
        # Posterior mean vector (full N+2):
        # mu = Sigma_inv^{-1} * (1/sigma_n²) * A'b
        rhs_full = (1 / sigma_n_b**2) * A_comb.T @ b_comb
        mu_full = np.linalg.solve(Sigma_inv_full, rhs_full)
        # Strip Rs/L block (cols 0..N-1 are gamma, N=Rs, N+1=L in our ordering)
        # → gamma block = first N rows/cols
        Sigma_inv_g = Sigma_inv_full[:N, :N]
        Sigma_inv_g = 0.5 * (Sigma_inv_g + Sigma_inv_g.T)
        Sigma_gamma = np.linalg.inv(Sigma_inv_g)  # N×N posterior covariance
        mu_gamma_bayes = mu_full[:N]  # N posterior mean for HMC
        sigma_n_bayes = sigma_n_b
        # x_ReIm stays as the constrained ridge solution (plotted DRT line)
        # HMC will add credible intervals around it
        _log(f"  sigma_n={sigma_n_b:.3e}  (from ridge residuals)")

    def extract(x):
        # x = [L, Rs, g_1...g_N] (DRTtools ordering)
        L = x[0]
        Rs = x[1]
        g = x[2:]  # gamma coefficients
        Z = A_re @ x + 1j * A_im @ x
        # tau_c = 1/(2pi*freq): ascending when freq is descending (DRTtools order).
        # trapezoid over ascending log(tau) gives positive for positive g → no minus sign.
        # (DRT_tikhonov uses -trapz(g, log(f)) where f is descending → same sign result)
        Rp = integrate.trapezoid(g, np.log(tau_c))
        return g, Rs, L, Z, Rp

    g_Im, Rs_Im, L_Im, Z_Im, Rp_Im = extract(x_Im)
    g_Re, Rs_Re, L_Re, Z_Re, Rp_Re = extract(x_Re)
    g_RI, Rs_RI, L_RI, Z_RI, Rp_RI = extract(x_ReIm)

    def res_single(A_use, x, b_use):
        return A_use @ x - b_use

    res_Im = res_single(A_im, x_Im, b_im)
    res_Re = res_single(A_re, x_Re, b_re)
    rc = res_single(np.vstack([A_im, A_re]), x_ReIm, np.hstack([b_im, b_re]))
    res_RI = (rc[:N] + rc[N:]) / 2

    # ── Smooth γ(τ) on fine grid ─────────────────────────────────────────
    # MATLAB style: tau = 1/freq (not 1/(2*pi*freq))
    # freq_fine = logspace(-taumin, -taumax, 10*N) where taumin/max from log10(1/freq)
    # tau_fine = 1 ./ freq_fine = logspace(taumin, taumax, 10*N)
    log_tau_vec = np.log10(1.0 / freq)
    taumax = np.max(log_tau_vec) + 0.5
    taumin = np.min(log_tau_vec) - 0.5
    freq_fine = np.logspace(-taumin, -taumax, 10 * N)
    tau_fine = 1.0 / freq_fine  # MATLAB style: tau = 1/freq

    # For map_array_to_gamma: use freq as tau_coll (MATLAB convention)
    # MATLAB: y0 = -log(freq), y = -log(freq_fine) = log(tau_fine)
    gamma_Im = map_array_to_gamma(freq_fine, freq, g_Im, epsilon, rbf_type)
    gamma_Re = map_array_to_gamma(freq_fine, freq, g_Re, epsilon, rbf_type)
    gamma_ReIm = map_array_to_gamma(freq_fine, freq, g_RI, epsilon, rbf_type)

    # ── HMC credible interval (optional, Bayesian mode only) ───────────────
    # DRTtools: HMC samples gamma ONLY (x_ridge[2:]), not Rs/L.
    # F = eye(N_gamma), g = eps*ones → gamma >= 0 constraint
    # Covariance uses gamma block of Sigma_full only.
    ci = {}
    if method == "bayes" and n_samples > 0 and Sigma_gamma is not None:
        _log(f"  HMC sampling ({n_samples} samples on gamma only)...")
        # initial point: ridge gamma (x_ReIm[:N]) + small offset (DRTtools: +100*eps)
        x0_hmc = np.maximum(x_ReIm[:N], 100 * np.finfo(float).eps)
        F_hmc = np.eye(N)  # gamma >= 0
        g_hmc = np.finfo(float).eps * np.ones(N)  # DRTtools uses eps, not 0
        try:
            Xs = HMC_exact(
                F_hmc, g_hmc, Sigma_gamma, mu_gamma_bayes, True, n_samples, x0_hmc
            )
            # Discard first 500 samples as burn-in (DRTtools: Xs[:,500:end])
            burn = min(500, n_samples // 2)
            Xs_post = Xs[:, burn:]
            samps = np.array(
                [
                    map_array_to_gamma(
                        tau_fine, tau_c, Xs_post[:, s], epsilon, rbf_type
                    )
                    for s in range(Xs_post.shape[1])
                ]
            )
            ci = {
                "g_mean": samps.mean(0),
                "g_std": samps.std(0),
                "g_lower": np.percentile(samps, 0.5, axis=0),  # 99% CI
                "g_upper": np.percentile(samps, 99.5, axis=0),
            }
            _log("  HMC done.")
        except Exception as e:
            print(f"  HMC failed: {e}")

    def make(g_fine, g_coeff, Z_rec, residuals):
        d = {
            # Use original EIS grid for impedance-like quantities (Re/Im/Residuals).
            "f": np.asarray(freq, dtype=float),
            "tau": np.asarray(tau_c, dtype=float),
            # Keep fine grid for gamma plotting.
            "f_gamma": 1.0 / tau_fine,
            "tau_gamma": tau_fine,
            "g": g_fine,
            "g_coeff": g_coeff,
            "Re": np.real(Z_rec),
            # RBF A_im is assembled with DRTtools sign; np.imag(Z_rec) already matches EIS Im convention.
            "Im": np.imag(Z_rec),
            "Residuals": residuals,
        }
        d.update(ci)
        if sigma_n_bayes is not None:
            d["sigma_n"] = sigma_n_bayes
        return d

    # ── Corrected Rp using analytic RBF integral ─────────────────────────────
    # Each RBF coefficient x_j represents a Gaussian centered at tau_j.
    # ∫ γ(lnτ) d(lnτ) = Σ x_j ∫ φ(lnτ - lnτ_j) d(lnτ) = Σ x_j * (√π / ε)
    # This is more accurate than the trapezoidal approximation on the coarse grid.
    if rbf_type == "Gaussian":
        rbf_integral = np.sqrt(np.pi) / epsilon  # ∫ exp(-(ε u)²) du from -∞ to +∞
    elif rbf_type in ("C0 Matern",):
        rbf_integral = 2.0 / epsilon
    elif rbf_type in ("C2 Matern",):
        rbf_integral = 4.0 / epsilon
    elif rbf_type in ("C4 Matern",):
        rbf_integral = 16.0 / (3.0 * epsilon)
    elif rbf_type in ("C6 Matern",):
        rbf_integral = 32.0 / (5.0 * epsilon)
    elif rbf_type in ("Inverse quadratic",):
        rbf_integral = np.pi / epsilon
    elif rbf_type in ("Cauchy",):
        rbf_integral = np.pi / epsilon
    else:
        rbf_integral = None  # fallback to trapz

    def rp_analytic(g_coeff):
        if rbf_integral is not None:
            return float(np.sum(np.maximum(g_coeff, 0.0)) * rbf_integral)
        return integrate.trapezoid(np.maximum(g_coeff, 0.0), np.log(tau_c))

    return {
        "Im": make(gamma_Im, g_Im, Z_Im, res_Im),
        "Re": make(gamma_Re, g_Re, Z_Re, res_Re),
        "ReIm": make(gamma_ReIm, g_RI, Z_RI, res_RI),
        "RL": {
            "Rs_Im": Rs_Im,
            "Rp_Im": rp_analytic(g_Im),
            "L_Im": L_Im,
            "Rs_Re": Rs_Re,
            "Rp_Re": rp_analytic(g_Re),
            "L_Re": L_Re,
            "Rs_ReIm": Rs_RI,
            "Rp_ReIm": rp_analytic(g_RI),
            "L_ReIm": L_RI,
            "Rp_trapz_Im": Rp_Im,
            "Rp_trapz_Re": Rp_Re,
            "Rp_trapz_ReIm": Rp_RI,
            "epsilon": epsilon,
            "lambda_eff": lam_use,
            "method": method,
        },
    }
