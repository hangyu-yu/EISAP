import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.create_viewport(title="Radio Button Example", width=600, height=300)

with dpg.window(label="Radio Button Demo"):
    # 添加单选按钮组
    dpg.add_radio_button(
        items=["Option 1", "Option 2", "Option 3"],
        tag="radio_group",
        default_value="Option 1",  # 默认选中项
        callback=lambda: print(f"Selected: {dpg.get_value('radio_group')}")
    )

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
