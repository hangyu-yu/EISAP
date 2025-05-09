import os
import glob
import numpy as np
import src.GUI as gui
import src.GUI.Utils as gui_utils
import dearpygui.dearpygui as dpg

"""
SOCEIS GUI Module Documentation
This module implements the GUI interface for SOCEIS using Dear PyGui. It provides functionality for:
- Loading and displaying application icons and partner logos
- Handling file selection and directory browsing
- Managing user selections through checkboxes
- Responsive layout adjustments based on viewport size
Main Components:
1. Image Handling:
   - load_images(): Loads image files and extracts their properties
   - create_texture_registry(): Creates texture registry for efficient image rendering
   - configure_images(): Dynamically adjusts image sizes based on viewport
2. Layout Management:
   - configure_spacers(): Calculates and sets spacer widths for responsive layout
   - update_image_sizes(): Main callback for responsive design adjustments
3. File Operations:
   - folder_selector_ok_callback(): Handles directory selection confirmation
   - folder_selector_cancel_callback(): Handles directory selection cancellation
   - select_files(): Populates file list based on directory and extension
   - update_file_list(): Updates UI with filtered files
4. Main Interface:
   - gui_tab_soceis(): Creates and configures the main SOCEIS tab
The GUI features:
- Responsive design that adapts to window resizing
- File browser with extension filtering
- Multi-selection capability
- Institutional branding with partner logos
- Dynamic layout spacers for consistent appearance
Configuration Requirements:
- config object must contain:
  - folder_path: Default directory path
  - file_extensions: Default file filter
  - file_list: List of available files
  - selected_files: List of user-selected files
"""

# Functions for GUI tab SOCEIS
def load_images(icon_path, picture_list):
    """
    Load images and return their properties.
    """
    images = {}
    for name, file in picture_list:
        width, height, _, data = dpg.load_image(os.path.join(icon_path, file))
        images[name] = {"width": width, "height": height, "data": data}
    return images

def create_texture_registry(images):
    """
    Create a texture registry for the loaded images.
    """
    with dpg.texture_registry(show=False):
        for tag, img in images.items():
            dpg.add_static_texture(img["width"], img["height"], img["data"], tag=f"{tag}_texture")

def configure_spacers(viewport_width, spacers):
    """
    Configure spacers based on viewport width.
    """
    for tag, ratio in spacers.items():
        dpg.configure_item(tag, width=int(viewport_width * ratio))

def configure_images(images, viewport_width, viewport_height):
    """
    Configure image sizes based on viewport dimensions.
    """
    logo_height = int(viewport_height * 0.05)
    dpg.configure_item("app_icon", width=int(viewport_width * 0.1), height=int(viewport_width * 0.1))
    for tag in ["epfl_icon", "gem_icon", "hq_icon"]:
        width = images[tag]["width"]
        height = images[tag]["height"]
        scaled_width = int(width * logo_height / height)
        dpg.configure_item(tag, width=scaled_width, height=logo_height)

def update_image_sizes():
    """
    Callback function to update image sizes and spacers when viewport is resized.
    """
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    # Update main app icon
    dpg.configure_item("app_icon", width=int(viewport_width * 0.1), height=int(viewport_width * 0.1))
    
    # Update partner logos dynamically
    logo_height = int(viewport_height * 0.05)
    total_logos_width = 0
    for tag in ["epfl_icon", "gem_icon", "hq_icon"]:
        width = dpg.get_item_width(f"{tag}_texture")
        height = dpg.get_item_height(f"{tag}_texture")
        scaled_width = int(width * logo_height / height)
        dpg.configure_item(tag, width=scaled_width, height=logo_height)
        total_logos_width += scaled_width
    
    # Update spacers dynamically
    spacers = {
        "main_icon_spacer": 0.45,
        "logos_spacer": (0.97 - total_logos_width / viewport_width) / 2,
        "version_spacer": 0.48,
        "welcome_spacer": 0.25,
        "file_dialog_before_spacer": 0.05,
        "Directory_before_spacer": 0.25,
        "Directory_child_before_spacer": 0.25,
        "extension_spacer": 0.25,
        "file_list_spacer": 0.25,
        "command_buttons_spacer": 0.25,
    }
    configure_spacers(viewport_width, spacers)
    
    # Update child window sizes
    dpg.configure_item("child_window_folder_directory", width=int(viewport_width * 0.5), height=80)
    dpg.configure_item("child_window_file_list_soceis", width=int(viewport_width * 0.5), height=int(viewport_height * 0.2))
    dpg.configure_item("child_window_tool_box_soceis", width=int(viewport_width * 0.5), height=int(viewport_height*0.1))
    
    # Update text wrapping
    dpg.configure_item("welcome_text", wrap=int(viewport_width * 0.5))
    dpg.configure_item("version_text", wrap=int(viewport_width * 0.04))

