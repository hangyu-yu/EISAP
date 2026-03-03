import os
import sys
import requests
import zipfile
import tempfile
import shutil
import subprocess
import time
from pathlib import Path
import dearpygui.dearpygui as dpg

class Updater:
    def __init__(self, config):
        self.config = config
        self.repo_url = "https://github.com/hangyu-yu/SOCEIS/archive/main.zip"
        self.current_exe = sys.executable
        self.script_dir = Path(__file__).resolve().parent.parent.parent.parent
        
    def download_and_replace(self, sender=None, app_data=None):
        """Main function to download and replace files"""
        try:
            dpg.set_value("status_text", "Starting download...")
            
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, "update.zip")
            
            if not self._download_update(zip_path):
                return False
            
            if not self._extract_update(zip_path, temp_dir):
                return False
            
            if not self._replace_files(temp_dir):
                return False
            
            self._restart_application()
            return True
            
        except Exception as e:
            dpg.set_value("status_text", f"Update failed: {str(e)}")
            return False
    
    def _download_update(self, zip_path):
        """Download update files"""
        try:
            response = requests.get(self.repo_url, stream=True, timeout=30)
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0:
                                progress = (downloaded_size / total_size) * 100
                                dpg.set_value("status_text", f"Download progress: {progress:.1f}%")
                
                dpg.set_value("status_text", "Download completed")
                return True
            else:
                dpg.set_value("status_text", f"Download failed, HTTP status: {response.status_code}")
                return False
                
        except Exception as e:
            dpg.set_value("status_text", f"Download error: {str(e)}")
            return False
    
    def _extract_update(self, zip_path, temp_dir):
        """Extract update files"""
        try:
            extract_path = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_path, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            dpg.set_value("status_text", "Extraction completed")
            return True
            
        except Exception as e:
            dpg.set_value("status_text", f"Extraction error: {str(e)}")
            return False
    
    def _replace_files(self, temp_dir):
        """Replace files with new versions"""
        try:
            extract_path = os.path.join(temp_dir, "extracted")
            extracted_items = os.listdir(extract_path)
            
            if not extracted_items:
                dpg.set_value("status_text", "No files found after extraction")
                return False
            
            source_dir = os.path.join(extract_path, extracted_items[0])
            target_dir = self.script_dir
            
            # Exclude Projects folder and config file
            exclude_list = {
                'Projects', 'src/GUI/config.json', '__pycache__', '.git',
                'config.ini', 'user_settings.ini', 'temp', 'logs', 'data'
            }
            
            self._copy_tree(source_dir, target_dir, exclude_list)
            dpg.set_value("status_text", "File replacement completed")
            return True
            
        except Exception as e:
            dpg.set_value("status_text", f"File replacement error: {str(e)}")
            return False
    
    def _copy_tree(self, source, target, exclude_list):
        """Recursively copy directory tree excluding specified items"""
        for item in os.listdir(source):
            if item in exclude_list:
                continue
                
            source_path = os.path.join(source, item)
            target_path = os.path.join(target, item)
            
            # Check for config file exclusion
            if any(excluded in str(source_path) for excluded in exclude_list if '/' in excluded or '\\' in excluded):
                continue
                
            if os.path.isdir(source_path):
                if not os.path.exists(target_path):
                    os.makedirs(target_path)
                self._copy_tree(source_path, target_path, exclude_list)
            else:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(source_path, target_path)
    
    def _restart_application(self):
        """Restart the application"""
        try:
            dpg.set_value("status_text", "Preparing to restart...")
            time.sleep(1)
            
            current_pid = os.getpid()
            
            if getattr(sys, 'frozen', False):
                restart_cmd = [self.current_exe]
            else:
                restart_cmd = [sys.executable, sys.argv[0]]
            
            subprocess.Popen(restart_cmd)
            
            time.sleep(2)
            os._exit(0)
            
        except Exception as e:
            dpg.set_value("status_text", f"Restart error: {str(e)}")
    
    def check_for_updates(self):
        """Check if updates are available (optional feature)"""
        try:
            response = requests.get("https://api.github.com/repos/hangyu-yu/SOCEIS/releases/latest", timeout=10)
            if response.status_code == 200:
                latest_version = response.json()['tag_name']
                current_version = getattr(self.config, 'version', '1.0.0')
                return latest_version != current_version
        except:
            pass
        return False