import { useMemo, useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    AreaChart,
    Area,
    ComposedChart,
    Line,
} from 'recharts'
import {
    TrendingUp,
    TrendingDown,
    Shield,
    AlertTriangle,
    Activity,
    BarChart2,
    Percent,
    DollarSign,
    Coins,
    Users,
    ChevronDown,
    ChevronUp
} from 'lucide-react'

interface ResultsDashboardProps {
    results: {
        analysis: any
        paths: any[]
        n_paths: number
        horizon_days: number
    }
    scenarioName?: string
    config?: Record<string, any>
}

function StatCard({
    label,
    value,
    subValue,
    icon: Icon,
    color = 'primary',
    trend,
    tooltip,
}: {
    label: string
    value: string
    subValue?: string
    icon: any
    color?: 'primary' | 'success' | 'warning' | 'danger'
    trend?: 'up' | 'down'
    tooltip?: string
}) {
    const colorMap = {
        primary: 'var(--accent-primary)',
        success: 'var(--accent-success)',
        warning: 'var(--accent-warning)',
        danger: 'var(--accent-danger)',
    }

    return (
        <motion.div
            className="stat-card-wrapper"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ '--stat-color': colorMap[color] } as React.CSSProperties}
            title={tooltip}
        >
            <div className="stat-icon">
                <Icon size={20} />
            </div>
            <div className="stat-content">
                <span className="stat-label">
                    {label}
                    {tooltip && <span className="stat-info-icon" title={tooltip}>ⓘ</span>}
                </span>
                <span className="stat-value">
                    {value}
                    {trend && (
                        <span className={`stat-trend ${trend}`}>
                            {trend === 'up' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                        </span>
                    )}
                </span>
                {subValue && <span className="stat-subvalue">{subValue}</span>}
            </div>
        </motion.div>
    )
}

const formatScenarioName = (name: string): string => {
    return name
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
}

