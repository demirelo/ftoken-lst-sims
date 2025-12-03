import numpy as np

class Asset:
    def __init__(self, name, initial_price):
        self.name = name
        self.initial_price = initial_price
        self.price_history = [initial_price]

    def current_price(self):
        return self.price_history[-1]

    def update_price(self, new_price):
        self.price_history.append(new_price)

class Underlying(Asset):
    def __init__(self, name, initial_price, mu, sigma):
        super().__init__(name, initial_price)
        self.mu = mu
        self.sigma = sigma

    def simulate_step(self, dt):
        """
        Simulates one time step using Geometric Brownian Motion.
        """
        current = self.current_price()
        # GBM: S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
        drift = (self.mu - 0.5 * self.sigma**2) * dt
        shock = self.sigma * np.sqrt(dt) * np.random.normal()
        new_price = current * np.exp(drift + shock)
        self.update_price(new_price)
        return new_price

class LST(Asset):
    def __init__(self, name, underlying, staking_yield, p_depeg=0.0, depeg_severity_mean=-0.05, depeg_severity_std=0.02):
        super().__init__(name, underlying.initial_price)
        self.underlying = underlying
        self.staking_yield = staking_yield
        self.p_depeg = p_depeg
        self.depeg_severity_mean = depeg_severity_mean
        self.depeg_severity_std = depeg_severity_std
        self.index = 1.0

    def simulate_step(self, dt):
        """
        Updates LST price based on underlying price, staking yield, and potential depeg.
        """
        # 1. Accrue yield
        self.index *= (1 + self.staking_yield * dt)
        
        # 2. Calculate theoretical price
        theoretical_price = self.underlying.current_price() * self.index
        
        # 3. Check for depeg
        depeg_factor = 0.0
        if self.p_depeg > 0 and np.random.random() < self.p_depeg:
            # Simple normal distribution for depeg severity (negative shock)
            # We take the absolute value of a normal distribution to ensure it's a deviation, 
            # but usually depegs are downside. Let's model it as a negative shock.
            # Using a log-normal or similar heavy tail would be better, but normal is a start as per plan.
            # We'll ensure it's negative.
            shock = np.random.normal(self.depeg_severity_mean, self.depeg_severity_std)
            depeg_factor = min(0, shock) # Ensure it's a discount or 0
            
        market_price = theoretical_price * (1 + depeg_factor)
        self.update_price(market_price)
        return market_price

