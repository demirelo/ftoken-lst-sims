# fTOKEN vs LST Monte Carlo Simulation

A comprehensive Monte Carlo simulation framework comparing **Floor-Backed Tokens (fTOKENs)** and **Liquid Staking Tokens (LSTs)** across multiple market regimes.

## Overview

This simulation implements a **Digital Twin** of fTOKEN markets with full bonding curve mechanics, mint/burn operations, and all critical smart contract invariants from the [Inverter Floors](https://github.com/InverterNetwork/floors-sc) implementation.

### Key Features

- **Digital Twin Model**: Linear bonding curve with premium supply dynamics
- **Smart Contract Fidelity**: All solvency invariants from `floors-sc` verified
- **Harmonic Tier Scaling**: O(m log m) floor elevation cost
- **Credit Modeling**: Endogenous loan demand with solvency checks
- **Batched Fee Injection**: FloorElevationManager simulation
- **3 Market Regimes**: Crypto Winter, Crab Market, Super Cycle

## Results Summary

**Framework**: 1,000 paths × 90 days

| Metric | Crypto Winter | Crab Market | Super Cycle |
|--------|---------------|-------------|-------------|
| **LST 95% VaR** | -60.3% | -28.0% | -40.8% |
| **fTOKEN 95% VaR** | -57.9% | -23.2% | -31.0% |
| **Protection** | +2.4% | +4.8% | +9.8% |
| **Insolvency** | 0.00% | 0.00% | 0.00% |

**Key Finding**: fTOKENs provide 2-10% downside protection vs LSTs while maintaining 100% solvency across all scenarios.

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Run All Scenarios

```bash
python main.py
```

This runs all three scenarios (Crypto Winter, Crab Market, Super Cycle) and generates:
- Summary statistics
- VaR calculations
- FPR distributions
- Comparison plots

### Run Tests

```bash
pytest tests/
```

## Project Structure

```
ftoken-lst-sims/
├── sims/
│   ├── models.py       # Asset models (Underlying, LST, fToken)
│   ├── engine.py       # Monte Carlo simulation engine
│   ├── scenarios.py    # Scenario configurations
│   └── analysis.py     # Post-simulation analysis
├── tests/
│   └── test_models.py  # Unit tests
├── main.py             # Entry point
├── SIMULATION_REPORT.md         # Full results and analysis
├── INVARIANT_VERIFICATION.md    # Smart contract comparison
└── README.md
```

## Technical Details

### Core Solvency Invariant

```
L_f - D >= P_f * S_total
```

Where:
- `L_f`: Floor reserves (AVAX)
- `D`: Outstanding debt
- `P_f`: Floor price
- `S_total`: Total supply

### Harmonic Tier Schedule

```python
M_i = κ * S_base / i
```

Enables O(m log m) scaling vs O(m²) for naive constant-capacity tiers.

### Digital Twin Components

1. **Bonding Curve**: `P = P_f + slope * S_premium`
2. **Mint/Burn**: Users can buy/sell at market price with fees
3. **Solvency Checks**: Rejects transactions that violate invariant
4. **Floor Elevation**: Greedy policy raises floor when headroom allows

## Documentation

- **[SIMULATION_REPORT.md](./SIMULATION_REPORT.md)**: Complete simulation results and analysis
- **[INVARIANT_VERIFICATION.md](./INVARIANT_VERIFICATION.md)**: Comparison with `floors-sc` smart contracts
- **[Research Paper](./Structural_Solvency_and_Risk_Topology.md)**: Theoretical foundation

## References

- [Inverter Floors Smart Contracts](https://github.com/InverterNetwork/floors-sc)
- Research Paper: "Structural Solvency and Risk Topology" (included)

## License

MIT
