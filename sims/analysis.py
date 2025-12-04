"""
Analysis Functions for fToken/LST Monte Carlo Simulations

This module provides metrics computation and analysis functions
aligned with the Structural Solvency report:
- VaR calculations (Section 5)
- FPR analysis (Section 9.3)
- Bad debt analysis (Section 9.2)
- Comparative return analysis (Section 8)
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional


# =============================================================================
# Value-at-Risk (VaR) Functions
# =============================================================================

def calculate_var(returns: np.ndarray, alpha: float = 0.05) -> float:
    """
    Calculate Value-at-Risk at confidence level alpha.
    
    Per spec Section 5.1:
    VaR_α is the return threshold at the α quantile.
    Negative values indicate losses.
    
    Args:
        returns: Array of returns
        alpha: Confidence level (0.05 = 95% VaR)
        
    Returns:
        VaR threshold (e.g., -0.15 for 15% loss at 95% confidence)
    """
    if len(returns) == 0:
        return 0.0
    return float(np.percentile(returns, alpha * 100))


def calculate_cvar(returns: np.ndarray, alpha: float = 0.05) -> float:
    """
    Calculate Conditional VaR (Expected Shortfall).
    
    CVaR is the expected return given that we're in the tail.
    More sensitive to tail risk than VaR.
    
    Args:
        returns: Array of returns
        alpha: Confidence level
        
    Returns:
        Expected return in the worst alpha% of outcomes
    """
    if len(returns) == 0:
        return 0.0
    var = calculate_var(returns, alpha)
    tail_returns = returns[returns <= var]
    if len(tail_returns) == 0:
        return var
    return float(np.mean(tail_returns))


def calculate_relative_var(
    lst_returns: np.ndarray,
    ftoken_returns: np.ndarray,
    alpha: float = 0.05
) -> Dict[str, float]:
    """
    Calculate relative VaR metrics comparing LST to fToken.
    
    Per spec Section 5.5:
    "Relative return R_rel = R_LST - R_fTOKEN"
    
    Args:
        lst_returns: Array of LST returns
        ftoken_returns: Array of fToken returns
        alpha: Confidence level
        
    Returns:
        Dictionary with relative risk metrics
    """
    relative_returns = lst_returns - ftoken_returns
    
    return {
        'relative_var': calculate_var(relative_returns, alpha),
        'relative_cvar': calculate_cvar(relative_returns, alpha),
        'relative_mean': float(np.mean(relative_returns)),
        'relative_std': float(np.std(relative_returns)),
        'lst_outperformance_prob': float(np.mean(relative_returns > 0)),
    }


# =============================================================================
# FPR (Floor Protection Ratio) Analysis
# =============================================================================

def analyze_fpr(
    fpr_series_list: List[np.ndarray],
    thresholds: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Comprehensive FPR analysis across all paths.
    
    Per spec Section 9.3:
    - Green zone: FPR >= 1.10
    - Yellow zone: 1.05 <= FPR < 1.10
    - Red zone: FPR < 1.05
    - Insolvency: FPR < 1.0
    
    Args:
        fpr_series_list: List of FPR time series (one per path)
        thresholds: Custom thresholds (default uses spec values)
        
    Returns:
        Dictionary with FPR analysis results
    """
    if thresholds is None:
        thresholds = {
            'insolvency': 1.0,
            'red_zone': 1.05,
            'yellow_zone': 1.10,
        }
    
    total_paths = len(fpr_series_list)
    if total_paths == 0:
        return {}
    
    # Calculate per-path metrics
    min_fpr_per_path = [np.min(fpr) for fpr in fpr_series_list]
    final_fpr_per_path = [fpr[-1] for fpr in fpr_series_list]
    mean_fpr_per_path = [np.mean(fpr) for fpr in fpr_series_list]
    
    # Zone analysis
    ever_insolvent = sum(1 for m in min_fpr_per_path if m < thresholds['insolvency'])
    ever_red = sum(1 for m in min_fpr_per_path if m < thresholds['red_zone'])
    ever_yellow = sum(1 for m in min_fpr_per_path if m < thresholds['yellow_zone'])
    
    # Time in zones (across all paths)
    total_steps = sum(len(fpr) for fpr in fpr_series_list)
    steps_insolvent = sum(np.sum(fpr < thresholds['insolvency']) for fpr in fpr_series_list)
    steps_red = sum(np.sum(fpr < thresholds['red_zone']) for fpr in fpr_series_list)
    steps_yellow = sum(np.sum(fpr < thresholds['yellow_zone']) for fpr in fpr_series_list)
    
    return {
        # Probabilities
        'prob_ever_insolvent': ever_insolvent / total_paths,
        'prob_ever_red_zone': ever_red / total_paths,
        'prob_ever_yellow_zone': ever_yellow / total_paths,
        
        # Time fractions
        'time_fraction_insolvent': steps_insolvent / total_steps if total_steps > 0 else 0,
        'time_fraction_red': steps_red / total_steps if total_steps > 0 else 0,
        'time_fraction_yellow': steps_yellow / total_steps if total_steps > 0 else 0,
        
        # Distribution statistics
        'min_fpr_mean': float(np.mean(min_fpr_per_path)),
        'min_fpr_std': float(np.std(min_fpr_per_path)),
        'min_fpr_5th_percentile': float(np.percentile(min_fpr_per_path, 5)),
        'min_fpr_1st_percentile': float(np.percentile(min_fpr_per_path, 1)),
        
        'final_fpr_mean': float(np.mean(final_fpr_per_path)),
        'final_fpr_std': float(np.std(final_fpr_per_path)),
        
        'mean_fpr_across_paths': float(np.mean(mean_fpr_per_path)),
        
        # Raw data for further analysis
        'min_fpr_distribution': np.array(min_fpr_per_path),
        'final_fpr_distribution': np.array(final_fpr_per_path),
    }


