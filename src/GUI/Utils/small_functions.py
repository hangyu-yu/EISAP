import os
import re
import sys
import csv
import numpy as np
import pandas as pd
import src.GUI as gui
from pathlib import Path
import dearpygui.dearpygui as dpg
import src.GUI.Utils as gui_utils

def string_abbreviation(string, begin=0, end=0):
    """
    Abbreviate a string by removing the first and last 'n' characters.
    
    Parameters:
        string (str): The input string to be abbreviated.
        begin (int): The number of characters to remove from the beginning of the string. Default is 0.
        end (int): The number of characters to remove from the end of the string. Default is 0.
    
    Returns:
        str: The abbreviated string.
    """
    return f"{string[:begin]}...{string[-end:]}" if len(string) > begin+end else string

def separate_multichannel_zahner(config, EIS, CNLS):
    """
    Smartly separate multiple EIS measurements in a single file based on data segments detection.
    Correctly handles multiple measurements by properly identifying each segment's boundaries.
    Uses tab as delimiter and ensures no empty lines in output.
    
    Parameters:
    -----------
    config : object
        Configuration object containing folder_path and file_extensions
    EIS : object
        EIS data object
    CNLS : object
        CNLS data object
        
    Returns:
    --------
    None (creates 'Individual' folder with processed files)
    """
    def smart_split(line):
        """Split line by tabs or whitespace, filtering empty values."""
        line = line.strip()
        if not line:
            return []
        if '\t' in line:
            parts = [p.strip() for p in line.split('\t') if p.strip()]
            if len(parts) >= 2:
                return parts
        return [p for p in re.split(r'\s+', line) if p]
 
    def contains_keyword(line, keywords):
        """Check if line contains any keyword (case insensitive)."""
        line_lower = line.lower()
        return any(keyword.lower() in line_lower for keyword in keywords)
 
    def is_numeric_row(line):
        """Check if line contains mostly numeric values."""
        line = line.replace('\t', ' ').replace(',', ' ').replace(';', ' ').replace('\n', ' ')
        parts = line.strip().split()
        if len(parts) < 2:
            return False
        numeric_count = 0
        for part in parts:
            try:
                float(part)
                numeric_count += 1
            except ValueError:
                pass
        return numeric_count / len(parts) > 0.8
 
    # Create output directory
    directory = config.folder_path
    individual_dir = os.path.join(directory, "Individual")
    os.makedirs(individual_dir, exist_ok=True)
    
    # Get all data files in directory
    data_files = [f for f in os.listdir(directory) 
                 if f.lower().endswith(tuple(ext.lower() for ext in ['.csv', '.txt', '.dat']))]
    
    for data_file in data_files:
        file_path = os.path.join(directory, data_file)
        
        try:
            # Read file with multiple encoding attempts
            encodings = ['utf-8', 'ISO-8859-1', 'latin1']
            lines = []
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = [line.strip() for line in f if line.strip()]  # Remove empty lines upfront
                    break
                except UnicodeDecodeError:
                    continue
            
            if not lines:
                print(f"Warning: Could not read file {data_file}")
                continue
            
            # Segment detection logic
            segments = []
            current_segment = None
            frequency_keywords = ["Freq", "Hz"]
            real_keywords = ["Zreal", "Re(Z)", "Real", "impedance'", 'Impedance,R/Ohm', "Zre"]
            imag_keywords = ["Zimag", "-Im(Z)", "Imag", "impedance''", 'impedance,i/ohm', 'Im(Z)', 'Zim']
            phase_keywords = ["Phase", "Zphz"]
            impedance_keywords = ["impedance", "Zmod", '|Z|']
            
            for i, line in enumerate(lines):
                # Check for standard EIS header
                if (contains_keyword(line, frequency_keywords) and 
                    contains_keyword(line, real_keywords) and 
                    contains_keyword(line, imag_keywords)):
                    if current_segment is not None:
                        current_segment['end'] = i
                        segments.append(current_segment)
                    current_segment = {
                        'header_idx': i,
                        'start': None,
                        'end': None,
                        'type': 'standard'
                    }
                # Check for alternative EIS header
                elif (contains_keyword(line, frequency_keywords) and 
                      contains_keyword(line, phase_keywords) and 
                      contains_keyword(line, impedance_keywords)):
                    if current_segment is not None:
                        current_segment['end'] = i
                        segments.append(current_segment)
                    current_segment = {
                        'header_idx': i,
                        'start': None,
                        'end': None,
                        'type': 'alternative'
                    }
                # Detect data start
                elif current_segment is not None and current_segment['start'] is None:
                    if is_numeric_row(line):
                        current_segment['start'] = i
                # Detect data end
                elif current_segment is not None and current_segment['start'] is not None:
                    if not is_numeric_row(line):
                        current_segment['end'] = i
                        segments.append(current_segment)
                        current_segment = None
            
            # Handle last segment
            if current_segment is not None and current_segment['start'] is not None:
                current_segment['end'] = len(lines)
                segments.append(current_segment)
            
            if not segments:
                print(f"Warning: No EIS segments found in file {data_file}")
                continue
            
            # Process each segment
            for seg_num, segment in enumerate(segments):
                try:
                    # Extract metadata (non-empty lines only)
                    metadata_lines = [line for line in lines[:min(5, segment['header_idx'])] if line.strip()]
                    
                    # Extract header and data (filter empty lines)
                    header = smart_split(lines[segment['header_idx']])
                    data_lines = [line for line in lines[segment['start']:segment['end']] 
                                if line.strip() and is_numeric_row(line)]
                    
                    # Create DataFrame with tab separator
                    data = pd.DataFrame([smart_split(line) for line in data_lines], columns=header)
                    
                    # Convert numeric columns
                    for col in data.columns:
                        data[col] = pd.to_numeric(data[col], errors='ignore')
                    
                    # Sort by frequency (descending)
                    # freq_col = next((col for col in data.columns 
                    #                if contains_keyword(col, frequency_keywords)), None)
                    # if freq_col:
                    #     data = data.sort_values(by=freq_col, ascending=False)
                    
                    # Prepare metadata
                    metadata = {
                        "original_file": os.path.basename(file_path),
                        "segment_number": seg_num + 1,
                        "total_segments": len(segments),
                        "segment_type": segment['type'],
                        "metadata": "\n".join(metadata_lines)
                    }
                    
                    # Save to new file with tab delimiter
                    base_name = os.path.splitext(data_file)[0]
                    output_file = f"{base_name}_seg{seg_num+1:03d}{config.file_extensions}"
                    output_path = os.path.join(individual_dir, output_file)
                    
                    with open(output_path, 'w', encoding='utf-8', newline='') as f:
                        # Write metadata as comments
                        for key, value in metadata.items():
                            f.write(f"# {key}: {value}\n")
                        # Write data with tab separator and no empty lines
                        data.to_csv(f, index=False, sep='\t', lineterminator='\n')
                
                except Exception as e:
                    print(f"Error processing segment {seg_num+1} in file {data_file}: {str(e)}")
                    continue
            
            # Update the file list in the GUI
            config.folder_path = individual_dir
            dpg.delete_item("selected_directory")
            dpg.add_text(config.folder_path, tag="selected_directory", parent="child_window_folder_directory")
            config.data_import_function = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "Functions", "01_Data_read", "read_general_all.py")
            dpg.set_value("file_extension_selector", config.file_extensions)
            gui_utils.file_list.update_file_list(config, "child_window_file_list_soceis", EIS, CNLS)
            
        except Exception as e:
            print(f"Error processing file {data_file}: {str(e)}")

