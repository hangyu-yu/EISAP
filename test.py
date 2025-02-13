from Methods.DRT.Utils import *

import numpy as np
import pandas as pd

# 示例数据
Re_trunc = np.array([1, 2, 3, 100, 5, 6, 7, 8, 9, 10])
Im_trunc = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 100])
frequency_trunc = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

_, Re_outliers = rmoutliers(Re_trunc, 3, 2)
_, Im_outliers = rmoutliers(Im_trunc, 3, 2)

print(Re_outliers)
print(Im_outliers)

# # 计算滚动均值和标准差
# Re_mean = pd.Series(Re_trunc).rolling(window=6, center=True).mean()
# Re_mean.iloc[0] = Re_trunc[0:3].mean()
# Re_mean.iloc[-1] = Re_trunc[-3:].mean()
# Re_residuals = np.abs(pd.Series(Re_trunc) - Re_mean)
# Re_threshold = 2 * np.std(Re_residuals)
# Re_outliers =  Re_residuals> Re_threshold

# Im_mean = pd.Series(Im_trunc).rolling(window=6, center=True).mean()
# Im_mean.iloc[0] = Im_trunc[0:3].mean()
# Im_mean.iloc[-1] = Im_trunc[-3:].mean()
# Im_residuals = np.abs(pd.Series(Im_trunc) - Im_mean)
# Im_threshold = 2 * np.std(Im_residuals)
# Im_outliers = Im_residuals > Im_threshold

# outliers = Re_outliers | Im_outliers

# # 去除异常值
# Re_trunc_clean = Re_trunc[~outliers]
# Im_trunc_clean = Im_trunc[~outliers]
# frequency_trunc_clean = frequency_trunc[~outliers]

# print("去除异常值后的 Re_trunc:", Re_trunc_clean)
# print("去除异常值后的 Im_trunc:", Im_trunc_clean)
# print("去除异常值后的 frequency_trunc:", frequency_trunc_clean)

# _, Re_outliers = rmoutliers(Re_trunc, 3, 2)
# _, Im_outliers = rmoutliers(Im_trunc, 3, 2)