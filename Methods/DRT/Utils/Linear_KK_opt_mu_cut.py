import pandas as pd
import numpy as np
import time
import Methods.DRT.Utils as fn

def Linear_KK_opt_mu_cut(eis_data, parameters):
    """
    Automatically search best point cut and mu value based on M. Schönleber's method.

    Parameters:
    eis_data (pd.DataFrame): DataFrame containing at least 'f', 'Re', 'Im', 'omega'
                             'Im' should not have been multiplied by -1 (i.e., imag(Z_RC) < 0)
    parameters (dict): Dictionary containing the optimization parameters limits:
                 'nlf_cut_min'   = minimum points to cut at low frequency
                 'nlf_cut_max'   = maximum points to cut at low frequency                
                 'nhf_cut_min'   = minimum points to cut at high frequency
                 'nlf_cut_max'   = maximum points to cut at high frequency
                 'mu_ll' = mu lower limit
                 'mu_ul' = mu upper limit
                 'mu_resolution' = Parameters.mu_resolution;
                 'nRCmax' = maximal number of RC elements
                 'Display' = display message of the results or not

    Returns:
    tuple: Five DataFrames containing EIS_Processed, EIS_kk_opt, RC_kk_opt, RsLCinv_kk_opt, and Parameters_opt
    """
    start_time = time.time()  # Start timing

    nlf_cut_min = parameters['nlf_cut_min']
    nlf_cut_max = parameters['nlf_cut_max']
    nhf_cut_min = parameters['nhf_cut_min']
    nhf_cut_max = parameters['nhf_cut_max']
    mu_ll = parameters['mu_ll']
    mu_ul = parameters['mu_ul']
    mu_resolution = parameters['mu_resolution']
    nRCmax = parameters['nRCmax']

    TreshIdeal = 0
    leng = len(eis_data['f'])

    for nlf_cut in range(nlf_cut_min, nlf_cut_max + 1):
        for nhf_cut in range(nhf_cut_min, nhf_cut_max + 1):
            Re = eis_data['Re'][nhf_cut:leng - nlf_cut]
            Im = eis_data['Im'][nhf_cut:leng - nlf_cut]
            f = eis_data['f'][nhf_cut:leng - nlf_cut]

            EIStmp = pd.DataFrame({'f': f, 'Re': Re, 'Im': Im})
            parameters_dummy = {'CellArea': 1}  # dummy cell area for ConvertToASR
            EIStmp = fn.ConvertToASR(EIStmp, parameters_dummy)  # ConvertToASR only used to add tau and omega to EIStmp

            loopcounter = 0
            for mu_treshold in np.arange(mu_ll, mu_ul + mu_resolution, mu_resolution):
                loopcounter += 1

                for nRC in range(1, nRCmax + 1):
                    parameters['nRC'] = nRC
                    EIS_kk, RC_kk, RsLinvC_kk = fn.Linear_KK(EIStmp, parameters)
                    Rk = RC_kk['R_RC']

                    mu = 1 - np.sum(np.abs(Rk[Rk < 0])) / np.sum(Rk[Rk >= 0])
                    if mu <= mu_treshold:
                        break

                TreshMax = max(max(np.abs(EIS_kk['di'])), max(np.abs(EIS_kk['dr'])))
                if TreshIdeal > TreshMax or TreshIdeal == 0:
                    TreshIdeal = TreshMax
                    loopideal = loopcounter
                    nhf_cut_opt = nhf_cut
                    nlf_cut_opt = nlf_cut
                    nRC_opt = nRC
                    RC_kk_opt = RC_kk
                    RsLCinv_kk_opt = RsLinvC_kk
                    EIS_Processed = EIStmp
                    EIS_kk_opt = EIS_kk

    mu = np.arange(mu_ll, mu_ul + mu_resolution, mu_resolution)
    mu_opt = mu[loopideal - 1]

    Parameters_opt = pd.DataFrame({'nhf_cut': [nhf_cut_opt], 'nlf_cut': [nlf_cut_opt], 'mu': [mu_opt], 'nRC': [nRC_opt]})

    end_time = time.time()  # End timing
    toc = end_time - start_time  # Calculate elapsed time

    if parameters['Display']:
        print(f"---- The optimal high frequency cut: {nhf_cut_opt}.")
        print(f"---- The optimal low frequency cut: {nlf_cut_opt}.")
        print(f"---- The optimal mu value: {mu_opt}.")
        print(f"---- The optimal number of RC elements: {nRC_opt}.")
        print(f"---- Computation time: {toc:.2f} s.")
        print("----------------------------------------------------------------")

    return EIS_Processed, EIS_kk_opt, RC_kk_opt, RsLCinv_kk_opt, Parameters_opt
