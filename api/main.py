"""
FastAPI Backend for fToken Simulator

Provides REST endpoints to configure and run Monte Carlo simulations.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import sys
import os
import uuid
import json

# Add parent directory to path to import sims
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sims.scenarios import SCENARIOS, get_scenario, describe_scenario, list_scenarios, AGENT_POPULATIONS
from sims.engine import SimulationEngine
from sims.agent_engine import AgentSimulationEngine, AgentSimConfig
from sims.agents import AGENT_TYPES, create_population
from sims.analysis import generate_full_analysis
import numpy as np
from enum import Enum


def make_json_serializable(obj):
    """Recursively convert numpy arrays and other non-serializable objects to JSON-compatible types."""
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return [make_json_serializable(x) for x in obj.tolist()]
    elif isinstance(obj, (np.integer, np.floating)):
        val = float(obj)
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.bool_):
        return bool(obj)
    else:
        return obj

app = FastAPI(
    title="fToken Simulator API",
    description="API for running Monte Carlo simulations of fToken vs LST",
    version="1.0.0",
    root_path="/api" if os.environ.get("VERCEL") else ""
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for simulation results
simulation_results: Dict[str, Any] = {}
simulation_status: Dict[str, str] = {}


# ============================================================================
# Pydantic Models
# ============================================================================

class SimulationConfig(BaseModel):
    """Configuration for running a simulation."""
    # Scenario base (optional - can be customized)
    scenario_name: Optional[str] = "crab_market"
    
    # Simulation mode: "agent" or "volume"
    simulation_mode: str = Field(default="agent", description="Simulation mode: 'agent' or 'volume'")
    
    # Simulation structure
    n_paths: int = Field(default=100, ge=10, le=2000, description="Number of Monte Carlo paths")
    horizon_days: int = Field(default=90, ge=7, le=365, description="Simulation horizon in days")
    
    # Market parameters
    initial_price: float = Field(default=100.0, gt=0, description="Initial underlying price (USD)")
    mu: float = Field(default=0.1, ge=-2.0, le=2.0, description="Annualized drift")
    sigma: float = Field(default=0.5, ge=0.1, le=2.0, description="Annualized volatility")
    
    # LST parameters
    staking_yield: float = Field(default=0.026, ge=0, le=0.20, description="LST staking yield (APY)")
    p_depeg: float = Field(default=0.002, ge=0, le=0.1, description="Daily depeg probability")
    depeg_mean: float = Field(default=-0.03, ge=-0.5, le=0, description="Mean depeg severity")
    depeg_std: float = Field(default=0.02, ge=0, le=0.2, description="Depeg severity std dev")
    
    # fToken parameters
    initial_reserves: float = Field(default=100000, gt=0, description="Initial reserves")
    initial_supply: float = Field(default=100000, gt=0, description="Initial token supply")
    initial_floor: float = Field(default=1.0, gt=0, description="Initial floor price")
    buy_fee: float = Field(default=0.005, ge=0, le=0.1, description="Buy fee (0.5% = 0.005)")
    sell_fee: float = Field(default=0.005, ge=0, le=0.1, description="Sell fee")
    origination_fee: float = Field(default=0.02, ge=0, le=0.1, description="Loan origination fee")
    fee_to_floor_ratio: float = Field(default=0.70, ge=0, le=1.0, description="Portion of fees to floor")
    fee_to_stakers_ratio: float = Field(default=0.25, ge=0, le=1.0, description="Portion of fees to stakers")
    fee_to_team_ratio: float = Field(default=0.05, ge=0, le=1.0, description="Portion of fees to team")
    
    # Credit facility
    loan_ltv: float = Field(default=0.7, ge=0.1, le=0.99, description="Loan LTV")
    debt_cap_bps: int = Field(default=5000, ge=1000, le=9000, description="Debt cap in bps")
    
    # LRE parameters
    lre_threshold: float = Field(default=2.0, ge=1.0, le=5.0, description="LRE trigger threshold")
    lre_realloc_bps: int = Field(default=2000, ge=500, le=5000, description="LRE reallocation bps")
    
    # Volume
    daily_volume_mean: float = Field(default=50000, ge=1000, description="Mean daily volume")
    daily_volume_std: float = Field(default=15000, ge=0, description="Volume std dev")


class AgentConfig(BaseModel):
    """Configuration for a single agent type."""
    count: int = Field(default=10, ge=0, le=200, description="Number of agents")
    initial_eth: float = Field(default=10000.0, gt=0, description="Initial ETH per agent")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Agent-specific params")


class SimulationRequest(BaseModel):
    """Full simulation request with config and agents."""
    config: SimulationConfig
    agents: Optional[Dict[str, AgentConfig]] = None


class SimulationResponse(BaseModel):
    """Response with simulation ID."""
    simulation_id: str
    status: str


class ScenarioInfo(BaseModel):
    """Information about a scenario."""
    name: str
    description: str
    config: Dict[str, Any]


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "message": "fToken Simulator API"}


@app.get("/scenarios", response_model=List[str])
async def get_scenarios():
    """List all available scenario names."""
    return list_scenarios()


@app.get("/scenarios/{name}", response_model=ScenarioInfo)
async def get_scenario_info(name: str):
    """Get details for a specific scenario."""
    if name not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found")
    
    return ScenarioInfo(
        name=name,
        description=describe_scenario(name),
        config=get_scenario(name)
    )


@app.get("/agents")
async def get_agent_types():
    """Get available agent types and their default parameters."""
    result = {}
    for agent_type, agent_class in AGENT_TYPES.items():
        default_params = getattr(agent_class, 'DEFAULT_PARAMS', {})
        result[agent_type] = {
            "description": agent_class.__doc__.strip().split('\n')[0] if agent_class.__doc__ else "",
            "default_params": default_params
        }
    return result


@app.get("/agent-populations/{scenario_name}")
async def get_agent_population(scenario_name: str):
    """Get the default agent population for a scenario."""
    if scenario_name not in AGENT_POPULATIONS:
        # Return a default population
        return AGENT_POPULATIONS.get('crab_market', {})
    return AGENT_POPULATIONS[scenario_name]


def run_simulation_task(sim_id: str, config: Dict[str, Any]):
    """Background task to run simulation."""
    try:
        simulation_status[sim_id] = "running"
        
        simulation_mode = config.get('simulation_mode', 'agent')
        
        if simulation_mode == 'agent':
            # Agent-based simulation
            agent_population = config.get('agent_population', {})
            print(f"DEBUG: Starting Agent Simulation with population: {agent_population}")
            
            # For agent-based simulation, use smaller supply to allow floor growth
            # (Scenario values are calibrated for volume-based simulation)
            agent_initial_supply = 10000  # Smaller scale for agent sim
            agent_initial_reserves = 11000  # 10% over-collateralized
            
            # Create agent config
            agent_config = AgentSimConfig(
                n_paths=config.get('n_paths', 100),
                horizon_days=config.get('horizon_days', 90),
                initial_price=config.get('initial_price', 100.0),
                mu=config.get('mu', 0.0),
                sigma=config.get('sigma', 0.5),
                staking_yield=config.get('staking_yield', 0.026),
                initial_reserves=agent_initial_reserves,
                initial_supply=agent_initial_supply,
                initial_floor=config.get('initial_floor', 1.0),
                buy_fee=config.get('buy_fee', 0.005),
                sell_fee=config.get('sell_fee', 0.005),
                origination_fee=config.get('origination_fee', 0.02),
                fee_to_floor_ratio=config.get('fee_to_floor_ratio', 0.70),
                debt_cap_bps=config.get('debt_cap_bps', 5000),
                lre_threshold=config.get('lre_threshold', 2.0),
                lre_realloc_bps=config.get('lre_realloc_bps', 2000),
                population_config=agent_population if agent_population else None,
            )
            
            engine = AgentSimulationEngine(agent_config, scenario_config=config)
            print(f"DEBUG: Engine initialized with {len(engine.agents)} agents")
            paths = engine.run()
            print(f"DEBUG: Simulation completed, paths generated: {len(paths)}")
        else:
            # Volume-based simulation
            engine = SimulationEngine(config)
            paths = engine.run()
        
        # Generate analysis
        analysis = generate_full_analysis(paths, config.get('scenario_name', 'custom'))
        
        # Extract path data for visualization (sample paths to reduce data size)
        sample_size = min(20, len(paths))
        sample_indices = list(range(0, len(paths), max(1, len(paths) // sample_size)))[:sample_size]
        
        path_data = []
        for idx in sample_indices:
            df = paths[idx]
            path_data.append({
                "path_id": idx,
                "underlying_price": df['underlying_price'].tolist(),
                "lst_price": df['lst_price'].tolist(),
                "ftoken_floor": df['ftoken_floor'].tolist(),
                "ftoken_fpr": df['ftoken_fpr'].tolist(),
                "ftoken_bad_debt_cumulative": df['ftoken_bad_debt_cumulative'].tolist(),
                "ftoken_supply": df['ftoken_supply'].tolist(),
                "ftoken_market_price": df['ftoken_market_price'].tolist(),
            })
        
        simulation_results[sim_id] = {
            "status": "completed",
            "analysis": make_json_serializable(analysis),
            "paths": make_json_serializable(path_data),
            "n_paths": len(paths),
            "horizon_days": config.get('horizon_days', 90),
            "simulation_mode": simulation_mode,
        }
        simulation_status[sim_id] = "completed"
        
    except Exception as e:
        import traceback
        simulation_status[sim_id] = "failed"
        simulation_results[sim_id] = {"status": "failed", "error": str(e), "traceback": traceback.format_exc()}


@app.post("/simulate", response_model=SimulationResponse)
async def start_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """Start a new simulation."""
    print(f"DEBUG: Received request. Config mode: {request.config.simulation_mode}")
    print(f"DEBUG: Received agents keys: {list(request.agents.keys()) if request.agents else 'None'}")
    sim_id = str(uuid.uuid4())
    
    # Build config from request
    if request.config.scenario_name:
        config = get_scenario(request.config.scenario_name)
    else:
        config = {}
    
    # Override with provided values
    config.update(request.config.model_dump(exclude_none=True, exclude={'scenario_name'}))
    
    # Add agents if provided
    if request.agents:
        agent_pop = {}
        for agent_type, agent_config in request.agents.items():
            agent_pop[agent_type] = agent_config.model_dump()
        config['agent_population'] = agent_pop
    
    simulation_status[sim_id] = "pending"
    background_tasks.add_task(run_simulation_task, sim_id, config)
    
    return SimulationResponse(simulation_id=sim_id, status="pending")


@app.get("/simulate/{sim_id}/status")
async def get_simulation_status(sim_id: str):
    """Get the status of a simulation."""
    if sim_id not in simulation_status:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return {"simulation_id": sim_id, "status": simulation_status[sim_id]}


@app.get("/simulate/{sim_id}/results")
async def get_simulation_results(sim_id: str):
    """Get the results of a completed simulation."""
    if sim_id not in simulation_results:
        if sim_id in simulation_status:
            return {"simulation_id": sim_id, "status": simulation_status[sim_id], "results": None}
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    return {"simulation_id": sim_id, **simulation_results[sim_id]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
