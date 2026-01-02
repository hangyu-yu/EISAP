# -*- coding: utf-8 -*-
from cmcrameri import cm
import matplotlib.pyplot as plt

def figure_initialization(width=1920, height=1080, font_size=42, colormap_name='vik', dpi=100, font_family='sans-serif', line_width=3, marker_edge_width=3):
    """
    Initialize the default format for academic plots.

    Parameters:
    - width (int): Width of the figure in pixels. Default is 1920.
    - height (int): Height of the figure in pixels. Default is 1080.
    - font_size (int): Font size for titles, labels, and other text. Default is 42.
    - colormap_name (str): Name of the colormap from cmcrameri. Default is 'vik'.
    - dpi (int): Dots per inch for the figure. Default is 300.
    - font_family (str): Font family for text. Default is 'Helvetica'.
    - line_width (float): Default line width for plots. Default is 3.
    - marker_edge_width (float): Default marker edge width. Default is 3.

    Returns:
    - None
    """
    # Set figure size in inches (convert pixels to inches using DPI)
    plt.rcParams['figure.figsize'] = (width/dpi, height/dpi)
    
    # Set font size and font family
    font_mapping = {
        'sans-serif': 'DejaVu Sans',      # 无衬线字体
        'serif': 'DejaVu Serif',          # 衬线字体
        'monospace': 'DejaVu Sans Mono'   # 等宽字体
    }
    
    # 获取对应的 Matplotlib 字体名称
    math_font = font_mapping.get(font_family, 'DejaVu Sans')
    
    # 设置全局参数
    plt.rcParams.update({
        'font.size': font_size,
        'font.family': font_family,
        'axes.labelsize': font_size ,
        'axes.titlesize': font_size + 2,
        'xtick.labelsize': font_size,
        'ytick.labelsize': font_size,
        'legend.fontsize': font_size,
        'figure.titlesize': font_size + 4,
        
        # 数学文本字体设置（使用正确的格式）
        'mathtext.fontset': 'stix',       # 使用 STIX 字体集
        'mathtext.rm': math_font,         # 常规数学字体
        'mathtext.it': math_font,         # 斜体数学字体
        'mathtext.bf': math_font,         # 粗体数学字体
    })
    
    # 设置颜色映射
    # plt.rcParams['image.cmap'] = colormap_name
    
    # Set line width and marker edge width
    plt.rcParams['lines.linewidth'] = line_width
    plt.rcParams['lines.markeredgewidth'] = marker_edge_width
    
    # Modify default marker size (1.5x the current default)
    plt.rcParams['lines.markersize'] = plt.rcParamsDefault['lines.markersize'] * 1.5
    
    # # Set colormap
    # if hasattr(cm, colormap_name):
    #     plt.rcParams['image.cmap'] = getattr(cm, colormap_name)
    # else:
    #     raise ValueError(f"Colormap '{colormap_name}' not found in cmcrameri.")

    # Set default legend properties (no box)
    plt.rcParams['legend.frameon'] = False

    # Set default figure window size
    plt.rcParams['figure.dpi'] = dpi

    print("---- Figure initialization complete with the following settings:")
    print(f"-- Size: {width}x{height} pixels, Font size: {font_size}, Font family: {font_family}, Line width: {line_width}, Marker edge width: {marker_edge_width}, Colormap: {colormap_name}, DPI: {dpi}, Marker size: {plt.rcParams['lines.markersize']}")
