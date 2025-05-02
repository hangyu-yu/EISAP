import os
import json
import numpy as np

class Config:
    def __init__(self, config_file="config.json"):
        self.project_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_file = os.path.join(self.project_path, 'src', 'GUI', config_file)
        # Default folder path
        self.folder_path = os.path.dirname(os.path.abspath(__file__))
        # Selected file extensions
        self.file_extensions = {}
        # File list
        self.file_list = []
        # Selected file paths
        self.selected_files = []
        # Displayed file name
        self.display_file = []
        # Select data import functino
        self.data_import_function = []
        # Store
        self.store = {}
        # Load configuration
        self.load_config()

    def load_config(self):
        """Load configuration from a JSON file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                data = json.load(f)
                if os.path.exists(data.get("folder_path", "")):
                    self.folder_path = data.get("folder_path", self.folder_path) or self.folder_path
                    self.file_list = data.get("file_list", self.file_list) or self.file_list
                    self.selected_files = data.get("selected_files", self.selected_files) or self.selected_files
                    self.file_extensions = data.get("file_extensions", self.file_extensions) or self.file_extensions
                    self.data_import_function = data.get("data_import_function", self.data_import_function) or self.data_import_function
                    self.display_file = data.get("display_file", self.display_file) or self.display_file

    def save_config(self):
        """Save configuration to a JSON file"""
        data = {
            "folder_path": self.folder_path,
            "file_list": self.file_list,
            "selected_files": self.selected_files,
            "file_extensions": self.file_extensions,
            "display_file": self.display_file,
            "data_import_function": self.data_import_function
        }
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=4)