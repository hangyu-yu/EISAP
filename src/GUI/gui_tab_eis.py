import os
import dearpygui.dearpygui as dpg
import glob

def gui_tab_eis(config):
    with dpg.tab(label="EIS", tag="tab_eis"):
        a = 1