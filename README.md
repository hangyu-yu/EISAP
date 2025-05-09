# SOCEIS

# Introduction
**SOCEIS** is a project focusing on the data treatment of electrochemical impedance spectroscopy (EIS) measurements with Tiknov-based distribution of relaxation time (DRT), equivalant circuit model (ECM), and complex non-linear least square (CNLS) fit methodologies. Notably, the CNLS fit based on ECM will be capable of adjusting the upper/lower bound of elements' parameters (R, τ, α) freely. Besides, a model parameter estimation will also be included.
## Dependancies
- numpy # ==2.2.5
- scipy # ==1.15.2
- pandas # ==2.2.3
- matplotlib # ==3.10.1
- dearpygui # ==2.0.0
- openpyxl # ==3.1.2

# ---------- Date: 2025.05.07 ----------
Beta version 0.2 with complete EIS, DRT and CNLS fit functionalities. Small bugs to be fixed
## To do list
- [ ] Pop-up window to indicate the fault operation
- [ ] Simply the batch process name with ID+number-file_name
- [ ] Pop-up progress bar for the saving, processing
- [ ] Modularized code design
- [ ] Delete only the curves instead of the whole tab
- [ ] Add functions
	- [ ] Interactive manual selected points for CNLS fit frequency determine
	- [ ] Visualized equivalent circuit model assembly and usage of only basic circuit component R, C, L, Q, fFLW, FLW, G, etc.
	- [ ] Z-HIT smoothing from Zahner
	- [ ] Different DRT methodologies
	- [ ] Image save
# ---------- Date: 2025.02.12 ----------
## To do list
- [x] Translate all the codes in Matlab environment into python code
	- [x] Check the results between the matlab environment and python environment 
- [x] Define the best HMI tool in python with open-access