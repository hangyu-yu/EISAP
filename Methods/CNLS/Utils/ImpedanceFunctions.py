# Created by: Guillaume Jeanmonod
# Date: 2025-02-25
# Version: 1.0
# Description: This file contains all the basic impedance functions
# Inputs:
#   Param = table/dataframe containing the parameters of the component
#   w= array of pulsation (2*pi*f)
# Outputs:
#   Z = array of impedance values

import numpy as np
import pandas as pd

# Helper function to handle large arguments in tanh
def safe_tanh(x):
    large = np.abs(x) > 100  # Threshold for large arguments
    result = np.tanh(x)
    result[large] = 1.0  # Approximate tanh(x) as 1 for large arguments
    return result

# Resistor
def Resistor(w,Param):
    R=Param[0]
    # Impedance
    Z = R*np.ones(len(w))
    return Z

# Inductor
def Inductor(w,Param):
    L=Param[0] 
    # Impedance
    Z = 1j*w*L
    return Z

#Non-ideal inductor
def Inductor_a(w,Param):
    L=Param[0]
    alpha=Param[1]
    # Impedance
    Z = L*(1j*w)**alpha
    return Z

# Capacitor
def Capacitor(w,Param):
    C=Param[0]
    # Impedance
    Z = 1/(1j*w*C)
    return Z

# CPE
def CPE(w,Param):
    Q=Param[0]
    alpha=Param[1]
    # Impedance
    Z = 1/(Q*(1j*w)**alpha)
    return Z

# R//C
def RC(w,param):
    R=param[0]
    tau0=param[1]
    # Impedance
    Z = R/(1+(1j*w*tau0))
    return Z

# R//Q
def RQ(w,param):
    # Zarc element (R//Q)
    # From Boukamp https://doi.org/10.1088/2515-7655/aba9e0
    R=param[0]
    tau0=param[1] # RQ=tau0^alpha
    alpha=param[2]
    # Impedance
    Z = R/(1+(1j*w*tau0)**alpha) # = R/(1+RQ(1j*w)^alpha)
    
    # Lasia
    # Q=tau0 # Lasia doesn't use tau but Q to define the RQ element
    # Z = 1/(R*Q*(1j*w)**alpha) # Lasia
    return Z
    
# Gerisher
def Gerisher(w,param):
    #From Boukamp https://doi.org/10.1088/2515-7655/aba9e0
    #In the original definitaion Z0 is used insted of R
    R=param[0]
    tau0=param[1]
    # Impedance
    Z = R/(1+(tau0*1j*w))**0.5
    return Z

# Fractal finite length Warburg element
def fFLW(w,param):
    # From Boukamp https://doi.org/10.1088/2515-7655/aba9e0
    # alpha<0.5 is the "fractal" coefficient (phi in the paper)
    # alpha=0.5 is an exact Warburg element
    R=param[0]
    tau0=param[1]
    alpha=param[2]
    # Impedance
    Z = R*safe_tanh((tau0*1j*w)**alpha)/(tau0*1j*w)**alpha; # Boukamp (eq. 29)
    return Z

# Finite length Warburg element
def FLW(w,param):
    # From Boukamp https://doi.org/10.1088/2515-7655/aba9e0
    # fract FLW with phi=0.5
    R=param[0]
    tau0=param[1]
    # Impedance
    Z = R*safe_tanh((tau0*1j*w)**0.5)/(tau0*1j*w)**0.5
    return Z

# RandleC
def RandleC(w,param):
    # C in parallel to a (finite length warburg and resistor in series)            
    R=param[0] # Resistance
    C=param[1] # Capacitance
    R_W=param[2] # Warburg resistance
    tau0_W=param[3] # Warburg time constant
    
    Z_C = Capacitor(w, [C])
    Z_W=FLW(w, [R_W, tau0_W])

    # Impedance
    Z = (Z_C**-1+(R+Z_W)**-1)**-1
    return Z

# RandleCPE
def RandleCPE(w,param):
    # CPE in parallel to a (finite length warburg and resistor in series)            
    R=param[0] # Resistance
    Q=param[1] # Constant phase element
    alpha_Q=param[2] # CPE exponent
    R_W=param[2] # Warburg resistance
    tau0_W=param[3] # Warburg time constant
            
    Z_CPE = CPE(w, [Q, alpha_Q])
    Z_W=FLW(w, [R_W, tau0_W])

    # Impedance
    Z = (Z_CPE**-1+(R+Z_W)**-1)**-1
    return Z

# RandleCPEfFLW
def RandleCPEfFLW(w,param):
    #CPE in parallel to a (fractal finite length warburg and a
    # resistor in series)
    R = param[0]  # R
    Q = param[1]  # Q CPE
    alpha_Q = param[2]  # alpha CPE
    R_W = param[3]  # R warburg
    tau0_W = param[4]  # tau0 warburg
    alpha_W = param[5]  # alpha warburg

    #Z_CPE = 1. / (Q * 1j * w) ** alpha_Q
    Z_CPE = CPE(w, [Q, alpha_Q])
    Z_W= fFLW(w, [R_W, tau0_W, alpha_W])
    
    # Impedance
    Z = (1 / Z_CPE + 1 / (R + Z_W)) ** -1
    return Z

# RandleCfFLW
def RandleCfFLW(w, param):
    # C in parallel to a (fractal finite length warburg and resistor in series)
    R = param[0]  # Resistance
    C = param[1]  # Capacitance
    R_W = param[2]  # Warburg resistance
    tau0_W = param[3]  # Warburg time constant
    alpha_W = param[4]  # Warburg exponent

    Z_C=Capacitor(w, [C])
    Z_W=fFLW(w, [R_W, tau0_W, alpha_W])
    
    # Impedance
    Z = (1 / Z_C + 1 / (R + Z_W)) ** -1
    return Z




