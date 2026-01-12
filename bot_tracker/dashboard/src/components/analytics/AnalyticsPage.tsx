import { useState, useEffect, useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell, ScatterChart, Scatter, PieChart, Pie
} from 'recharts';
import { AnalyticsSummary, MarketAnalytics, PnLTimelinePoint } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8080' : '');

type AssetFilter = 'ALL' | 'BTC' | 'ETH';

interface PriceExecutionAnalysis {
  total_trades: number;
  trades_with_price_data: number;
  avg_spread_captured: number;
  pct_at_bid: number;
  pct_at_ask: number;
  pct_between: number;
  avg_combined_cost: number;
  pct_below_dollar: number;
  combined_cost_distribution: { bucket: string; count: number }[];
  markets_analyzed: number;
  order_placement_analysis: { market_slug: string; combined_cost: number; avg_up: number; avg_down: number }[];
}

export function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [markets, setMarkets] = useState<MarketAnalytics[]>([]);
  const [pnlTimeline, setPnlTimeline] = useState<PnLTimelinePoint[]>([]);
  const [priceExecution, setPriceExecution] = useState<PriceExecutionAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [assetFilter, setAssetFilter] = useState<AssetFilter>('ALL');
  const [selectedMarket, setSelectedMarket] = useState<MarketAnalytics | null>(null);

  // Fetch analytics data
  useEffect(() => {
    const fetchAnalytics = async () => {
      setIsLoading(true);
      try {
        const [summaryRes, marketsRes, timelineRes, priceExecRes] = await Promise.all([
          fetch(`${API_BASE}/api/analytics/summary`),
          fetch(`${API_BASE}/api/analytics/markets`),
          fetch(`${API_BASE}/api/analytics/pnl-timeline`),
          fetch(`${API_BASE}/api/analytics/price-execution`)
        ]);

        if (summaryRes.ok) setSummary(await summaryRes.json());
        if (marketsRes.ok) setMarkets(await marketsRes.json());
        if (timelineRes.ok) setPnlTimeline(await timelineRes.json());
        if (priceExecRes.ok) setPriceExecution(await priceExecRes.json());
      } catch (error) {
        console.error('Failed to fetch analytics:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  // Filter markets by asset
  const filteredMarkets = useMemo(() => {
    if (assetFilter === 'ALL') return markets;
    return markets.filter(m => m.asset === assetFilter);
  }, [markets, assetFilter]);

  // Filter timeline by asset
  const filteredTimeline = useMemo(() => {
    if (assetFilter === 'ALL') return pnlTimeline;
    const filtered = pnlTimeline.filter(p => p.asset === assetFilter);
    // Recalculate cumulative P&L for filtered data
    let cumulative = 0;
    return filtered.map(p => {
      cumulative += p.pnl;
      return { ...p, cumulative_pnl: cumulative };
    });
  }, [pnlTimeline, assetFilter]);

  // P&L distribution buckets
  const pnlDistribution = useMemo(() => {
    const buckets: { range: string; count: number; pnl: number; isProfit: boolean }[] = [];
    const step = 50;
    const min = -300;
    const max = 400;

    for (let i = min; i < max; i += step) {
      const rangeMarkets = filteredMarkets.filter(m => m.pnl >= i && m.pnl < i + step);
      if (rangeMarkets.length > 0 || (i >= -100 && i <= 100)) {
        buckets.push({
          range: `$${i}`,
          count: rangeMarkets.length,
          pnl: i + step / 2,
          isProfit: i >= 0
        });
      }
    }
    return buckets;
  }, [filteredMarkets]);

  // Maker ratio vs P&L scatter data
  const makerScatterData = useMemo(() => {
    return filteredMarkets.map(m => ({
      maker_ratio: m.maker_ratio,
      pnl: m.pnl,
      slug: m.slug,
      asset: m.asset
    }));
  }, [filteredMarkets]);

  // Bias analysis
  const biasAnalysis = useMemo(() => {
    const upBias = filteredMarkets.filter(m => m.net_bias === 'UP');
    const downBias = filteredMarkets.filter(m => m.net_bias === 'DOWN');
    const balanced = filteredMarkets.filter(m => m.net_bias === 'BALANCED');
    const correct = filteredMarkets.filter(m => m.correct_bias === true);
    const incorrect = filteredMarkets.filter(m => m.correct_bias === false);

    return {
      upBias: upBias.length,
      downBias: downBias.length,
      balanced: balanced.length,
      upBiasPnl: upBias.reduce((sum, m) => sum + m.pnl, 0),
      downBiasPnl: downBias.reduce((sum, m) => sum + m.pnl, 0),
      balancedPnl: balanced.reduce((sum, m) => sum + m.pnl, 0),
      correctCount: correct.length,
      incorrectCount: incorrect.length,
      correctPnl: correct.reduce((sum, m) => sum + m.pnl, 0),
      incorrectPnl: incorrect.reduce((sum, m) => sum + m.pnl, 0)
    };
  }, [filteredMarkets]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!summary || markets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-gray-400">
        <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p className="text-lg">No resolved markets yet</p>
        <p className="text-sm mt-2">Analytics will appear once markets resolve</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Asset Filter */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Analytics Dashboard</h2>
        <div className="flex gap-2">
          {(['ALL', 'BTC', 'ETH'] as AssetFilter[]).map(asset => (
            <button
              key={asset}
              onClick={() => setAssetFilter(asset)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                assetFilter === asset
                  ? asset === 'BTC' ? 'bg-orange-600 text-white' :
                    asset === 'ETH' ? 'bg-blue-600 text-white' :
                    'bg-gray-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {asset}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <SummaryCard
          label="Total P&L"
          value={`$${summary.total_pnl.toFixed(2)}`}
          color={summary.total_pnl >= 0 ? 'green' : 'red'}
        />
        <SummaryCard
          label="Win Rate"
          value={`${summary.win_rate.toFixed(1)}%`}
          subtext={`${summary.winning_markets}W / ${summary.losing_markets}L`}
          color={summary.win_rate >= 50 ? 'green' : 'yellow'}
        />
        <SummaryCard
          label="Markets"
          value={summary.total_markets.toString()}
          subtext={`${summary.btc_markets} BTC / ${summary.eth_markets} ETH`}
        />
        <SummaryCard
          label="Edge"
          value={`${summary.effective_edge.toFixed(3)}%`}
          subtext="P&L / Volume"
          color={summary.effective_edge > 0 ? 'green' : 'red'}
        />
        <SummaryCard
          label="Profit Factor"
          value={summary.profit_factor >= 999 ? '∞' : `${summary.profit_factor.toFixed(2)}x`}
          subtext="Profit / Loss"
          color={summary.profit_factor > 1 ? 'green' : 'red'}
        />
        <SummaryCard
          label="Maker Ratio"
          value={`${summary.avg_maker_ratio.toFixed(1)}%`}
          subtext="Avg across markets"
          color="blue"
        />
      </div>

      {/* Win/Loss Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard
          label="Avg Win"
          value={`+$${summary.avg_win.toFixed(2)}`}
          color="green"
        />
        <SummaryCard
          label="Avg Loss"
          value={`-$${Math.abs(summary.avg_loss).toFixed(2)}`}
          color="red"
        />
        <SummaryCard
          label="BTC P&L"
          value={`$${summary.btc_pnl.toFixed(2)}`}
          subtext={`${summary.btc_markets} markets`}
          color={summary.btc_pnl >= 0 ? 'green' : 'red'}
        />
        <SummaryCard
          label="ETH P&L"
          value={`$${summary.eth_pnl.toFixed(2)}`}
          subtext={`${summary.eth_markets} markets`}
          color={summary.eth_pnl >= 0 ? 'green' : 'red'}
        />
      </div>

      {/* Charts Row 1: Cumulative P&L and Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cumulative P&L Chart */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-medium text-white mb-4">Cumulative P&L Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={filteredTimeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(v) => v ? new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}
                stroke="#9CA3AF"
                tick={{ fontSize: 11 }}
              />
              <YAxis
                tickFormatter={(v) => `$${v}`}
                stroke="#9CA3AF"
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                labelStyle={{ color: '#9CA3AF' }}
                formatter={(value: number) => [`$${value.toFixed(2)}`, 'Cumulative P&L']}
                labelFormatter={(label) => label ? new Date(label).toLocaleString() : ''}
              />
              <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />
              <Line
                type="monotone"
                dataKey="cumulative_pnl"
                stroke="#10B981"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* P&L Distribution */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-medium text-white mb-4">P&L Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={pnlDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="range" stroke="#9CA3AF" tick={{ fontSize: 10 }} />
              <YAxis stroke="#9CA3AF" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                formatter={(value: number) => [value, 'Markets']}
              />
              <ReferenceLine x="$0" stroke="#6B7280" strokeDasharray="3 3" />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {pnlDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.isProfit ? '#10B981' : '#EF4444'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2: Maker Ratio vs P&L and Bias Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Maker Ratio vs P&L Scatter */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-medium text-white mb-4">Maker Ratio vs P&L</h3>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                type="number"
                dataKey="maker_ratio"
                name="Maker %"
                unit="%"
                domain={[0, 100]}
                stroke="#9CA3AF"
                tick={{ fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="pnl"
                name="P&L"
                unit="$"
                stroke="#9CA3AF"
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                formatter={(value: number, name: string) => [
                  name === 'P&L' ? `$${value.toFixed(2)}` : `${value.toFixed(1)}%`,
                  name
                ]}
              />
              <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />
              <Scatter name="Markets" data={makerScatterData} fill="#8B5CF6">
                {makerScatterData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.pnl >= 0 ? '#10B981' : '#EF4444'}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Position Bias Analysis */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-medium text-white mb-4">Position Bias Analysis</h3>
          <div className="grid grid-cols-2 gap-4">
            {/* Bias Distribution */}
            <div>
              <p className="text-sm text-gray-400 mb-2">Position Bias Distribution</p>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Heavy UP', value: biasAnalysis.upBias, fill: '#10B981' },
                      { name: 'Heavy DOWN', value: biasAnalysis.downBias, fill: '#EF4444' },
                      { name: 'Balanced', value: biasAnalysis.balanced, fill: '#6B7280' }
                    ]}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={30}
                    outerRadius={60}
                    paddingAngle={2}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-4 text-xs mt-2">
                <span className="text-green-400">UP: {biasAnalysis.upBias}</span>
                <span className="text-red-400">DOWN: {biasAnalysis.downBias}</span>
                <span className="text-gray-400">BAL: {biasAnalysis.balanced}</span>
              </div>
            </div>

            {/* Bias Correctness */}
            <div>
              <p className="text-sm text-gray-400 mb-2">Bias Correctness</p>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-green-400">Correct Bias</span>
                    <span className="text-white">{biasAnalysis.correctCount} ({((biasAnalysis.correctCount / filteredMarkets.length) * 100).toFixed(0)}%)</span>
                  </div>
                  <div className="text-xs text-gray-400">
                    P&L: <span className={biasAnalysis.correctPnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                      ${biasAnalysis.correctPnl.toFixed(2)}
                    </span>
                    {' '}(avg: ${biasAnalysis.correctCount > 0 ? (biasAnalysis.correctPnl / biasAnalysis.correctCount).toFixed(2) : '0'})
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-red-400">Wrong Bias</span>
                    <span className="text-white">{biasAnalysis.incorrectCount} ({((biasAnalysis.incorrectCount / filteredMarkets.length) * 100).toFixed(0)}%)</span>
                  </div>
                  <div className="text-xs text-gray-400">
                    P&L: <span className={biasAnalysis.incorrectPnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                      ${biasAnalysis.incorrectPnl.toFixed(2)}
                    </span>
                    {' '}(avg: ${biasAnalysis.incorrectCount > 0 ? (biasAnalysis.incorrectPnl / biasAnalysis.incorrectCount).toFixed(2) : '0'})
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Price Execution Analysis - KEY FEATURE */}
      {priceExecution && priceExecution.trades_with_price_data > 0 && (
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-4">
            <h3 className="text-lg font-medium text-white">Price Execution Analysis</h3>
            <span className="px-2 py-0.5 bg-green-900/50 text-green-400 text-xs rounded">KEY</span>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
            <div className="bg-gray-700/50 rounded p-3">
              <p className="text-gray-400 text-xs">Avg Combined Cost</p>
              <p className={`text-xl font-bold ${priceExecution.avg_combined_cost < 1 ? 'text-green-400' : 'text-red-400'}`}>
                ${priceExecution.avg_combined_cost.toFixed(4)}
              </p>
              <p className="text-gray-500 text-xs">{priceExecution.avg_combined_cost < 1 ? 'Below $1 ' : 'Above $1 '}</p>
            </div>
            <div className="bg-gray-700/50 rounded p-3">
              <p className="text-gray-400 text-xs">% Below $1.00</p>
              <p className={`text-xl font-bold ${priceExecution.pct_below_dollar > 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                {priceExecution.pct_below_dollar.toFixed(1)}%
              </p>
              <p className="text-gray-500 text-xs">of {priceExecution.markets_analyzed} markets</p>
            </div>
            <div className="bg-gray-700/50 rounded p-3">
              <p className="text-gray-400 text-xs">At Bid (Maker)</p>
              <p className="text-xl font-bold text-blue-400">{priceExecution.pct_at_bid.toFixed(1)}%</p>
              <p className="text-gray-500 text-xs">of matched trades</p>
            </div>
            <div className="bg-gray-700/50 rounded p-3">
              <p className="text-gray-400 text-xs">At Ask (Taker)</p>
              <p className="text-xl font-bold text-orange-400">{priceExecution.pct_at_ask.toFixed(1)}%</p>
              <p className="text-gray-500 text-xs">of matched trades</p>
            </div>
            <div className="bg-gray-700/50 rounded p-3">
              <p className="text-gray-400 text-xs">Between Bid/Ask</p>
              <p className="text-xl font-bold text-purple-400">{priceExecution.pct_between.toFixed(1)}%</p>
              <p className="text-gray-500 text-xs">mid-market fills</p>
            </div>
            <div className="bg-gray-700/50 rounded p-3">
              <p className="text-gray-400 text-xs">Trades w/ Price Data</p>
              <p className="text-xl font-bold text-white">{priceExecution.trades_with_price_data}</p>
              <p className="text-gray-500 text-xs">of {priceExecution.total_trades} total</p>
            </div>
          </div>

          {/* Combined Cost Distribution Chart */}
          {priceExecution.combined_cost_distribution.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm text-gray-400 mb-3">Combined Cost Distribution (UP + DOWN)</h4>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={priceExecution.combined_cost_distribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="bucket" stroke="#9CA3AF" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#9CA3AF" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                    formatter={(value: number) => [value, 'Markets']}
                  />
                  <ReferenceLine x="$1.00" stroke="#EF4444" strokeDasharray="3 3" label={{ value: '$1.00', fill: '#EF4444', fontSize: 10 }} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {priceExecution.combined_cost_distribution.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={parseFloat(entry.bucket.replace('$', '')) < 1 ? '#10B981' : '#EF4444'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <p className="text-center text-xs text-gray-500 mt-2">
                Target: Buy UP + DOWN for less than $1.00 combined to guarantee profit
              </p>
            </div>
          )}

          {/* Order Placement Visual */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="h-24 bg-gradient-to-t from-blue-900/30 to-transparent rounded-lg flex items-end justify-center pb-2">
                <div
                  className="bg-blue-500 rounded"
                  style={{ height: `${Math.max(10, priceExecution.pct_at_bid)}%`, width: '60%' }}
                />
              </div>
              <p className="text-sm text-blue-400 mt-2">At Bid</p>
              <p className="text-xs text-gray-400">Maker orders (better prices)</p>
            </div>
            <div className="text-center">
              <div className="h-24 bg-gradient-to-t from-purple-900/30 to-transparent rounded-lg flex items-end justify-center pb-2">
                <div
                  className="bg-purple-500 rounded"
                  style={{ height: `${Math.max(10, priceExecution.pct_between)}%`, width: '60%' }}
                />
              </div>
              <p className="text-sm text-purple-400 mt-2">Between</p>
              <p className="text-xs text-gray-400">Mid-market execution</p>
            </div>
            <div className="text-center">
              <div className="h-24 bg-gradient-to-t from-orange-900/30 to-transparent rounded-lg flex items-end justify-center pb-2">
                <div
                  className="bg-orange-500 rounded"
                  style={{ height: `${Math.max(10, priceExecution.pct_at_ask)}%`, width: '60%' }}
                />
              </div>
              <p className="text-sm text-orange-400 mt-2">At Ask</p>
              <p className="text-xs text-gray-400">Taker orders (worse prices)</p>
            </div>
          </div>
        </div>
      )}

      {/* Markets Table */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-white">Market Details</h3>
          <span className="text-sm text-gray-400">{filteredMarkets.length} markets</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-3 font-medium">Market</th>
                <th className="pb-3 font-medium">Asset</th>
                <th className="pb-3 font-medium">Winner</th>
                <th className="pb-3 font-medium text-right">P&L</th>
                <th className="pb-3 font-medium text-right">Trades</th>
                <th className="pb-3 font-medium text-right">Maker %</th>
                <th className="pb-3 font-medium text-right">Hedge %</th>
                <th className="pb-3 font-medium text-right">Edge %</th>
                <th className="pb-3 font-medium">Bias</th>
              </tr>
            </thead>
            <tbody className="text-gray-300">
              {filteredMarkets.slice(0, 50).map((market) => (
                <tr
                  key={market.slug}
                  className="border-b border-gray-700/50 hover:bg-gray-700/30 cursor-pointer"
                  onClick={() => setSelectedMarket(market)}
                >
                  <td className="py-2 max-w-xs truncate" title={market.slug}>
                    {formatMarketSlug(market.slug)}
                  </td>
                  <td className="py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      market.asset === 'BTC' ? 'bg-orange-900/50 text-orange-400' : 'bg-blue-900/50 text-blue-400'
                    }`}>
                      {market.asset}
                    </span>
                  </td>
                  <td className="py-2">
                    <span className={`${market.winner === 'up' ? 'text-green-400' : 'text-red-400'}`}>
                      {market.winner?.toUpperCase() || '-'}
                    </span>
                  </td>
                  <td className={`py-2 text-right font-medium ${market.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${market.pnl.toFixed(2)}
                  </td>
                  <td className="py-2 text-right">{market.trades}</td>
                  <td className="py-2 text-right">{market.maker_ratio.toFixed(1)}%</td>
                  <td className="py-2 text-right">{market.hedge_ratio.toFixed(1)}%</td>
                  <td className="py-2 text-right">{market.edge.toFixed(2)}%</td>
                  <td className="py-2">
                    <span className={`text-xs ${
                      market.correct_bias === true ? 'text-green-400' :
                      market.correct_bias === false ? 'text-red-400' : 'text-gray-400'
                    }`}>
                      {market.net_bias}
                      {market.correct_bias !== null && (market.correct_bias ? ' ✓' : ' ✗')}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredMarkets.length > 50 && (
            <p className="text-center text-gray-400 text-sm mt-4">
              Showing 50 of {filteredMarkets.length} markets
            </p>
          )}
        </div>
      </div>

      {/* Market Detail Modal */}
      {selectedMarket && (
        <MarketDetailModal market={selectedMarket} onClose={() => setSelectedMarket(null)} />
      )}
    </div>
  );
}

// Summary Card Component
function SummaryCard({
  label,
  value,
  subtext,
  color = 'gray'
}: {
  label: string;
  value: string;
  subtext?: string;
  color?: 'green' | 'red' | 'yellow' | 'blue' | 'gray';
}) {
  const colorClasses = {
    green: 'text-green-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    blue: 'text-blue-400',
    gray: 'text-white'
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <p className="text-gray-400 text-sm">{label}</p>
      <p className={`text-2xl font-bold ${colorClasses[color]}`}>{value}</p>
      {subtext && <p className="text-gray-500 text-xs mt-1">{subtext}</p>}
    </div>
  );
}

// Market Detail Modal
function MarketDetailModal({ market, onClose }: { market: MarketAnalytics; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-medium text-white">{formatMarketSlug(market.slug)}</h3>
            <p className="text-sm text-gray-400">{market.question}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-700/50 rounded p-3">
            <p className="text-gray-400 text-xs">P&L</p>
            <p className={`text-xl font-bold ${market.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${market.pnl.toFixed(2)}
            </p>
          </div>
          <div className="bg-gray-700/50 rounded p-3">
            <p className="text-gray-400 text-xs">Winner</p>
            <p className={`text-xl font-bold ${market.winner === 'up' ? 'text-green-400' : 'text-red-400'}`}>
              {market.winner?.toUpperCase()}
            </p>
          </div>
          <div className="bg-gray-700/50 rounded p-3">
            <p className="text-gray-400 text-xs">Volume</p>
            <p className="text-xl font-bold text-white">${market.volume.toFixed(2)}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div>
            <p className="text-gray-400 text-sm mb-2">Position</p>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-green-400">UP Net:</span>
                <span className="text-white">{market.up_net.toFixed(2)} shares</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-400">DOWN Net:</span>
                <span className="text-white">{market.down_net.toFixed(2)} shares</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Bias:</span>
                <span className={market.correct_bias ? 'text-green-400' : 'text-red-400'}>
                  {market.net_bias} {market.correct_bias ? '(Correct)' : '(Wrong)'}
                </span>
              </div>
            </div>
          </div>
          <div>
            <p className="text-gray-400 text-sm mb-2">Pricing</p>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Avg UP Price:</span>
                <span className="text-white">${market.avg_up_price.toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Avg DOWN Price:</span>
                <span className="text-white">${market.avg_down_price.toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Combined:</span>
                <span className={market.combined_price < 1 ? 'text-green-400' : 'text-red-400'}>
                  ${market.combined_price.toFixed(4)}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3">
          <div className="bg-gray-700/50 rounded p-2 text-center">
            <p className="text-xs text-gray-400">Trades</p>
            <p className="text-lg font-medium text-white">{market.trades}</p>
          </div>
          <div className="bg-gray-700/50 rounded p-2 text-center">
            <p className="text-xs text-gray-400">Maker %</p>
            <p className="text-lg font-medium text-blue-400">{market.maker_ratio.toFixed(1)}%</p>
          </div>
          <div className="bg-gray-700/50 rounded p-2 text-center">
            <p className="text-xs text-gray-400">Hedge %</p>
            <p className="text-lg font-medium text-purple-400">{market.hedge_ratio.toFixed(1)}%</p>
          </div>
          <div className="bg-gray-700/50 rounded p-2 text-center">
            <p className="text-xs text-gray-400">Edge</p>
            <p className={`text-lg font-medium ${market.edge > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {market.edge.toFixed(2)}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper to format market slug
function formatMarketSlug(slug: string): string {
  // Extract date from slug like "btc-updown-15m-1768084200"
  const match = slug.match(/(\w+)-updown-15m-(\d+)/);
  if (match) {
    const asset = match[1].toUpperCase();
    const timestamp = parseInt(match[2]);
    const date = new Date(timestamp * 1000);
    return `${asset} ${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} ${date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
  }
  return slug;
}
