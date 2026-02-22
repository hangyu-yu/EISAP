import os
import glob
import shutil
import platform
import numpy as np
import src.GUI as gui
from pathlib import Path
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
        "version_spacer": 0.45,
        "welcome_spacer_1": 0.25,
        "welcome_spacer_2": 0.25,
        "file_dialog_before_spacer": 0.05,
        "Directory_before_spacer": 0.25,
        "Directory_child_before_spacer": 0.25,
        "extension_spacer": 0.25,
        "file_list_spacer": 0.25,
        "command_buttons_spacer": 0.25,
    }
    configure_spacers(viewport_width, spacers)
    dpg.configure_item("logos_spacer", width=int(viewport_width*(0.97-total_logos_width/viewport_width)/2))
    dpg.configure_item("EPFL_HQ_spacer", width=int(viewport_width*(0.97-total_logos_width/viewport_width)/2 / 50))
    dpg.configure_item("logos_spacer_above", height=int(viewport_height * 0.02))
    dpg.configure_item("logos_spacer_below", height=int(viewport_height * 0.02))
    
    # Update child window sizes
    dpg.configure_item("child_window_folder_directory", width=int(viewport_width * 0.5), height=80)
    dpg.configure_item("child_window_file_list_soceis", width=int(viewport_width * 0.5), height=int(viewport_height * 0.2))
    dpg.configure_item("child_window_tool_box_soceis", width=int(viewport_width * 0.5), height=int(viewport_height*0.1))
    
    # Update text wrapping
    dpg.configure_item("welcome_text_1", wrap=int(viewport_width * 0.5))
    dpg.configure_item("welcome_text_2", wrap=int(viewport_width * 0.5))

# Functions for file dialog callbacks
def folder_selector_ok_callback(sender, app_data, config, EIS, CNLS):
    """
    Callback function when directory is selected in file dialog.
    """
    print('OK was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)
    if config.folder_path != app_data['file_path_name']:
        dpg.delete_item("file_dialog_eis")  # Delete the tab bar if it already exists
        dpg.delete_item("tab_eis", children_only=False)  # Delete the tab if it already exists
        dpg.delete_item("tab_drt", children_only=False)  # Clear the tab content if it exists
        dpg.delete_item("tab_cnls", children_only=False)  # Clear the tab content if it exists
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

    if 'folder_path_old' in config.store.keys():
        if config.folder_path_old != config.folder_path:
            dpg.delete_item("file_dialog_eis")  # Delete the tab bar if it already exists
            dpg.delete_item("tab_eis", children_only=False)  # Delete the tab if it already exists
            dpg.delete_item("tab_drt", children_only=False)  # Clear the tab content if it exists
            dpg.delete_item("tab_cnls", children_only=False)  # Clear the tab
    config.store['folder_path_old'] = config.folder_path

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
                    ("hq_icon", "HydroQuebec.png"),
                    ("bfh_icon", "BFH.png")]
    
    def has_special_chars(path_str):
        try:
            path_str.encode('ascii')
            return False
        except UnicodeEncodeError:
            return True
    if platform.system() in ('Darwin', 'Linux'):
        # Direct loading for macOS/Linux
        root_dir = Path(__file__).resolve().parent.parent.parent
        icon_path = root_dir / "assets" / "icons"
    else:
        # Windows - check if we need temp directory
        root_dir = Path(__file__).resolve().parent.parent.parent
        original_path = str(root_dir)
        
        if has_special_chars(original_path):
            # Use temp directory if path has special characters
            temp_dir = Path("C:/Temp/SOCEIS_Fonts")
            temp_dir.mkdir(parents=True, exist_ok=True)
            icon_path = temp_dir
            
            # Copy icon files to temp directory if not already there
            icons_src_dir = root_dir / "assets" / "icons"
            for icon_file in icons_src_dir.glob('*'):
                if icon_file.is_file() and not (temp_dir / icon_file.name).exists():
                    shutil.copy2(icon_file, temp_dir / icon_file.name)
        else:
            # Use original path if no special characters
            icon_path = root_dir / "assets" / "icons"

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
                
                dpg.add_spacer(height = int(viewport_height * 0.02), tag="logos_spacer_above")  # Spacer for vertical alignment
                with dpg.group(horizontal=True, horizontal_spacing=20):
                    spacer_width = int(viewport_width*(0.97-total_logos_width/viewport_width)/2)
                    dpg.add_spacer(width=spacer_width, tag="logos_spacer")
                    for tag, img in images.items():
                        if tag != "app_icon":
                            scaled_width = int(img["width"] * (viewport_height * 0.05) / img["height"])
                            if tag == "hq_icon":
                                dpg.add_spacer(width=spacer_width / 50, tag=f"EPFL_HQ_spacer")
                            dpg.add_image(f"{tag}_texture", 
                                      width=scaled_width, 
                                      height=int(viewport_height * 0.05),
                                      tag=tag)
                dpg.add_spacer(height = int(viewport_height * 0.02), tag="logos_spacer_below")
                # Version text with original spacer
                with dpg.group(horizontal=True, horizontal_spacing=20):
                    dpg.add_spacer(width=int(viewport_width*0.45), tag="version_spacer")
                    dpg.add_text("(/so.sis/) Beta V1.0", tag="version_text")
                # Welcome text with original spacer
                with dpg.group(horizontal=True, horizontal_spacing=20):
                    dpg.add_spacer(width=int(viewport_width * 0.25), tag="welcome_spacer_1")
                    dpg.add_text("Bienvenue sur SOCEIS. Ce logiciel a été développé par Hangyu Yu (EPFL-GEM, Sion, Suisse, sous la direction du Prof. Jan Van Herle) et Guillaume Jeamonod (Hydro-Québec, Montréal, Canada), sur la base du code original créé par Priscilla Caliandro (BFH, Bienne, Suisse).", 
                                wrap=int(viewport_width * 0.5),
                                tag="welcome_text_1")
                with dpg.group(horizontal=True, horizontal_spacing=20):
                    dpg.add_spacer(width=int(viewport_width * 0.25), tag="welcome_spacer_2")
                    dpg.add_text("Welcome to SOCEIS. This software was developed by Hangyu Yu (EPFL-GEM, Sion, Switzerland, headed by Prof. Jan Van Herle) and Guillaume Jeamonod (Hydro-Québec, Montreal, Canada) based on the code developed by Priscilla Caliandro (BFH, Biel, Switzerland).", 
                                wrap=int(viewport_width * 0.5),
                                tag="welcome_text_2")
            
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
                        dpg.add_menu_item(label="Separate multi-channel zahner files", callback=lambda: gui_utils.small_functions.separate_multichannel_zahner(config, EIS, CNLS)) 
                        dpg.add_menu_item(label="Separate multi-channel biologic files", callback=lambda: gui_utils.small_functions.separate_multichannel_biologic(config, EIS, CNLS)) 
                dpg.add_text(config.folder_path, tag="selected_directory", parent="child_window_folder_directory")

        # Setup the file dialog
        if not config.file_extensions:
            config.file_extensions = ".txt"
        
        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="extension_spacer")
            dpg.add_text("File extension:")
            dpg.add_combo(
                items=[".txt", ".mpt", ".csv", ".xlsx", ".dta", ".z"],
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
