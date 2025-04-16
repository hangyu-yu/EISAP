from importlib import reload
import platform
import os
import glob
import sys
sys.path.append(os.path.dirname(os.path.dirname(sys.path[0])))
import numpy as np
import pandas as pd
import Functions as fn
import matplotlib.pyplot as plt
from Methods.CNLS.Circuit import Circuit


# 01 - Initialization
if platform.system() == 'Darwin':  # macOS
    Folder_Path = r'/Users/atlas/Library/CloudStorage/OneDrive-Personal/Experience/00_PhD/12_Side_quests/03_Maryam_data_AMON/02_Sorted_Data/02_NH3'
elif platform.system() == 'Windows':  # Windows
    Folder_Path = r'D:\OneDrive\Experience\00_PhD\12_Side_quests\03_Maryam_data_AMON\02_Sorted_Data\02_NH3'
fn.figure_initialization(width=1920, height=1080, font_size=24, colormap_name='vik', dpi=100, font_family='Times New Roman', line_width=3, marker_edge_width=3)

txt_files = glob.glob(os.path.join(Folder_Path, '*.txt'))