def classify_fpr_zone(fpr: float) -> str:
    """
    Classify FPR into zone.
    
    Per spec Section 9.3:
    - Green: >= 1.10
    - Yellow: [1.05, 1.10)
    - Red: < 1.05
    """
    if fpr >= 1.10:
        return "green"
    elif fpr >= 1.05:
        return "yellow"
    else:
        return "red"


# =============================================================================
# Bad Debt Analysis
# =============================================================================

def analyze_bad_debt(paths: List[pd.DataFrame]) -> Dict[str, Any]:
    """
    Analyze bad debt metrics across all paths.
    
    Per spec Section 9.2:
    "Bad debt hits L_f directly... reduces headroom"
    
    Args:
        paths: List of path DataFrames with 'ftoken_bad_debt_cumulative' column
        
    Returns:
        Dictionary with bad debt analysis
    """
    if len(paths) == 0:
        return {}
    
    # Extract bad debt data
    final_bad_debt = [df['ftoken_bad_debt_cumulative'].iloc[-1] for df in paths]
    max_bad_debt = [df['ftoken_bad_debt_cumulative'].max() for df in paths]
    
    # Count paths with any bad debt
    paths_with_bad_debt = sum(1 for bd in final_bad_debt if bd > 0)
    
    # Get initial reserves for ratio calculation
    initial_reserves = paths[0]['ftoken_reserves'].iloc[0] if len(paths) > 0 else 1
    
    return {
        'probability_of_bad_debt': paths_with_bad_debt / len(paths),
        'paths_with_bad_debt': paths_with_bad_debt,
        
        'mean_bad_debt': float(np.mean(final_bad_debt)),
        'max_bad_debt': float(np.max(final_bad_debt)),
        'std_bad_debt': float(np.std(final_bad_debt)),
        
        # As fraction of initial reserves
        'mean_bad_debt_ratio': float(np.mean(final_bad_debt)) / initial_reserves,
        'max_bad_debt_ratio': float(np.max(final_bad_debt)) / initial_reserves,
        
        # Distribution percentiles
        'bad_debt_95th_percentile': float(np.percentile(final_bad_debt, 95)),
        'bad_debt_99th_percentile': float(np.percentile(final_bad_debt, 99)),
        
        # Raw distribution
        'bad_debt_distribution': np.array(final_bad_debt),
    }


