import os
import dearpygui.dearpygui as dpg

def gui_tab_soceis():
    """
    Function to create the SOCEIS tab in the GUI.
    This function is called from the main GUI file.
    """
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    with dpg.tab(label="SOCEIS"):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icons")
        soceis_width, soceis_height, soceis_channels, soceis_data = dpg.load_image(os.path.join(icon_path, 'app_icon.png'))
        epfl_width, epfl_height, epfl_channels, epfl_data = dpg.load_image(os.path.join(icon_path, 'EPFL.png'))
        gem_width, gem_height, gem_channels, gem_data = dpg.load_image(os.path.join(icon_path, 'GEM.png'))
        hq_width, hq_height, hq_channels, hq_data = dpg.load_image(os.path.join(icon_path, 'HydroQuebec.png'))
        epfl_scaled_width = int(epfl_width * (viewport_height * 0.05) / epfl_height)
        gem_scaled_width = int(gem_width * (viewport_height * 0.05) / gem_height)
        hq_scaled_width = int(hq_width * (viewport_height * 0.05) / hq_height)
        with dpg.texture_registry(show=False):
            dpg.add_static_texture(soceis_width, soceis_height, soceis_data, tag="app_icon_texture")
            dpg.add_static_texture(epfl_width, epfl_height, epfl_data, tag="epfl_icon_texture")
            dpg.add_static_texture(gem_width, gem_height, gem_data, tag="gem_icon_texture")
            dpg.add_static_texture(hq_width, hq_height, hq_data, tag="hq_icon_texture")
        
        with dpg.group(horizontal=True, horizontal_spacing=0):
            with dpg.group():
                with dpg.group(horizontal=True, horizontal_spacing=0):
                    dpg.add_spacer(width=int(viewport_width * 0.45))
                    dpg.add_image("app_icon_texture", width=int(viewport_width * 0.1), height=int(viewport_width * 0.1))
                
                with dpg.group(horizontal=True, horizontal_spacing=10):
                    dpg.add_spacer(width=int(viewport_width*(1-(epfl_scaled_width+gem_scaled_width+hq_scaled_width)/viewport_width)/2))
                    dpg.add_image("epfl_icon_texture", width=epfl_scaled_width, height=int(viewport_height * 0.05))
                    dpg.add_image("gem_icon_texture", width=gem_scaled_width, height=int(viewport_height * 0.05))
                    dpg.add_image("hq_icon_texture", width=hq_scaled_width, height=int(viewport_height * 0.05))
                with dpg.group(horizontal=True, horizontal_spacing=0):
                    dpg.add_spacer(width=int(viewport_width*0.49))
                    dpg.add_text("V0.1", wrap=int(viewport_width * 0.04))
                with dpg.group(horizontal=True, horizontal_spacing=0):
                    dpg.add_spacer(width=int(viewport_width * 0.25))
                    dpg.add_text("Bienvenue au SOCEIS. Ce logiciel a été développé par Hangyu Yu (EPFL-GEM, Sion, Suisse). Nous remercions Guillaume Jeamonod (Hydro-Québec, Montréal, Canada) pour sa contribution précieuse.", wrap=int(viewport_width * 0.5))
            dpg.add_spacer(width=int(viewport_width * 0.05))