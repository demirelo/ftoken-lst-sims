import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Info, Sparkles } from 'lucide-react'

interface SimulationConfigProps {
    config: Record<string, any>
    onChange: (key: string, value: any) => void
    presaleEnabled: boolean
    onPresaleToggle: (enabled: boolean) => void
    presaleType: 'bull' | 'neutral' | 'bear'
    onPresaleTypeChange: (type: 'bull' | 'neutral' | 'bear') => void
}

interface ConfigSection {
    title: string
    icon: string
    description: string
    fields: ConfigField[]
}

interface ConfigField {
    key: string
    label: string
    type: 'number' | 'range' | 'select'
    min?: number
    max?: number
    step?: number
    unit?: string
    hint?: string
    options?: { value: any; label: string }[]
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
            { key: 'p_depeg', label: 'Depeg Probability', type: 'range', min: 0, max: 0.05, step: 0.001, unit: 'daily', hint: 'Daily chance of depeg event' },
            { key: 'depeg_mean', label: 'Depeg Severity', type: 'range', min: -0.3, max: 0, step: 0.01, hint: 'Average depeg discount when it occurs' },
        ]
    },
    {
        title: 'fToken Configuration',
        icon: '🪙',
        description: 'Token fees and floor mechanics',
        fields: [
            { key: 'initial_floor', label: 'Initial Floor', type: 'number', min: 0.1, max: 10, step: 0.01 },
            { key: 'buy_fee', label: 'Buy Fee', type: 'range', min: 0, max: 0.05, step: 0.001, unit: '%', hint: 'Fee on token purchases' },
            { key: 'sell_fee', label: 'Sell Fee', type: 'range', min: 0, max: 0.05, step: 0.001, unit: '%', hint: 'Fee on token sales' },
            { key: 'origination_fee', label: 'Origination Fee', type: 'range', min: 0, max: 0.1, step: 0.005, unit: '%', hint: 'Fee on new loans' },
        ]
    },
    {
        title: 'Fee Distribution',
        icon: '💰',
        description: 'How collected fees are distributed (must sum to 100%)',
        fields: [
            { key: 'fee_to_floor_ratio', label: 'To Floor Elevation', type: 'range', min: 0, max: 1, step: 0.05, unit: '%', hint: 'Portion that elevates fToken floor' },
            { key: 'fee_to_stakers_ratio', label: 'To Stakers', type: 'range', min: 0, max: 1, step: 0.05, unit: '%', hint: 'Portion distributed to fToken stakers' },
            { key: 'fee_to_team_ratio', label: 'To Floors Team', type: 'range', min: 0, max: 1, step: 0.05, unit: '%', hint: 'Portion to protocol treasury' },
        ]
    },
    {
        title: 'Credit Facility',
        icon: '💳',
        description: 'Loan parameters for leverage positions',
        fields: [
            { key: 'loan_ltv', label: 'Loan LTV', type: 'range', min: 0.1, max: 0.99, step: 0.01, hint: 'Maximum loan-to-value ratio' },
            { key: 'debt_cap_pct', label: 'Debt Cap', type: 'range', min: 10, max: 90, step: 5, unit: '%', hint: 'Max debt as % of reserves' },
        ]
    },
    {
        title: 'LRE Parameters',
        icon: '🔄',
        description: 'Liquidity Reserve Event triggers and actions',
        fields: [
            { key: 'lre_threshold', label: 'LRE Threshold', type: 'range', min: 1, max: 5, step: 0.1, hint: 'Premium/Floor ratio to trigger LRE' },
            { key: 'lre_realloc_pct', label: 'Reallocation', type: 'range', min: 5, max: 50, step: 5, unit: '%', hint: '% of reserves reallocated per LRE' },
        ]
    },
    {
        title: 'Trading Volume',
        icon: '📊',
        description: 'Agent trading activity (affects fee generation and liquidity)',
        fields: [
            { key: 'daily_volume_mean', label: 'Mean Daily Volume', type: 'number', min: 1000, max: 1000000, step: 1000, hint: 'Average daily trading volume in USD' },
            { key: 'daily_volume_std', label: 'Volume Std Dev', type: 'number', min: 0, max: 500000, step: 1000, hint: 'Volume variability' },
        ]
    },
]