class fToken(Asset):
    def __init__(self, name, underlying, initial_reserves, initial_supply, initial_floor, 
                 buy_fee, sell_fee, origination_fee, elevation_threshold=0, 
                 tier_schedule='naive', tier_capacity_base=100000, tick_size=0.01,
                 premium_slope=0.00001): # Slope of the premium curve
        super().__init__(name, initial_floor)
        self.underlying = underlying
        self.reserves = initial_reserves
        
        # Supply split
        self.floor_supply = initial_supply # S_0
        self.premium_supply = 0.0          # S_premium
        self.total_supply = initial_supply # S_total
        
        self.floor_price = initial_floor   # P_f
        self.debt = 0.0
        
        self.buy_fee = buy_fee
        self.sell_fee = sell_fee
        self.origination_fee = origination_fee
        
        # Elevation Manager params
        self.elevation_threshold = elevation_threshold
        self.pending_fees = 0.0
        
        self.tier_schedule = tier_schedule
        self.tier_capacity_base = tier_capacity_base
        self.tick_size = tick_size
        self.premium_slope = premium_slope
        
        self.merges_count = 0
        
        # Track history
        self.reserves_history = [initial_reserves]
        self.supply_history = [initial_supply]
        self.floor_history = [initial_floor]
        self.fpr_history = [self.calculate_fpr()]
        self.debt_history = [0.0]

    def get_market_price(self):
        # Simple Linear Curve: P = P_f + slope * S_premium
        return self.floor_price + (self.premium_slope * self.premium_supply)

    def calculate_fpr(self):
        # FPR = (Reserves - Debt) / (Floor Price * Total Supply)
        # Note: Liability covers ALL tokens at Floor Price
        liability = self.floor_price * self.total_supply
        if liability == 0: return float('inf')
        return (self.reserves - self.debt) / liability

    def calculate_headroom(self):
        # Headroom = (Reserves - Debt) - (Floor Price * Total Supply)
        return (self.reserves - self.debt) - (self.floor_price * self.total_supply)

    def get_next_tier_capacity(self):
        """
        Returns the capacity of the next tier to be merged.
        Harmonic Schedule: Capacity ~ 1/m. 
        Total Floor Supply ~ sum(1/k) ~ ln(m).
        Liability ~ P_f * S_0 ~ m * ln(m). -> O(m log m)
        """
        if self.tier_schedule == 'naive':
            return self.tier_capacity_base
        elif self.tier_schedule == 'harmonic':
            return self.tier_capacity_base / (self.merges_count + 1)
        else:
            return self.tier_capacity_base

    def simulate_step(self, dt, buy_volume, sell_volume, new_loan_amount):
        """
        Updates fToken state: Mint/Burn, Fees, Floor Raising.
        """
        # 1. Process Trading (Mint/Burn)
        # We assume buy_volume and sell_volume are in UNDERLYING units for simplicity of the simulation driver,
        # or we convert. Let's assume they are in UNDERLYING (e.g. AVAX volume).
        
        # BUY: User sends AVAX -> Contract
        if buy_volume > 0:
            market_price = self.get_market_price()
            # Fee deduction
            fee = buy_volume * self.buy_fee
            net_investment = buy_volume - fee
            
            # Mint tokens
            tokens_minted = net_investment / market_price
            
            self.reserves += net_investment # Add net to reserves
            self.pending_fees += fee        # Add fee to pending
            self.premium_supply += tokens_minted
            self.total_supply += tokens_minted
            
        # SELL: User sends fToken -> Contract
        # We need to estimate how many tokens 'sell_volume' (in AVAX) represents
        if sell_volume > 0:
            market_price = self.get_market_price()
            # Approximate tokens to sell to get 'sell_volume' worth of exit liquidity
            # (Ignoring slippage for this step size)
            tokens_to_burn = sell_volume / market_price
            
            # Cap at premium supply? 
            # In reality, users can sell floor tokens too (redemption).
            # But usually they sell premium first.
            # Let's assume they can sell anything.
            
            if tokens_to_burn > self.total_supply:
                tokens_to_burn = self.total_supply
            
            gross_payout = tokens_to_burn * market_price
            fee = gross_payout * self.sell_fee
            net_payout = gross_payout - fee
            
            # SOLVENCY CHECK FOR SELL
            # New Reserves = Old Reserves - Net Payout
            # New Supply = Old Supply - Tokens
            # New Liability = Floor * New Supply
            # Constraint: New Reserves - Debt >= New Liability
            
            new_reserves = self.reserves - net_payout
            new_supply = self.total_supply - tokens_to_burn
            new_liability = self.floor_price * new_supply
            
            if new_reserves - self.debt >= new_liability:
                # Safe to sell
                self.reserves = new_reserves
                self.pending_fees += fee
                self.total_supply = new_supply
                
                if self.premium_supply >= tokens_to_burn:
                    self.premium_supply -= tokens_to_burn
                else:
                    self.premium_supply = 0
            else:
                # REJECT SELL (Contract Reverts)
                # In simulation, we just don't execute it.
                pass

        # 2. Loan Origination
        loan_fee = new_loan_amount * self.origination_fee
        
        # Solvency Check (Strict: Ignore pending fees)
        # Headroom impact: -new_loan_amount (Reserves don't increase by principal, Debt increases)
        net_headroom_change = -new_loan_amount
        
        current_headroom = self.calculate_headroom()
        
        if current_headroom + net_headroom_change >= 0:
            self.debt += new_loan_amount
            self.pending_fees += loan_fee 
        else:
            pass
            
        # 3. Elevation (Batched)
        if self.pending_fees >= self.elevation_threshold:
            self.reserves += self.pending_fees
            self.pending_fees = 0.0
            
            # Try to raise floor
            while True:
                headroom = self.calculate_headroom()
                # Cost to raise floor price by tick:
                # We need to back the ENTIRE supply at the new price.
                # Delta Liability = Tick * Total Supply
                cost_to_raise = self.tick_size * self.total_supply
                
                if headroom >= cost_to_raise - 1e-9:
                    self.floor_price += self.tick_size
                    
                    # Check for Tier Merge
                    # Merging converts Premium Supply -> Floor Supply
                    # It doesn't change Total Supply or Price immediately,
                    # but it "locks in" the backing requirement for that chunk.
                    # Actually, in the model, S_0 is just a tracking var for the floor tier.
                    # The constraint is on Total Supply.
                    # But the "Harmonic" logic depends on 'merges_count'.
                    
                    next_capacity = self.get_next_tier_capacity()
                    
                    # Can we merge?
                    # Merging just moves tokens from Premium to Floor bucket.
                    # It doesn't cost reserves directly, BUT it might imply
                    # we are "filling up" the floor tier.
                    # The paper says: "Merge next tier if L_f - D >= P_next * (S_0 + M_next)"
                    # Here P_next is the current floor price (we just raised it).
                    # So we check if we can support the NEW larger floor supply.
                    
                    # Wait, if we merge, S_0 increases.
                    # Does that change liability?
                    # Liability = P_f * S_total.
                    # S_total doesn't change.
                    # So merging is "free" in terms of immediate solvency?
                    # NO. In the real contract, "Floor" is a specific segment.
                    # Merging means expanding that segment.
                    # It allows the floor price to keep rising.
                    # If we don't merge, we might hit a cap?
                    # Let's assume we merge if we have enough "Excess Headroom" to secure it?
                    # Or just merge whenever we can?
                    # The code says: "Safe-merge: Can merge next tier only if: L_f - D >= P_next * (S_0 + M_next)"
                    # My Liability calc uses S_total.
                    # If S_total > S_0 + M_next, then we are ALREADY backing it.
                    # So we can always merge if S_total is large enough?
                    # Let's stick to the logic:
                    # If we have enough reserves to back (S_0 + next_capacity) at current P_f, we merge.
                    
                    required_backing = self.floor_price * (self.floor_supply + next_capacity)
                    if (self.reserves - self.debt) >= required_backing:
                        # Merge!
                        # Transfer capacity from Premium to Floor
                        # But wait, do we actually have 'next_capacity' amount of premium tokens?
                        # The 'tier_capacity' is just a structural limit.
                        # If S_premium < next_capacity, we can only merge what we have?
                        # Or does the tier structure exist independently of current supply?
                        # In the contract, Segments are pre-defined.
                        # Merging means "activating" the next segment as part of the floor.
                        # If that segment is empty (no supply), it's just a capacity increase.
                        # If it has supply, that supply becomes floor supply.
                        
                        # For the simulation, let's assume S_premium is the "excess supply above floor tier".
                        # If we expand the floor tier, we swallow some S_premium.
                        
                        amount_to_merge = next_capacity
                        if self.premium_supply < amount_to_merge:
                            # We can merge, but we only shift what we have?
                            # Or we shift the capacity, and S_premium becomes negative? No.
                            # If S_premium is low, it means we are barely above floor.
                            # Merging increases the "Floor Cap".
                            pass
                        
                        self.floor_supply += amount_to_merge
                        # We don't strictly need to subtract from premium_supply if premium_supply is calculated as Total - Floor.
                        # But I defined premium_supply as a state var.
                        # Let's make premium_supply derived? 
                        # Or update it.
                        
                        # If S_total = S_floor + S_premium.
                        # Then S_premium = S_total - S_floor.
                        # So if S_floor increases, S_premium decreases.
                        pass
                        
                        self.merges_count += 1
                else:
                    break
        
        # Recalculate Premium Supply based on new Floor Supply
        # S_premium = max(0, S_total - S_floor)
        self.premium_supply = max(0.0, self.total_supply - self.floor_supply)
        
        # Update history
        self.update_price(self.floor_price)
        self.reserves_history.append(self.reserves)
        self.supply_history.append(self.total_supply) # Track Total Supply
        self.floor_history.append(self.floor_price)
        self.fpr_history.append(self.calculate_fpr())
        self.debt_history.append(self.debt)
        
        return self.floor_price
