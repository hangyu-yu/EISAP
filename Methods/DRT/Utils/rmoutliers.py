import numpy as np
import pandas as pd

def rmoutliers(data, window_size, threshold_constant):
    """
    Remove outliers from the given data using rolling mean and standard deviation.
    
    Parameters:
    data (np.array): Impedance data (real or imaginary part).
    window_size (int): Window size for the rolling mean.
    threshold_constant (float): Threshold constant for identifying outliers.
    
    Returns:
    np.array: Cleaned impedance data.
    np.array: Indices of the outliers.
    """
    
    # Calculate rolling mean and standard deviation
    data_series = pd.Series(data)
    data_mean = data_series.rolling(window=window_size, center=True).mean()
    
    # Handle NaN values by replacing them with the mean of nearby values
    nan_indices = data_mean.index[data_mean.isna()]
    for idx in nan_indices:
        if idx < window_size:
            data_mean.iloc[idx] = data_series[:window_size].mean()
        else:
            data_mean.iloc[idx] = data_series[-window_size:].mean()
    
    # Identify outliers
    data_residuals = np.abs(data_series - data_mean)
    data_threshold = threshold_constant * np.std(data_residuals)
    outliers = data_residuals > data_threshold
    
    # Remove outliers
    data_clean = data[~outliers]
    
    return data_clean, outliers