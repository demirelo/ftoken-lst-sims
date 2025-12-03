import numpy as np
import pandas as pd
from .models import Underlying, LST, fToken

class SimulationEngine:
    def __init__(self, config):
        self.config = config
        self.paths = []

    def run(self):
        n_paths = self.config['n_paths']
        horizon_days = self.config['horizon_days']
        dt = self.config['dt'] # in years, e.g. 1/365
        steps = int(horizon_days / (dt * 365))
        
        print(f"Starting simulation: {n_paths} paths, {steps} steps...")

        for i in range(n_paths):
            path_data = self._run_single_path(steps, dt)
            self.paths.append(path_data)
            if (i+1) % 100 == 0:
                print(f"Completed {i+1}/{n_paths} paths")

        return self.paths

    def _run_single_path(self, steps, dt):
        # Initialize assets for this path
        underlying = Underlying(
            "AVAX", 
            self.config['initial_price'], 
            self.config['mu'], 
            self.config['sigma']
        )
        
        lst = LST(
            "sAVAX", 
            underlying, 
            self.config['staking_yield'],
            p_depeg=self.config.get('p_depeg', 0),
            depeg_severity_mean=self.config.get('depeg_mean', -0.05),
            depeg_severity_std=self.config.get('depeg_std', 0.02)
        )
        
        ftoken = fToken(
            "fAVAX", 
            underlying, 
            initial_reserves=self.config['initial_reserves'], 
            initial_supply=self.config['initial_supply'], 
            initial_floor=self.config['initial_floor'],
            buy_fee=self.config['buy_fee'],
            sell_fee=self.config['sell_fee'],
            origination_fee=self.config['origination_fee'],
            elevation_threshold=self.config.get('elevation_threshold', 0),
            tier_schedule=self.config.get('tier_schedule', 'naive'),
            tier_capacity_base=self.config.get('tier_capacity', 100000)
        )

        # Data storage for this path
        history = {
            'time': [],
            'underlying_price': [],
            'lst_price': [],
            'ftoken_price': [],
            'ftoken_fpr': [],
            'ftoken_supply': [],
            'ftoken_reserves': [],
            'ftoken_floor': [],
            'ftoken_debt': []
        }

        for step in range(steps):
            t = step * dt
            
            # 1. Update Underlying
            u_price = underlying.simulate_step(dt)
            
            # 2. Update LST
            lst_price = lst.simulate_step(dt)
            
            # 3. Update fToken
            # Volume
            vol_mean = self.config.get('daily_volume_mean', 10000) * dt * 365
            vol_std = self.config.get('daily_volume_std', 2000) * dt * 365
            total_volume = max(0, np.random.normal(vol_mean, vol_std))
            
            # Split volume 50/50 buy/sell for simplicity
            buy_volume = total_volume * 0.5
            sell_volume = total_volume * 0.5
            
            # Loans
            loan_mean = self.config.get('daily_loan_origination_mean', 0) * dt * 365
            loan_std = self.config.get('daily_loan_origination_std', 0) * dt * 365
            new_loan = max(0, np.random.normal(loan_mean, loan_std)) if loan_mean > 0 else 0
            
            ft_price = ftoken.simulate_step(dt, buy_volume, sell_volume, new_loan)

            # Store
            history['time'].append(t)
            history['underlying_price'].append(u_price)
            history['lst_price'].append(lst_price)
            history['ftoken_price'].append(ft_price)
            history['ftoken_fpr'].append(ftoken.fpr_history[-1])
            history['ftoken_reserves'].append(ftoken.reserves)
            history['ftoken_supply'].append(ftoken.total_supply)
            history['ftoken_floor'].append(ftoken.floor_price)
            history['ftoken_debt'].append(ftoken.debt)

        return pd.DataFrame(history)
