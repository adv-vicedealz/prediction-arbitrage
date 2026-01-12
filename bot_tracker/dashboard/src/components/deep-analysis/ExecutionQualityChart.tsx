import { useState, useEffect } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import type { ExecutionQualityData, ExecutionQualityTrade } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

interface Props {
  selectedMarket: string | null;
}

export function ExecutionQualityChart({ selectedMarket }: Props) {
  const [data, setData] = useState<ExecutionQualityData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const url = selectedMarket
          ? `${API_BASE}/api/deep-analysis/execution-quality?market=${encodeURIComponent(selectedMarket)}`
          : `${API_BASE}/api/deep-analysis/execution-quality`;
        const res = await fetch(url);
        const result = await res.json();
        setData(result);
      } catch (err) {
        console.error('Failed to fetch execution quality:', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [selectedMarket]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
      </div>
    );
  }

  if (!data || data.summary.matched_trades === 0) {
    return (
      <div className="text-center text-gray-400 py-12">
        No trades with price data available for analysis.
      </div>
    );
  }

  // Prepare scatter data (only trades with execution scores)
  const scatterData = data.trades
    .filter((t: ExecutionQualityTrade) => t.execution_score !== null && t.market_mid !== null)
    .map((t: ExecutionQualityTrade) => ({
      x: t.market_mid,
      y: t.trade_price,
      role: t.role,
      side: t.side,
      outcome: t.outcome,
      shares: t.shares,
      score: t.execution_score,
    }));

  // Split by role for coloring
  const makerTrades = scatterData.filter((t) => t.role === 'maker');
  const takerTrades = scatterData.filter((t) => t.role === 'taker');

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <StatCard
          label="Total Trades"
          value={data.summary.total_trades.toString()}
        />
        <StatCard
          label="With Price Data"
          value={data.summary.matched_trades.toString()}
          subtitle={`${((data.summary.matched_trades / data.summary.total_trades) * 100).toFixed(0)}%`}
        />
        <StatCard
          label="Avg Exec Score"
          value={data.summary.avg_execution_score.toFixed(3)}
          subtitle="0=bid, 1=ask"
          highlight={data.summary.avg_execution_score < 0.5 ? 'green' : 'red'}
        />
        <StatCard
          label="At Bid (<10%)"
          value={`${data.summary.pct_at_bid.toFixed(1)}%`}
          highlight="green"
        />
        <StatCard
          label="At Ask (>90%)"
          value={`${data.summary.pct_at_ask.toFixed(1)}%`}
          highlight="red"
        />
        <StatCard
          label="Mid Range"
          value={`${data.summary.pct_mid.toFixed(1)}%`}
        />
        <StatCard
          label="Maker Avg"
          value={data.summary.maker_avg_score.toFixed(3)}
          highlight={data.summary.maker_avg_score < 0.5 ? 'green' : undefined}
        />
        <StatCard
          label="Taker Avg"
          value={data.summary.taker_avg_score.toFixed(3)}
          highlight={data.summary.taker_avg_score > 0.5 ? 'red' : undefined}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scatter Plot */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">
            Trade Price vs Market Mid (Diagonal = Perfect Execution)
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                type="number"
                dataKey="x"
                name="Market Mid"
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(2)}
                stroke="#9CA3AF"
                fontSize={12}
                label={{ value: 'Market Mid Price', position: 'bottom', fill: '#9CA3AF', fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="Trade Price"
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(2)}
                stroke="#9CA3AF"
                fontSize={12}
                label={{ value: 'Trade Price', angle: -90, position: 'insideLeft', fill: '#9CA3AF', fontSize: 11 }}
              />
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p>Market Mid: {d.x?.toFixed(4)}</p>
                      <p>Trade Price: {d.y?.toFixed(4)}</p>
                      <p>Role: {d.role}</p>
                      <p>Side: {d.side}</p>
                      <p>Score: {d.score?.toFixed(3)}</p>
                    </div>
                  );
                }}
              />
              {/* Diagonal reference line (perfect execution) */}
              <ReferenceLine
                segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
                stroke="#6B7280"
                strokeDasharray="5 5"
              />
              <Scatter name="Maker" data={makerTrades} fill="#10B981" opacity={0.6} />
              <Scatter name="Taker" data={takerTrades} fill="#EF4444" opacity={0.6} />
            </ScatterChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-2 text-xs text-gray-200">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full bg-green-500"></span>
              Maker
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full bg-red-500"></span>
              Taker
            </span>
            <span className="text-gray-300">Below diagonal = better execution</span>
          </div>
        </div>

        {/* Histogram */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">
            Execution Score Distribution (0 = At Bid, 1 = At Ask)
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={data.distribution} margin={{ top: 20, right: 20, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="bucket"
                stroke="#9CA3AF"
                fontSize={10}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis stroke="#9CA3AF" fontSize={12} />
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p>Range: {d.bucket}</p>
                      <p>Count: {d.count}</p>
                    </div>
                  );
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data.distribution.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      entry.start < 0.3
                        ? '#10B981'  // Green for good execution
                        : entry.start >= 0.7
                        ? '#EF4444'  // Red for poor execution
                        : '#6366F1'  // Purple for mid
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-2 text-xs text-gray-200">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-green-500"></span>
              Near Bid (Good)
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-indigo-500"></span>
              Mid Range
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-red-500"></span>
              Near Ask (Poor)
            </span>
          </div>
        </div>
      </div>

      {/* NEW: Execution Quality Over Time */}
      {data.time_analysis && data.time_analysis.by_minute.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">
            Execution Quality by Market Phase
            {data.time_analysis.degradation_pct !== 0 && (
              <span className={`ml-2 text-xs ${data.time_analysis.degradation_pct > 0 ? 'text-red-400' : 'text-green-400'}`}>
                ({data.time_analysis.degradation_pct > 0 ? '+' : ''}{data.time_analysis.degradation_pct.toFixed(1)}% late vs early)
              </span>
            )}
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.time_analysis.by_minute} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="minute"
                stroke="#9CA3AF"
                fontSize={11}
                label={{ value: 'Minute into Market', position: 'bottom', fill: '#9CA3AF', fontSize: 10 }}
              />
              <YAxis
                domain={[0, 1]}
                stroke="#9CA3AF"
                fontSize={11}
                tickFormatter={(v) => v.toFixed(2)}
              />
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p className="font-medium">Minute {d.minute}</p>
                      <p>Avg Score: {d.avg_score?.toFixed(3)}</p>
                      <p className="text-green-400">Maker: {d.maker_avg?.toFixed(3)}</p>
                      <p className="text-red-400">Taker: {d.taker_avg?.toFixed(3)}</p>
                      <p className="text-gray-400">Trades: {d.trade_count}</p>
                    </div>
                  );
                }}
              />
              <ReferenceLine y={0.5} stroke="#6B7280" strokeDasharray="3 3" label={{ value: 'Mid', fill: '#6B7280', fontSize: 10 }} />
              <Line type="monotone" dataKey="avg_score" name="Average" stroke="#06B6D4" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="maker_avg" name="Maker" stroke="#10B981" strokeWidth={1} dot={{ r: 2 }} opacity={0.7} />
              <Line type="monotone" dataKey="taker_avg" name="Taker" stroke="#EF4444" strokeWidth={1} dot={{ r: 2 }} opacity={0.7} />
              <Legend />
            </LineChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-6 mt-2 text-xs">
            <span className="text-gray-400">Early (0-4 min): <span className="text-cyan-400">{data.time_analysis.early_avg?.toFixed(3)}</span></span>
            <span className="text-gray-400">Late (10-14 min): <span className="text-cyan-400">{data.time_analysis.late_avg?.toFixed(3)}</span></span>
          </div>
        </div>
      )}

      {/* NEW: Slippage Cost Analysis */}
      {data.slippage && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">Slippage Impact ($ Cost)</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            <div className={`rounded-lg p-3 text-center ${data.slippage.total_usd < 0 ? 'bg-red-900/30 border border-red-700' : 'bg-green-900/30 border border-green-700'}`}>
              <p className="text-xs text-gray-400">Total Slippage</p>
              <p className={`text-xl font-bold ${data.slippage.total_usd < 0 ? 'text-red-400' : 'text-green-400'}`}>
                ${data.slippage.total_usd.toFixed(2)}
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Maker Slippage</p>
              <p className={`text-lg font-bold ${data.slippage.by_role.maker < 0 ? 'text-red-400' : 'text-green-400'}`}>
                ${data.slippage.by_role.maker.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500">
                {data.slippage.total_usd !== 0 ? ((Math.abs(data.slippage.by_role.maker) / Math.abs(data.slippage.total_usd)) * 100).toFixed(0) : 0}%
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Taker Slippage</p>
              <p className={`text-lg font-bold ${data.slippage.by_role.taker < 0 ? 'text-red-400' : 'text-green-400'}`}>
                ${data.slippage.by_role.taker.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500">
                {data.slippage.total_usd !== 0 ? ((Math.abs(data.slippage.by_role.taker) / Math.abs(data.slippage.total_usd)) * 100).toFixed(0) : 0}%
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Per Trade Avg</p>
              <p className={`text-lg font-bold ${data.slippage.avg_per_trade < 0 ? 'text-red-400' : 'text-green-400'}`}>
                ${data.slippage.avg_per_trade.toFixed(3)}
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">BUY vs SELL</p>
              <p className="text-sm">
                <span className={data.slippage.by_side.buy < 0 ? 'text-red-400' : 'text-green-400'}>${data.slippage.by_side.buy.toFixed(2)}</span>
                {' / '}
                <span className={data.slippage.by_side.sell < 0 ? 'text-red-400' : 'text-green-400'}>${data.slippage.by_side.sell.toFixed(2)}</span>
              </p>
              <p className="text-xs text-gray-500">UP/DOWN: ${data.slippage.by_outcome.up.toFixed(2)} / ${data.slippage.by_outcome.down.toFixed(2)}</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* NEW: Trade Size vs Execution Score */}
        {data.size_analysis && (
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">
              Trade Size Impact on Execution
              <span className={`ml-2 text-xs ${data.size_analysis.correlation > 0 ? 'text-red-400' : 'text-green-400'}`}>
                (r = {data.size_analysis.correlation.toFixed(3)})
              </span>
            </h3>
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-400">Small (&lt;50)</p>
                <p className={`text-lg font-bold ${data.size_analysis.by_bucket.small < 0.5 ? 'text-green-400' : 'text-red-400'}`}>
                  {data.size_analysis.by_bucket.small.toFixed(3)}
                </p>
              </div>
              <div className="bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-400">Medium (50-200)</p>
                <p className={`text-lg font-bold ${data.size_analysis.by_bucket.medium < 0.5 ? 'text-green-400' : 'text-red-400'}`}>
                  {data.size_analysis.by_bucket.medium.toFixed(3)}
                </p>
              </div>
              <div className="bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-400">Large (&gt;200)</p>
                <p className={`text-lg font-bold ${data.size_analysis.by_bucket.large < 0.5 ? 'text-green-400' : 'text-red-400'}`}>
                  {data.size_analysis.by_bucket.large.toFixed(3)}
                </p>
              </div>
            </div>
            <div className="text-xs text-gray-400 text-center">
              {data.size_analysis.correlation > 0.1
                ? 'Larger trades execute worse (positive correlation)'
                : data.size_analysis.correlation < -0.1
                ? 'Larger trades execute better (negative correlation)'
                : 'Trade size has minimal impact on execution quality'}
            </div>
          </div>
        )}

        {/* NEW: Side/Outcome Breakdown Heatmap */}
        {data.breakdown && (
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Execution Score by Trade Type</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400">
                  <th className="text-left py-2"></th>
                  <th className="text-center py-2">BUY</th>
                  <th className="text-center py-2">SELL</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="py-2 text-gray-300 font-medium">UP</td>
                  <td className="py-2 text-center">
                    <span className={`px-3 py-1 rounded ${getScoreColor(data.breakdown.buy_up)}`}>
                      {data.breakdown.buy_up.toFixed(3)}
                    </span>
                  </td>
                  <td className="py-2 text-center">
                    <span className={`px-3 py-1 rounded ${getScoreColor(data.breakdown.sell_up)}`}>
                      {data.breakdown.sell_up.toFixed(3)}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="py-2 text-gray-300 font-medium">DOWN</td>
                  <td className="py-2 text-center">
                    <span className={`px-3 py-1 rounded ${getScoreColor(data.breakdown.buy_down)}`}>
                      {data.breakdown.buy_down.toFixed(3)}
                    </span>
                  </td>
                  <td className="py-2 text-center">
                    <span className={`px-3 py-1 rounded ${getScoreColor(data.breakdown.sell_down)}`}>
                      {data.breakdown.sell_down.toFixed(3)}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div className="mt-3 text-xs text-gray-400 text-center">
              Best: {getBestWorst(data.breakdown, 'best')} | Worst: {getBestWorst(data.breakdown, 'worst')}
            </div>
          </div>
        )}
      </div>

      {/* Interpretation */}
      <div className="bg-gray-900/50 rounded-lg p-4 text-sm text-gray-300">
        <p className="font-medium text-gray-300 mb-2">How to Read This:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Execution Score 0.0</strong> = Trade executed at the bid (best price for buyers)</li>
          <li><strong>Execution Score 1.0</strong> = Trade executed at the ask (worst price for buyers)</li>
          <li><strong>Score &lt; 0.5</strong> = Better than mid-market execution</li>
          <li>Maker orders typically execute near 0 (at bid), taker orders near 1 (at ask)</li>
          <li>Points below the diagonal line = better than expected execution</li>
          <li><strong>Slippage</strong> = Dollar cost of executing worse than mid-market (negative = lost money)</li>
        </ul>
      </div>
    </div>
  );
}

