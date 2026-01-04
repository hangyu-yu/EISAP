import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(sys.path[0]))))
import glob
import platform
import numpy as np
import pandas as pd
import src.Functions as fn 
import matplotlib.pyplot as plt
from collections import defaultdict

def Read_Beckhoff(file_path=None):
    """
    读取并合并Beckhoff数据CSV文件
    
    Parameters
    ----------
    file_path : str, optional
        数据文件所在路径。如果为None，则根据操作系统自动设置默认路径
    
    Returns
    -------
    pd.DataFrame
        合并并处理后的数据表
    """
    # ========== Initialization ===========
    
    # 获取所有CSV文件
    file_names = [f for f in os.listdir(file_path) if f.endswith('.csv')]
    
    # 读取并合并所有文件
    all_data = []
    for file_name in file_names:
        fullname = os.path.join(file_path, file_name)
        
        # 读取文件的第一行作为表头
        with open(fullname, 'r', encoding='utf-8') as f:
            header_line = f.readline().strip()
        
        # 分割列名（MATLAB中使用';'作为分隔符）
        original_column_names = header_line.split(';')
        
        # 处理重复列名（添加数字后缀）
        name_count_map = defaultdict(int)
        column_names = []
        
        for i, current_name in enumerate(original_column_names):
            name_count_map[current_name] += 1
            count = name_count_map[current_name]
            
            if count > 1:
                new_name = f"{current_name}{count}"
            else:
                new_name = current_name
            
            column_names.append(new_name)
        
        # 读取数据（使用pandas，更高效）
        # 注意：MATLAB代码中使用';'作为分隔符，这里保持一致
        data_tmp = pd.read_csv(fullname, sep=';', skiprows=1, names=column_names, 
                               encoding='utf-8', engine='python')
        
        all_data.append(data_tmp)
    
    # 合并所有数据
    if all_data:
        data = pd.concat(all_data, ignore_index=True)
    else:
        # 如果没有找到文件，创建空DataFrame
        data = pd.DataFrame()
    
    # 转换数据类型为float（排除Timestamp列）
    for col in data.columns:
        if col != 'Timestamp':
            try:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            except:
                pass
    
    # 处理Timestamp列（MATLAB中的操作）
    if 'Timestamp' in data.columns and len(data) > 0:
        # 将Timestamp转换为数值，假设是纳秒时间戳
        data['Timestamp'] = pd.to_numeric(data['Timestamp'], errors='coerce')
        # MATLAB代码: data.Timestamp = (data.Timestamp - data.Timestamp(1)) / 3600/1e9;
        data['Timestamp'] = (data['Timestamp'] - data['Timestamp'].iloc[0]) / 3600 / 1e9
    
    return data