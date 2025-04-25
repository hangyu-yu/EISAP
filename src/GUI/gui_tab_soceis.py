import os
import dearpygui.dearpygui as dpg
import glob

def update_image_sizes():
    """
    Callback function to update image sizes when viewport is resized.
    """
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    # Update main app icon
    dpg.configure_item("app_icon", width=int(viewport_width * 0.1), height=int(viewport_width * 0.1))
    
    # Update partner logos (keeping original scaling logic)
    logo_height = int(viewport_height * 0.05)
    epfl_width = dpg.get_item_width("epfl_icon_texture")
    epfl_height = dpg.get_item_height("epfl_icon_texture")
    epfl_scaled_width = int(epfl_width * logo_height / epfl_height)
    dpg.configure_item("epfl_icon", width=epfl_scaled_width, height=logo_height)
    
    gem_width = dpg.get_item_width("gem_icon_texture")
    gem_height = dpg.get_item_height("gem_icon_texture")
    gem_scaled_width = int(gem_width * logo_height / gem_height)
    dpg.configure_item("gem_icon", width=gem_scaled_width, height=logo_height)
    
    hq_width = dpg.get_item_width("hq_icon_texture")
    hq_height = dpg.get_item_height("hq_icon_texture")
    hq_scaled_width = int(hq_width * logo_height / hq_height)
    dpg.configure_item("hq_icon", width=hq_scaled_width, height=logo_height)
    
    # Update spacer widths (keeping original complex calculations)
    dpg.configure_item("main_icon_spacer", width=int(viewport_width * 0.45))
    
    epfl_scaled_width = int(dpg.get_item_width("epfl_icon_texture") * logo_height / dpg.get_item_height("epfl_icon_texture"))
    gem_scaled_width = int(dpg.get_item_width("gem_icon_texture") * logo_height / dpg.get_item_height("gem_icon_texture"))
    hq_scaled_width = int(dpg.get_item_width("hq_icon_texture") * logo_height / dpg.get_item_height("hq_icon_texture"))
    total_logos_width = epfl_scaled_width + gem_scaled_width + hq_scaled_width
    spacer_width = int(viewport_width*(0.97-total_logos_width/viewport_width)/2)
    dpg.configure_item("logos_spacer", width=spacer_width)
    
    dpg.configure_item("version_spacer", width=int(viewport_width*0.49))
    dpg.configure_item("welcome_spacer", width=int(viewport_width * 0.25))
    dpg.configure_item("right_spacer", width=int(viewport_width * 0.05))
    dpg.configure_item("Directory_before_spacer", width=int(viewport_width * 0.25))
    dpg.configure_item("Directory_child_before_spacer", width=int(viewport_width * 0.25))
    dpg.configure_item("child_window_folder_directory", width=int(viewport_width * 0.5))
    dpg.configure_item("extension_spacer", width=int(viewport_width * 0.25))
    dpg.configure_item("file_list_spacer", width=int(viewport_width * 0.25))
    dpg.configure_item("file_list_child_window", width=int(viewport_width * 0.5))
    
    # Update text wrapping
    dpg.configure_item("welcome_text", wrap=int(viewport_width * 0.5))
    dpg.configure_item("version_text", wrap=int(viewport_width * 0.04))

