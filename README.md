<p align="center">
  <img src="assets/icons/app_icon.png" alt="SOCEIS Logo" width="150"/>
</p>
<p align="center">
  <img src="assets/images/EPFL.png" alt="EPFL" height="70" hspace="20"/>
  <img src="assets/images/GEM.png" alt="GEM" height="70" hspace="20"/>
  <img src="assets/images/HydroQuebec.png" alt="Hydro-Québec" height="70" hspace="20"/>
  <img src="assets/images/BFH.png" alt="BFH" height="70" hspace="20"/>
</p>

# SOCEIS - Electrochemical Impedance Spectroscopy Analysis Suite
Under development, more features up to come.

## Overview
**SOCEIS** is an advanced Python-based toolkit for comprehensive analysis of electrochemical impedance spectroscopy (EIS) data, developed by **Hangyu Yu** (EPFL-GEM, Sion, Switzerland, headed by **Prof. Jan Van Herle**) and **Guillaume Jeamonod** (Hydro-Québec, Montreal, Canada) based on the code developed by **Priscilla Caliandro** (BFH, Biel, Switzerland).. The software integrates three core methodologies:

1. **Distribution of Relaxation Time (DRT)** - Tikhonov-regularized deconvolution
2. **Equivalent Circuit Modeling (ECM)** - Flexible circuit topology builder with constraint management
3. **Complex Nonlinear Least Squares (CNLS) Fitting** - Advanced optimization with:
   - Bounded parameter constraints (R, τ, α, etc.)
   - Adjustable parameter constraints

## Key Features
### ▸ Experimental Workflow Integration
- Batch processing with ECM constraints adjustment
- Intuitive results illustration with individual measruement analysis and multiple data analysis
- Native support for Zahner `.txt`/`.csv` files and BioLogic `.mpt` formats

## Technical Specifications
### System Requirements
- Python 3.8+ (64-bit)

### Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| NumPy | ≥1.20 | Core numerical operations |
| SciPy | ≥1.7 | Optimization & signal processing |
| Pandas | ≥1.3 | Data structure management |
| Matplotlib | ≥3.5 | Publication-quality visualization |
| DearPyGui | ≥1.7 | GPU-accelerated UI framework |
| OpenPyXL | ≥3.0 | Excel report generation |
| streamlit |  | SOCEIS Viewer |
| plotly |  | SOCEIS Viewer |

<p align="center">
  <img src="assets/images/Fig_example_main.png" width="width: 100%;">
  <img src="assets/images/Fig_example_EIS.png" width="width: 100%;">
  <img src="assets/images/Fig_example_DRT.png" width="width: 100%;">
  <img src="assets/images/Fig_example_CNLS.png" width="width: 100%;">
</p>

# Citing SOCEIS

If you use **SOCEIS** in your work, please cite our papers:

> **Caliandro, P., Nakajo, A., Diethelm, S., & Van herle, J.** (2019).  
> *Model-assisted identification of solid oxide cell elementary processes by electrochemical impedance spectroscopy measurements.*  
> Journal of Power Sources, **436**, 226838.

> **Yu, H., Frantz, C., Savioz, L., Aubin, P., Fronterotta, D., Geipel, C., Moussaoui, H., Jeanmonod, G., Wang, L., & Van herle, J.** (2025).  
> *Poisoning and recovery behavior of Ni-GDC based electrolyte-supported solid oxide fuel cell exposed to common sulfur compounds under processed biogas environment.*  
> Journal of Power Sources, **642**, 236901.

---

## You can use the BibTeX

```bibtex
@article{caliandroModelassistedIdentificationSolid2019,
  title = {Model-Assisted Identification of Solid Oxide Cell Elementary Processes by Electrochemical Impedance Spectroscopy Measurements},
  author = {Caliandro, P. and Nakajo, A. and Diethelm, S. and {Van herle}, J.},
  year = {2019},
  month = oct,
  journal = {Journal of Power Sources},
  volume = {436},
  pages = {226838},
  issn = {0378-7753},
  doi = {10.1016/j.jpowsour.2019.226838},
  urldate = {2022-06-24},
  lccn = {2}
}

@article{yuPoisoningRecoveryBehavior2025,
  title = {Poisoning and Recovery Behavior of {{Ni-GDC}} Based Electrolyte-Supported Solid Oxide Fuel Cell Exposed to Common Sulfur Compounds under Processed Biogas Environment},
  author = {Yu, Hangyu and Frantz, C{\'e}dric and Savioz, Louis and Aubin, Philippe and Fronterotta, Dante and Geipel, Christian and Moussaoui, Hamza and Jeanmonod, Guillaume and Wang, Ligang and {Van herle}, Jan},
  year = {2025},
  month = jun,
  journal = {Journal of Power Sources},
  volume = {642},
  pages = {236901},
  issn = {0378-7753},
  doi = {10.1016/j.jpowsour.2025.236901},
  urldate = {2025-04-13},
  lccn = {3}
}
```

# Major updates
## ---------- Date: 2025.05.07 ----------
Beta version 0.2 with complete EIS, DRT and CNLS fit functionalities. Small bugs to be fixed
### To do list
- [ ] If CNLS fit results are not completely saved, error.
- [ ] Pop-up window to indicate the fault operation
- [ ] Simply the batch process name with ID+number-file_name
- [ ] Pop-up progress bar for the saving, processing
- [ ] Modularized code design
- [ ] Delete only the curves instead of the whole tab
- [ ] Add functions
	- [ ] Add Warburg element for Li-BAT
  - [ ] Peak finder for quick frequency selection
  - [ ] Plot lambda in DRT
  - [ ] Plot ohmic resistance and polarization resistance trend in EIS and DRT tabs
	- [ ] Interactive manual selected points for CNLS fit frequency determine
	- [ ] Visualized equivalent circuit model assembly and usage of only basic circuit component R, C, L, Q, fFLW, FLW, G, etc.
	- [ ] Z-HIT smoothing from Zahner
	- [ ] Different DRT methodologies
	- [ ] Image save
## ---------- Date: 2025.02.12 ----------
### To do list
- [x] Translate all the codes in Matlab environment into python code
	- [x] Check the results between the matlab environment and python environment 
- [x] Define the best HMI tool in python with open-access
