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
} from 'recharts';
import type { ExecutionQualityData, ExecutionQualityTrade } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
          <div className="flex justify-center gap-4 mt-2 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full bg-green-500"></span>
              Maker
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-full bg-red-500"></span>
              Taker
            </span>
            <span className="text-gray-500">Below diagonal = better execution</span>
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
          <div className="flex justify-center gap-4 mt-2 text-xs">
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

      {/* Interpretation */}
      <div className="bg-gray-900/50 rounded-lg p-4 text-sm text-gray-400">
        <p className="font-medium text-gray-300 mb-2">How to Read This:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Execution Score 0.0</strong> = Trade executed at the bid (best price for buyers)</li>
          <li><strong>Execution Score 1.0</strong> = Trade executed at the ask (worst price for buyers)</li>
          <li><strong>Score &lt; 0.5</strong> = Better than mid-market execution</li>
          <li>Maker orders typically execute near 0 (at bid), taker orders near 1 (at ask)</li>
          <li>Points below the diagonal line = better than expected execution</li>
        </ul>
      </div>
    </div>
  );
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
