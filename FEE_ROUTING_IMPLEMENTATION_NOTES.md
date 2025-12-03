# Fee Routing Model Correction - Implementation Notes

## Current (Incorrect) Implementation

```python
# ALL fees go to pending_fees → reserves
fee = reserve_amount * self.buy_fee
self.reserves += (reserve_amount - fee)  # Net investment to reserves
self.pending_fees += fee  # Fee to pending → eventually reserves
```

**Problem**: This assumes 100% of fees go to floor backing.

## Corrected Implementation

### Fee Routing with alpha_f

```python
# Fee split based on alpha_f (fee-to-floor ratio)
total_fee = reserve_amount * self.buy_fee

# Split fee
fee_to_floor = total_fee * alpha_f      # 40-90% to floor backing
fee_to_governance = total_fee * (1 - alpha_f)  # 10-60% to governance/treasury

# Update reserves
net_investment = reserve_amount - total_fee
self.reserves += net_investment        # User's net investment
self.pending_fees += fee_to_floor     # Only floor portion to pending
self.governance_fees += fee_to_governance  # Track governance share
```

### Premium Supply Mechanics

**Key principle**: Premium supply accumulates from **buy demand**, not fees!

```python
# User buys at premium
market_price = self.get_market_price()  # e.g., 1.15 AVAX (> 1.0 floor)
tokens_minted = net_investment / market_price

# These tokens are backed by the bonding curve
backing_per_token = market_price  # ≥ floor_price

# Premium supply increases
self.premium_supply += tokens_minted
self.total_supply += tokens_minted
```

### LRE Trigger Condition

```python
# Calculate premium liquidity (backing for premium-tier tokens)
premium_liquidity = sum(price_i * supply_i for premium segments)
                  = self.reserves - (self.floor_price * self.floor_supply)

# Calculate floor liquidity
floor_liquidity = self.floor_price * self.floor_supply

# LRE condition
if (premium_liquidity / floor_liquidity) >= lre_threshold:
    # Trigger LRE
    reallocate_amount = premium_liquidity * lre_realloc_bps / 10000
    # Move reallocate_amount to floor backing
```

## Required Code Changes

### 1. Add `fee_to_floor_ratio` parameter

**File**: `sims/models.py` - `fToken.__init__`

```python
def __init__(
    self,
    # ... existing params
    fee_to_floor_ratio: float = 0.70,  # NEW: Default 70%
):
    # ... existing code
    self.fee_to_floor_ratio = fee_to_floor_ratio
    self.governance_fees_accumulated = 0.0
```

### 2. Update `buy()` method

**File**: `sims/models.py` - `fToken.buy`

```python
def buy(self, reserve_amount: float, execution_price: float = None) -> Tuple[float, float, float]:
    # Calculate fee
    fee = reserve_amount * self.buy_fee
    net_investment = reserve_amount - fee
    
    # Split fee
    fee_to_floor = fee * self.fee_to_floor_ratio
    fee_to_governance = fee * (1 - self.fee_to_floor_ratio)
    
    # Update state
    self.reserves += net_investment  # User's net investment backs the tokens
    self.pending_fees += fee_to_floor  # Only floor portion to pending
    self.governance_fees_accumulated += fee_to_governance
    
    # Mint tokens at market price
    price = execution_price if execution_price else self.get_market_price()
    tokens_minted = net_investment / price
    
    self.premium_supply += tokens_minted
    self.total_supply += tokens_minted
    
    return tokens_minted, fee_to_floor, fee_to_governance
```

### 3. Update `sell()` method similarly

### 4. Update `originate_loan()` method similarly

### 5. Update `process_elevation()`

No changes needed - pending_fees already only contains floor portion.

### 6. Update engine to pass `fee_to_floor_ratio`

**File**: `sims/engine.py` - `_run_single_path`

```python
ftoken = fToken(
    # ... existing params
    fee_to_floor_ratio=self.config.get('fee_to_floor_ratio', 0.70),
)
```

## Testing Strategy

### Sensitivity Analysis

Test with `alpha_f` ∈ {0.40, 0.65, 0.90}

**Expected outcomes**:

1. **Higher alpha_f → Faster floor elevation**
   - More fees → floor backing
   - Faster floor price growth
   - Lower premium accumulation (less to governance)

2. **Lower alpha_f → More LRE activation**
   - Less fees consumed by floor
   - Premium liquidity accumulates
   - LRE threshold reached more frequently

3. **Trade-off visualization**:
   ```
   alpha_f = 0.40 → Slow floor, High LRE, High governance revenue
   alpha_f = 0.65 → Balanced
   alpha_f = 0.90 → Fast floor, Low LRE, Low governance revenue
   ```

## LTV vs Debt Cap Interaction

### Per-User LTV Constraint

```python
# When user originates loan
max_loan_for_user = floor_price * collateral_tokens * LTV

Example:
- User locks 1000 fTOKEN
- Floor = 1.2 AVAX
- LTV = 80%
→ max_loan = 1.2 * 1000 * 0.80 = 960 AVAX
```

### Global Debt Cap Constraint

```python
# System-wide constraint
total_debt_all_users <= (debt_cap_bps / 10000) * total_reserves

Example:
- Total reserves = 1,100,000 AVAX
- Debt cap = 50% (5000 bps)
→ max_total_debt = 550,000 AVAX
```

### Interaction

```python
def originate_loan(self, amount, collateral_tokens, ltv=0.80):
    # Check 1: User-level LTV
    max_for_user = self.floor_price * collateral_tokens * ltv
    if amount > max_for_user:
        return False, "Exceeds LTV limit"
    
    # Check 2: Global debt cap
    if (self.debt + amount) > self.get_debt_cap():
        return False, "Exceeds global debt cap"
    
    # Check 3: Coverage buffer
    if not self._check_coverage_after_loan(amount, collateral_tokens):
        return False, "Insufficient coverage"
    
    # All checks passed
    self.debt += amount
    self.locked_supply += collateral_tokens
    # ... process loan
```

**Key insight**: Debt cap is hit when **many users** borrow close to their LTV limits simultaneously.

## Next Steps

1. Implement fee routing changes
2. Run sensitivity analysis for alpha_f ∈ {0.40, 0.65, 0.90}
3. Generate band plots showing performance range
4. Document LRE activation frequency across alpha_f values

Would you like me to proceed with implementing these changes?
