import { motion } from 'framer-motion'
import { TrendingDown, TrendingUp, Minus, Zap, Snowflake, Sun, Info } from 'lucide-react'
import { useState } from 'react'

interface ScenarioSelectorProps {
    scenarios: string[]
    selected: string
    onSelect: (scenario: string) => void
}

interface ScenarioMeta {
    icon: any
    color: string
    description: string
    tooltip: string
    params: { drift: string; volatility: string; duration: string }
}

const scenarioMeta: Record<string, ScenarioMeta> = {
    crypto_winter: {
        icon: Snowflake,
        color: '#60a5fa',
        description: 'Severe 75% drawdown, high volatility',
        tooltip: 'Simulates a prolonged bear market with -150% annualized drift and 80% volatility. Tests floor resilience under extreme stress.',
        params: { drift: '-150%', volatility: '80%', duration: '90 days' }
    },
    crab_market: {
        icon: Minus,
        color: '#fbbf24',
        description: 'Sideways market, low volatility',
        tooltip: 'Flat price action with 0% drift and 30% volatility. Good baseline for fee accumulation and floor elevation testing.',
        params: { drift: '0%', volatility: '30%', duration: '90 days' }
    },
    super_cycle: {
        icon: Sun,
        color: '#34d399',
        description: 'Strong bull market, high volume',
        tooltip: 'Bull market with +100% drift and 60% volatility. Tests LRE triggers and reserve reallocation at high premiums.',
        params: { drift: '+100%', volatility: '60%', duration: '180 days' }
    },
    presale_bull: {
        icon: TrendingUp,
        color: '#a78bfa',
        description: '7-day presale with bullish sentiment',
        tooltip: 'Short presale period assuming high participation. Use with a market scenario for full picture.',
        params: { drift: '+50%', volatility: '40%', duration: '7 days' }
    },
    presale_neutral: {
        icon: Minus,
        color: '#94a3b8',
        description: '7-day presale with neutral sentiment',
        tooltip: 'Moderate presale participation. Combine with market scenarios via the presale toggle.',
        params: { drift: '0%', volatility: '40%', duration: '7 days' }
    },
    presale_bear: {
        icon: TrendingDown,
        color: '#f87171',
        description: '7-day presale with bearish sentiment',
        tooltip: 'Low participation presale. Smaller initial supply means different floor dynamics.',
        params: { drift: '-30%', volatility: '50%', duration: '7 days' }
    },
    leverage_ltv80: {
        icon: Zap,
        color: '#fb923c',
        description: 'High leverage stress test at 80% LTV',
        tooltip: 'Tests credit facility at 80% LTV. Moderate liquidation risk.',
        params: { drift: '-50%', volatility: '70%', duration: '60 days' }
    },
    leverage_ltv90: {
        icon: Zap,
        color: '#f472b6',
        description: 'Aggressive leverage at 90% LTV',
        tooltip: 'Near-max leverage testing. Higher bad debt probability.',
        params: { drift: '-50%', volatility: '70%', duration: '60 days' }
    },
    leverage_ltv99: {
        icon: Zap,
        color: '#ef4444',
        description: 'Extreme stress test at 99% LTV',
        tooltip: 'Maximum leverage scenario. Extreme bad debt accumulation expected.',
        params: { drift: '-75%', volatility: '80%', duration: '60 days' }
    },
}

const formatScenarioName = (name: string): string => {
    return name
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
}