export default function ResultsDashboard({ results, scenarioName, config }: ResultsDashboardProps) {
    const { analysis, paths } = results
    const [ethPrice, setEthPrice] = useState<number | null>(null)

    // Fetch current ETH price from CoinGecko
    useEffect(() => {
        fetch('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd')
            .then(res => res.json())
            .then(data => {
                setEthPrice(data.ethereum?.usd || null)
            })
            .catch(err => {
                console.error('Failed to fetch ETH price:', err)
            })
    }, [])

    // Prepare chart data from sample paths - scaled to real USD if ethPrice available
    const priceChartData = useMemo(() => {
        if (!paths || paths.length === 0) return []

        const numSteps = paths[0].underlying_price.length
        const data = []

        // Scale to real ETH price if available, accounting for simulation's initial price
        const scaleFactor = (ethPrice && config?.initial_price) ? ethPrice / config.initial_price : 1

        for (let i = 0; i < numSteps; i++) {
            const entry: any = { day: i }

            // Calculate averages across paths
            let avgUnderlying = 0
            let avgLst = 0
            let avgFloor = 0        // ETH-denominated floor
            let avgFloorUSD = 0     // USD-denominated floor
            let avgLstRatio = 0     // LST / Underlying ratio
            let avgFpr = 0
            let avgMarketPrice = 0  // fETH market price in ETH

            paths.forEach((path: any) => {
                const underlying = path.underlying_price[i]
                const lst = path.lst_price[i]
                const floor = path.ftoken_floor[i]
                const marketPrice = path.ftoken_market_price ? path.ftoken_market_price[i] : floor

                avgUnderlying += underlying / paths.length
                avgLst += lst / paths.length
                avgFloor += floor / paths.length
                avgFloorUSD += (floor * underlying) / paths.length
                avgLstRatio += (lst / underlying) / paths.length
                avgFpr += path.ftoken_fpr[i] / paths.length
                avgMarketPrice += marketPrice / paths.length
            })

            // Scale to real USD
            entry.ethUSD = avgUnderlying * scaleFactor
            entry.stethUSD = avgLst * scaleFactor
            entry.fethFloorUSD = avgFloorUSD * scaleFactor

            // Keep ETH-denominated values for the other chart
            entry.avgFloor = avgFloor
            entry.avgMarketPrice = avgMarketPrice
            entry.avgPremiumDiff = avgMarketPrice - avgFloor  // The actual gap between market and floor
            entry.avgLstRatio = avgLstRatio
            entry.avgFpr = avgFpr

            data.push(entry)
        }

        return data
    }, [paths, ethPrice])

    // Extract key metrics from analysis
    const metrics = useMemo(() => {
        if (!analysis) return null

        const varAnalysis = analysis.var_analysis || {}
        const fprAnalysis = analysis.fpr_analysis || {}
        const floorMetrics = analysis.floor_metrics || {}
        const lreMetrics = analysis.lre_metrics || {}
        const volumeMetrics = analysis.volume_metrics || {}
        const creditMetrics = analysis.credit_metrics || {}
        const supplyMetrics = analysis.supply_metrics || {}

        return {
            lstVaR: varAnalysis.lst?.var_5pct || 0,
            ftokenVaR: varAnalysis.ftoken_usd?.var_5pct || 0,
            lstMean: varAnalysis.lst?.mean || 0,
            ftokenMean: varAnalysis.ftoken_usd?.mean || 0,
            probInsolvency: fprAnalysis.prob_ever_insolvent || 0,
            probRedZone: fprAnalysis.prob_ever_red_zone || 0,
            minFpr5th: fprAnalysis.min_fpr_5th_percentile || 0,
            finalFprMean: fprAnalysis.final_fpr_mean || 0,
            floorGrowth: floorMetrics.mean_floor_growth || 0,
            finalFloor: floorMetrics.mean_final_floor || 1.0,
            lreEvents: lreMetrics.mean_lre_events || 0,
            stakersFees: analysis.fee_metrics?.mean_stakers_fees || 0,
            teamFees: analysis.fee_metrics?.mean_team_fees || 0,
            avgDailyBuyVolume: volumeMetrics.avg_daily_buy_volume || 0,
            avgDailySellVolume: volumeMetrics.avg_daily_sell_volume || 0,
            avgDailyLoanVolume: volumeMetrics.avg_daily_loan_volume || 0,
            meanFinalDebt: creditMetrics.mean_final_debt || 0,
            meanMaxDebt: creditMetrics.mean_max_debt || 0,
            meanFinalLocked: creditMetrics.mean_final_locked || 0,
            meanFinalSupply: supplyMetrics.mean_final_supply || 0,
            meanFinalMarketCap: supplyMetrics.mean_final_market_cap || 0,
        }
    }, [analysis])

    // Calculate real USD prices based on simulation and live ETH price
    const realPrices = useMemo(() => {
        if (!ethPrice || !metrics) return null

        // Final floor in ETH times real ETH price        // Final floor in ETH (from metrics) times real ETH price
        const fethFloorUSD = metrics.finalFloor * ethPrice

        // stETH is approximately 1:1 with ETH plus staking premium
        // In sim, LST ratio is avgLstRatio at final step
        const finalData = priceChartData[priceChartData.length - 1]
        const lstRatio = finalData?.avgLstRatio || 1.0
        const stethUSD = ethPrice * lstRatio

        return {
            ethPrice,
            fethFloorUSD,
            stethUSD,
            fethCeiling: stethUSD, // fToken can trade up to stETH price
        }
    }, [ethPrice, metrics, priceChartData])

    const [showDetails, setShowDetails] = useState(false)

    if (!metrics) {
        return <div>No analysis data available</div>
    }

    return (
        <div className="results-dashboard">
            {/* Scenario Info Banner */}
            {scenarioName && config && (
                <section className="scenario-info-banner">
                    <div className="scenario-info-header">
                        <h2 className="scenario-info-title">{formatScenarioName(scenarioName)}</h2>
                        <span className="scenario-info-paths">{results.n_paths} paths × {results.horizon_days} days</span>
                    </div>
                    <div className="scenario-info-params">
                        <div className="param-group">
                            <span className="param-label">Drift (μ)</span>
                            <span className="param-value">{((config.mu || 0) * 100).toFixed(0)}%</span>
                        </div>
                        <div className="param-group">
                            <span className="param-label">Volatility (σ)</span>
                            <span className="param-value">{((config.sigma || 0) * 100).toFixed(0)}%</span>
                        </div>
                        <div className="param-group">
                            <span className="param-label">LTV</span>
                            <span className="param-value">{((config.loan_ltv || 0) * 100).toFixed(0)}%</span>
                        </div>
                        <div className="param-group">
                            <span className="param-label">Buy Fee</span>
                            <span className="param-value">{((config.buy_fee || 0) * 100).toFixed(1)}%</span>
                        </div>
                        <div className="param-group">
                            <span className="param-label">Staking Yield</span>
                            <span className="param-value">{((config.staking_yield || 0) * 100).toFixed(2)}%</span>
                        </div>
                        <div className="param-group">
                            <span className="param-label">Fee → Floor</span>
                            <span className="param-value">{((config.fee_to_floor_ratio || 0) * 100).toFixed(0)}%</span>
                        </div>
                    </div>
                </section>
            )}

            {/* Live Price Banner */}
            {realPrices && (
                <section className="live-price-banner">
                    <div className="live-price-item eth">
                        <DollarSign size={20} />
                        <span className="live-price-label">Live ETH Price</span>
                        <span className="live-price-value">${realPrices.ethPrice.toLocaleString()}</span>
                    </div>
                    <div className="live-price-divider" />
                    <div className="live-price-item feth">
                        <Coins size={20} />
                        <span className="live-price-label">fETH Floor (Simulated)</span>
                        <span className="live-price-value">${realPrices.fethFloorUSD.toFixed(2)}</span>
                        <span className="live-price-subtext">{metrics.finalFloor.toFixed(4)} ETH</span>
                    </div>
                    <div className="live-price-divider" />
                    <div className="live-price-item steth">
                        <Coins size={20} />
                        <span className="live-price-label">stETH (Simulated)</span>
                        <span className="live-price-value">${realPrices.stethUSD.toFixed(2)}</span>
                        <span className="live-price-subtext">{(realPrices.stethUSD / realPrices.ethPrice).toFixed(4)} ETH</span>
                    </div>
                </section>
            )}

            {/* Performance Overview */}
            <section className="metrics-section">
                <h2 className="section-title">
                    <TrendingUp size={24} />
                    Performance Overview
                </h2>
                <div className="metrics-grid">
                    <StatCard
                        label="Floor Growth (Annualized)"
                        value={`${(metrics.floorGrowth * 100).toFixed(2)}%`}
                        icon={TrendingUp}
                        color="success"
                        trend={metrics.floorGrowth > 0 ? 'up' : 'down'}
                        tooltip="Projected annual growth rate of the floor price based on simulation results."
                    />
                    <StatCard
                        label="fETH Market Cap"
                        value={`${metrics.meanFinalMarketCap.toLocaleString(undefined, { maximumFractionDigits: 0 })} ETH`}
                        subValue={realPrices ? `≈ $${(metrics.meanFinalMarketCap * realPrices.ethPrice).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : undefined}
                        icon={Coins}
                        color="success"
                        tooltip="Total market capitalization of fETH (Supply × Floor Price)."
                    />
                    <StatCard
                        label="Team Revenue"
                        value={`${metrics.teamFees.toFixed(2)} ETH`}
                        subValue={realPrices ? `≈ $${(metrics.teamFees * realPrices.ethPrice).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : undefined}
                        icon={Activity}
                        color="primary"
                        tooltip="Total accumulated fees distributed to the team."
                    />
                </div>
            </section>

            {/* Volume & Activity - Moved outside of details section */}
            <section className="metrics-section">
                <h2 className="section-title">
                    <BarChart2 size={24} />
                    Volume & Activity
                </h2>
                <div className="metrics-grid">
                    <StatCard
                        label="Buy Volume"
                        value={`${metrics.avgDailyBuyVolume.toLocaleString(undefined, { maximumFractionDigits: 0 })} ETH`}
                        subValue={realPrices ? `≈ $${(metrics.avgDailyBuyVolume * realPrices.ethPrice).toLocaleString(undefined, { maximumFractionDigits: 0 })}/day` : undefined}
                        icon={TrendingUp}
                        color="success"
                        tooltip="Average daily buy volume in ETH across all simulation paths."
                    />
                    <StatCard
                        label="Sell Volume"
                        value={`${metrics.avgDailySellVolume.toLocaleString(undefined, { maximumFractionDigits: 0 })} ETH`}
                        subValue={realPrices ? `≈ $${(metrics.avgDailySellVolume * realPrices.ethPrice).toLocaleString(undefined, { maximumFractionDigits: 0 })}/day` : undefined}
                        icon={TrendingDown}
                        color="warning"
                        tooltip="Average daily sell volume in ETH across all simulation paths."
                    />
                    <StatCard
                        label="Loan Volume"
                        value={`${metrics.avgDailyLoanVolume.toLocaleString(undefined, { maximumFractionDigits: 0 })} ETH`}
                        subValue={realPrices ? `≈ $${(metrics.avgDailyLoanVolume * realPrices.ethPrice).toLocaleString(undefined, { maximumFractionDigits: 0 })}/day` : undefined}
                        icon={Activity}
                        color="primary"
                        tooltip="Average daily new loan origination volume in ETH."
                    />
                </div>
            </section>

            {/* fETH Price Chart (ETH-denominated) - PRIMARY CHART */}
            <section className="chart-section">
                <h2 className="section-title">
                    <BarChart2 size={24} />
                    fETH Price & Premium
                </h2>
                <p className="chart-description">Market price vs floor price, showing premium over time</p>
                <div className="chart-card">
                    <ResponsiveContainer width="100%" height={300}>
                        <ComposedChart data={priceChartData}>
                            <defs>
                                <linearGradient id="premiumGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#fbbf24" stopOpacity={0.6} />
                                    <stop offset="100%" stopColor="#fbbf24" stopOpacity={0.3} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                            <XAxis
                                dataKey="day"
                                stroke="var(--text-muted)"
                                tickFormatter={(val) => `D${val}`}
                            />
                            <YAxis
                                stroke="var(--text-muted)"
                                tickFormatter={(val) => `${val.toFixed(3)}`}
                                label={{ value: 'ETH', angle: -90, position: 'insideLeft' }}
                                domain={[(dataMin: number) => Math.floor(dataMin * 100) / 100, (dataMax: number) => Math.ceil(dataMax * 100) / 100]}
                            />
                            <Tooltip
                                contentStyle={{
                                    background: 'var(--bg-tertiary)',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: 'var(--radius-md)'
                                }}
                                formatter={(value: number, name: string) => {
                                    return [`${value.toFixed(4)} ETH`, name]
                                }}
                            />
                            <Legend />
                            {/* Market Price area - yellow fill from bottom */}
                            <Area
                                type="monotone"
                                dataKey="avgMarketPrice"
                                name="Premium"
                                stroke="transparent"
                                fill="url(#premiumGradient)"
                                strokeWidth={0}
                            />
                            {/* Floor area - masks the yellow below floor line */}
                            <Area
                                type="monotone"
                                dataKey="avgFloor"
                                name="Floor Price"
                                stroke="#34d399"
                                fill="var(--bg-secondary)"
                                strokeWidth={3}
                            />
                            {/* Market Price line on top */}
                            <Line
                                type="monotone"
                                dataKey="avgMarketPrice"
                                name="Market Price"
                                stroke="#60a5fa"
                                strokeWidth={2}
                                dot={false}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            </section>

            {/* USD Price Chart */}
            <section className="chart-section">
                <h2 className="section-title">
                    <DollarSign size={24} />
                    Price Evolution (USD)
                </h2>
                <p className="chart-description">
                    {ethPrice
                        ? `Real USD prices based on live ETH ($${ethPrice.toLocaleString()})`
                        : 'Normalized prices (live ETH price loading...)'}
                </p>
                <div className="chart-card">
                    <ResponsiveContainer width="100%" height={300}>
                        <ComposedChart data={priceChartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                            <XAxis
                                dataKey="day"
                                stroke="var(--text-muted)"
                                tickFormatter={(val) => `D${val}`}
                            />
                            <YAxis
                                stroke="var(--text-muted)"
                                scale="log"
                                domain={['auto', 'auto']}
                                tickFormatter={(val) => `$${val.toLocaleString()}`}
                            />
                            <Tooltip
                                contentStyle={{
                                    background: 'var(--bg-tertiary)',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: 'var(--radius-md)'
                                }}
                                formatter={(value: number, name: string) => [`$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`, name]}
                            />
                            <Legend />
                            <Area
                                type="monotone"
                                dataKey="ethUSD"
                                name="ETH"
                                stroke="#94a3b8"
                                fill="rgba(148, 163, 184, 0.1)"
                                strokeWidth={2}
                            />
                            <Line
                                type="monotone"
                                dataKey="stethUSD"
                                name="stETH"
                                stroke="#60a5fa"
                                strokeWidth={2}
                                dot={false}
                            />
                            <Line
                                type="monotone"
                                dataKey="fethFloorUSD"
                                name="fETH Floor"
                                stroke="#34d399"
                                strokeWidth={3}
                                dot={false}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            </section>

            {/* ETH-Denominated Price Chart */}
            <section className="chart-section">
                <h2 className="section-title">
                    <Coins size={24} />
                    Price Evolution (ETH-Denominated)
                </h2>
                <p className="chart-description">Floor and stETH/ETH ratio over time</p>
                <div className="chart-card">
                    <ResponsiveContainer width="100%" height={300}>
                        <ComposedChart data={priceChartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                            <XAxis
                                dataKey="day"
                                stroke="var(--text-muted)"
                                tickFormatter={(val) => `D${val}`}
                            />
                            <YAxis
                                stroke="var(--text-muted)"
                                domain={[0.98, 'auto']}
                                tickFormatter={(val) => val.toFixed(3)}
                            />
                            <Tooltip
                                contentStyle={{
                                    background: 'var(--bg-tertiary)',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: 'var(--radius-md)'
                                }}
                                formatter={(value: number, name: string) => [value.toFixed(4), name]}
                            />
                            <Legend />
                            <Line
                                type="monotone"
                                dataKey="avgFloor"
                                name="fETH Floor (ETH)"
                                stroke="#34d399"
                                strokeWidth={3}
                                dot={false}
                            />
                            <Line
                                type="monotone"
                                dataKey="avgLstRatio"
                                name="stETH/ETH Ratio"
                                stroke="#60a5fa"
                                strokeWidth={2}
                                dot={false}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                </div>
            </section>

            {/* FPR Chart */}
            <section className="chart-section">
                <h2 className="section-title">
                    <Shield size={24} />
                    Floor Protection Ratio
                </h2>
                <div className="chart-card">
                    <ResponsiveContainer width="100%" height={250}>
                        <AreaChart data={priceChartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                            <XAxis
                                dataKey="day"
                                stroke="var(--text-muted)"
                                tickFormatter={(val) => `D${val}`}
                            />
                            <YAxis
                                stroke="var(--text-muted)"
                                domain={[0.9, 'auto']}
                            />
                            <Tooltip
                                contentStyle={{
                                    background: 'var(--bg-tertiary)',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: 'var(--radius-md)'
                                }}
                            />
                            <defs>
                                <linearGradient id="fprGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <Area
                                type="monotone"
                                dataKey="avgFpr"
                                name="FPR (Avg)"
                                stroke="#8b5cf6"
                                fill="url(#fprGradient)"
                                strokeWidth={2}
                            />
                            {/* Reference lines */}
                            <Line
                                type="monotone"
                                dataKey={() => 1.0}
                                name="Insolvency"
                                stroke="#ef4444"
                                strokeDasharray="5 5"
                                dot={false}
                            />
                            <Line
                                type="monotone"
                                dataKey={() => 1.05}
                                name="Red Zone"
                                stroke="#f59e0b"
                                strokeDasharray="5 5"
                                dot={false}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </section>

            {/* Comparison Summary */}
            <section className="comparison-section">
                <h2 className="section-title">
                    <Percent size={24} />
                    Return Comparison
                </h2>
                <div className="comparison-grid">
                    <div className="comparison-card ftoken">
                        <h3>fETH</h3>
                        <div className="comparison-stat">
                            <span className="comparison-label">Mean Return</span>
                            <span className="comparison-value">{(metrics.ftokenMean * 100).toFixed(2)}%</span>
                        </div>
                        <div className="comparison-stat">
                            <span className="comparison-label">VaR (95%)</span>
                            <span className="comparison-value">{(metrics.ftokenVaR * 100).toFixed(2)}%</span>
                        </div>
                        <div className="comparison-stat">
                            <span className="comparison-label">Floor Growth</span>
                            <span className="comparison-value text-success">{(metrics.floorGrowth * 100).toFixed(2)}%</span>
                        </div>
                        {realPrices && (
                            <div className="comparison-stat highlight">
                                <span className="comparison-label">Real Floor Price</span>
                                <span className="comparison-value">${realPrices.fethFloorUSD.toFixed(2)}</span>
                            </div>
                        )}
                    </div>
                    <div className="comparison-card lst">
                        <h3>stETH</h3>
                        <div className="comparison-stat">
                            <span className="comparison-label">Mean Return</span>
                            <span className="comparison-value">{(metrics.lstMean * 100).toFixed(2)}%</span>
                        </div>
                        <div className="comparison-stat">
                            <span className="comparison-label">VaR (95%)</span>
                            <span className="comparison-value">{(metrics.lstVaR * 100).toFixed(2)}%</span>
                        </div>
                        <div className="comparison-stat">
                            <span className="comparison-label">Staking Yield</span>
                            <span className="comparison-value">2.6% APY</span>
                        </div>
                        {realPrices && (
                            <div className="comparison-stat highlight">
                                <span className="comparison-label">Real Price</span>
                                <span className="comparison-value">${realPrices.stethUSD.toFixed(2)}</span>
                            </div>
                        )}
                    </div>
                </div>
            </section>

            <button
                className="details-toggle-btn"
                onClick={() => setShowDetails(!showDetails)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    width: '100%',
                    padding: '1rem',
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    marginTop: '2rem',
                    marginBottom: '1rem',
                    fontWeight: 600
                }}
            >
                {showDetails ? 'Hide Detailed Analysis' : 'Show Detailed Analysis'}
                {showDetails ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>

            {/* Volume & Activity Section - Always Visible */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <StatCard
                    label="BUY VOLUME"
                    value={`${Math.round(analysis.volume_metrics.total_buy_volume).toLocaleString()} ETH`}
                    subValue={`${Math.round(analysis.volume_metrics.avg_daily_buy_volume).toLocaleString()} / day`}
                    icon={TrendingUp}
                    color="success"
                    trend="up"
                    tooltip="Total quantity of ETH bought by agents (and average per day)."
                />
                <StatCard
                    label="SELL VOLUME"
                    value={`${Math.round(analysis.volume_metrics.total_sell_volume).toLocaleString()} ETH`}
                    subValue={`${Math.round(analysis.volume_metrics.avg_daily_sell_volume).toLocaleString()} / day`}
                    icon={TrendingDown}
                    color="warning"
                    trend="down"
                    tooltip="Total quantity of ETH sold by agents (and average per day)."
                />
                <StatCard
                    label="LOAN VOLUME"
                    value={`${Math.round(analysis.volume_metrics.total_loan_volume).toLocaleString()} ETH`}
                    subValue={`${Math.round(analysis.volume_metrics.avg_daily_loan_volume).toLocaleString()} / day`}
                    icon={Activity}
                    color="primary"
                    tooltip="Total quantity of new loans originated (and average per day)."
                />
            </div>
            {showDetails && (
                <div className="detailed-analysis">
                    {/* Risk Analysis */}
                    <section className="metrics-section">
                        <h2 className="section-title">
                            <Shield size={24} />
                            Risk Analysis
                        </h2>
                        <div className="metrics-grid">
                            <StatCard
                                label="fToken VaR (95%)"
                                value={`${(metrics.ftokenVaR * 100).toFixed(1)}%`}
                                icon={Shield}
                                color={metrics.ftokenVaR > -0.20 ? 'success' : 'warning'}
                                tooltip="Value at Risk: The maximum expected loss at 95% confidence. Lower (less negative) is better."
                            />
                            <StatCard
                                label="LST VaR (95%)"
                                value={`${(metrics.lstVaR * 100).toFixed(1)}%`}
                                icon={TrendingDown}
                                color={metrics.lstVaR > -0.30 ? 'warning' : 'danger'}
                                tooltip="LST Value at Risk: Maximum expected loss for holding stETH at 95% confidence."
                            />
                            <StatCard
                                label="Prob. Insolvency"
                                value={`${(metrics.probInsolvency * 100).toFixed(2)}%`}
                                icon={AlertTriangle}
                                color={metrics.probInsolvency < 0.01 ? 'success' : 'danger'}
                                tooltip="Probability that FPR drops below 1.0 at any point, meaning floor liabilities exceed reserves."
                            />
                            <StatCard
                                label="Min FPR (5th pctl)"
                                value={metrics.minFpr5th.toFixed(3)}
                                icon={Shield}
                                color={metrics.minFpr5th > 1.05 ? 'success' : metrics.minFpr5th > 1.0 ? 'warning' : 'danger'}
                                tooltip="Floor Protection Ratio at 5th percentile. Values >1.0 mean solvent; >1.05 is healthy buffer."
                            />
                            <StatCard
                                label="Final FPR Mean"
                                value={metrics.finalFprMean.toFixed(3)}
                                icon={BarChart2}
                                color="primary"
                                tooltip="Average FPR at end of simulation. Higher means more overcollateralized."
                            />
                            <StatCard
                                label="LRE Events"
                                value={metrics.lreEvents.toFixed(1)}
                                icon={Activity}
                                color="primary"
                                tooltip="Liquidity Reallocation Events: automatic floor raises from excess premium liquidity."
                            />
                            <StatCard
                                label="Prob. Red Zone"
                                value={`${(metrics.probRedZone * 100).toFixed(1)}%`}
                                icon={AlertTriangle}
                                color={metrics.probRedZone < 0.10 ? 'success' : 'warning'}
                                tooltip="Probability FPR drops below 1.05 (buffer zone). Not insolvent but reduced safety margin."
                            />
                        </div>
                    </section>

                    {/* Agent Behavior */}
                    <section className="metrics-section">
                        <h2 className="section-title">
                            <Users size={24} />
                            Agent Behavior
                        </h2>
                        <div className="metrics-grid">
                            <StatCard
                                label="Total Borrowed"
                                value={`${metrics.meanFinalDebt.toLocaleString(undefined, { maximumFractionDigits: 0 })} fETH`}
                                subValue={realPrices ? `≈ $${(metrics.meanFinalDebt * realPrices.ethPrice).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : undefined}
                                icon={DollarSign}
                                color="primary"
                                tooltip="Average total debt (borrowed fETH) at the end of the simulation."
                            />
                            <StatCard
                                label="Peak Borrowing"
                                value={`${metrics.meanMaxDebt.toLocaleString(undefined, { maximumFractionDigits: 0 })} fETH`}
                                subValue={realPrices ? `≈ $${(metrics.meanMaxDebt * realPrices.ethPrice).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : undefined}
                                icon={TrendingUp}
                                color="warning"
                                tooltip="Average maximum debt reached during the simulation."
                            />
                            <StatCard
                                label="Locked Collateral"
                                value={`${metrics.meanFinalLocked.toLocaleString(undefined, { maximumFractionDigits: 0 })} fETH`}
                                subValue={realPrices ? `≈ $${(metrics.meanFinalLocked * realPrices.ethPrice).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : undefined}
                                icon={Coins}
                                color="success"
                                tooltip="Average amount of fETH locked as collateral for loans."
                            />
                        </div>
                    </section>
                </div>
            )}

            <style>{`
        .results-dashboard {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xl);
        }

        .scenario-info-banner {
          background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.1));
          border: 1px solid rgba(139, 92, 246, 0.3);
          border-radius: var(--radius-lg);
          padding: var(--spacing-lg);
        }

        .scenario-info-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--spacing-md);
        }

        .scenario-info-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--text-primary);
          margin: 0;
        }

        .scenario-info-paths {
          font-size: 0.75rem;
          color: var(--text-muted);
          font-family: var(--font-mono);
          background: var(--bg-tertiary);
          padding: var(--spacing-xs) var(--spacing-sm);
          border-radius: var(--radius-sm);
        }

        .scenario-info-params {
          display: flex;
          flex-wrap: wrap;
          gap: var(--spacing-lg);
        }

        .param-group {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .param-label {
          font-size: 0.65rem;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .param-value {
          font-size: 0.9rem;
          font-weight: 600;
          font-family: var(--font-mono);
          color: var(--text-primary);
        }

        .live-price-banner {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: var(--spacing-xl);
          padding: var(--spacing-lg);
          background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(34, 211, 238, 0.1));
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
        }

        .live-price-divider {
          width: 1px;
          height: 40px;
          background: var(--border-color);
        }

        .live-price-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--spacing-xs);
        }

        .live-price-item svg {
          color: var(--text-muted);
        }

        .live-price-item.eth svg { color: #94a3b8; }
        .live-price-item.feth svg { color: #34d399; }
        .live-price-item.steth svg { color: #60a5fa; }

        .live-price-label {
          font-size: 0.75rem;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .live-price-value {
          font-size: 1.25rem;
          font-weight: 700;
          font-family: var(--font-mono);
          color: var(--text-primary);
        }

        .live-price-subtext {
          font-size: 0.7rem;
          color: var(--text-secondary);
          font-family: var(--font-mono);
        }

        .section-title {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          font-size: 1.25rem;
          margin-bottom: var(--spacing-lg);
          color: var(--text-primary);
        }

        .chart-description {
          font-size: 0.8rem;
          color: var(--text-muted);
          margin-top: calc(-1 * var(--spacing-md));
          margin-bottom: var(--spacing-md);
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: var(--spacing-md);
        }

        .stat-card-wrapper {
          display: flex;
          align-items: flex-start;
          gap: var(--spacing-md);
          padding: var(--spacing-lg);
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
          border-left: 3px solid var(--stat-color);
        }

        .stat-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          border-radius: var(--radius-md);
          background: color-mix(in srgb, var(--stat-color) 15%, transparent);
          color: var(--stat-color);
        }

        .stat-content {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xs);
        }

        .stat-label {
          font-size: 0.7rem;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .stat-value {
          display: flex;
          align-items: center;
          gap: var(--spacing-xs);
          font-size: 1.1rem;
          font-weight: 600;
          font-family: var(--font-mono);
          color: var(--text-primary);
        }

        .stat-subvalue {
          font-size: 0.75rem;
          color: var(--text-secondary);
          font-family: var(--font-mono);
        }

        .stat-trend {
          display: flex;
        }

        .stat-trend.up { color: var(--accent-success); }
        .stat-trend.down { color: var(--accent-danger); }

        .chart-section {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
          padding: var(--spacing-lg);
        }

        .chart-card {
          margin-top: var(--spacing-md);
        }

        .comparison-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: var(--spacing-lg);
        }

        @media (max-width: 768px) {
          .comparison-grid {
            grid-template-columns: 1fr;
          }
          .live-price-banner {
            flex-direction: column;
          }
          .live-price-divider {
            width: 100%;
            height: 1px;
          }
        }

        .comparison-card {
          padding: var(--spacing-xl);
          border-radius: var(--radius-lg);
          border: 1px solid var(--border-color);
        }

        .comparison-card.ftoken {
          background: linear-gradient(145deg, rgba(34, 211, 238, 0.1), var(--bg-card));
          border-color: rgba(34, 211, 238, 0.3);
        }

        .comparison-card.lst {
          background: linear-gradient(145deg, rgba(96, 165, 250, 0.1), var(--bg-card));
          border-color: rgba(96, 165, 250, 0.3);
        }

        .comparison-card h3 {
          font-size: 1.125rem;
          margin-bottom: var(--spacing-lg);
          color: var(--text-primary);
        }

        .comparison-stat {
          display: flex;
          justify-content: space-between;
          padding: var(--spacing-sm) 0;
          border-bottom: 1px solid var(--border-color);
        }

        .comparison-stat:last-child {
          border-bottom: none;
        }

        .comparison-stat.highlight {
          background: rgba(255, 255, 255, 0.05);
          margin: var(--spacing-xs) calc(-1 * var(--spacing-md));
          padding: var(--spacing-sm) var(--spacing-md);
          border-radius: var(--radius-sm);
          border-bottom: none;
        }

        .comparison-label {
          color: var(--text-secondary);
          font-size: 0.875rem;
        }

        .comparison-value {
          font-family: var(--font-mono);
          font-weight: 600;
        }
      `}</style>
        </div>
    )
}
