import numpy as np
from scipy.linalg import norm
from scipy.interpolate import interp1d

import matplotlib.pyplot as plt

def LambdaOPT(EIS_Data, Parameters):
    """
    LAMBDAOPT compute the optimal Tikhonov regularization parameters based on
    the turning point of the L-curve. The turning point is found using the
    maximum curvature.

    Ref: Per Christian Hansen and Dianne Prost O Leary. The Use of the L-Curve in the Regularization
    of Discrete Ill-Posed Problems. SIAM Journal on Scientific Computing, 14(6):
    1487–1503, nov 1993. ISSN 1064-8275. doi: 10.1137/0914086.

    Created by Guillaume Jeanmonod
    Translated to Python by Hangyu Yu

    Parameters
    ----------
    EIS_Data : DataFrame
        A table containing at least f, Zp, Zpp, omega.
    Parameters : dict
        A dictionary containing:
            lambda_min : float
                The minimum value of the regularization parameter.
            lambda_max : float
                The maximum value of the regularization parameter.
            n : int
                Number of lambda values to be tested.
            lambda_plot : bool
                Boolean for displaying figure or not.
            TextOutput : bool
                Boolean for displaying text or not.

    Returns
    -------
    lambda_optimal : float
        The optimal value of the Tikhonov regularization parameter.
    """

    if Parameters['lambda_plot']:
        fig, axs = plt.subplots(1, 3, figsize=(12, 3))
        color_map = plt.cm.autumn(np.linspace(0, 1, Parameters['n']))

    lambda_values = np.logspace(np.log10(Parameters['lambda_min']), np.log10(Parameters['lambda_max']), Parameters['n'])

    NormRes = []
    NormDRT = []

    for counter, lambda_val in enumerate(lambda_values):
        Parameters_DRT = Parameters.copy()
        Parameters_DRT['lambda'] = lambda_val

        DRT = DRT_tikonov(EIS_Data, Parameters_DRT)

        NormRes.append(norm(DRT['Re']['Residuals']))
        NormDRT.append(norm(DRT['Re']['g']))

        if Parameters['lambda_plot']:
            axs[0].semilogx(DRT['Im']['f'], DRT['Im']['g'], color=color_map[counter])
            axs[0].set_xlabel('f (Hz)')
            axs[0].set_ylabel(r'$\gamma [\Omega \cdot cm^2 \cdot s]$')
            axs[0].legend([f'{val:.2e}' for val in lambda_values], loc='best', fontsize='small')

    NormRes = np.array(NormRes)
    NormDRT = np.array(NormDRT)

    # Curvature
    logx = np.log(NormRes**2)
    logy = np.log(NormDRT**2)
    dlogx = np.gradient(logx)
    dlogy = np.gradient(logy)
    ddlogx = np.gradient(dlogx)
    ddlogy = np.gradient(dlogy)

    k = np.abs((dlogx * ddlogy - dlogy * ddlogx)) / (dlogx**2 + dlogy**2)**1.5

    if Parameters['lambda_plot']:
        axs[1].semilogx(lambda_values, k, 'k')
        axs[1].scatter(lambda_values, k, c=color_map, s=25)
        axs[1].set_xlabel(r'$\lambda$')
        axs[1].set_ylabel('curvature')

    lambda_optimal = lambda_values[np.argmax(k)]

    if Parameters['lambda_plot']:
        axs[2].loglog(NormRes, NormDRT, 'k-')
        axs[2].scatter(NormRes, NormDRT, c=color_map, s=25)
        axs[2].set_xlabel(r'$||A\gamma - b||$')
        axs[2].set_ylabel(r'$||\gamma||$')

        sm = plt.cm.ScalarMappable(cmap=plt.cm.autumn, norm=plt.Normalize(vmin=Parameters['lambda_min'], vmax=Parameters['lambda_max']))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=axs, orientation='vertical', fraction=0.02, pad=0.04)
        cbar.set_label(r'$\lambda$', rotation=0, labelpad=10)
        cbar.ax.tick_params(labelsize=10)

        plt.show()

    if Parameters['TextOutput']:
        print(f"lambda optimal is {lambda_optimal}")

    return lambda_optimal

def DRT_tikonov(EIS_Data, Parameters_DRT):
    # Placeholder function for DRT_tikonov
    # This function should be implemented based on the specific requirements
    # and data structure of EIS_Data and Parameters_DRT.
    pass
