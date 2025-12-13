import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from sims.engine import SimulationEngine
from sims.scenarios import SCENARIOS

def verify_presale():
    print("Verifying Presale Looping Implementation...")
    
    # Base config
    config = SCENARIOS['crab_market'].copy()
    config['n_paths'] = 1
    config['horizon_days'] = 1
    config['initial_supply'] = 100000
    config['presale_enabled'] = True
    config['presale_type'] = 'bull' # Should target ~2.5x leverage
    
    print(f"\nConfiguration:")
    print(f"  Initial Supply: {config['initial_supply']}")
    print(f"  Presale Enabled: {config['presale_enabled']}")
    print(f"  Presale Type: {config['presale_type']}")
    
    # Run simulation
    engine = SimulationEngine(config)
    paths = engine.run()
    df = paths[0]
    
    # Check results at step 0
    start_supply = df['ftoken_supply'].iloc[0]
    start_reserves = df['ftoken_reserves'].iloc[0]
    start_leverage = start_supply / start_reserves
    
    print(f"\nResults at Step 0:")
    print(f"  Supply: {start_supply:.2f} (Expected > 100,000)")
    print(f"  Reserves: {start_reserves:.2f}")
    print(f"  Leverage: {start_leverage:.2f}x (Expected ~2.5x)")
    
    if start_supply > 110000 and start_leverage > 1.5:
        print("\n✅ SUCCESS: Presale looping active! Supply significantly increased.")
    else:
        print("\n❌ FAILURE: Supply didn't increase significantly.")

if __name__ == "__main__":
    verify_presale()