function getScoreColor(score: number): string {
  if (score < 0.3) return 'bg-green-900/50 text-green-400';
  if (score < 0.5) return 'bg-green-900/30 text-green-300';
  if (score < 0.7) return 'bg-yellow-900/30 text-yellow-400';
  return 'bg-red-900/50 text-red-400';
}

function getBestWorst(breakdown: { buy_up: number; buy_down: number; sell_up: number; sell_down: number }, type: 'best' | 'worst'): string {
  const entries = [
    { label: 'BUY UP', value: breakdown.buy_up },
    { label: 'BUY DOWN', value: breakdown.buy_down },
    { label: 'SELL UP', value: breakdown.sell_up },
    { label: 'SELL DOWN', value: breakdown.sell_down },
  ];
  const sorted = entries.sort((a, b) => a.value - b.value);
  const item = type === 'best' ? sorted[0] : sorted[sorted.length - 1];
  return `${item.label} (${item.value.toFixed(3)})`;
}

function StatCard({
  label,
  value,
  subtitle,
  highlight,
}: {
  label: string;
  value: string;
  subtitle?: string;
  highlight?: 'green' | 'red';
}) {
  return (
    <div className="bg-gray-900 rounded-lg p-3">
      <p className="text-xs text-gray-400">{label}</p>
      <p
        className={`text-lg font-bold ${
          highlight === 'green'
            ? 'text-green-400'
            : highlight === 'red'
            ? 'text-red-400'
            : 'text-white'
        }`}
      >
        {value}
      </p>
      {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
    </div>
  );
}