function formatValue(value: number, field: ConfigField): string {
    // These fields are already in percentage form (50 = 50%), don't multiply again
    if (field.key === 'debt_cap_pct' || field.key === 'lre_realloc_pct') {
        return `${value.toFixed(0)}%`
    }
    // These fields are decimals that need *100 for display
    if (field.unit === '%' || field.key.includes('fee') || field.key.includes('ratio')) {
        return `${(value * 100).toFixed(1)}%`
    }
    if (field.unit === 'APY') {
        return `${(value * 100).toFixed(2)}%`
    }
    if (field.key === 'mu' || field.key === 'sigma') {
        return `${(value * 100).toFixed(0)}%`
    }
    if (field.key === 'depeg_mean') {
        return `${(value * 100).toFixed(1)}%`
    }
    if (field.key === 'p_depeg') {
        return `${(value * 100).toFixed(2)}%`
    }
    return value.toLocaleString()
}

const presaleTypes = [
    { value: 'bull', label: 'Bullish', color: '#34d399', desc: 'High participation' },
    { value: 'neutral', label: 'Neutral', color: '#94a3b8', desc: 'Moderate participation' },
    { value: 'bear', label: 'Bearish', color: '#f87171', desc: 'Low participation' },
]

export default function SimulationConfig({
    config,
    onChange,
    presaleEnabled,
    onPresaleToggle,
    presaleType,
    onPresaleTypeChange
}: SimulationConfigProps) {
    const [openSections, setOpenSections] = useState<Set<string>>(new Set(['Simulation Structure', 'Market Parameters']))

    const toggleSection = (title: string) => {
        setOpenSections(prev => {
            const newSet = new Set(prev)
            if (newSet.has(title)) {
                newSet.delete(title)
            } else {
                newSet.add(title)
            }
            return newSet
        })
    }

    // Convert bps fields to percentage for display
    const getDisplayValue = (key: string, value: number): number => {
        if (key === 'debt_cap_bps') return value / 100
        if (key === 'lre_realloc_bps') return value / 100
        return value
    }

    const handleChange = (key: string, value: number) => {
        // Convert percentage back to bps for storage
        if (key === 'debt_cap_pct') {
            onChange('debt_cap_bps', value * 100)
        } else if (key === 'lre_realloc_pct') {
            onChange('lre_realloc_bps', value * 100)
        } else {
            onChange(key, value)
        }
    }

    return (
        <div className="config-container">
            {/* Presale Option */}
            <div className="presale-section">
                <div className="presale-header">
                    <div className="presale-toggle-row">
                        <label className="toggle-label">
                            <input
                                type="checkbox"
                                checked={presaleEnabled}
                                onChange={(e) => onPresaleToggle(e.target.checked)}
                            />
                            <span className="toggle-slider"></span>
                            <span className="toggle-text">
                                <Sparkles size={16} />
                                Include 7-Day Presale Period
                            </span>
                        </label>
                    </div>
                    <AnimatePresence>
                        {presaleEnabled && (
                            <motion.div
                                className="presale-types"
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                            >
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
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {configSections.map((section) => {
                const isOpen = openSections.has(section.title)

                return (
                    <div key={section.title} className="config-section">
                        <button
                            className="config-section-header"
                            onClick={() => toggleSection(section.title)}
                        >
                            <div className="config-section-title">
                                <span className="config-section-icon">{section.icon}</span>
                                <div className="config-section-text">
                                    <span>{section.title}</span>
                                    <span className="config-section-desc">{section.description}</span>
                                </div>
                            </div>
                            <motion.div
                                animate={{ rotate: isOpen ? 180 : 0 }}
                                transition={{ duration: 0.2 }}
                            >
                                <ChevronDown size={20} />
                            </motion.div>
                        </button>

                        <AnimatePresence>
                            {isOpen && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="config-section-content"
                                >
                                    <div className="config-fields">
                                        {section.fields.map((field) => {
                                            // Handle bps to % conversion
                                            let displayKey = field.key
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
                                                                <span className="config-hint" title={field.hint}>
                                                                    <Info size={14} />
                                                                </span>
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

        .presale-section {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
          padding: var(--spacing-lg);
          margin-bottom: var(--spacing-md);
        }

        .presale-toggle-row {
          display: flex;
          align-items: center;
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

        .toggle-text {
          display: flex;
          align-items: center;
          gap: var(--spacing-xs);
          font-weight: 500;
          color: var(--text-primary);
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
        }

        .config-section {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
          overflow: hidden;
        }

        .config-section-header {
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

        .config-section-header:hover {
          background: var(--bg-tertiary);
        }

        .config-section-title {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
        }

        .config-section-text {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
        }

        .config-section-text span:first-child {
          font-weight: 600;
        }

        .config-section-desc {
          font-size: 0.75rem;
          color: var(--text-muted);
          font-weight: 400 !important;
        }

        .config-section-icon {
          font-size: 1.25rem;
        }

        .config-section-content {
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
      `}</style>
        </div>
    )
}