def separate_multichannel_biologic(config, EIS, CNLS):
    """
    Separate multiple EIS measurements by identifying frequency repetition boundaries
    and saving each segment as a separate CSV file with original order preserved.
    """
    def smart_split(line):
        """Split line by tabs, handling quoted strings if needed."""
        return [x.strip() for x in line.strip().split('\t') if x]

    # Create output directory
    directory = config.folder_path
    individual_dir = os.path.join(directory, "Individual")
    os.makedirs(individual_dir, exist_ok=True)
    
    # Get all MPT files in directory
    data_files = [f for f in os.listdir(directory) if f.lower().endswith('.mpt')]
    
    for data_file in data_files:
        file_path = os.path.join(directory, data_file)
        
        try:
            # Read file with multiple encoding attempts
            encodings = ['utf-8', 'ISO-8859-1', 'latin1']
            lines = []
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = [line.strip() for line in f if line.strip()]
                    break
                except UnicodeDecodeError:
                    continue
            
            if not lines:
                print(f"Warning: Could not read file {data_file}")
                continue
            
            # Find header row (contains 'freq/Hz')
            header_idx = None
            freq_col_idx = None
            for i, line in enumerate(lines):
                if 'freq/Hz' in line:
                    header_idx = i
                    header = smart_split(lines[header_idx])
                    freq_col_idx = header.index('freq/Hz')
                    break
            
            if header_idx is None:
                print(f"Warning: No frequency column found in file {data_file}")
                continue
            
            # Extract frequency values
            frequencies = []
            valid_lines = []
            for i in range(header_idx + 1, len(lines)):
                parts = smart_split(lines[i])
                if len(parts) > freq_col_idx:
                    try:
                        freq = float(parts[freq_col_idx])
                        frequencies.append(freq)
                        valid_lines.append(lines[i])
                    except ValueError:
                        continue
            
            if not frequencies:
                print(f"Warning: No valid frequency data found in file {data_file}")
                continue
            
            # Find boundaries where frequency jumps back to start (new measurement)
            boundaries = []
            start_idx = 0
            initial_freq = frequencies[0]
            
            for i in range(1, len(frequencies)):
                # Check if frequency repeats the initial value (new cycle starts)
                if abs(frequencies[i] - initial_freq) < 1e-6:  # Floating point comparison
                    boundaries.append((start_idx, i-1))
                    start_idx = i
            
            # Add the last segment
            if start_idx < len(frequencies):
                boundaries.append((start_idx, len(frequencies)-1))
            
            if len(boundaries) <= 1:
                print(f"Warning: Only found 1 segment in file {data_file}")
                continue
            
            # Save each segment as a separate CSV file
            base_name = os.path.splitext(data_file)[0]
            
            for seg_num, (start_idx, end_idx) in enumerate(boundaries):
                try:
                    # 创建DataFrame
                    segment_data = []
                    for i in range(start_idx, end_idx + 1):
                        segment_data.append(smart_split(valid_lines[i]))
                    
                    df = pd.DataFrame(segment_data, columns=header)
                    
                    # 构建输出路径
                    output_file = f"{base_name}_seg{seg_num+1:03d}.csv"
                    output_path = os.path.join(individual_dir, output_file)
                    
                    # 使用to_csv写入文件
                    df.to_csv(
                        output_path,
                        index=False,          # 不写入行索引
                        sep='\t',            # 保持制表符分隔
                        encoding='utf-8',    # UTF-8编码
                        lineterminator='\n', # 明确指定行终止符
                        quoting=csv.QUOTE_NONE,  # 不添加额外引号
                        escapechar='\\'      # 转义字符
                    )
                    
                    print(f"Saved segment {seg_num+1} with {len(df)} data points")
                    
                except Exception as e:
                    print(f"Error processing segment {seg_num+1}: {str(e)}")
                    continue
            
            # Update the file list in the GUI
            config.folder_path = individual_dir
            dpg.delete_item("selected_directory")
            dpg.add_text(config.folder_path, tag="selected_directory", parent="child_window_folder_directory")
            dpg.set_value("file_extension_selector", ".csv")
            config.data_import_function = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "Functions", "01_Data_read", "read_general_all.py")
            gui_utils.file_list.update_file_list(config, "child_window_file_list_soceis", EIS, CNLS)
            
        except Exception as e:
            print(f"Error processing file {data_file}: {str(e)}")