# Functions for file dialog callbacks
def folder_selector_ok_callback(sender, app_data, config, EIS, CNLS):
    """
    Callback function when directory is selected in file dialog.
    """
    print('OK was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)
    config.folder_path = app_data['file_path_name']
    EIS.file_folder = config.folder_path
    CNLS.file_folder = config.folder_path
    config.store['beacon_DRT_import'] = True
    print("Folder path:", config.folder_path)
    past_file_names = list(config.store.keys())
    for item in past_file_names:
        config.store.pop(item) if item not in ['element_list', 'peak_fixed_frequencies', 'Elements', 'segment_constraints', 'beacon_DRT_import', 'nbr_peaks'] else None
        if item == 'Elements':
            config.store[item] = [{'name': 'L1', 'type': 'Inductor', 'Param': [1], 'Ub': [np.inf], 'Lb': [1e-10]},
                                  {'name': 'R2', 'type': 'Resistor', 'Param': [1], 'Ub': [np.inf], 'Lb': [1e-10]}]
    dpg.set_value("selected_directory", config.folder_path)

    gui_utils.file_list.update_file_list(config, "child_window_file_list_soceis", EIS, CNLS)

def folder_selector_cancel_callback(sender, app_data):
    """
    Callback function when file dialog is cancelled.
    """
    print('Cancel was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)

# Main function to create the SOCEIS tab
def gui_tab_soceis(config, EIS, CNLS):
    """
    Function to create the SOCEIS tab in the GUI.
    This function is called from the main GUI file.
    """
    # Initialization of resources
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()

    picture_list = [("app_icon", "app_icon.png"), 
                    ("epfl_icon", "EPFL.png"), 
                    ("gem_icon", "GEM.png"), 
                    ("hq_icon", "HydroQuebec.png")]
    
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icons")

    images = load_images(icon_path, picture_list) # Load images and their properties

    with dpg.tab(label="SOCEIS", tag="tab_soceis", parent="tab_bar_main"):
        # Create texture registry
        create_texture_registry(images)

        # Calculate initial scaled widths for logos
        total_logos_width = sum(int(img["width"] * (viewport_height * 0.05) / img["height"]) for img in images.values())
        
        with dpg.group(horizontal=True, horizontal_spacing=20):
            with dpg.group():
                # Main app icon with original spacer calculation
                with dpg.group(horizontal=True, horizontal_spacing=20):
                    dpg.add_spacer(width=int(viewport_width * 0.45), tag="main_icon_spacer")
                    dpg.add_image("app_icon_texture", 
                                width=int(viewport_width * 0.1), 
                                height=int(viewport_width * 0.1),
                                tag="app_icon")
                
                # Partner logos with original complex spacer calculation
                with dpg.group(horizontal=True, horizontal_spacing=20):
                    spacer_width = int(viewport_width*(0.97-total_logos_width/viewport_width)/2)
                    dpg.add_spacer(width=spacer_width, tag="logos_spacer")
                    for tag, img in images.items():
                        if tag != "app_icon":
                            scaled_width = int(img["width"] * (viewport_height * 0.05) / img["height"])
                            dpg.add_image(f"{tag}_texture", 
                                      width=scaled_width, 
                                      height=int(viewport_height * 0.05),
                                      tag=tag)
                
                # Version text with original spacer
                with dpg.group(horizontal=True, horizontal_spacing=20):
                    dpg.add_spacer(width=int(viewport_width*0.48), tag="version_spacer")
                    dpg.add_text("Beta V0.4", tag="version_text")
                
                # Welcome text with original spacer
                with dpg.group(horizontal=True, horizontal_spacing=20):
                    dpg.add_spacer(width=int(viewport_width * 0.25), tag="welcome_spacer")
                    dpg.add_text("Bienvenue au SOCEIS. Ce logiciel a été développé par Hangyu Yu (EPFL-GEM, Sion, Suisse). Nous remercions Guillaume Jeamonod (Hydro-Québec, Montréal, Canada) pour sa contribution précieuse.", 
                                wrap=int(viewport_width * 0.5),
                                tag="welcome_text")
            
        # Right spacer with original width
        dpg.add_spacer(width=int(viewport_width * 0.05), tag="file_dialog_before_spacer")
        dpg.add_file_dialog(
            directory_selector=True, 
            show=False, 
            default_path=config.folder_path if config.folder_path is not None and "[Error]" not in config.folder_path else os.getcwd(),
            callback=lambda sender, app_data: folder_selector_ok_callback(sender, app_data, config, EIS, CNLS),
            tag="file_dialog_soceis",
            cancel_callback=lambda sender, app_data: folder_selector_cancel_callback(sender, app_data),
            width=700,
            height=400)

        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="Directory_before_spacer")
            dpg.add_button(label="Choose project folder", callback=lambda: dpg.show_item("file_dialog_soceis"))
        
        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="Directory_child_before_spacer")
            with dpg.child_window(width=int(viewport_width*0.5), height=80, horizontal_scrollbar=True, menubar=True, tag="child_window_folder_directory"):
                with dpg.menu_bar():
                    with dpg.menu(label="Selected directory"):
                        dpg.add_menu_item(label="")
                dpg.add_text(config.folder_path, tag="selected_directory")
                
        # Setup the file dialog
        if not config.file_extensions:
            config.file_extensions = ".txt"
        
        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="extension_spacer")
            dpg.add_text("File extension:")
            dpg.add_combo(
                items=[".txt", ".mpt", ".csv", ".xlsx"],
                tag = 'file_extension_selector',
                default_value=config.file_extensions,
                callback=lambda _, app_data: gui_utils.file_list.update_file_list(config, "child_window_file_list_soceis", EIS, CNLS),
                width=100
            )

        gui_utils.file_list.select_files(config, "child_window_file_list_soceis")

        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="file_list_spacer")
            with dpg.child_window(width=int(viewport_width*0.5), height=int(viewport_height*0.2), horizontal_scrollbar=True, menubar=True, tag="child_window_file_list_soceis"):
                gui_utils.file_list.update_file_list(config, "child_window_file_list_soceis", EIS, CNLS)

        # Add the buttons
        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="command_buttons_spacer")
            with dpg.child_window(width=int(viewport_width*0.5), height=int(viewport_height*0.1), horizontal_scrollbar=True, menubar=True, tag="child_window_tool_box_soceis"):
                with dpg.menu_bar():
                    with dpg.menu(label="Tool box"):
                        dpg.add_menu_item(label="") 
                with dpg.group(horizontal=True, horizontal_spacing=10):
                    dpg.add_button(label="EIS analysis", callback=lambda: gui.gui_tab_eis(config, EIS, CNLS))
                    dpg.add_button(label="DRT analysis", callback=lambda: gui.gui_tab_drt(config, EIS, CNLS))
                    dpg.add_button(label="CNLS fitting", callback=lambda: gui.gui_tab_cnls(config, EIS, CNLS))

    # Set up viewport resize callback using correct API
    dpg.set_viewport_resize_callback(update_image_sizes)
