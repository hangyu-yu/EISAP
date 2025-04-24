import dearpygui.dearpygui as dpg

def gui_tab_soceis():
    """
    Function to create the SOCEIS tab in the GUI.
    This function is called from the main GUI file.
    """
    with dpg.tab(label="SOCEIS"):
        dpg.add_text("Welcome to Tab 1!")
        dpg.add_button(label="Click Me", callback=lambda: print("Button in Tab 1 clicked!"))