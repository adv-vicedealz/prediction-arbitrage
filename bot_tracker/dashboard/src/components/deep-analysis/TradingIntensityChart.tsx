import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import type { TradingIntensityData } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

export function TradingIntensityChart() {
  const [data, setData] = useState<TradingIntensityData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/deep-analysis/intensity-patterns`);
        const result = await res.json();
        setData(result);
      } catch (err) {
        console.error('Failed to fetch intensity patterns:', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
      </div>
    );
  }

  if (!data || data.total_trades === 0) {
    return (
      <div className="text-center text-gray-400 py-12">
        No trading intensity data available.
      </div>
    );
  }

  // Find peak minutes
  const sortedByCount = [...data.by_minute].sort((a, b) => b.trade_count - a.trade_count);
  const peakMinute = sortedByCount[0]?.minute;
  const totalVolume = data.by_minute.reduce((sum, m) => sum + m.volume, 0);

  // Phase pie chart data
  const phaseData = [
    { name: 'Early (0-33%)', value: data.by_phase.early, color: '#10B981' },
    { name: 'Middle (33-67%)', value: data.by_phase.middle, color: '#6366F1' },
    { name: 'Late (67-100%)', value: data.by_phase.late, color: '#EF4444' },
  ].filter((p) => p.value > 0);

  // Color gradient for minutes (darker = more trades)
  const maxCount = Math.max(...data.by_minute.map((m) => m.trade_count));

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Total Trades</p>
          <p className="text-lg font-bold text-white">{data.total_trades.toLocaleString()}</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Peak Minute</p>
          <p className="text-lg font-bold text-cyan-400">Min {peakMinute}</p>
          <p className="text-xs text-gray-500">{sortedByCount[0]?.trade_count} trades</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Early Phase</p>
          <p className="text-lg font-bold text-green-400">{data.by_phase.early}</p>
          <p className="text-xs text-gray-500">{((data.by_phase.early / data.total_trades) * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Middle Phase</p>
          <p className="text-lg font-bold text-indigo-400">{data.by_phase.middle}</p>
          <p className="text-xs text-gray-500">{((data.by_phase.middle / data.total_trades) * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Late Phase</p>
          <p className="text-lg font-bold text-red-400">{data.by_phase.late}</p>
          <p className="text-xs text-gray-500">{((data.by_phase.late / data.total_trades) * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <p className="text-xs text-gray-400">Total Volume</p>
          <p className="text-lg font-bold text-white">${totalVolume.toLocaleString()}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trade Count by Minute */}
        <div className="lg:col-span-2 bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">Trade Count by Minute (0-14)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.by_minute} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="minute"
                stroke="#9CA3AF"
                fontSize={11}
                label={{ value: 'Minute into Market', position: 'bottom', fill: '#9CA3AF', fontSize: 10 }}
              />
              <YAxis stroke="#9CA3AF" fontSize={11} />
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p className="font-medium">Minute {d.minute}</p>
                      <p>Trades: {d.trade_count}</p>
                      <p>Volume: ${d.volume?.toLocaleString()}</p>
                    </div>
                  );
                }}
              />
              <Bar dataKey="trade_count" radius={[4, 4, 0, 0]}>
                {data.by_minute.map((entry, index) => {
                  const intensity = entry.trade_count / maxCount;
                  let color = '#6366F1';
                  if (entry.minute < 5) color = `rgba(16, 185, 129, ${0.4 + intensity * 0.6})`; // Green for early
                  else if (entry.minute >= 10) color = `rgba(239, 68, 68, ${0.4 + intensity * 0.6})`; // Red for late
                  else color = `rgba(99, 102, 241, ${0.4 + intensity * 0.6})`; // Purple for middle
                  return <Cell key={`cell-${index}`} fill={color} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-2 text-xs text-gray-200">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-green-500"></span>
              Early (0-4)
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-indigo-500"></span>
              Middle (5-9)
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-red-500"></span>
              Late (10-14)
            </span>
          </div>
        </div>

        {/* Phase Distribution Pie */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">Phase Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={phaseData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                dataKey="value"
                label={({ name, percent }) => `${name.split(' ')[0]} ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {phaseData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p className="font-medium">{d.name}</p>
                      <p>{d.value} trades</p>
                      <p>{((d.value / data.total_trades) * 100).toFixed(1)}%</p>
                    </div>
                  );
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Volume by Minute */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">Volume by Minute</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data.by_minute} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="minute" stroke="#9CA3AF" fontSize={11} />
            <YAxis
              tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
              stroke="#9CA3AF"
              fontSize={11}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload[0]) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                    <p>Minute {d.minute}</p>
                    <p>Volume: ${d.volume?.toLocaleString()}</p>
                  </div>
                );
              }}
            />
            <Bar dataKey="volume" fill="#F59E0B" radius={[4, 4, 0, 0]} opacity={0.8} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Interpretation */}
      <div className="bg-gray-900/50 rounded-lg p-4 text-sm text-gray-300">
        <p className="font-medium text-gray-300 mb-2">What This Tells Us:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Peak minute</strong>: Most active trading period - may indicate optimal entry timing</li>
          <li><strong>Early phase heavy</strong>: Aggressive position building at market open</li>
          <li><strong>Late phase heavy</strong>: Waiting for better prices or last-minute hedging</li>
          <li><strong>Even distribution</strong>: Consistent market-making throughout duration</li>
        </ul>
      </div>
    </div>
  );
}
