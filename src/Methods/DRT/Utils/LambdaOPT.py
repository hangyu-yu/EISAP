import numpy as np
from scipy.linalg import norm
from scipy.interpolate import interp1d

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import src.Methods.DRT.Utils as fn

def LambdaOPT(EIS_data, parameters):
    """
    Compute the optimal Tikhonov regularization parameter based on the turning point of the L-curve.
    The turning point is found using the maximum curvature.

    Parameters:
    EIS_data (pd.DataFrame): DataFrame containing at least 'f', 'Re', 'Im', 'omega'
                             'Im' should not have been multiplied by -1 (i.e., imag(Z_RC) < 0)
                             Frequency should be ordered from highest to lowest
    parameters (dict): Dictionary containing:
                       'lambda_min' = minimum value of the regularization parameter
                       'lambda_max' = maximum value of the regularization parameter
                       'n' = number of lambda values to be tested
                       'PlotFig' = boolean for displaying figure or not
                       'TextOutput' = boolean for displaying text or not

    Returns:
    float: The optimal value of the Tikhonov regularization parameter
    """
    if parameters['PlotFig']:
        cmap = plt.cm.get_cmap(plt.rcParams['image.cmap'])
        color = cmap(np.linspace(0, 1, parameters['n']))
        cm_tmp = plt.rcParams['image.cmap']
        plt.rcParams['image.cmap'] = 'autumn'
        fig = plt.figure(figsize=(15, 5))
        gs = gridspec.GridSpec(1, 4, width_ratios=[25,25,25, 1], wspace=0.6, hspace=0.3)

        axs=[]
        axs.append(fig.add_subplot(gs[0, 0]))
        axs.append(fig.add_subplot(gs[0, 1]))
        axs.append(fig.add_subplot(gs[0, 2]))
        axs.append(fig.add_subplot(gs[0, 3]))

    lambda_values = np.logspace(np.log10(parameters['lambda_min']), np.log10(parameters['lambda_max']), parameters['n'])
    return_data = bool(parameters.get('ReturnData', False))

    norm_res = []
    norm_drt = []

    use_tknv_pos = bool(parameters.get('tknv_pos', False))

    for counter, lambda_val in enumerate(lambda_values):
        parameters_drt = parameters.copy()
        parameters_drt['lambda'] = lambda_val

        if use_tknv_pos:
            drt = fn.DRT_tknv_pos(EIS_data, parameters_drt)
        else:
            drt = fn.DRT_tikhonov(EIS_data, parameters_drt)

        norm_res.append(np.linalg.norm(drt['Re']['Residuals']))
        norm_drt.append(np.linalg.norm(drt['Re']['g']))

        if parameters['PlotFig']:
            axs[0].semilogx(drt['Im']['f'], drt['Im']['g'], color=color[counter])
        

    if parameters['PlotFig']:
        # axs[0].legend([f"{val:.3g}" for val in lambda_values], loc='best')
        axs[0].set_xlabel('f (Hz)')
        axs[0].set_ylabel(r'$\gamma\, [\Omega \cdot cm^2 \cdot s]$')

    # Curvature on log-log L-curve
    norm_res_arr = np.asarray(norm_res, dtype=float)
    norm_drt_arr = np.asarray(norm_drt, dtype=float)
    eps = 1e-300
    logx = np.log(np.clip(norm_res_arr ** 2, eps, None))
    logy = np.log(np.clip(norm_drt_arr ** 2, eps, None))
    dlogx = np.gradient(logx)
    dlogy = np.gradient(logy)
    ddlogx = np.gradient(dlogx)
    ddlogy = np.gradient(dlogy)

    denom = np.clip((dlogx ** 2 + dlogy ** 2) ** 1.5, eps, None)
    k = np.abs((dlogx * ddlogy - dlogy * ddlogx)) / denom

    if parameters['PlotFig']:
        axs[1].semilogx(lambda_values, k, 'k')
        axs[1].scatter(lambda_values, k, s=25, color=color[counter])
        axs[1].set_xlabel(r'$\lambda$')
        axs[1].set_ylabel('curvature')

    max_curvature_index = int(np.argmax(k))
    lambda_optimal = float(lambda_values[max_curvature_index])

    if parameters['PlotFig']:
        axs[2].loglog(norm_res, norm_drt, 'k-')
        axs[2].scatter(norm_res, norm_drt, color=color, s=25)
        axs[2].set_xlabel(r'||A$\gamma$ - b||')
        axs[2].set_ylabel(r'||$\gamma$||')

        # Create a ScalarMappable for the colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=np.log10(parameters['lambda_min']), vmax=np.log10(parameters['lambda_max'])))
        sm.set_array([])

        # Add a fourth subplot for the colorbar
        cb = fig.colorbar(sm, cax=axs[3], orientation='vertical')
        cb.set_ticks(np.linspace(np.log10(parameters['lambda_min']), np.log10(parameters['lambda_max']), 11))
        cb.set_ticklabels([f"{val:.3g}" for val in np.logspace(np.log10(parameters['lambda_min']), np.log10(parameters['lambda_max']), 11)])
        cb.set_label(r'$\lambda$', rotation=0, labelpad=20, fontsize=14)
        plt.rcParams['image.cmap'] = cm_tmp

        # Show plot
        #plt.show(block=False)

    if return_data:
        return {
            'lambda_optimal': lambda_optimal,
            'lambda_values': lambda_values,
            'norm_res': norm_res_arr,
            'norm_drt': norm_drt_arr,
            'curvature': np.asarray(k, dtype=float),
            'max_curvature_index': max_curvature_index,
            'tknv_pos': use_tknv_pos,
        }

    return lambda_optimal
