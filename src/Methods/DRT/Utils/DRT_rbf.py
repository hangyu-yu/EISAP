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
from scipy import integrate, optimize
from scipy.linalg import toeplitz


# ══════════════════════════════════════════════════════════════════════════════
# 1.  compute_epsilon  (port of compute_epsilon.m)
# ══════════════════════════════════════════════════════════════════════════════
def _rbf_fwhm_coeff(rbf_type):
    """Return 2×half-width at half-maximum for each RBF (in ε-normalised units)."""
    if rbf_type == 'Gaussian':
        return 2.0 * np.sqrt(np.log(2.0))
    elif rbf_type == 'C0 Matern':
        return 2.0 * np.log(2.0)
    elif rbf_type == 'C2 Matern':
        return 2.0 * optimize.brentq(
            lambda x: np.exp(-abs(x)) * (1 + abs(x)) - 0.5, 0.1, 10.0)
    elif rbf_type == 'C4 Matern':
        return 2.0 * optimize.brentq(
            lambda x: 1/3*np.exp(-abs(x))*(3+3*abs(x)+x**2) - 0.5, 0.1, 10.0)
    elif rbf_type == 'C6 Matern':
        return 2.0 * optimize.brentq(
            lambda x: 1/15*np.exp(-abs(x))*(15+15*abs(x)+6*x**2+abs(x)**3)-0.5,
            0.1, 10.0)
    elif rbf_type == 'Inverse quadratic':
        return 2.0 * optimize.brentq(lambda x: 1/(1+x**2) - 0.5, 0.1, 10.0)
    elif rbf_type == 'Cauchy':
        return 2.0 * optimize.brentq(lambda x: 1/(1+abs(x)) - 0.5, 0.1, 10.0)
    elif rbf_type == 'Piecewise linear':
        return 0.0
    else:
        raise ValueError(f"Unknown rbf_type: {rbf_type}")


def compute_epsilon(freq, coeff=0.5, rbf_type='Gaussian',
                    shape_control='FWHM Coefficient'):
    """
    Compute RBF shape parameter ε  (port of compute_epsilon.m).

    'FWHM Coefficient': ε = coeff × FWHM_coeff / Δ(ln τ)
    'Shape Factor':     ε = coeff  (direct)
    """
    if shape_control == 'FWHM Coefficient':
        # DRTtools expects freq descending (high→low), so tau = 1/f is ascending
        # Use abs() to be robust to either ordering
        delta = abs(np.mean(np.diff(np.log(1.0 / freq))))
        return coeff * _rbf_fwhm_coeff(rbf_type) / delta
    elif shape_control == 'Shape Factor':
        return float(coeff)
    else:
        raise ValueError(f"Unknown shape_control: {shape_control}")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  RBF kernel  φ(x)
# ══════════════════════════════════════════════════════════════════════════════
def _rbf(x, epsilon, rbf_type):
    ax = np.abs(epsilon * x)
    if   rbf_type == 'Gaussian':           return np.exp(-(epsilon*x)**2)
    elif rbf_type == 'C0 Matern':          return np.exp(-ax)
    elif rbf_type == 'C2 Matern':          return np.exp(-ax) * (1 + ax)
    elif rbf_type == 'C4 Matern':          return 1/3*np.exp(-ax)*(3+3*ax+ax**2)
    elif rbf_type == 'C6 Matern':          return 1/15*np.exp(-ax)*(15+15*ax+6*ax**2+ax**3)
    elif rbf_type == 'Inverse quadratic':  return 1.0/(1+(epsilon*x)**2)
    elif rbf_type == 'Cauchy':             return 1.0/(1+ax)
    else: raise ValueError(f"RBF {rbf_type} not supported")


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
        with np.errstate(over='ignore', invalid='ignore'):
            rbf_val = _rbf(x, epsilon, rbf_type)
            denom   = 1.0 + alpha**2 * np.exp(2*x)
            return np.where(rbf_val < 1e-300, 0.0, rbf_val / denom)
    val, _ = integrate.quad(integrand, -x_range, x_range,
                             limit=300, epsrel=1e-8, epsabs=1e-12)
    return val