def gui_tab_soceis(config):
    """
    Function to create the SOCEIS tab in the GUI.
    This function is called from the main GUI file.
    """
    viewport_width = dpg.get_viewport_width()
    viewport_height = dpg.get_viewport_height()
    
    with dpg.tab(label="SOCEIS"):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icons")
        
        # Load images
        soceis_width, soceis_height, soceis_channels, soceis_data = dpg.load_image(os.path.join(icon_path, 'app_icon.png'))
        epfl_width, epfl_height, epfl_channels, epfl_data = dpg.load_image(os.path.join(icon_path, 'EPFL.png'))
        gem_width, gem_height, gem_channels, gem_data = dpg.load_image(os.path.join(icon_path, 'GEM.png'))
        hq_width, hq_height, hq_channels, hq_data = dpg.load_image(os.path.join(icon_path, 'HydroQuebec.png'))
        
        # Calculate initial scaled widths for logos
        epfl_scaled_width = int(epfl_width * (viewport_height * 0.05) / epfl_height)
        gem_scaled_width = int(gem_width * (viewport_height * 0.05) / gem_height)
        hq_scaled_width = int(hq_width * (viewport_height * 0.05) / hq_height)
        
        # Create texture registry
        with dpg.texture_registry(show=False):
            dpg.add_static_texture(soceis_width, soceis_height, soceis_data, tag="app_icon_texture")
            dpg.add_static_texture(epfl_width, epfl_height, epfl_data, tag="epfl_icon_texture")
            dpg.add_static_texture(gem_width, gem_height, gem_data, tag="gem_icon_texture")
            dpg.add_static_texture(hq_width, hq_height, hq_data, tag="hq_icon_texture")
        
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
                    total_logos_width = epfl_scaled_width + gem_scaled_width + hq_scaled_width
                    spacer_width = int(viewport_width*(0.97-total_logos_width/viewport_width)/2)
                    dpg.add_spacer(width=spacer_width, tag="logos_spacer")
                    dpg.add_image("epfl_icon_texture", 
                                width=epfl_scaled_width, 
                                height=int(viewport_height * 0.05),
                                tag="epfl_icon")
                    dpg.add_image("gem_icon_texture", 
                                width=gem_scaled_width, 
                                height=int(viewport_height * 0.05),
                                tag="gem_icon")
                    dpg.add_image("hq_icon_texture", 
                                width=hq_scaled_width, 
                                height=int(viewport_height * 0.05),
                                tag="hq_icon")
                
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
    
        # Set up the folder selection dialog
        def callback(sender, app_data):
            print('OK was clicked.')
            print("Sender: ", sender)
            print("App Data: ", app_data)
            config.folder_path = app_data['file_path_name']
            print("Folder path:", config.folder_path)

        def cancel_callback(sender, app_data):
            print('Cancel was clicked.')
            print("Sender: ", sender)
            print("App Data: ", app_data)

        dpg.add_file_dialog(
            directory_selector=True, show=False, callback=callback, tag="file_dialog_id",
            cancel_callback=cancel_callback, width=700 ,height=400)

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

        def update_file_list():
            """
            Update the file list based on the selected extension and default folder path.
            """
            config.file_extensions = dpg.get_value("file_extension_selector")
            select_files()
            dpg.configure_item("file_listbox", items=[os.path.basename(file) for file in config.file_list])
            
        def select_files():
            """
            Update the selected file paths in the config.
            """
            if os.path.isdir(config.folder_path):
                config.file_list = sorted(glob.glob(os.path.join(config.folder_path, f"*{config.file_extensions}")))
                if not config.file_list:
                    config.file_list = ['[Error] No file found! Recheck the folder path or report the issue.']
            else:
                config.file_list = ['[Error] Folder path not found! Recheck the folder path or report the issue.']

        select_files()

        with dpg.group(horizontal=True, horizontal_spacing=20):
            dpg.add_spacer(width=int(viewport_width * 0.25), tag="file_list_spacer")
            with dpg.child_window(width=viewport_width*0.5, height=200, horizontal_scrollbar=True, menubar=True, tag="file_list_child_window"):
                for file in config.file_list:
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(label=os.path.basename(file), tag=f"checkbox_{os.path.basename(file)}")
                    checkbox_tag = f"checkbox_{os.path.basename(file)}"
                    if os.path.basename(file) in config.selected_files:
                        dpg.set_value(checkbox_tag, True)
        
        
        def update_selected_files():
            """
            Update the list of selected files in config.selected_files.
            """
            config.selected_files = [
            os.path.basename(file) for file in config.file_list
            if dpg.get_value(f"checkbox_{os.path.basename(file)}")
            ]
            print("Selected files:", config.selected_files)

        # Automatically update selected files whenever a checkbox is toggled
        for file in config.file_list:
            checkbox_tag = f"checkbox_{os.path.basename(file)}"
            dpg.set_item_callback(checkbox_tag, lambda sender, app_data, tag=checkbox_tag: update_selected_files())

        # Synchronize checkboxes with config.selected_files
        def sync_checkboxes():
            """
            Ensure checkboxes reflect the current state of config.selected_files.
            """
            for file in config.file_list:
                checkbox_tag = f"checkbox_{os.path.basename(file)}"
                is_selected = os.path.basename(file) in config.selected_files
            dpg.set_value(checkbox_tag, is_selected)

        # Call sync_checkboxes initially to ensure consistency
        sync_checkboxes()

        # Update the file list whenever the extension is changed
        dpg.set_item_callback("file_extension_selector", update_file_list)

    
    # Set up viewport resize callback using correct API
    dpg.set_viewport_resize_callback(update_image_sizes)
