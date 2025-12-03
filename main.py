import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
from sims.engine import SimulationEngine
from sims.scenarios import SCENARIOS
from sims.analysis import calculate_var, analyze_fpr, get_terminal_returns, compare_returns

def run_scenario(scenario_name, config):
    print(f"\n--- Running Scenario: {scenario_name} ---")
    engine = SimulationEngine(config)
    paths = engine.run()
    
    # Extract data
    lst_returns = get_terminal_returns(paths, 'lst_price')
    # For fToken, we need to convert floor price to USD value to compare apples to apples
    # Value_USD = Floor_AVAX * Price_AVAX_USD
    # The simulation stores 'ftoken_price' which is the floor in AVAX.
    # We need to multiply by underlying price to get USD value if we want USD returns.
    # Wait, the paper says: "V_fTOKEN_USD(t) = P_f(t) * P_AVAX_USD(t)"
    # Our 'ftoken_price' in history is P_f(t). 'underlying_price' is P_AVAX_USD(t).
    
    ftoken_returns_usd = []
    for df in paths:
        start_val = df['ftoken_price'].iloc[0] * df['underlying_price'].iloc[0]
        end_val = df['ftoken_price'].iloc[-1] * df['underlying_price'].iloc[-1]
        ret = (end_val / start_val) - 1
        ftoken_returns_usd.append(ret)
        
    # Calculate Metrics
    var_95_lst = calculate_var(lst_returns, 0.05)
    var_95_ftoken = calculate_var(ftoken_returns_usd, 0.05)
    
    fpr_paths = [df['ftoken_fpr'].values for df in paths]
    prob_insolvency = analyze_fpr(fpr_paths, threshold=1.0)
    prob_stress = analyze_fpr(fpr_paths, threshold=1.05)
    
    print(f"\nResults for {scenario_name}:")
    print(f"LST 95% VaR: {var_95_lst:.2%}")
    print(f"fTOKEN 95% VaR (USD): {var_95_ftoken:.2%}")
    print(f"Prob FPR < 1.0: {prob_insolvency:.2%}")
    print(f"Prob FPR < 1.05: {prob_stress:.2%}")
    
    # Save a sample plot
    plt.figure(figsize=(10, 6))
    # Plot first 5 paths
    for i in range(min(5, len(paths))):
        df = paths[i]
        plt.plot(df['time'], df['underlying_price'], 'k-', alpha=0.1, label='Underlying' if i==0 else "")
        plt.plot(df['time'], df['lst_price'], 'b-', alpha=0.3, label='LST' if i==0 else "")
        # fToken USD value
        ft_usd = df['ftoken_price'] * df['underlying_price']
        plt.plot(df['time'], ft_usd, 'g-', alpha=0.5, label='fTOKEN (USD)' if i==0 else "")
        
    plt.title(f"Sample Paths: {scenario_name}")
    plt.xlabel("Years")
    plt.ylabel("Price (USD)")
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{scenario_name}_paths.png")
    plt.close()
    
    return {
        'scenario': scenario_name,
        'var_lst': var_95_lst,
        'var_ftoken': var_95_ftoken,
        'prob_insolvency': prob_insolvency
    }

def main():
    parser = argparse.ArgumentParser(description="Run LST vs fTOKEN Simulations")
    parser.add_argument('--scenario', type=str, help="Specific scenario to run (crypto_winter, crab_market, super_cycle)")
    args = parser.parse_args()
    
    results = []
    
    if args.scenario:
        if args.scenario not in SCENARIOS:
            print(f"Unknown scenario: {args.scenario}")
            return
        results.append(run_scenario(args.scenario, SCENARIOS[args.scenario]))
    else:
        for name, config in SCENARIOS.items():
            results.append(run_scenario(name, config))
            
    # Summary Table
    print("\n--- Summary ---")
    summary_df = pd.DataFrame(results)
    print(summary_df)

if __name__ == "__main__":
    main()