import pandas as pd
import numpy as np
import re
import os
import csv

def separate_multichannel_fcd(config, EIS, CNLS):
    """
    Process fcd files by separating stack and cell impedance data into different CSV files.
    """
    def smart_split(line):
        """Split line by tabs."""
        return [x.strip() for x in line.strip().split('\t') if x]

    def detect_impedance_columns(header):
        """Detect all impedance-related columns."""
        columns = {}
        
        for i, col_name in enumerate(header):
            # 检测频率列
            if 'Z_Freq' in col_name or 'Freq' in col_name:
                columns['freq'] = i
                print(f"Detected frequency column: {col_name} at index {i}")
            
            # 检测电堆阻抗列 (无数字后缀)
            elif col_name.startswith('Z_Real') and not re.match(r'Z_Real\d+', col_name):
                columns['real_stack'] = i
                print(f"Detected stack real impedance: {col_name} at index {i}")
            
            elif col_name.startswith('Z_Imag') and not re.match(r'Z_Imag\d+', col_name):
                columns['imag_stack'] = i
                print(f"Detected stack imaginary impedance: {col_name} at index {i}")
            
            # 检测电池阻抗列 (数字后缀格式)
            elif re.match(r'Z_Real\d+', col_name):
                if 'real_cells' not in columns:
                    columns['real_cells'] = {}
                # 提取数字后缀
                cell_num = re.search(r'Z_Real(\d+)', col_name).group(1)
                columns['real_cells'][cell_num] = i
                print(f"Detected cell {cell_num} real impedance: {col_name} at index {i}")
            
            elif re.match(r'Z_Imag\d+', col_name):
                if 'imag_cells' not in columns:
                    columns['imag_cells'] = {}
                # 提取数字后缀
                cell_num = re.search(r'Z_Imag(\d+)', col_name).group(1)
                columns['imag_cells'][cell_num] = i
                print(f"Detected cell {cell_num} imaginary impedance: {col_name} at index {i}")
        
        return columns

    def extract_channel_data(data_rows, impedance_cols, header, channel_type, channel_num=None):
        """Extract data for specific channel (stack or cell)."""
        extracted_data = []
        
        for row in data_rows:
            try:
                # 验证频率数据
                freq = float(row[impedance_cols['freq']])
                if freq <= 0 or np.isnan(freq):
                    continue
                
                # 根据通道类型提取数据
                if channel_type == 'stack':
                    # 电堆数据：频率 + 电堆阻抗
                    if 'real_stack' in impedance_cols and 'imag_stack' in impedance_cols:
                        z_real = float(row[impedance_cols['real_stack']])
                        z_imag = float(row[impedance_cols['imag_stack']])
                        
                        if not (np.isnan(z_real) or np.isinf(z_real) or 
                                np.isnan(z_imag) or np.isinf(z_imag)):
                            extracted_row = [
                                row[impedance_cols['freq']],  # Frequency
                                row[impedance_cols['real_stack']],  # Z_Real
                                row[impedance_cols['imag_stack']]   # Z_Imag
                            ]
                            extracted_data.append(extracted_row)
                
                elif channel_type == 'cell' and channel_num is not None:
                    # 电池数据：频率 + 指定电池的阻抗
                    real_key = str(channel_num)
                    imag_key = str(channel_num)
                    
                    if (real_key in impedance_cols.get('real_cells', {}) and 
                        imag_key in impedance_cols.get('imag_cells', {})):
                        
                        z_real = float(row[impedance_cols['real_cells'][real_key]])
                        z_imag = float(row[impedance_cols['imag_cells'][imag_key]])
                        
                        if not (np.isnan(z_real) or np.isinf(z_real) or 
                                np.isnan(z_imag) or np.isinf(z_imag)):
                            extracted_row = [
                                row[impedance_cols['freq']],  # Frequency
                                row[impedance_cols['real_cells'][real_key]],  # Z_Real
                                row[impedance_cols['imag_cells'][imag_key]]   # Z_Imag
                            ]
                            extracted_data.append(extracted_row)
                            
            except (ValueError, IndexError):
                continue
        
        return extracted_data

    # Create output directory
    directory = config.folder_path
    individual_dir = os.path.join(directory, "Individual")
    os.makedirs(individual_dir, exist_ok=True)
    
    # Get all fcd files
    data_files = [f for f in os.listdir(directory) if f.lower().endswith('.fcd')]
    
    for data_file in data_files:
        file_path = os.path.join(directory, data_file)
        
        try:
            # Read file
            encodings = ['utf-8', 'ISO-8859-1', 'latin1']
            lines = []
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = [line.strip() for line in f if line.strip()]
                    break
                except UnicodeDecodeError:
                    continue
            
            if not lines:
                print(f"Warning: Could not read file {data_file}")
                continue
            
            # Find data start and header
            data_start_idx = None
            header_idx = None
            
            for i, line in enumerate(lines):
                if line == "End Comments":
                    data_start_idx = i + 1
                    if data_start_idx < len(lines):
                        header_idx = data_start_idx - 2
                        header = smart_split(lines[header_idx])
                        break
            
            if header_idx is None:
                print(f"Warning: Data format incorrect in file {data_file}")
                continue
            
            # Detect impedance columns
            impedance_cols = detect_impedance_columns(header)
            if 'freq' not in impedance_cols:
                print(f"Warning: No frequency column found in {data_file}")
                continue
            
            # Extract all raw data
            raw_data = []
            for i in range(header_idx + 1, len(lines)):
                parts = smart_split(lines[i])
                if len(parts) >= len(header):
                    raw_data.append(parts)
            
            base_name = os.path.splitext(data_file)[0]
            files_created = []
            
            # 保存电堆数据 (_0后缀)
            if 'real_stack' in impedance_cols and 'imag_stack' in impedance_cols:
                stack_data = extract_channel_data(raw_data, impedance_cols, header, 'stack')
                if stack_data:
                    stack_df = pd.DataFrame(stack_data, columns=['Freq', 'Z_Real', 'Z_Imag'])
                    output_file = f"{base_name}_0.csv"
                    output_path = os.path.join(individual_dir, output_file)
                    
                    stack_df.to_csv(
                        output_path,
                        index=False,
                        sep='\t',
                        encoding='utf-8',
                        lineterminator='\n',
                        quoting=csv.QUOTE_NONE,
                        escapechar='\\'
                    )
                    files_created.append(f"stack (_0): {len(stack_data)} points")
                    print(f"Saved stack data to {output_file}")
            
            # 保存各电池数据 (_1, _2, _3...后缀)
            if 'real_cells' in impedance_cols:
                for cell_num in impedance_cols['real_cells'].keys():
                    if cell_num in impedance_cols.get('imag_cells', {}):
                        cell_data = extract_channel_data(raw_data, impedance_cols, header, 'cell', cell_num)
                        if cell_data:
                            cell_df = pd.DataFrame(cell_data, columns=['Freq', 'Z_Real', 'Z_Imag'])
                            output_file = f"{base_name}_{cell_num}.csv"
                            output_path = os.path.join(individual_dir, output_file)
                            
                            cell_df.to_csv(
                                output_path,
                                index=False,
                                sep='\t',
                                encoding='utf-8',
                                lineterminator='\n',
                                quoting=csv.QUOTE_NONE,
                                escapechar='\\'
                            )
                            files_created.append(f"cell {cell_num} (_{cell_num}): {len(cell_data)} points")
                            print(f"Saved cell {cell_num} data to {output_file}")
            
            if files_created:
                print(f"Successfully processed {data_file}: {', '.join(files_created)}")
            else:
                print(f"Warning: No valid impedance data found in {data_file}")
            
            # Update GUI
            config.folder_path = individual_dir
            dpg.delete_item("selected_directory")
            dpg.add_text(config.folder_path, tag="selected_directory", parent="child_window_folder_directory")
            dpg.set_value("file_extension_selector", ".csv")
            config.data_import_function = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "Functions", "01_Data_read", "read_general_all.py")
            gui_utils.file_list.update_file_list(config, "child_window_file_list_soceis", EIS, CNLS)
            
        except Exception as e:
            print(f"Error processing file {data_file}: {str(e)}")
            import traceback
            traceback.print_exc()