def g_ii(freq_n, freq_m, epsilon, rbf_type):
    alpha = 2.0 * np.pi * freq_n / freq_m
    x_range = max(10.0 / (epsilon + 1e-10), 30.0)
    def integrand(x):
        with np.errstate(over='ignore', invalid='ignore'):
            rbf_val = _rbf(x, epsilon, rbf_type)
            ex      = np.exp(np.clip(x, -700, 700))
            denom   = 1.0 + alpha**2 * ex**2
            return np.where(rbf_val < 1e-300, 0.0,
                             rbf_val * alpha * ex / denom)
    val, _ = integrate.quad(integrand, -x_range, x_range,
                             limit=300, epsrel=1e-8, epsabs=1e-12)
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


def assemble_A_re(freq, epsilon, rbf_type='Gaussian'):
    """A_re matrix (N×N), DRT part only (no Rs/L columns)."""
    N = len(freq)
    if rbf_type == 'Piecewise linear':
        A  = np.zeros((N, N))
        lt = np.log(1.0 / freq)
        for n in range(N):
            for m in range(N):
                dt = (lt[m+1]-lt[m] if m==0 else
                      lt[m]-lt[m-1] if m==N-1 else
                      lt[m+1]-lt[m-1])
                A[n, m] = 0.5/(1+(2*np.pi*freq[n]/freq[m])**2)*dt
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


def assemble_A_im(freq, epsilon, rbf_type='Gaussian'):
    """A_im matrix (N×N), DRT part only.  Element = −g_ii (DRTtools sign)."""
    N = len(freq)
    if rbf_type == 'Piecewise linear':
        A  = np.zeros((N, N))
        lt = np.log(1.0 / freq)
        for n in range(N):
            for m in range(N):
                dt = (lt[m+1]-lt[m] if m==0 else
                      lt[m]-lt[m-1] if m==N-1 else
                      lt[m+1]-lt[m-1])
                alpha = 2*np.pi*freq[n]/freq[m]
                A[n, m] = -0.5*alpha/(1+alpha**2)*dt
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
    if rbf_type == 'Gaussian':
        return -epsilon*(-1+a**2)*np.exp(-a**2/2)*np.sqrt(np.pi/2)
    elif rbf_type == 'C0 Matern':
        return epsilon*(1-abs(a))*np.exp(-abs(a))
    elif rbf_type == 'C2 Matern':
        return epsilon/6*(3+3*abs(a)-abs(a)**3)*np.exp(-abs(a))
    elif rbf_type == 'C4 Matern':
        return (epsilon/30*(105+105*abs(a)+30*abs(a)**2-5*abs(a)**3-5*abs(a)**4-abs(a)**5)
                *np.exp(-abs(a)))
    elif rbf_type == 'C6 Matern':
        return (epsilon/140*(10395+10395*abs(a)+3780*abs(a)**2+315*abs(a)**3
                             -210*abs(a)**4-84*abs(a)**5-14*abs(a)**6-abs(a)**7)
                *np.exp(-abs(a)))
    elif rbf_type == 'Inverse quadratic':
        return 4*epsilon*(4-3*a**2)*np.pi/(4+a**2)**3
    elif rbf_type == 'Cauchy':
        if a == 0:
            return 2/3*epsilon
        num = (abs(a)*(2+abs(a))*(4+3*abs(a)*(2+abs(a)))
               -2*(1+abs(a))**2*(4+abs(a)*(2+abs(a)))*np.log(1+abs(a)))
        den = abs(a)**3*(1+abs(a))*(2+abs(a))**3
        return 4*epsilon*num/den
    else:
        raise ValueError(f"inner_prod_rbf_1 not implemented for {rbf_type}")


