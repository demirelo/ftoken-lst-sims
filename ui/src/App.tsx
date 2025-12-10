import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Play,
  Settings,
  BarChart3,
  Layers,
  TrendingUp,
  RefreshCcw,
  AlertCircle
} from 'lucide-react'
import './index.css'
import './App.css'
import SimulationConfig from './components/SimulationConfig'
import ResultsDashboard from './components/ResultsDashboard'
import ScenarioSelector from './components/ScenarioSelector'

const API_URL = import.meta.env.PROD ? '/api' : 'http://localhost:8000'

// Default configuration values
const DEFAULT_CONFIG = {
  n_paths: 100,  // Restored to 100 after optimizing agent population size
  horizon_days: 90,
  initial_price: 100,
  mu: 0.1,
  sigma: 0.5,
  staking_yield: 0.026,
  p_depeg: 0.002,
  depeg_mean: -0.03,
  initial_reserves: 100000,
  initial_supply: 100000,
  initial_floor: 1.0,
  buy_fee: 0.005,  // 0.5%
  sell_fee: 0.005,
  origination_fee: 0.02,
  fee_to_floor_ratio: 0.70,
  fee_to_stakers_ratio: 0.25,
  fee_to_team_ratio: 0.05,
  loan_ltv: 0.7,
  debt_cap_bps: 5000,  // 50%
  lre_threshold: 2.0,
  lre_realloc_bps: 2000,  // 20%
  // Volume parameters (new percentage-based)
  baseline_daily_volume_pct: 0.05,  // 5% of supply trades daily
  volume_scenario_multiplier: 1.0,  // Scenario multiplier (e.g., 0.3 for bear, 1.5 for bull)
  demand_bias: 0.0,  // Buy/sell imbalance for premium dynamics
  enable_loan_activity: true,
  enable_leverage_looping: true,
}

interface SimulationState {
  id: string | null
  status: 'idle' | 'pending' | 'running' | 'completed' | 'failed'
  results: any | null
  error: string | null
}