def font_size_confirm_callback(sender, app_data, config, font_path_medium, font_path_light):
    config.font_size = dpg.get_value("input_text_font_size")
    dpg.delete_item("window_font_size_popup")
    
    config.save_config()
    print("[LOG] Configuration saved.")
    print(f"---- Font size changed to {config.font_size}.")

    current_file = os.path.abspath(__file__)
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))
    target_file = os.path.join(parent_dir, "SOCEIS.py")
    if os.name == 'nt':  # Windows
        import subprocess
        subprocess.Popen([sys.executable, target_file], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:  # Linux/macOS
        os.execv(sys.executable, [sys.executable, target_file])
    dpg.destroy_context()

def font_size_callback(sender, app_data, config, font_path_medium, font_path_light):
    print("-- Adjust font size...")
    with dpg.window(
        label="Font size", 
        tag="window_font_size_popup", 
        modal=True, 
        width=300, 
        height=150
    ):
        with dpg.group(horizontal=True):
            dpg.add_text(f"Current font size: {config.font_size}")
        with dpg.group(horizontal=True):
            dpg.add_text("Input the font size:")
            dpg.add_input_int(tag="input_text_font_size", 
                              default_value=config.font_size, 
                              width=-1)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Confirm", callback=lambda: font_size_confirm_callback(sender, app_data, config, font_path_medium, font_path_light))
            dpg.add_button(label="Cancel", callback=lambda: print("---- Font size change cancelled."))