export default function ScenarioSelector({ scenarios, selected, onSelect }: ScenarioSelectorProps) {
    const [hoveredScenario, setHoveredScenario] = useState<string | null>(null)

    // Filter out presale and leverage scenarios - they're now configurable via parameters
    const marketScenarios = scenarios.filter(s =>
        !s.startsWith('presale_') && !s.startsWith('leverage_')
    )

    return (
        <div className="scenario-container">
            <div className="scenario-grid">
                {marketScenarios.map((scenario, index) => {
                    const meta = scenarioMeta[scenario] || {
                        icon: TrendingUp,
                        color: '#6366f1',
                        description: 'Custom scenario',
                        tooltip: 'Custom scenario configuration',
                        params: { drift: 'Custom', volatility: 'Custom', duration: 'Custom' }
                    }
                    const Icon = meta.icon
                    const isSelected = scenario === selected
                    const isHovered = scenario === hoveredScenario

                    return (
                        <motion.button
                            key={scenario}
                            className={`scenario-card ${isSelected ? 'selected' : ''}`}
                            onClick={() => onSelect(scenario)}
                            onMouseEnter={() => setHoveredScenario(scenario)}
                            onMouseLeave={() => setHoveredScenario(null)}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.05 }}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            style={{
                                '--accent-color': meta.color,
                            } as React.CSSProperties}
                        >
                            <div className="scenario-icon" style={{ background: `${meta.color}20`, color: meta.color }}>
                                <Icon size={24} />
                            </div>
                            <div className="scenario-info">
                                <h3 className="scenario-name">{formatScenarioName(scenario)}</h3>
                                <p className="scenario-desc">{meta.description}</p>
                                <div className="scenario-params">
                                    <span>μ: {meta.params.drift}</span>
                                    <span>σ: {meta.params.volatility}</span>
                                </div>
                            </div>
                            {isSelected && (
                                <motion.div
                                    className="scenario-check"
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ type: 'spring', stiffness: 500 }}
                                >
                                    ✓
                                </motion.div>
                            )}

                            {/* Tooltip */}
                            {isHovered && (
                                <motion.div
                                    className="scenario-tooltip"
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                >
                                    <Info size={14} />
                                    <span>{meta.tooltip}</span>
                                </motion.div>
                            )}
                        </motion.button>
                    )
                })}
            </div>

            <style>{`
        .scenario-container {
          position: relative;
        }

        .scenario-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: var(--spacing-md);
        }

        .scenario-card {
          display: flex;
          align-items: flex-start;
          gap: var(--spacing-md);
          padding: var(--spacing-lg);
          background: var(--bg-card);
          border: 2px solid var(--border-color);
          border-radius: var(--radius-lg);
          cursor: pointer;
          text-align: left;
          transition: all var(--transition-normal);
          position: relative;
          z-index: 1;
        }

        .scenario-card:hover {
          border-color: var(--accent-color);
          box-shadow: 0 0 20px color-mix(in srgb, var(--accent-color) 20%, transparent);
          z-index: 50;
        }

        .scenario-card.selected {
          border-color: var(--accent-color);
          background: linear-gradient(
            145deg,
            color-mix(in srgb, var(--accent-color) 10%, var(--bg-card)),
            var(--bg-card)
          );
          box-shadow: 0 0 30px color-mix(in srgb, var(--accent-color) 25%, transparent);
        }

        .scenario-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          border-radius: var(--radius-md);
          flex-shrink: 0;
        }

        .scenario-info {
          flex: 1;
          min-width: 0;
        }

        .scenario-name {
          font-size: 1rem;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: var(--spacing-xs);
        }

        .scenario-desc {
          font-size: 0.8rem;
          color: var(--text-muted);
          line-height: 1.4;
          margin-bottom: var(--spacing-xs);
        }

        .scenario-params {
          display: flex;
          gap: var(--spacing-md);
          font-size: 0.7rem;
          font-family: var(--font-mono);
          color: var(--text-secondary);
        }

        .scenario-check {
          position: absolute;
          top: var(--spacing-sm);
          right: var(--spacing-sm);
          width: 24px;
          height: 24px;
          background: var(--accent-color);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 0.75rem;
          font-weight: bold;
        }

        .scenario-tooltip {
          position: absolute;
          top: calc(100% - 12px);
          left: var(--spacing-md);
          right: var(--spacing-md);
          background: rgba(15, 23, 42, 0.98);
          border: 1px solid var(--accent-color);
          border-radius: var(--radius-md);
          padding: var(--spacing-md);
          display: flex;
          align-items: flex-start;
          gap: var(--spacing-sm);
          font-size: 0.8rem;
          line-height: 1.5;
          color: var(--text-primary);
          z-index: 100;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        }

        .scenario-tooltip svg {
          flex-shrink: 0;
          color: var(--accent-color);
          margin-top: 2px;
        }
      `}</style>
        </div>
    )
}