# =============================================================================
# Return Comparison
# =============================================================================

def compare_returns(
    lst_returns: np.ndarray,
    ftoken_returns: np.ndarray
) -> pd.DataFrame:
    """
    Create comparative return statistics DataFrame.
    
    Args:
        lst_returns: Array of LST returns
        ftoken_returns: Array of fToken returns
        
    Returns:
        DataFrame with comparative statistics
    """
    df = pd.DataFrame({
        'LST': lst_returns,
        'fTOKEN': ftoken_returns
    })
    
    stats = df.describe(percentiles=[0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    
    # Add additional metrics
    stats.loc['VaR_5%'] = [calculate_var(lst_returns, 0.05), calculate_var(ftoken_returns, 0.05)]
    stats.loc['CVaR_5%'] = [calculate_cvar(lst_returns, 0.05), calculate_cvar(ftoken_returns, 0.05)]
    stats.loc['VaR_1%'] = [calculate_var(lst_returns, 0.01), calculate_var(ftoken_returns, 0.01)]
    stats.loc['CVaR_1%'] = [calculate_cvar(lst_returns, 0.01), calculate_cvar(ftoken_returns, 0.01)]
    stats.loc['skewness'] = [float(pd.Series(lst_returns).skew()), float(pd.Series(ftoken_returns).skew())]
    stats.loc['kurtosis'] = [float(pd.Series(lst_returns).kurtosis()), float(pd.Series(ftoken_returns).kurtosis())]
    
    return stats


def get_terminal_returns(
    paths: List[pd.DataFrame],
    asset_price_col: str,
    initial_value: Optional[float] = None
) -> np.ndarray:
    """
    Extract terminal returns from path DataFrames.
    
    Args:
        paths: List of path DataFrames
        asset_price_col: Column name for asset price
        initial_value: Optional fixed initial value
        
    Returns:
        Array of terminal returns
    """
    returns = []
    for df in paths:
        start_price = df[asset_price_col].iloc[0] if initial_value is None else initial_value
        end_price = df[asset_price_col].iloc[-1]
        ret = (end_price / start_price) - 1 if start_price > 0 else 0
        returns.append(ret)
    return np.array(returns)


def get_ftoken_usd_returns(paths: List[pd.DataFrame]) -> np.ndarray:
    """
    Calculate fToken USD returns (floor * underlying price).
    
    Per spec Section 5.3:
    V_fTOKEN_USD(t) = P_f(t) * P_underlying_USD(t)
    
    Args:
        paths: List of path DataFrames
        
    Returns:
        Array of USD-denominated fToken returns
    """
    returns = []
    for df in paths:
        start_val = df['ftoken_floor'].iloc[0] * df['underlying_price'].iloc[0]
        end_val = df['ftoken_floor'].iloc[-1] * df['underlying_price'].iloc[-1]
        ret = (end_val / start_val) - 1 if start_val > 0 else 0
        returns.append(ret)
    return np.array(returns)


# =============================================================================
# Comprehensive Analysis Report
# =============================================================================

def generate_full_analysis(paths: List[pd.DataFrame], scenario_name: str = "") -> Dict[str, Any]:
    """
    Generate comprehensive analysis report for a simulation run.
    
    Args:
        paths: List of path DataFrames from SimulationEngine
        scenario_name: Name of the scenario for reporting
        
    Returns:
        Dictionary with all analysis results
    """
    if len(paths) == 0:
        return {'error': 'No paths to analyze'}
    
    # Extract return series
    lst_returns = get_terminal_returns(paths, 'lst_price')
    ftoken_floor_returns = get_terminal_returns(paths, 'ftoken_floor')
    ftoken_usd_returns = get_ftoken_usd_returns(paths)
    underlying_returns = get_terminal_returns(paths, 'underlying_price')
    
    # Extract FPR series
    fpr_series = [df['ftoken_fpr'].values for df in paths]
    
    # Compute all analyses
    return {
        'scenario': scenario_name,
        'n_paths': len(paths),
        'n_steps': len(paths[0]) if len(paths) > 0 else 0,
        
        # VaR Analysis (Section 5)
        'var_analysis': {
            'lst': {
                'var_5pct': calculate_var(lst_returns, 0.05),
                'var_1pct': calculate_var(lst_returns, 0.01),
                'cvar_5pct': calculate_cvar(lst_returns, 0.05),
                'mean': float(np.mean(lst_returns)),
                'std': float(np.std(lst_returns)),
            },
            'ftoken_floor': {
                'var_5pct': calculate_var(ftoken_floor_returns, 0.05),
                'var_1pct': calculate_var(ftoken_floor_returns, 0.01),
                'cvar_5pct': calculate_cvar(ftoken_floor_returns, 0.05),
                'mean': float(np.mean(ftoken_floor_returns)),
                'std': float(np.std(ftoken_floor_returns)),
            },
            'ftoken_usd': {
                'var_5pct': calculate_var(ftoken_usd_returns, 0.05),
                'var_1pct': calculate_var(ftoken_usd_returns, 0.01),
                'cvar_5pct': calculate_cvar(ftoken_usd_returns, 0.05),
                'mean': float(np.mean(ftoken_usd_returns)),
                'std': float(np.std(ftoken_usd_returns)),
            },
            'underlying': {
                'var_5pct': calculate_var(underlying_returns, 0.05),
                'var_1pct': calculate_var(underlying_returns, 0.01),
                'cvar_5pct': calculate_cvar(underlying_returns, 0.05),
                'mean': float(np.mean(underlying_returns)),
                'std': float(np.std(underlying_returns)),
            },
            'relative': calculate_relative_var(lst_returns, ftoken_usd_returns),
        },
        
        # FPR Analysis (Section 9.3)
        'fpr_analysis': analyze_fpr(fpr_series),
        
        # Bad Debt Analysis (Section 9.2)
        'bad_debt_analysis': analyze_bad_debt(paths),
        
        # Comparative Return Statistics
        'return_comparison': compare_returns(lst_returns, ftoken_usd_returns).to_dict(),
        
        # Floor elevation metrics
        'floor_metrics': {
            'mean_floor_growth': float(np.mean([
                (df['ftoken_floor'].iloc[-1] / df['ftoken_floor'].iloc[0]) - 1 
                for df in paths
            ])),
            'mean_final_floor': float(np.mean([df['ftoken_floor'].iloc[-1] for df in paths])),
            'std_final_floor': float(np.std([df['ftoken_floor'].iloc[-1] for df in paths])),
        },
        
        # LRE metrics
        'lre_metrics': {
            'mean_lre_events': float(np.mean([df['ftoken_lre_triggered'].sum() for df in paths])),
            'max_lre_events': int(np.max([df['ftoken_lre_triggered'].sum() for df in paths])),
            'paths_with_lre': sum(1 for df in paths if df['ftoken_lre_triggered'].sum() > 0),
        },
        
        # Depeg metrics
        'depeg_metrics': {
            'mean_depeg_events': float(np.mean([df['lst_depeg_event'].sum() for df in paths])),
            'max_depeg_events': int(np.max([df['lst_depeg_event'].sum() for df in paths])),
            'paths_with_depeg': sum(1 for df in paths if df['lst_depeg_event'].sum() > 0),
        },
        
        # Credit metrics
        'credit_metrics': {
            'mean_final_debt': float(np.mean([df['ftoken_debt'].iloc[-1] for df in paths])),
            'mean_max_debt': float(np.mean([df['ftoken_debt'].max() for df in paths])),
            'mean_final_locked': float(np.mean([df['ftoken_locked_supply'].iloc[-1] for df in paths])),
        },
        
        # Supply metrics
        'supply_metrics': {
            'mean_final_supply': float(np.mean([df['ftoken_supply'].iloc[-1] for df in paths])),
            'mean_final_market_cap': float(np.mean([df['ftoken_supply'].iloc[-1] * df['ftoken_floor'].iloc[-1] for df in paths])),
            'mean_max_supply': float(np.mean([df['ftoken_supply'].max() for df in paths])),
            'mean_min_supply': float(np.mean([df['ftoken_supply'].min() for df in paths])),
        },
        
        # Fee metrics
        'fee_metrics': {
            'mean_stakers_fees': float(np.mean([df['stakers_fees'].iloc[-1] for df in paths])),
            'mean_team_fees': float(np.mean([df['team_fees'].iloc[-1] for df in paths])),
            'max_stakers_fees': float(np.max([df['stakers_fees'].iloc[-1] for df in paths])),
            'max_team_fees': float(np.max([df['team_fees'].iloc[-1] for df in paths])),
        },
        
        # Volume metrics
        'volume_metrics': {
            'avg_daily_buy_volume': float(np.mean([df['buy_volume'].mean() for df in paths])),
            'avg_daily_sell_volume': float(np.mean([df['sell_volume'].mean() for df in paths])),
            'avg_daily_loan_volume': float(np.mean([df['loan_volume'].mean() for df in paths])),
            'total_buy_volume': float(np.mean([df['buy_volume'].sum() for df in paths])),
            'total_sell_volume': float(np.mean([df['sell_volume'].sum() for df in paths])),
        },
    }


def print_analysis_summary(analysis: Dict[str, Any]):
    """Print a human-readable summary of analysis results."""
    print(f"\n{'='*60}")
    print(f"Analysis Summary: {analysis.get('scenario', 'Unknown Scenario')}")
    print(f"{'='*60}")
    print(f"Paths: {analysis['n_paths']}, Steps: {analysis['n_steps']}")
    
    print(f"\n--- Value-at-Risk (95% confidence) ---")
    var = analysis['var_analysis']
    print(f"LST VaR:          {var['lst']['var_5pct']:+.2%}")
    print(f"fToken USD VaR:   {var['ftoken_usd']['var_5pct']:+.2%}")
    print(f"Underlying VaR:   {var['underlying']['var_5pct']:+.2%}")
    print(f"fToken Floor VaR: {var['ftoken_floor']['var_5pct']:+.2%} (in reserve units)")
    
    print(f"\n--- Expected Returns ---")
    print(f"LST Mean:          {var['lst']['mean']:+.2%}")
    print(f"fToken USD Mean:   {var['ftoken_usd']['mean']:+.2%}")
    print(f"Underlying Mean:   {var['underlying']['mean']:+.2%}")
    
    print(f"\n--- FPR (Floor Protection Ratio) ---")
    fpr = analysis['fpr_analysis']
    print(f"Prob Ever Insolvent (FPR < 1.0): {fpr['prob_ever_insolvent']:.2%}")
    print(f"Prob Ever Red Zone (FPR < 1.05): {fpr['prob_ever_red_zone']:.2%}")
    print(f"Min FPR (5th percentile):        {fpr['min_fpr_5th_percentile']:.3f}")
    print(f"Final FPR Mean:                  {fpr['final_fpr_mean']:.3f}")
    
    print(f"\n--- Bad Debt ---")
    bd = analysis['bad_debt_analysis']
    print(f"Probability of Bad Debt: {bd['probability_of_bad_debt']:.2%}")
    print(f"Mean Bad Debt:           {bd['mean_bad_debt']:,.0f}")
    print(f"Max Bad Debt:            {bd['max_bad_debt']:,.0f}")
    
    print(f"\n--- Floor Elevation ---")
    fm = analysis['floor_metrics']
    print(f"Mean Floor Growth: {fm['mean_floor_growth']:+.2%}")
    print(f"Mean Final Floor:  {fm['mean_final_floor']:.4f}")
    
    print(f"\n--- Events ---")
    print(f"Mean LRE Events:   {analysis['lre_metrics']['mean_lre_events']:.1f}")
    print(f"Mean Depeg Events: {analysis['depeg_metrics']['mean_depeg_events']:.1f}")
    
    print(f"{'='*60}\n")
