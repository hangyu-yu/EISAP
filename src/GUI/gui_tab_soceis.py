import os
import dearpygui.dearpygui as dpg
import glob

# Functions for GUI tab SOCEIS
def load_images(icon_path, picture_list):
    """
    Load images and return their properties.
    """
    images = {}
    for name, file in picture_list:
        width, height, channels, data = dpg.load_image(os.path.join(icon_path, file))
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
        "version_spacer": 0.49,
        "welcome_spacer": 0.25,
        "right_spacer": 0.05,
        "Directory_before_spacer": 0.25,
        "Directory_child_before_spacer": 0.25,
        "extension_spacer": 0.25,
        "file_list_spacer": 0.25,
    }
    configure_spacers(viewport_width, spacers)
    
    # Update child window sizes
    dpg.configure_item("child_window_folder_directory", width=int(viewport_width * 0.5))
    dpg.configure_item("file_list_child_window", width=int(viewport_width * 0.5))
    
    # Update text wrapping
    dpg.configure_item("welcome_text", wrap=int(viewport_width * 0.5))
    dpg.configure_item("version_text", wrap=int(viewport_width * 0.04))

# Synchronize checkboxes with config.selected_files
# Set up the folder selection dialog
def callback(sender, app_data, config):
    print('OK was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)
    config.folder_path = app_data['file_path_name']
    print("Folder path:", config.folder_path)
def cancel_callback(sender, app_data):
    print('Cancel was clicked.')
    print("Sender: ", sender)
    print("App Data: ", app_data)

def update_file_list(config):
    """
    Update the file list based on the selected extension and default folder path.
    """
    config.file_extensions = dpg.get_value("file_extension_selector")
    select_files()
    dpg.configure_item("file_listbox", items=[os.path.basename(file) for file in config.file_list])
    
def select_files(config):
    """
    Update the selected file paths in the config.
    """
    if os.path.isdir(config.folder_path):
        config.file_list = sorted(glob.glob(os.path.join(config.folder_path, f"*{config.file_extensions}")))
        if not config.file_list:
            config.file_list = ['[Error] No file found! Recheck the folder path or report the issue.']
    else:
        config.file_list = ['[Error] Folder path not found! Recheck the folder path or report the issue.']
    
def sync_checkboxes(config):
    """
    Ensure checkboxes reflect the current state of config.selected_files.
    """
    for file in config.file_list:
        checkbox_tag = f"checkbox_{os.path.basename(file)}"
        is_selected = os.path.basename(file) in config.selected_files
    dpg.set_value(checkbox_tag, is_selected)


def update_selected_files(config):
    """
    Update the list of selected files in config.selected_files.
    """
    config.selected_files = [
    os.path.basename(file) for file in config.file_list
    if dpg.get_value(f"checkbox_{os.path.basename(file)}")
    ]
    print("Selected files:", config.selected_files)

# Main function to create the SOCEIS tab
def gui_tab_soceis(config):
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

    with dpg.tab(label="SOCEIS"):
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
                    dpg.add_spacer(width=int(viewport_width*0.49), tag="version_spacer")
                    dpg.add_text("V0.1", wrap=int(viewport_width * 0.04), tag="version_text")
                
                # Welcome text with original spacer
                with dpg.group(horizontal=True, horizontal_spacing=20):
                    dpg.add_spacer(width=int(viewport_width * 0.25), tag="welcome_spacer")
                    dpg.add_text("Bienvenue au SOCEIS. Ce logiciel a été développé par Hangyu Yu (EPFL-GEM, Sion, Suisse). Nous remercions Guillaume Jeamonod (Hydro-Québec, Montréal, Canada) pour sa contribution précieuse.", 
                                wrap=int(viewport_width * 0.5),
                                tag="welcome_text")
            
            # Right spacer with original width
            dpg.add_spacer(width=int(viewport_width * 0.05), tag="right_spacer")

        dpg.add_file_dialog(
            directory_selector=True, show=False, callback=callback(config), tag="file_dialog_id",
            cancel_callback=cancel_callback(config), width=700 ,height=400)

        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="Directory_before_spacer")
            dpg.add_button(label="Choose project folder", callback=lambda: dpg.show_item("file_dialog_id"))
        
        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="Directory_child_before_spacer")
            with dpg.child_window(width=viewport_width*0.5, height=80, horizontal_scrollbar=True, menubar=True, tag="child_window_folder_directory"):
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
                default_value=config.file_extensions,
                tag="file_extension_selector",
                callback=lambda sender, app_data: print(f"Selected extension: {app_data}"),
                width=100
            )

        select_files(config)

        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="file_list_spacer")
            with dpg.child_window(width=viewport_width*0.5, height=200, horizontal_scrollbar=True, menubar=True, tag="file_list_child_window"):
                for file in config.file_list:
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(label=os.path.basename(file), tag=f"checkbox_{os.path.basename(file)}")
                    checkbox_tag = f"checkbox_{os.path.basename(file)}"
                    if os.path.basename(file) in config.selected_files:
                        dpg.set_value(checkbox_tag, True)
    
        # Automatically update selected files whenever a checkbox is toggled
        for file in config.file_list:
            checkbox_tag = f"checkbox_{os.path.basename(file)}"
            dpg.set_item_callback(checkbox_tag, lambda sender, app_data, tag=checkbox_tag: update_selected_files(config))

        # Call sync_checkboxes initially to ensure consistency
        sync_checkboxes(config)

        # Update the file list whenever the extension is changed
        dpg.set_item_callback("file_extension_selector", update_file_list(config))

    
    # Set up viewport resize callback using correct API
    dpg.set_viewport_resize_callback(update_image_sizes)
