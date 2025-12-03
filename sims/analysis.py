import numpy as np
import pandas as pd

def calculate_var(returns, alpha=0.05):
    """
    Calculates Value-at-Risk at confidence level alpha.
    Returns the absolute return threshold (e.g., -0.15 for 15% loss).
    """
    if len(returns) == 0:
        return 0.0
    return np.percentile(returns, alpha * 100)

def analyze_fpr(fpr_series_list, threshold=1.0):
    """
    Calculates the probability that FPR falls below a threshold at any point in the path.
    fpr_series_list: list of lists or arrays, each representing FPR path.
    """
    failures = 0
    total_paths = len(fpr_series_list)
    
    for path_fpr in fpr_series_list:
        if np.min(path_fpr) < threshold:
            failures += 1
            
    return failures / total_paths if total_paths > 0 else 0.0

def compare_returns(lst_returns, ftoken_returns):
    """
    Returns a DataFrame with comparative statistics.
    """
    df = pd.DataFrame({
        'LST': lst_returns,
        'fTOKEN': ftoken_returns
    })
    
    stats = df.describe(percentiles=[0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    return stats

def get_terminal_returns(paths, asset_price_col, initial_value=None):
    """
    Extracts terminal returns from a list of path DataFrames.
    """
    returns = []
    for df in paths:
        start_price = df[asset_price_col].iloc[0] if initial_value is None else initial_value
        end_price = df[asset_price_col].iloc[-1]
        ret = (end_price / start_price) - 1
        returns.append(ret)
    return np.array(returns)
