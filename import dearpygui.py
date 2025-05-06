import dearpygui.dearpygui as dpg
import numpy as np

def get_points_on_curve(x_data, y_data, num_points=1):
    """
    完全重构的稳定版曲线取点工具
    参数:
        x_data: x轴数据数组
        y_data: y轴数据数组
        num_points: 需要获取的点数量
    返回:
        选择的点坐标列表 [(x1,y1), (x2,y2), ...]
    """
    points = []
    
    # 初始化DearPyGUI
    dpg.create_context()
    dpg.create_viewport(title='Point Picker', width=800, height=600)
    
    # 创建主窗口
    with dpg.window(label="Main Window", tag="main_window", width=800, height=600):
        # 创建绘图区域
        with dpg.plot(label="Curve Plot", height=-1, width=-1, tag="plot"):
            dpg.add_plot_axis(dpg.mvXAxis, label="X")
            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Y")
            dpg.add_line_series(x_data, y_data, parent=y_axis, tag="curve")
    
    # 点击事件处理 - 使用更可靠的回调方式
    def plot_click_callback(sender, app_data):
        if dpg.is_item_hovered("plot"):
            mouse_pos = dpg.get_plot_mouse_pos()
            idx = np.argmin(np.abs(x_data - mouse_pos[0]))
            points.append((x_data[idx], y_data[idx]))
            
            # 标记选中的点
            with dpg.draw_node(parent="plot"):
                dpg.draw_circle((x_data[idx], y_data[idx]), 0.05, color=(255, 0, 0, 255))
            
            if len(points) >= num_points:
                dpg.stop_dearpygui()
    
    # 直接绑定回调到绘图区域
    with dpg.item_handler_registry(tag="plot_handler"):
        dpg.add_item_clicked_handler(callback=plot_click_callback)
    dpg.bind_item_handler_registry("plot", "plot_handler")
    
    # 配置并运行GUI
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
    
    return points[:num_points]

# 使用示例
if __name__ == "__main__":
    # 生成示例数据
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    
    # 获取3个点
    selected_points = get_points_on_curve(x, y, num_points=3)
    print("Selected points:")
    for i, (x, y) in enumerate(selected_points, 1):
        print(f"Point {i}: x={x:.2f}, y={y:.2f}")
