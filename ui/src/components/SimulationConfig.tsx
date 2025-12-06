import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Info, RotateCcw, Sparkles } from 'lucide-react'
import Tooltip from './Tooltip'

interface AgentPopulation {
  count: number
  initial_eth: number
}

interface SimulationConfigProps {
  config: Record<string, any>
  onConfigChange: (key: string, value: any) => void
  onReset: () => void
  presaleEnabled: boolean
  onPresaleToggle: (enabled: boolean) => void
  presaleType: 'bull' | 'neutral' | 'bear'
  onPresaleTypeChange: (type: 'bull' | 'neutral' | 'bear') => void
  simulationMode: 'agent' | 'volume'
  onSimulationModeChange: (mode: 'agent' | 'volume') => void
  agentPopulation: Record<string, AgentPopulation>
  onAgentPopulationChange: (population: Record<string, AgentPopulation>) => void
}

interface ConfigSection {
  title: string
  icon: React.ReactNode
  description: string
  fields: ConfigField[]
}

interface ConfigField {
  key: string
  label: string
  type: 'number' | 'range' | 'select' | 'checkbox'
  min?: number
  max?: number
  step?: number
  options?: { value: any; label: string }[]
  unit?: string
  hint?: string
}

const configSections: ConfigSection[] = [
  {
    title: 'Simulation Structure',
    icon: '⚙️',
    description: 'Controls simulation size and duration',
    fields: [
      { key: 'n_paths', label: 'Monte Carlo Paths', type: 'number', min: 10, max: 500, step: 10, hint: 'More paths = smoother results but slower' },
      { key: 'horizon_days', label: 'Horizon (Days)', type: 'number', min: 7, max: 365, step: 1, hint: 'Simulation duration in days' },
    ]
  },
  {
    title: 'Market Parameters',
    icon: '📈',
    description: 'Underlying asset price dynamics (overrides scenario)',
    fields: [
      { key: 'initial_price', label: 'Initial Price', type: 'number', min: 1, max: 10000, step: 1, unit: 'USD' },
      { key: 'mu', label: 'Drift (μ)', type: 'range', min: -2, max: 2, step: 0.05, hint: 'Annualized expected return' },
      { key: 'sigma', label: 'Volatility (σ)', type: 'range', min: 0.1, max: 2, step: 0.05, hint: 'Annualized volatility' },
    ]
  },
  {
    title: 'LST Parameters',
    icon: '🔷',
    description: 'Liquid Staking Token yield and depeg risk',
    fields: [
      { key: 'staking_yield', label: 'Staking Yield', type: 'range', min: 0, max: 0.20, step: 0.002, unit: 'APY', hint: 'Annual staking rewards' },
      { key: 'p_depeg', label: 'Depeg Probability', type: 'range', min: 0, max: 0.05, step: 0.001, unit: '%', hint: 'Daily chance of depeg event' },
      { key: 'depeg_mean', label: 'Depeg Severity', type: 'range', min: -0.3, max: 0, step: 0.01, hint: 'Average depeg discount when it occurs' },
      { key: 'depeg_std', label: 'Depeg Volatility', type: 'range', min: 0, max: 0.1, step: 0.001, hint: 'Volatility of depeg severity' },
      { key: 'stress_depeg_multiplier', label: 'Stress Multiplier', type: 'range', min: 1, max: 5, step: 0.1, hint: 'How much worse depegs are in stress scenarios' },
    ]
  },
  {
    title: 'fToken Configuration',
    icon: '💎',
    description: 'Protocol parameters and fee structure',
    fields: [
      { key: 'initial_reserves', label: 'Initial Reserves', type: 'number', min: 1000, max: 10000000, step: 1000, unit: 'ETH' },
      { key: 'initial_supply', label: 'Initial Supply', type: 'number', min: 1000, max: 10000000, step: 1000, unit: 'fETH' },
      { key: 'initial_floor', label: 'Initial Floor', type: 'number', min: 0.1, max: 10, step: 0.01, unit: 'ETH' },
      { key: 'buy_fee', label: 'Buy Fee', type: 'range', min: 0, max: 0.1, step: 0.001, unit: '%', hint: 'Fee charged on minting' },
      { key: 'sell_fee', label: 'Sell Fee', type: 'range', min: 0, max: 0.1, step: 0.001, unit: '%', hint: 'Fee charged on redemption' },
      { key: 'origination_fee', label: 'Origination Fee', type: 'range', min: 0, max: 0.1, step: 0.001, unit: '%', hint: 'Fee charged on new loans' },
      // Fee Distribution
      { key: 'fee_to_floor_ratio', label: 'To Floor Elevation', type: 'range', min: 0, max: 1, step: 0.05, unit: '%', hint: 'Portion of fees used to raise floor' },
      { key: 'fee_to_stakers_ratio', label: 'To Stakers', type: 'range', min: 0, max: 1, step: 0.05, unit: '%', hint: 'Portion of fees distributed to stakers' },
      { key: 'fee_to_team_ratio', label: 'To Floors Team', type: 'range', min: 0, max: 1, step: 0.05, unit: '%', hint: 'Portion of fees to development team' },

      { key: 'loan_ltv', label: 'Loan LTV', type: 'range', min: 0.1, max: 0.95, step: 0.05, unit: '%', hint: 'Max Loan-to-Value ratio' },
      { key: 'debt_cap_pct', label: 'Debt Cap', type: 'range', min: 0, max: 1, step: 0.05, unit: '%', hint: 'Max debt as % of reserves' },
      { key: 'lre_threshold', label: 'LRE Threshold', type: 'range', min: 1.1, max: 5.0, step: 0.1, hint: 'Premium multiple triggering LRE' },
      { key: 'lre_realloc_pct', label: 'LRE Reallocation', type: 'range', min: 0, max: 1, step: 0.05, unit: '%', hint: '% of excess liquidity used to raise floor' },
    ]
  },
  {
    title: 'Agent Behavior',
    icon: '🤖',
    description: 'Simulated market participant tendencies',
    fields: [
      { key: 'enable_loan_activity', label: 'Enable Loans', type: 'checkbox', hint: 'Allow agents to take loans' },
      { key: 'enable_leverage_looping', label: 'Enable Looping', type: 'checkbox', hint: 'Allow agents to loop leverage' },
      { key: 'target_lock_ratio', label: 'Target Lock Ratio', type: 'range', min: 0, max: 1, step: 0.05, unit: '%', hint: 'Target % of supply locked in loans' },
      { key: 'repay_probability', label: 'Repay Prob.', type: 'range', min: 0, max: 0.1, step: 0.001, unit: '%', hint: 'Daily probability of loan repayment' },
      { key: 'leverage_probability_base', label: 'Leverage Prob.', type: 'range', min: 0, max: 0.2, step: 0.005, unit: '%', hint: 'Base probability of leveraging up' },
    ]
  },
  {
    title: 'Trading Volume',
    icon: '📊',
    description: 'Volume settings for volume-based simulation mode',
    fields: [
      { key: 'baseline_daily_volume_pct', label: 'Baseline Daily Volume', type: 'range', min: 0.01, max: 0.30, step: 0.01, unit: '%', hint: 'Base % of supply that trades daily (e.g., 5% = 0.05)' },
      { key: 'volume_scenario_multiplier', label: 'Scenario Multiplier', type: 'range', min: 0.1, max: 3.0, step: 0.1, hint: 'Adjusts volume for market conditions (0.3 = bear, 1.0 = normal, 1.5 = bull)' },
    ]
  }
]