function App() {
  const [activeTab, setActiveTab] = useState<'config' | 'results'>('config')
  const [scenarios, setScenarios] = useState<string[]>([])
  const [selectedScenario, setSelectedScenario] = useState<string>('crab_market')
  const [scenarioConfig, setScenarioConfig] = useState<any>(null)
  const [customConfig, setCustomConfig] = useState<any>({ ...DEFAULT_CONFIG })
  const [ethPrice, setEthPrice] = useState<number | null>(null)

  // Presale state
  const [presaleEnabled, setPresaleEnabled] = useState(false)
  const [presaleType, setPresaleType] = useState<'bull' | 'neutral' | 'bear'>('neutral')

  // Simulation mode: 'agent' (default) or 'volume'
  const [simulationMode, setSimulationMode] = useState<'agent' | 'volume'>('agent')

  // Agent population configuration (for agent-based mode)
  // Capital scaled to be ~10-20% of initial market: ~2000 ETH total vs 10000 supply
  const [agentPopulation, setAgentPopulation] = useState<Record<string, { count: number; initial_eth: number }>>({
    LeverageSeeker: { count: 15, initial_eth: 30 },
    YieldSeeker: { count: 25, initial_eth: 25 },
    DAT: { count: 8, initial_eth: 100 },
    Arbitrageur: { count: 10, initial_eth: 15 },
    FloorHolder: { count: 15, initial_eth: 50 },
  })

  const [simulation, setSimulation] = useState<SimulationState>({
    id: null,
    status: 'idle',
    results: null,
    error: null
  })

  // Fetch live ETH price on mount
  useEffect(() => {
    fetch('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd')
      .then(res => res.json())
      .then(data => {
        const price = data.ethereum.usd
        if (price) {
          setEthPrice(price)
          setCustomConfig((prev: any) => ({
            ...prev,
            initial_price: price
          }))
        }
      })
      .catch(err => console.error('Failed to fetch ETH price:', err))
  }, [])

  // Fetch available scenarios on mount
  useEffect(() => {
    fetch(`${API_URL}/scenarios`)
      .then(res => res.json())
      .then(data => setScenarios(data))
      .catch(err => console.error('Failed to fetch scenarios:', err))
  }, [])

  // Fetch scenario config when selection changes
  useEffect(() => {
    if (selectedScenario) {
      // Fetch scenario config
      fetch(`${API_URL}/scenarios/${selectedScenario}`)
        .then(res => res.json())
        .then(data => {
          setScenarioConfig(data.config)
          // Merge scenario config with defaults
          setCustomConfig((_prev: any) => {
            const newConfig = {
              ...DEFAULT_CONFIG,
              ...data.config,
            }
            if (ethPrice) {
              newConfig.initial_price = ethPrice
            }
            return newConfig
          })
        })
        .catch(err => console.error('Failed to fetch scenario config:', err))

      // Fetch agent population for this scenario
      fetch(`${API_URL}/agent-populations/${selectedScenario}`)
        .then(res => res.json())
        .then(data => setAgentPopulation(data))
        .catch(err => console.error('Failed to fetch agent population:', err))
    }
  }, [selectedScenario, ethPrice])

  // Poll for simulation status
  useEffect(() => {
    if (simulation.id && (simulation.status === 'pending' || simulation.status === 'running')) {
      const interval = setInterval(() => {
        fetch(`${API_URL}/simulate/${simulation.id}/results`)
          .then(res => res.json())
          .then(data => {
            if (data.status === 'completed') {
              setSimulation(prev => ({
                ...prev,
                status: 'completed',
                results: data
              }))
              setActiveTab('results')
              clearInterval(interval)
            } else if (data.status === 'failed') {
              setSimulation(prev => ({
                ...prev,
                status: 'failed',
                error: data.error || 'Simulation failed'
              }))
              clearInterval(interval)
            }
          })
          .catch(err => console.error('Failed to poll simulation:', err))
      }, 1000)

      return () => clearInterval(interval)
    }
  }, [simulation.id, simulation.status])

  const runSimulation = async () => {
    setSimulation({ id: null, status: 'pending', results: null, error: null })

    try {
      // Build config with presale if enabled
      const config: any = {
        scenario_name: selectedScenario,
        simulation_mode: simulationMode,
        ...customConfig,
      }

      // If presale is enabled, add presale parameters
      if (presaleEnabled) {
        config.presale_enabled = true
        config.presale_type = presaleType
      }

      // Prepare request body
      const requestBody: any = { config }

      // If agent mode, add agents to request body
      if (simulationMode === 'agent') {
        requestBody.agents = agentPopulation
      }

      console.log('Sending simulation request:', requestBody)

      const response = await fetch(`${API_URL}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      })

      const data = await response.json()
      setSimulation(prev => ({
        ...prev,
        id: data.simulation_id,
        status: 'running'
      }))
    } catch (err) {
      setSimulation(prev => ({
        ...prev,
        status: 'failed',
        error: 'Failed to start simulation'
      }))
    }
  }

  const updateConfig = (key: string, value: any) => {
    setCustomConfig((prev: any) => ({
      ...prev,
      [key]: value
    }))
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <Layers className="logo-icon" />
            <span className="logo-text">fToken Simulator</span>
          </div>
          <nav className="nav-tabs">
            <button
              className={`nav-tab ${activeTab === 'config' ? 'active' : ''}`}
              onClick={() => setActiveTab('config')}
            >
              <Settings size={18} />
              Configuration
            </button>
            <button
              className={`nav-tab ${activeTab === 'results' ? 'active' : ''}`}
              onClick={() => setActiveTab('results')}
              disabled={!simulation.results}
            >
              <BarChart3 size={18} />
              Results
            </button>
          </nav>
          <div className="header-actions">
            <button
              className={`btn btn-primary btn-lg ${simulation.status === 'running' ? 'animate-pulse' : ''}`}
              onClick={runSimulation}
              disabled={simulation.status === 'running' || simulation.status === 'pending'}
            >
              {simulation.status === 'running' || simulation.status === 'pending' ? (
                <>
                  <RefreshCcw size={18} className="spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play size={18} />
                  Run Simulation
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <AnimatePresence mode="wait">
          {activeTab === 'config' ? (
            <motion.div
              key="config"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="config-page"
            >
              {/* Scenario Selection */}
              <section className="section">
                <h2 className="section-title">
                  <TrendingUp size={24} />
                  Select Market Scenario
                </h2>
                <ScenarioSelector
                  scenarios={scenarios}
                  selected={selectedScenario}
                  onSelect={setSelectedScenario}
                />
              </section>

              {/* Configuration */}
              <section className="section">
                <h2 className="section-title">
                  <Settings size={24} />
                  Simulation Parameters
                </h2>
                {scenarioConfig && (
                  <SimulationConfig
                    config={customConfig}
                    onConfigChange={updateConfig}
                    onReset={() => setCustomConfig({ ...DEFAULT_CONFIG })}
                    presaleEnabled={presaleEnabled}
                    onPresaleToggle={setPresaleEnabled}
                    presaleType={presaleType}
                    onPresaleTypeChange={setPresaleType}
                    simulationMode={simulationMode}
                    onSimulationModeChange={setSimulationMode}
                    agentPopulation={agentPopulation}
                    onAgentPopulationChange={setAgentPopulation}
                  />
                )}
              </section>
            </motion.div>
          ) : (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="results-page"
            >
              {simulation.results && (
                <ResultsDashboard
                  results={simulation.results}
                  scenarioName={selectedScenario}
                  config={customConfig}
                />
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Status Toast */}
        <AnimatePresence>
          {simulation.status === 'running' && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className="status-toast"
            >
              <div className="spinner" />
              <span>Running Monte Carlo simulation...</span>
            </motion.div>
          )}
          {simulation.status === 'failed' && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className="status-toast error"
            >
              <AlertCircle size={20} />
              <span>{simulation.error}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}

export default App