def inner_prod_rbf_2(freq_n, freq_m, epsilon, rbf_type):
    a = epsilon * np.log(freq_n / freq_m)
    if rbf_type == 'Gaussian':
        return epsilon**3*(3-6*a**2+a**4)*np.exp(-a**2/2)*np.sqrt(np.pi/2)
    elif rbf_type == 'C0 Matern':
        return epsilon**3*(1+abs(a))*np.exp(-abs(a))
    elif rbf_type == 'C2 Matern':
        return epsilon**3/6*(3+3*abs(a)-6*abs(a)**2+abs(a)**3)*np.exp(-abs(a))
    elif rbf_type == 'C4 Matern':
        return (epsilon**3/30*(45+45*abs(a)-15*abs(a)**3-5*abs(a)**4+abs(a)**5)
                *np.exp(-abs(a)))
    elif rbf_type == 'C6 Matern':
        return (epsilon**3/140*(2835+2835*abs(a)+630*abs(a)**2-315*abs(a)**3
                                -210*abs(a)**4-42*abs(a)**5+abs(a)**7)
                *np.exp(-abs(a)))
    elif rbf_type == 'Inverse quadratic':
        return 48*(16+5*a**2*(-8+a**2))*np.pi*epsilon**3/(4+a**2)**5
    elif rbf_type == 'Cauchy':
        if a == 0:
            return 8/5*epsilon**3
        num = (abs(a)*(2+abs(a))*(-96+abs(a)*(2+abs(a))*(-30+abs(a)*(2+abs(a))*(4+abs(a)*(2+abs(a)))))
               +12*(1+abs(a))**2*(16+abs(a)*(2+abs(a))*(12+abs(a)*(2+abs(a))))*np.log(1+abs(a)))
        den = abs(a)**5*(1+abs(a))*(2+abs(a))**5
        return 8*epsilon**3*num/den
    else:
        raise ValueError(f"inner_prod_rbf_2 not implemented for {rbf_type}")


# ══════════════════════════════════════════════════════════════════════════════
# 6.  assemble_M  (port of assemble_M_1.m / assemble_M_2.m)
# ══════════════════════════════════════════════════════════════════════════════
def assemble_M(freq, epsilon, rbf_type='Gaussian', der_used='1st order'):
    """Derivative regularization matrix M (N×N core block)."""
    N  = len(freq)
    ip = inner_prod_rbf_1 if der_used == '1st order' else inner_prod_rbf_2

    if rbf_type == 'Piecewise linear':
        lt = np.log(1.0 / freq)
        L  = np.zeros((N-1, N))
        for k in range(N-1):
            d = lt[k+1] - lt[k]
            L[k, k] = -1/d; L[k, k+1] = 1/d
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
    if rbf_type == 'Piecewise linear':
        return x.copy()
    y_fine = -np.log(tau_fine)
    y_c    = -np.log(tau_colloc)
    gamma  = np.array([np.dot(x, _rbf(yf - y_c, epsilon, rbf_type))
                        for yf in y_fine])
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
    sigma_n      = np.exp(log_theta[0])
    sigma_beta   = np.exp(log_theta[1])
    sigma_lambda = np.exp(log_theta[2])

    W     = (1/sigma_beta**2)*np.eye(N_taus+1) + (1/sigma_lambda**2)*M
    W     = 0.5*(W+W.T)
    K_agm = (1/sigma_n**2)*(A.T@A) + W
    K_agm = 0.5*(K_agm+K_agm.T)

    try:
        L_W   = np.linalg.cholesky(W)
        L_agm = np.linalg.cholesky(K_agm)
    except np.linalg.LinAlgError:
        return 1e20

    u     = np.linalg.solve(L_agm.T, np.linalg.solve(L_agm, A.T@Z))
    mu_x  = (1/sigma_n**2)*u
    E_mu  = (0.5/sigma_n**2*np.dot(A@mu_x-Z, A@mu_x-Z)
             + 0.5*mu_x@(W@mu_x))

    nmll  = -(  np.sum(np.log(np.diag(L_W)))
              - np.sum(np.log(np.diag(L_agm)))
              - 0.5*N_freqs*np.log(sigma_n**2)
              - E_mu
              - 0.5*N_freqs*np.log(2*np.pi))
    return nmll


