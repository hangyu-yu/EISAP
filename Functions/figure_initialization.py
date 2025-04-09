# -*- coding: utf-8 -*-
from cmcrameri import cm
import matplotlib.pyplot as plt

def figure_initialization(width=1920, height=1080, font_size=42, colormap_name='vik', dpi=100, font_family='Times New Roman', line_width=3, marker_edge_width=3):
    """
    Initialize the default format for academic plots.

    Parameters:
    - width (int): Width of the figure in pixels. Default is 1920.
    - height (int): Height of the figure in pixels. Default is 1080.
    - font_size (int): Font size for titles, labels, and other text. Default is 42.
    - colormap_name (str): Name of the colormap from cmcrameri. Default is 'vik'.
    - dpi (int): Dots per inch for the figure. Default is 300.
    - font_family (str): Font family for text. Default is 'Times New Roman'.
    - line_width (float): Default line width for plots. Default is 3.
    - marker_edge_width (float): Default marker edge width. Default is 3.

    Returns:
    - None
    """
    # Set figure size in inches (convert pixels to inches using DPI)
    plt.rcParams['figure.figsize'] = (width/dpi, height/dpi)
    
    # Set font size and font family
    plt.rcParams['font.size'] = font_size
    plt.rcParams['axes.titlesize'] = font_size
    plt.rcParams['axes.labelsize'] = font_size
    plt.rcParams['xtick.labelsize'] = font_size
    plt.rcParams['ytick.labelsize'] = font_size
    plt.rcParams['font.family'] = font_family
    plt.rcParams['mathtext.fontset'] = 'custom'  # 使用自定义字体
    plt.rcParams['mathtext.rm'] = font_family    # 数学公式中的普通文本字体
    plt.rcParams['mathtext.it'] = font_family    # 数学公式中的斜体字体
    plt.rcParams['mathtext.bf'] = font_family    # 数学公式中的粗体字体
    plt.rcParams['mathtext.sf'] = font_family    # Sans-serif text in math
    plt.rcParams['mathtext.tt'] = font_family    # Monospace text in math
    
    # Set line width and marker edge width
    plt.rcParams['lines.linewidth'] = line_width
    plt.rcParams['lines.markeredgewidth'] = marker_edge_width
    
    # Modify default marker size (1.5x the current default)
    plt.rcParams['lines.markersize'] = plt.rcParamsDefault['lines.markersize'] * 1.5
    
    # Set colormap
    if hasattr(cm, colormap_name):
        plt.rcParams['image.cmap'] = getattr(cm, colormap_name)
    else:
        raise ValueError(f"Colormap '{colormap_name}' not found in cmcrameri.")

    # Set default legend properties (no box)
    plt.rcParams['legend.frameon'] = False

    # Set default figure window size
    plt.rcParams['figure.dpi'] = dpi

    print("---- Figure initialization complete with the following settings:")
    print(f"-- Size: {width}x{height} pixels, Font size: {font_size}, Font family: {font_family}, Line width: {line_width}, Marker edge width: {marker_edge_width}, Colormap: {colormap_name}, DPI: {dpi}, Marker size: {plt.rcParams['lines.markersize']}")
