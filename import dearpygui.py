import dearpygui.dearpygui as dpg

dpg.create_context()

with dpg.window(label="Empty Table Example"):
    with dpg.table(header_row=True, tag="empty_table"):  # `header_row=True` 确保表头可见
        dpg.add_table_column(label="ID", width=100)
        dpg.add_table_column(label="Name", width=200)
        dpg.add_table_column(label="Value", width=150)
        
        # 不添加任何 `table_row`，表格将只显示表头

dpg.create_viewport()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