# ══════════════════════════════════════════════════════════════════════════════
# 9.  HMC_exact  (port of HMC_exact.m — Pakman & Paninski, arXiv 1208.4118)
#     Sample from truncated Gaussian N(μ, Σ) subject to F x + g > 0.
# ══════════════════════════════════════════════════════════════════════════════
def HMC_exact(F, g, M_mat, mu_r, cov, n_samples, initial_X):
    if cov:
        mu = mu_r.copy(); g = g + F@mu
        R  = np.linalg.cholesky(M_mat).T
        F  = F@R.T
        initial_X = np.linalg.solve(R.T, initial_X - mu)
    else:
        r  = mu_r.copy(); R = np.linalg.cholesky(M_mat).T
        mu = np.linalg.solve(R, np.linalg.solve(R.T, r))
        g  = g + F@mu; F = F@np.linalg.inv(R)
        initial_X = R@(initial_X - mu)

    d = len(initial_X); nearzero = 1e4*np.finfo(float).eps
    Xs = np.zeros((d, n_samples)); Xs[:,0] = initial_X
    last_X = initial_X.copy(); F2 = np.sum(F**2, axis=1); Ft = F.T
    i = 1
    while i < n_samples:
        V0 = np.random.randn(d); X = last_X.copy(); T = np.pi/2; tt = 0.0; j = -1
        while True:
            a = V0.copy(); b = X.copy()
            fa = F@a; fb = F@b
            U  = np.sqrt(fa**2 + fb**2)
            phi= np.arctan2(-fa, fb)
            pn = np.abs(g/(U+1e-300)) <= 1
            inds = np.where(pn)[0]
            if len(inds) > 0:
                t1 = -phi[pn] + np.arccos(-g[pn]/(U[pn]+1e-300))
                t1 = np.where(t1 < 0, t1+2*np.pi, t1)
                if j >= 0 and pn[j]:
                    cs = np.cumsum(pn); idx = int(cs[j])-1
                    if idx < len(t1):
                        if abs(t1[idx])<nearzero or abs(t1[idx]-2*np.pi)<nearzero:
                            t1[idx] = np.inf
                mt = np.min(t1); m_ind = inds[np.argmin(t1)]; j = int(m_ind)
            else:
                mt = T
            tt += mt
            if tt >= T: mt -= tt-T; stop = True
            else:       stop = False
            X = a*np.sin(mt) + b*np.cos(mt)
            V = a*np.cos(mt) - b*np.sin(mt)
            if stop: break
            qj = F[j,:]@V/F2[j]; V0 = V - 2*qj*Ft[:,j]
        if np.all(F@X + g > 0):
            Xs[:,i] = X; last_X = X.copy(); i += 1

    return R.T@Xs + mu[:,None] if cov else np.linalg.solve(R, Xs) + mu[:,None]


