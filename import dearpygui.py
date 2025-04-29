import dearpygui.dearpygui as dpg
import random
import time

def main():
    dpg.create_context()
    dpg.create_viewport(title="Efficient Table Update", width=800, height=600)
    
    # 初始数据
    data = [
        {"id": 1, "name": "Item 1", "value": 10.5},
        {"id": 2, "name": "Item 2", "value": 20.3}
    ]
    
    # 创建表格
    with dpg.window(tag="main_window"):
        with dpg.table(tag="data_table", header_row=True):
            dpg.add_table_column(label="ID")
            dpg.add_table_column(label="Name")
            dpg.add_table_column(label="Value")
            
            # 存储行引用
            row_tags = []
            for i, item in enumerate(data):
                with dpg.table_row(tag=f"row_{i}"):
                    dpg.add_text(item["id"], tag=f"id_{i}")
                    dpg.add_text(item["name"], tag=f"name_{i}")
                    dpg.add_text(item["value"], tag=f"value_{i}")
                row_tags.append(f"row_{i}")
    
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    # 更新函数
    def update_table():
        for i, item in enumerate(data):
            # 模拟数据变化
            item["value"] = round(random.uniform(0, 100), 2)
            # 直接更新文本项
            dpg.set_value(f"value_{i}", item["value"])
    
    # 主循环
    while dpg.is_dearpygui_running():
        update_table()
        time.sleep(1)  # 每秒更新一次
        dpg.render_dearpygui_frame()
    
    dpg.destroy_context()

if __name__ == "__main__":
    main()
