import dearpygui.dearpygui as dpg
import numpy as np

# 初始化
dpg.create_context()
dpg.create_viewport(title="静态折线图工具集", width=1000, height=800)

# 生成模拟数据
x = np.linspace(0, 2*np.pi, 50)
y1 = np.sin(x)
y2 = np.cos(x)
y3 = np.sin(x) * np.cos(x)

with dpg.window(label="主窗口", width=1000, height=800):
    # 创建绘图区域（带标题和边框）
    with dpg.plot(
        label="三角函数对比", 
        height=600, 
        width=-1,  # 自动填充窗口宽度
        no_title=False,  # 显示标题
        no_menus=False,  # 显示右键菜单
        border=True,     # 显示边框
        no_mouse_pos=False  # 显示鼠标位置坐标
    ):
        # -----------------------------------------------
        # 1. 坐标轴配置
        # -----------------------------------------------
        dpg.add_plot_axis(
            dpg.mvXAxis, 
            label="角度 (rad)", 
            tag="x_axis",
            lock_min=True,  # 锁定最小范围
            lock_max=True   # 锁定最大范围
        )
        y_axis = dpg.add_plot_axis(
            dpg.mvYAxis, 
            label="函数值", 
            tag="y_axis",
            lock_min=False,
            lock_max=False
        )
        
        # -----------------------------------------------
        # 2. 绘制三条曲线（不同样式）
        # -----------------------------------------------
        # 正弦曲线（红色实线）
        dpg.add_line_series(
            x, y1, 
            label="sin(x)",
            parent=y_axis,
            color=(255, 0, 0, 255),  # RGBA颜色
            thickness=2,
            tag="series_sin"
        )
        
        # 余弦曲线（蓝色虚线）
        dpg.add_line_series(
            x, y2,
            label="cos(x)",
            parent=y_axis,
            color=(0, 0, 255, 255),
            thickness=2,
            tag="series_cos"
        )
        dpg.bind_item_theme("series_cos", dpg.mvPlotTheme_Stairs)  # 阶梯样式
        
        # 乘积曲线（绿色带标记点）
        dpg.add_line_series(
            x, y3,
            label="sin(x)*cos(x)",
            parent=y_axis,
            color=(0, 255, 0, 255),
            thickness=3,
            tag="series_mix"
        )
        dpg.add_scatter_series(  # 添加数据点标记
            x, y3,
            label="数据点",
            parent=y_axis,
            size=5,
            fill=(0, 255, 0, 150),
            outline=(0, 0, 0, 255)
        )
        
        # -----------------------------------------------
        # 3. 添加辅助工具
        # -----------------------------------------------
        # 网格线（XY轴均显示）
        dpg.add_plot_legend(location=dpg.mvPlot_Location_North)  # 图例放在顶部
        dpg.set_axis_grid("x_axis", True)
        dpg.set_axis_grid("y_axis", True)
        
        # 参考线（水平/垂直）
        dpg.add_drag_line(
            tag="ref_line1",
            label="y=0.5",
            color=(255, 255, 0, 150),
            default_value=0.5,
            vertical=False
        )
        dpg.add_drag_line(
            tag="ref_line2",
            label="x=3.14",
            color=(255, 165, 0, 150),
            default_value=3.14,
            vertical=True
        )
        
        # 区域高亮
        dpg.add_plot_annotation(
            tag="highlight",
            label="极值区",
            default_value=(1.57, 0.9),  # 位置
            color=(255, 0, 0, 100),
            offset=(10, 10),
            clamp=True
        )
        dpg.add_area_series(
            [2.0, 2.5], [0.2, 0.8],
            parent=y_axis,
            fill=(100, 200, 255, 50),
            tag="highlight_area"
        )
    
    # -----------------------------------------------
    # 4. 添加控制按钮（导出/样式调整）
    # -----------------------------------------------
    with dpg.group(horizontal=True):
        dpg.add_button(
            label="导出PNG",
            callback=lambda: dpg.save_viewport_image("plot_export.png"),
            width=100
        )
        dpg.add_button(
            label="深色主题",
            callback=lambda: dpg.bind_theme(dpg.mvTheme_Dark),
            width=100
        )
        dpg.add_button(
            label="浅色主题",
            callback=lambda: dpg.bind_theme(dpg.mvTheme_Light),
            width=100
        )
        dpg.add_checkbox(
            label="显示网格",
            default_value=True,
            callback=lambda s: (
                dpg.set_axis_grid("x_axis", dpg.get_value(s)),
                dpg.set_axis_grid("y_axis", dpg.get_value(s))
            )
        )

# 设置初始视图范围
dpg.set_axis_limits("x_axis", 0, 2*np.pi)
dpg.set_axis_limits("y_axis", -1.2, 1.2)

# 应用自定义样式
with dpg.theme() as global_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
        dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 5)
dpg.bind_theme(global_theme)

# 运行并导出
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