# ══════════════════════════════════════════════════════════════════════════════
# 10.  Main function  DRT_rbf
# ══════════════════════════════════════════════════════════════════════════════
def DRT_rbf(EIS_data, parameters):
    """
    DRT via Gaussian RBF discretization with ridge or Bayesian regularization.
    Full Python port of DRTtools (Ciucci lab).

    Parameters
    ----------
    EIS_data : pd.DataFrame  (columns: f, Re, Im, omega)
               Im NOT sign-flipped (Im of RC < 0).  Freq highest→lowest.
    parameters : dict
        'lambda'        – regularization parameter
        'rbf_type'      – default 'Gaussian'
        'coeff'         – FWHM coefficient, default 0.5
        'shape_control' – 'FWHM Coefficient' (default) or 'Shape Factor'
        'der_used'      – '1st order' (default) or '2nd order'
        'method'        – 'ridge' (default) or 'bayes'
        'theta0'        – initial [σ_n, σ_β, σ_λ] for Bayes
        'n_samples'     – HMC samples for credible interval (default 0 = skip)

    Returns
    -------
    dict with same keys as DRT_tikhonov:
        'Im', 'Re', 'ReIm' → {'f','tau','g','g_coeff','Re','Im','Residuals'}
        'RL'               → scalar parameters + epsilon + lambda_eff
    Bayesian mode adds: 'g_mean','g_std','g_lower','g_upper','theta_opt'
    """
    data = EIS_data.copy()
    if 'tau'   not in data.columns: data['tau']   = 1/(2*np.pi*data['f'])
    if 'omega' not in data.columns: data['omega'] = 2*np.pi*data['f']

    freq  = data['f'].values
    omega = data['omega'].values
    b_re  = data['Re'].values
    b_im  = -data['Im'].values      # sign flip: −Im(Z_RC) > 0
    N     = len(freq)

    rbf_type      = parameters.get('rbf_type',      'Gaussian')
    coeff         = parameters.get('coeff',          0.5)
    shape_control = parameters.get('shape_control',  'FWHM Coefficient')
    der_used      = parameters.get('der_used',       '1st order')
    method        = parameters.get('method',         'ridge')
    lam           = parameters['lambda']
    n_samples     = parameters.get('n_samples',       0)

    tau_c = 1.0/(2*np.pi*freq)

    # ── ε ──────────────────────────────────────────────────────────────────
    epsilon = compute_epsilon(freq, coeff=coeff, rbf_type=rbf_type,
                               shape_control=shape_control)
    print(f"  ε = {epsilon:.4f}  rbf = {rbf_type}")

    # ── A matrices ──────────────────────────────────────────────────────────
    print("  Assembling A_re ...")
    A_re_drt =  assemble_A_re(freq, epsilon, rbf_type)
    print("  Assembling A_im ...")
    # Sign convention fix:
    #   DRTtools assemble_A_im returns -g_ii (designed for b_im = Im(Z) < 0)
    #   Here we follow DRT_tikhonov convention: b_im = -Im(Z) > 0
    #   So we negate to get +g_ii, keeping the equation A_im @ g = b_im correct
    A_im_drt = -assemble_A_im(freq, epsilon, rbf_type)

    # Full: x = [g_1...g_N, Rs, L]  (DRT_tikhonov column order)
    A_re = np.hstack([A_re_drt, np.ones((N,1)),  np.zeros((N,1))])
    A_im = np.hstack([A_im_drt, np.zeros((N,1)), -omega.reshape(-1,1)])

    # ── M matrix ───────────────────────────────────────────────────────────
    print(f"  Assembling M ({der_used}) ...")
    M_core = assemble_M(freq, epsilon, rbf_type=rbf_type, der_used=der_used)
    M_ext  = np.zeros((N+2, N+2))
    M_ext[:N, :N] = M_core     # Rs and L not penalised

    # ── Bayesian hyperparameter optimisation ─────────────────────────────
    lam_eff        = lam
    theta_opt_vals = None
    mu_bayes       = None

    if method == 'bayes':
        print("  Optimising hyperparameters (NMLL) ...")
        A_bay = np.vstack([A_im[:, :N+1], A_re[:, :N+1]])  # drop L column
        b_bay = np.hstack([b_im, b_re])
        M_bay = M_ext[:N+1, :N+1]
        Z_sc  = float(np.mean(np.abs(b_re + 1j*b_im)))
        t0    = parameters.get('theta0', [0.01*Z_sc, 1.0, 1.0])

        res_opt = optimize.minimize(
            NMLL_fct, x0=np.log(t0),
            args=(b_bay, A_bay, M_bay, 2*N, N),
            method='Nelder-Mead',
            options={'xatol':1e-8,'fatol':1e-8,'maxiter':5000,'disp':False})

        theta_opt_vals = np.exp(res_opt.x)
        sn, sb, sl = theta_opt_vals
        lam_eff = sn**2 / sl**2
        print(f"  sigma_n={sn:.3e}  sigma_b={sb:.3e}  sigma_l={sl:.3e}  lam_eff={lam_eff:.3e}")

        # Bayesian posterior mean (Ciucci & Chen 2015): mu = sigma_n^{-2} K^{-1} A^T Z
        W     = (1/sb**2)*np.eye(N+1) + (1/sl**2)*M_bay
        W     = 0.5*(W + W.T)
        K     = (1/sn**2)*(A_bay.T @ A_bay) + W
        K     = 0.5*(K + K.T)
        Sigma = np.linalg.inv(K)
        mu_bayes = (1/sn**2) * (Sigma @ A_bay.T @ b_bay)
        mu_bayes[:N] = np.maximum(mu_bayes[:N], 0.0)  # non-negativity projection

    # For Bayesian mode, lam_eff = sn²/sl² can be near-zero (degenerate NMLL).
    # Use max(lam_eff, lam) as a floor so Im/Re modes remain well-conditioned.
    lam_use = max(lam_eff, lam) if method == 'bayes' else lam_eff

    # ── Solve: port of DRTtools quadprog ────────────────────────────────────
    # min x^T (A^T A + lam M) x - 2 b^T A x   s.t. gamma >= 0
    def solve(A_use, b_use, lam_s=None):
        if lam_s is None: lam_s = lam_use
        n = A_use.shape[1]
        H = A_use.T @ A_use + lam_s * M_ext
        H = 0.5*(H + H.T)
        def obj(x):  return x @ H @ x - 2*(b_use @ A_use) @ x
        def grad(x): return 2*H @ x - 2*A_use.T @ b_use
        bounds = [(0, None)]*N + [(None, None), (None, None)]
        r = optimize.minimize(obj, np.zeros(n), jac=grad, method='L-BFGS-B',
                              bounds=bounds,
                              options={'maxiter':10000,'ftol':1e-15,'gtol':1e-11})
        return r.x

    # For Bayesian mode: use posterior mean directly for ReIm;
    # ridge solve for Im/Re-only modes using Bayesian lambda_eff
    x_Im   = solve(A_im,                   b_im)
    x_Re   = solve(A_re,                   b_re)
    if method == 'bayes' and mu_bayes is not None:
        # Pad mu_bayes (N+1 cols) to (N+2) by adding L=0
        x_ReIm = np.hstack([mu_bayes, 0.0])
    else:
        x_ReIm = solve(np.vstack([A_im,A_re]), np.hstack([b_im,b_re]))

    def extract(x):
        g  = x[:N]; Rs = x[N]; L = x[N+1]
        Z  = A_re@x + 1j*A_im@x
        # tau_c = 1/(2pi*freq): ascending when freq is descending (DRTtools order).
        # trapezoid over ascending log(tau) gives positive for positive g → no minus sign.
        # (DRT_tikhonov uses -trapz(g, log(f)) where f is descending → same sign result)
        Rp = integrate.trapezoid(g, np.log(tau_c))
        return g, Rs, L, Z, Rp

    g_Im, Rs_Im, L_Im, Z_Im, Rp_Im = extract(x_Im)
    g_Re, Rs_Re, L_Re, Z_Re, Rp_Re = extract(x_Re)
    g_RI, Rs_RI, L_RI, Z_RI, Rp_RI = extract(x_ReIm)

    def res_single(A_use, x, b_use): return A_use@x - b_use
    res_Im  = res_single(A_im, x_Im, b_im)
    res_Re  = res_single(A_re, x_Re, b_re)
    rc      = res_single(np.vstack([A_im,A_re]), x_ReIm, np.hstack([b_im,b_re]))
    res_RI  = (rc[:N]+rc[N:])/2

    # ── Smooth γ(τ) on fine grid ─────────────────────────────────────────
    tau_fine = np.logspace(np.log10(tau_c.min())-0.5,
                            np.log10(tau_c.max())+0.5, 300)
    f_fine   = 1.0/(2*np.pi*tau_fine)

    gamma_Im   = map_array_to_gamma(tau_fine, tau_c, g_Im,  epsilon, rbf_type)
    gamma_Re   = map_array_to_gamma(tau_fine, tau_c, g_Re,  epsilon, rbf_type)
    gamma_ReIm = map_array_to_gamma(tau_fine, tau_c, g_RI,  epsilon, rbf_type)

    # ── HMC credible interval (optional) ────────────────────────────────
    ci = {}
    if method == 'bayes' and n_samples > 0 and theta_opt_vals is not None:
        print(f"  HMC sampling ({n_samples} samples) …")
        sn, sb, sl = theta_opt_vals
        A_hmc = np.vstack([A_im, A_re]); b_hmc = np.hstack([b_im, b_re])
        W     = (1/sb**2)*np.eye(N+2) + (1/sl**2)*M_ext
        K     = (1/sn**2)*(A_hmc.T@A_hmc) + W; K = 0.5*(K+K.T)
        Sigma = np.linalg.inv(K)
        mu    = (1/sn**2)*(Sigma@A_hmc.T@b_hmc)
        F_hmc = np.eye(N+2)[:N]           # only DRT coefficients ≥ 0
        g_hmc = np.zeros(N)
        x0    = np.maximum(x_ReIm, 1e-10)
        try:
            Xs = HMC_exact(F_hmc, g_hmc, Sigma, mu, True, n_samples, x0)
            samps = np.array([map_array_to_gamma(tau_fine, tau_c,
                                                  Xs[:N,s], epsilon, rbf_type)
                               for s in range(n_samples)])
            ci = {'g_mean' : samps.mean(0),
                  'g_std'  : samps.std(0),
                  'g_lower': np.percentile(samps,  2.5, axis=0),
                  'g_upper': np.percentile(samps, 97.5, axis=0)}
            print("  HMC done.")
        except Exception as e:
            print(f"  HMC failed: {e}")

    def make(g_fine, g_coeff, Z_rec, residuals):
        d = {'f': f_fine, 'tau': tau_fine,
             'g': g_fine, 'g_coeff': g_coeff,
             'Re': np.real(Z_rec), 'Im': -np.imag(Z_rec),
             'Residuals': residuals}
        d.update(ci)
        if theta_opt_vals is not None: d['theta_opt'] = theta_opt_vals
        return d

    # ── Corrected Rp using analytic RBF integral ─────────────────────────────
    # Each RBF coefficient x_j represents a Gaussian centered at tau_j.
    # ∫ γ(lnτ) d(lnτ) = Σ x_j ∫ φ(lnτ - lnτ_j) d(lnτ) = Σ x_j * (√π / ε)
    # This is more accurate than the trapezoidal approximation on the coarse grid.
    if rbf_type == 'Gaussian':
        rbf_integral = np.sqrt(np.pi) / epsilon   # ∫ exp(-(ε u)²) du from -∞ to +∞
    elif rbf_type in ('C0 Matern',):
        rbf_integral = 2.0 / epsilon
    elif rbf_type in ('C2 Matern',):
        rbf_integral = 4.0 / epsilon
    elif rbf_type in ('C4 Matern',):
        rbf_integral = 16.0 / (3.0 * epsilon)
    elif rbf_type in ('C6 Matern',):
        rbf_integral = 32.0 / (5.0 * epsilon)
    elif rbf_type in ('Inverse quadratic',):
        rbf_integral = np.pi / epsilon
    elif rbf_type in ('Cauchy',):
        rbf_integral = np.pi / epsilon
    else:
        rbf_integral = None   # fallback to trapz

    def rp_analytic(g_coeff):
        if rbf_integral is not None:
            return float(np.sum(np.maximum(g_coeff, 0.0)) * rbf_integral)
        return integrate.trapezoid(np.maximum(g_coeff, 0.0), np.log(tau_c))

    return {
        'Im'  : make(gamma_Im,   g_Im,  Z_Im,  res_Im),
        'Re'  : make(gamma_Re,   g_Re,  Z_Re,  res_Re),
        'ReIm': make(gamma_ReIm, g_RI,  Z_RI,  res_RI),
        'RL'  : {'Rs_Im': Rs_Im, 'Rp_Im': rp_analytic(g_Im), 'L_Im': L_Im,
                 'Rs_Re': Rs_Re, 'Rp_Re': rp_analytic(g_Re), 'L_Re': L_Re,
                 'Rs_ReIm': Rs_RI, 'Rp_ReIm': rp_analytic(g_RI), 'L_ReIm': L_RI,
                 'Rp_trapz_Im': Rp_Im, 'Rp_trapz_Re': Rp_Re, 'Rp_trapz_ReIm': Rp_RI,
                 'epsilon': epsilon, 'lambda_eff': lam_eff, 'method': method},
    }
