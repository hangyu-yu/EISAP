import dearpygui.dearpygui as dpg

dpg.create_context()

def intx_callback(sender, app_data, user_data):
    """处理intx输入的回调函数"""
    print(f"{user_data['type']} 输入值更新: {app_data}")

with dpg.window(label="Input IntX 控件演示", width=600, height=400):
    # 1. 单整数输入 (基础对照)
    dpg.add_text("基本整数输入:")
    dpg.add_input_int(
        label="单一整数",
        default_value=42,
        callback=intx_callback,
        user_data={"type": "int"},
        width=120,
        min_value=0,
        max_value=100,
        min_clamped=True,
        max_clamped=False
    )
    
    dpg.add_spacer(height=20)
    
    # 2. 二维整数输入 (int2)
    dpg.add_text("二维整数输入 (如坐标):")
    dpg.add_input_intx(
        label="位置坐标",
        default_value=(10, 20),
        callback=intx_callback,
        user_data={"type": "int2"},
        width=120,
        size=2,
        min_value=0,
        max_value=500,
        format="%d px",
        on_enter=True
    )
    
    dpg.add_spacer(height=15)
    
    # 3. 三维整数输入 (int3)
    dpg.add_text("三维整数输入 (如颜色RGB):")
    dpg.add_input_intx(
        label="RGB颜色",
        default_value=(255, 128, 0),
        callback=intx_callback,
        user_data={"type": "int3"},
        width=150,
        size=3,
        min_value=0,
        max_value=255,
        min_clamped=True,
        max_clamped=True,
        format="%03d"
    )
    
    dpg.add_spacer(height=15)
    
    # 4. 四维整数输入 (int4)
    dpg.add_text("四维整数输入 (如RGBA颜色):")
    dpg.add_input_intx(
        label="RGBA颜色",
        default_value=(255, 128, 0, 255),
        callback=intx_callback,
        user_data={"type": "int4"},
        width=180,
        size=4,
        min_value=0,
        max_value=255,
        format="RGBA(%d,%d,%d,%d)",
        readonly=False
    )

dpg.create_viewport(title='Input IntX 控件演示', width=600, height=400)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
