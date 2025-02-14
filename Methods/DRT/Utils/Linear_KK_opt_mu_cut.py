import pandas as pd
import numpy as np
import time
from Methods.DRT.Utils import ConvertToASR, Linear_KK

def Linear_KK_opt_mu_cut(EIS_Data, Parameters):
    """
    This function is used to automatically search best point cut and mu value based on: M. Schönleber, 10.1016/j.electacta.2014.01.034
    Modified by Guillaume Jeanmonod from the function opt_mu_cut created by Dante Fronterotta
    Translated by Hangyu Yu
    """

    start_time = time.time()
    nlf_cut_min = Parameters['nlf_cut_min']
    nlf_cut_max = Parameters['nlf_cut_max']

    nhf_cut_min = Parameters['nhf_cut_min']
    nhf_cut_max = Parameters['nhf_cut_max']

    mu_ll = Parameters['mu_ll']
    mu_ul = Parameters['mu_ul']
    mu_resolution = Parameters['mu_resolution']

    nRCmax = Parameters['nRCmax']

    TreshIdeal = 0

    leng = len(EIS_Data['f'])

    for nlf_cut in range(nlf_cut_min, nlf_cut_max + 1):
        for nhf_cut in range(nhf_cut_min, nhf_cut_max + 1):

            Zp = EIS_Data['Zp'][nhf_cut:leng - nlf_cut]
            Zpp = EIS_Data['Zpp'][nhf_cut:leng - nlf_cut]
            f = EIS_Data['f'][nhf_cut:leng - nlf_cut]

            EIStmp = pd.DataFrame({'f': f, 'Zp': Zp, 'Zpp': Zpp})
            Parameters_dummy = {'CellArea': 1}  # dummy cell area for ConvertToASR
            EIStmp = ConvertToASR(EIStmp, Parameters_dummy)  # ConvertToASR only used to add tau and omega to EIStmp

            loopcounter = 0
            for mu_treshold in np.arange(mu_ll, mu_ul + mu_resolution, mu_resolution):

                loopcounter += 1

                for nRC in range(1, nRCmax + 1):
                    Parameters['nRC'] = nRC

                    EIS_kk, RC_kk, RsLinvC_kk = Linear_KK(EIStmp, Parameters)
                    Rk = RC_kk['R_RC']

                    mu = 1 - sum(abs(Rk[Rk < 0])) / sum(Rk[Rk >= 0])
                    if mu <= mu_treshold:
                        break

                TreshMax = max(max(abs(EIS_kk['di'])), max(abs(EIS_kk['dr'])))
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

    Parameters_opt = pd.DataFrame({
        'nhf_cut': [nhf_cut_opt],
        'nlf_cut': [nlf_cut_opt],
        'mu': [mu_opt],
        'nRC': [nRC_opt]
    })

    if Parameters['Display']:
        print(f'---- The optimal high frequency cut: {nhf_cut_opt}.')
        print(f'---- The optimal low frequency cut: {nlf_cut_opt}.')
        print(f'---- The optimal mu value: {mu_opt}.')
        print(f'---- The optimal number of RC elements: {nRC_opt}.')
        print(f'---- Computation time: {time.time() - start_time} s.')
        print('----------------------------------------------------------------')

    return EIS_Processed, EIS_kk_opt, RC_kk_opt, RsLCinv_kk_opt, Parameters_opt
