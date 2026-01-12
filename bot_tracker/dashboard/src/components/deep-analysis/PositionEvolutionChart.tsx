import { useState, useEffect } from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { PositionEvolutionPoint } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

interface Props {
  marketSlug: string;
}

export function PositionEvolutionChart({ marketSlug }: Props) {
  const [data, setData] = useState<PositionEvolutionPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const res = await fetch(
          `${API_BASE}/api/deep-analysis/market/${encodeURIComponent(marketSlug)}/position-evolution`
        );
        const result = await res.json();
        setData(result);
      } catch (err) {
        console.error('Failed to fetch position evolution:', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [marketSlug]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center text-gray-400 py-12">
        No position data available for this market.
      </div>
    );
  }

  // Add index for x-axis
  const chartData = data.map((d, i) => ({
    ...d,
    tradeNum: i + 1,
  }));

  // Get final position stats
  const finalPosition = data[data.length - 1];
  const minHedge = Math.min(...data.map((d) => d.hedge_ratio));
  const maxHedge = Math.max(...data.map((d) => d.hedge_ratio));

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Final UP</p>
          <p className="text-lg font-bold text-green-400">{finalPosition.up_shares.toFixed(0)}</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Final DOWN</p>
          <p className="text-lg font-bold text-red-400">{finalPosition.down_shares.toFixed(0)}</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Net Position</p>
          <p className={`text-lg font-bold ${finalPosition.net_position >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {finalPosition.net_position.toFixed(0)}
          </p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Final Hedge</p>
          <p className="text-lg font-bold text-cyan-400">{finalPosition.hedge_ratio.toFixed(1)}%</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Total Cost</p>
          <p className="text-lg font-bold text-white">${finalPosition.total_cost.toFixed(2)}</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Total Revenue</p>
          <p className="text-lg font-bold text-white">${finalPosition.total_revenue.toFixed(2)}</p>
        </div>
      </div>

      {/* Position Building Chart */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">Position Building Over Time</h3>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="tradeNum"
              stroke="#9CA3AF"
              fontSize={11}
              label={{ value: 'Trade Number', position: 'bottom', fill: '#9CA3AF', fontSize: 10 }}
            />
            <YAxis
              yAxisId="shares"
              stroke="#9CA3AF"
              fontSize={11}
              label={{ value: 'Shares', angle: -90, position: 'insideLeft', fill: '#9CA3AF', fontSize: 10 }}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload[0]) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                    <p className="font-medium">Trade #{d.tradeNum}</p>
                    <p className="text-green-400">UP: {d.up_shares?.toFixed(0)}</p>
                    <p className="text-red-400">DOWN: {d.down_shares?.toFixed(0)}</p>
                    <p className="text-cyan-400">Hedge: {d.hedge_ratio?.toFixed(1)}%</p>
                    <p className="text-gray-400">Net: {d.net_position?.toFixed(0)}</p>
                  </div>
                );
              }}
            />
            {/* Stacked areas for UP and DOWN */}
            <Area
              yAxisId="shares"
              type="stepAfter"
              dataKey="up_shares"
              stackId="1"
              stroke="#10B981"
              fill="#10B981"
              fillOpacity={0.4}
              name="UP Shares"
            />
            <Area
              yAxisId="shares"
              type="stepAfter"
              dataKey="down_shares"
              stackId="2"
              stroke="#EF4444"
              fill="#EF4444"
              fillOpacity={0.4}
              name="DOWN Shares"
            />
            {/* Net position line */}
            <Line
              yAxisId="shares"
              type="stepAfter"
              dataKey="net_position"
              stroke="#F59E0B"
              strokeWidth={2}
              dot={false}
              name="Net Position"
            />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-6 mt-2 text-xs text-gray-200">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-green-500 opacity-60"></span>
            UP Shares
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-red-500 opacity-60"></span>
            DOWN Shares
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-yellow-500"></span>
            Net Position
          </span>
        </div>
      </div>

      {/* Hedge Ratio Evolution */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">Hedge Ratio Evolution</h3>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="tradeNum"
              stroke="#9CA3AF"
              fontSize={11}
            />
            <YAxis
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              stroke="#9CA3AF"
              fontSize={11}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload[0]) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                    <p>Trade #{d.tradeNum}</p>
                    <p className="text-cyan-400">Hedge: {d.hedge_ratio?.toFixed(1)}%</p>
                  </div>
                );
              }}
            />
            {/* Reference line at 100% */}
            <Line
              type="stepAfter"
              dataKey="hedge_ratio"
              stroke="#06B6D4"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="text-center text-xs text-gray-300 mt-2">
          Min: {minHedge.toFixed(1)}% | Max: {maxHedge.toFixed(1)}%
        </div>
      </div>

      {/* Interpretation */}
      <div className="bg-gray-900/50 rounded-lg p-4 text-sm text-gray-300">
        <p className="font-medium text-gray-300 mb-2">How to Read This:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>UP Shares (green)</strong>: Net long position in UP outcome</li>
          <li><strong>DOWN Shares (red)</strong>: Net long position in DOWN outcome</li>
          <li><strong>Net Position (yellow line)</strong>: UP - DOWN (positive = biased towards UP)</li>
          <li><strong>Hedge Ratio 100%</strong>: Perfectly balanced UP and DOWN positions</li>
          <li><strong>Hedge Ratio 0%</strong>: Completely one-sided position (directional bet)</li>
        </ul>
      </div>
    </div>
  );
}
