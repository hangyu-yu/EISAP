import dearpygui.dearpygui as dpg

def update_window_size(window_parameter):
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    # Update the size of the child windows
    # Example window_parameter
    # window_parameter = {
    #     "window_1": (0.5, 0.5),  # 50% width and 50% height of the viewport
    #     "window_2": (0.3, 0.7),  # 30% width and 70% height of the viewport
    #     "window_3": (0.8, 0.4)   # 80% width and 40% height of the viewport
    # }
    for tag, ratios in window_parameter.items():
        width_ratio, height_ratio = ratios
        new_width = int(viewport_width * width_ratio)
        new_height = int(viewport_height * height_ratio)
        dpg.configure_item(tag, width=new_width, height=new_height)