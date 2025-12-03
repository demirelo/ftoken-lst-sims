"""
Test fee routing sensitivity: alpha_f from 40% to 90%

This tests how fee-to-floor ratio affects:
- Floor elevation rate
- Premium accumulation  
- LRE activation
- Overall system performance
"""

import numpy as np
import matplotlib.pyplot as plt
from sims.engine import SimulationEngine
from sims.scenarios import get_scenario
from sims.analysis import generate_full_analysis

def run_fee_routing_sensitivity():
    """Run Super Cycle scenario with different fee routing ratios."""
    
    # Test alpha_f values: 40%, 65%, 90%
    alpha_f_values = [0.40, 0.65, 0.90]
    results = {}
    
    np.random.seed(42)
    
    base_config = get_scenario('super_cycle')
    base_config['n_paths'] = 300  # Faster for sensitivity analysis
    
    for alpha_f in alpha_f_values:
        print(f"\n{'='*60}")
        print(f"Running with alpha_f = {alpha_f:.0%} (Fee-to-Floor Ratio)")
        print(f"{'='*60}")
        
        # Update config
        config = base_config.copy()
        config['fee_to_floor_ratio'] = alpha_f
        
        # Run simulation
        engine = SimulationEngine(config)
        paths = engine.run()
        
        # Analyze
        analysis = generate_full_analysis(paths, f'super_cycle_alpha{int(alpha_f*100)}')
        results[alpha_f] = analysis
        
        print(f"\n--- Results for alpha_f = {alpha_f:.0%} ---")
        print(f"fToken Mean Return:  {analysis['var_analysis']['ftoken_usd']['mean']:+.1%}")
        print(f"fToken VaR (95%):    {analysis['var_analysis']['ftoken_usd']['var_5pct']:+.1%}")
        print(f"Floor Growth Mean:   {analysis['floor_metrics']['mean_floor_growth']:+.1%}")
        print(f"LRE Events Mean:     {analysis['lre_metrics']['mean_lre_events']:.1f}")
        print(f"Min FPR (5th pctl):  {analysis['fpr_analysis']['min_fpr_5th_percentile']:.3f}")
    
    # Create comparison plots
    plot_fee_routing_bands(results, alpha_f_values)
    
    return results


def plot_fee_routing_bands(results, alpha_f_values):
    """Plot results showing bands across fee routing ratios."""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Fee Routing Sensitivity Analysis (Super Cycle)', 
                 fontsize=14, fontweight='bold')
    
    metrics = {
        'fToken Mean Return': lambda r: r['var_analysis']['ftoken_usd']['mean'] * 100,
        'fToken VaR (95%)': lambda r: r['var_analysis']['ftoken_usd']['var_5pct'] * 100,
        'Floor Growth': lambda r: r['floor_metrics']['mean_floor_growth'] * 100,
        'LRE Events': lambda r: r['lre_metrics']['mean_lre_events'],
    }
    
    for ax, (metric_name, metric_fn) in zip(axes.flat, metrics.items()):
        values = [metric_fn(results[a]) for a in alpha_f_values]
        alpha_pct = [int(a*100) for a in alpha_f_values]
        
        ax.plot(alpha_pct, values, marker='o', linewidth=2, markersize=8, color='#2E86C1')
        ax.fill_between(alpha_pct, values, alpha=0.2, color='#2E86C1')
        ax.set_xlabel('Fee-to-Floor Ratio (%)', fontsize=11)
        ax.set_ylabel(metric_name, fontsize=11)
        ax.set_title(metric_name, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_xticks(alpha_pct)
    
    plt.tight_layout()
    plt.savefig('fee_routing_sensitivity.png', dpi=150, bbox_inches='tight')
    print(f"\nSaved sensitivity plot: fee_routing_sensitivity.png")
    plt.close()
    
    # Print summary table
    print(f"\n{'='*80}")
    print("FEE ROUTING SENSITIVITY SUMMARY")
    print(f"{'='*80}")
    print(f"{'Metric':<30} {'40%':>15} {'65%':>15} {'90%':>15}")
    print('-' * 80)
    
    for metric_name, metric_fn in metrics.items():
        values = [metric_fn(results[a]) for a in alpha_f_values]
        if 'LRE' in metric_name:
            print(f"{metric_name:<30} {values[0]:>15.1f} {values[1]:>15.1f} {values[2]:>15.1f}")
        else:
            print(f"{metric_name:<30} {values[0]:>14.1f}% {values[1]:>14.1f}% {values[2]:>14.1f}%")
    
    print(f"{'='*80}\n")


if __name__ == '__main__':
    results = run_fee_routing_sensitivity()