export default function SimulationConfig({
  config,
  onConfigChange,
  onReset,
  presaleEnabled,
  onPresaleToggle,
  presaleType,
  onPresaleTypeChange,
  simulationMode,
  onSimulationModeChange,
  agentPopulation,
  onAgentPopulationChange
}: SimulationConfigProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>('Simulation Structure')

  const handleChange = (key: string, value: any) => {
    // Handle special conversions if needed
    if (key === 'debt_cap_pct') {
      onConfigChange('debt_cap_bps', Math.round(value * 10000))
    } else if (key === 'lre_realloc_pct') {
      onConfigChange('lre_realloc_bps', Math.round(value * 10000))
    } else {
      onConfigChange(key, value)
    }
  }

  const formatValue = (value: number, field: ConfigField) => {
    if (field.type === 'checkbox') return value ? 'Yes' : 'No'
    if (field.unit === '%') return `${(value * 100).toFixed(2)}%`
    if (field.unit === 'APY') return `${(value * 100).toFixed(1)}%`
    if (field.unit === 'USD') return `$${value.toLocaleString()}`
    return value.toLocaleString()
  }

  const getDisplayValue = (key: string, value: number) => {
    if (key === 'debt_cap_bps' || key === 'lre_realloc_bps') {
      return value / 10000
    }
    return value
  }

  const presaleTypes = [
    { value: 'bull', label: 'Bullish', color: '#10B981', desc: 'High demand, quick sellout' },
    { value: 'neutral', label: 'Neutral', color: '#6366F1', desc: 'Steady growth, moderate demand' },
    { value: 'bear', label: 'Bearish', color: '#EF4444', desc: 'Low demand, slow growth' }
  ]

  // Agent archetypes with descriptions
  const agentTypes = [
    {
      key: 'LeverageSeeker',
      icon: '🎯',
      name: 'Leverage Seeker',
      desc: 'Aggressive leverage user. Enters at 85% LTV, deleverages on stress, re-levers on recovery.',
      color: '#ef4444'
    },
    {
      key: 'YieldSeeker',
      icon: '🌱',
      name: 'Yield Seeker',
      desc: 'Conservative holder. Buys at low premium, holds for floor growth, modest 50% LTV.',
      color: '#22c55e'
    },
    {
      key: 'DAT',
      icon: '📊',
      name: 'DAT (DCA)',
      desc: 'Long-term accumulator. DCAs based on discounted future floor estimate.',
      color: '#3b82f6'
    },
    {
      key: 'Arbitrageur',
      icon: '⚡',
      name: 'Arbitrageur',
      desc: 'Short-term speculator. Buys <3% premium, exits at 10-20%, max 14-day holds.',
      color: '#f59e0b'
    },
    {
      key: 'FloorHolder',
      icon: '🏦',
      name: 'Floor Holder',
      desc: 'Credit facility user. Uses tokens as collateral at 70% LTV, tops up on floor rises.',
      color: '#8b5cf6'
    },
  ]

  const updateAgentCount = (agentType: string, count: number) => {
    onAgentPopulationChange({
      ...agentPopulation,
      [agentType]: { ...agentPopulation[agentType], count }
    })
  }

  const updateAgentEth = (agentType: string, eth: number) => {
    onAgentPopulationChange({
      ...agentPopulation,
      [agentType]: { ...agentPopulation[agentType], initial_eth: eth }
    })
  }

  const totalAgents = Object.values(agentPopulation).reduce((sum, a) => sum + a.count, 0)

  return (
    <div className="simulation-config">
      <div className="config-header-row">
        <h2 className="config-title">
          <Sparkles size={20} className="text-accent-primary" />
          Configuration
        </h2>
        <button onClick={onReset} className="btn-reset" title="Reset to defaults">
          <RotateCcw size={16} />
        </button>
      </div>

      {/* Simulation Mode Toggle */}
      <div className="mode-toggle-section">
        <div className="mode-toggle-label">Simulation Engine</div>
        <div className="mode-toggle-buttons">
          <button
            className={`mode-btn ${simulationMode === 'agent' ? 'active' : ''}`}
            onClick={() => onSimulationModeChange('agent')}
          >
            <span className="mode-icon">🤖</span>
            <span className="mode-name">Agent-Based</span>
            <span className="mode-desc">Individual agent behaviors</span>
          </button>
          <button
            className={`mode-btn ${simulationMode === 'volume' ? 'active' : ''}`}
            onClick={() => onSimulationModeChange('volume')}
          >
            <span className="mode-icon">📊</span>
            <span className="mode-name">Volume-Based</span>
            <span className="mode-desc">Statistical volume model</span>
          </button>
        </div>
      </div>

      {/* Agent Archetypes Section - Only show in agent mode */}
      {simulationMode === 'agent' && (
        <div className="config-section agent-archetypes-section">
          <div className="section-header active">
            <div className="section-title-group">
              <span className="section-icon">👥</span>
              <div className="section-info">
                <span className="section-name">Agent Archetypes</span>
                <span className="section-desc">Configure {totalAgents} market participants</span>
              </div>
            </div>
          </div>

          <div className="agent-grid">
            {agentTypes.map((agent) => (
              <div
                key={agent.key}
                className="agent-card"
                style={{ borderColor: agent.color }}
              >
                <div className="agent-header">
                  <span className="agent-icon">{agent.icon}</span>
                  <span className="agent-name">{agent.name}</span>
                </div>
                <p className="agent-desc">{agent.desc}</p>
                <div className="agent-controls">
                  <div className="agent-control">
                    <label>Count</label>
                    <input
                      type="range"
                      min={0}
                      max={200}
                      step={1}
                      value={agentPopulation[agent.key]?.count || 0}
                      onChange={(e) => updateAgentCount(agent.key, parseInt(e.target.value))}
                    />
                    <span className="control-value">{agentPopulation[agent.key]?.count || 0}</span>
                  </div>
                  <div className="agent-control">
                    <label>ETH each</label>
                    <input
                      type="range"
                      min={1}
                      max={100}
                      step={1}
                      value={agentPopulation[agent.key]?.initial_eth || 10}
                      onChange={(e) => updateAgentEth(agent.key, parseInt(e.target.value))}
                    />
                    <span className="control-value">{agentPopulation[agent.key]?.initial_eth || 10} ETH</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Presale Section */}
      <div className="config-section">
        <button
          className={`section-header ${presaleEnabled ? 'active' : ''}`}
          onClick={() => onPresaleToggle(!presaleEnabled)}
        >
          <div className="section-title-group">
            <span className="section-icon">🚀</span>
            <div className="section-info">
              <span className="section-name">Presale Phase</span>
              <span className="section-desc">Simulate initial token distribution</span>
            </div>
          </div>
          <div className="toggle-label" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={presaleEnabled}
              onChange={(e) => onPresaleToggle(e.target.checked)}
            />
            <span className="toggle-slider"></span>
          </div>
        </button>

        <AnimatePresence>
          {presaleEnabled && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="section-content"
            >
              <div className="config-fields">
                <div className="presale-types" style={{ gridColumn: '1 / -1', display: 'flex', gap: '1rem' }}>
                  {presaleTypes.map(pt => (
                    <button
                      key={pt.value}
                      className={`presale-type-btn ${presaleType === pt.value ? 'active' : ''}`}
                      onClick={() => onPresaleTypeChange(pt.value as any)}
                      style={{ '--type-color': pt.color } as React.CSSProperties}
                    >
                      <span className="presale-type-label">{pt.label}</span>
                      <span className="presale-type-desc">{pt.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {configSections
        .filter(section => {
          // Hide "Agent Behavior" in agent mode (agents handle this)
          if (simulationMode === 'agent' && section.title === 'Agent Behavior') return false
          // Hide "Trading Volume" in agent mode (only for volume-based)
          if (simulationMode === 'agent' && section.title === 'Trading Volume') return false
          return true
        })
        .map((section) => {
          const isExpanded = expandedSection === section.title

          return (
            <div key={section.title} className="config-section">
              <button
                className={`section-header ${isExpanded ? 'active' : ''}`}
                onClick={() => setExpandedSection(isExpanded ? null : section.title)}
              >
                <div className="section-title-group">
                  <span className="section-icon">{section.icon}</span>
                  <div className="section-info">
                    <span className="section-name">{section.title}</span>
                    <span className="section-desc">{section.description}</span>
                  </div>
                </div>
                {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>

              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="section-content"
                  >
                    <div className="config-fields">
                      {section.fields.map((field) => {
                        // Handle bps to % conversion
                        let value = config[field.key] ?? 0

                        if (field.key === 'debt_cap_pct') {
                          value = getDisplayValue('debt_cap_bps', config['debt_cap_bps'] ?? 5000)
                        } else if (field.key === 'lre_realloc_pct') {
                          value = getDisplayValue('lre_realloc_bps', config['lre_realloc_bps'] ?? 2000)
                        }

                        return (
                          <div key={field.key} className="config-field">
                            <div className="config-field-header">
                              <label className="config-label">
                                {field.label}
                                {field.hint && (
                                  <Tooltip content={field.hint}>
                                    <span className="config-hint">
                                      <Info size={14} />
                                    </span>
                                  </Tooltip>
                                )}
                              </label>
                              <span className="config-value font-mono">
                                {formatValue(value, field)}
                              </span>
                            </div>

                            {field.type === 'range' ? (
                              <input
                                type="range"
                                className="form-range"
                                min={field.min}
                                max={field.max}
                                step={field.step}
                                value={value}
                                onChange={(e) => handleChange(field.key, parseFloat(e.target.value))}
                              />
                            ) : field.type === 'number' ? (
                              <input
                                type="number"
                                className="form-input"
                                min={field.min}
                                max={field.max}
                                step={field.step}
                                value={value}
                                onChange={(e) => handleChange(field.key, parseFloat(e.target.value) || 0)}
                              />
                            ) : field.type === 'checkbox' ? (
                              <label className="toggle-label">
                                <input
                                  type="checkbox"
                                  checked={!!value}
                                  onChange={(e) => handleChange(field.key, e.target.checked)}
                                />
                                <span className="toggle-slider"></span>
                              </label>
                            ) : null}
                          </div>
                        )
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}

      <style>{`
        .config-container {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-sm);
        }

        .toggle-label {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
          cursor: pointer;
        }

        .toggle-label input {
          display: none;
        }

        .toggle-slider {
          width: 48px;
          height: 24px;
          background: var(--bg-tertiary);
          border-radius: 12px;
          position: relative;
          transition: background var(--transition-fast);
        }

        .toggle-slider::after {
          content: '';
          position: absolute;
          top: 2px;
          left: 2px;
          width: 20px;
          height: 20px;
          background: white;
          border-radius: 50%;
          transition: transform var(--transition-fast);
        }

        .toggle-label input:checked + .toggle-slider {
          background: var(--accent-primary);
        }

        .toggle-label input:checked + .toggle-slider::after {
          transform: translateX(24px);
        }

        .config-section {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
          overflow: hidden;
        }

        .section-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          padding: var(--spacing-md) var(--spacing-lg);
          background: transparent;
          border: none;
          color: var(--text-primary);
          cursor: pointer;
          transition: background var(--transition-fast);
        }

        .section-header:hover {
          background: var(--bg-tertiary);
        }

        .section-title-group {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
        }

        .section-info {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
        }

        .section-name {
          font-weight: 600;
        }

        .section-desc {
          font-size: 0.75rem;
          color: var(--text-muted);
          font-weight: 400 !important;
        }

        .section-icon {
          font-size: 1.25rem;
        }

        .section-content {
          overflow: hidden;
          border-top: 1px solid var(--border-color);
        }

        .config-fields {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: var(--spacing-md);
          padding: var(--spacing-lg);
        }

        .config-field {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xs);
        }

        .config-field-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .config-label {
          display: flex;
          align-items: center;
          gap: var(--spacing-xs);
          font-size: 0.875rem;
          color: var(--text-secondary);
        }

        .config-hint {
          color: var(--text-muted);
          cursor: help;
          display: flex;
          align-items: center;
        }

        .config-value {
          font-size: 0.875rem;
          color: var(--accent-primary);
          font-weight: 500;
        }

        .form-input {
          background: var(--bg-tertiary);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-md);
          padding: var(--spacing-sm) var(--spacing-md);
          color: var(--text-primary);
          font-size: 0.875rem;
          font-family: var(--font-mono);
        }

        .form-input:focus {
          outline: none;
          border-color: var(--accent-primary);
          box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }

        .presale-types {
          display: flex;
          gap: var(--spacing-sm);
          margin-top: var(--spacing-md);
          overflow: hidden;
        }

        .presale-type-btn {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--spacing-xs);
          padding: var(--spacing-md);
          background: var(--bg-tertiary);
          border: 2px solid var(--border-color);
          border-radius: var(--radius-md);
          cursor: pointer;
          transition: all var(--transition-fast);
        }

        .presale-type-btn:hover {
          border-color: var(--type-color);
        }

        .presale-type-btn.active {
          border-color: var(--type-color);
          background: color-mix(in srgb, var(--type-color) 15%, var(--bg-tertiary));
        }

        .presale-type-label {
          font-weight: 600;
          color: var(--text-primary);
        }

        .presale-type-desc {
          font-size: 0.75rem;
          color: var(--text-muted);
          text-align: center;
        }
      `}</style>
    </div>
  )
}
