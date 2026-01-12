import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { LossPatternData, BoxPlotData } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

export function LossPatternAnalysis() {
  const [data, setData] = useState<LossPatternData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/deep-analysis/loss-patterns`);
        const result = await res.json();
        setData(result);
      } catch (err) {
        console.error('Failed to fetch loss patterns:', err);
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

  if (!data || (data.winners.count === 0 && data.losers.count === 0)) {
    return (
      <div className="text-center text-gray-400 py-12">
        No market data available for loss pattern analysis.
      </div>
    );
  }

  const winRate = (data.winners.count / (data.winners.count + data.losers.count)) * 100;

  // Format metric name for display
  const formatMetricName = (metric: string): string => {
    const names: Record<string, string> = {
      avg_hedge_ratio: 'Hedge Ratio',
      avg_maker_ratio: 'Maker Ratio',
      avg_combined_price: 'Combined Price',
      avg_trades: 'Avg Trades',
      avg_volume: 'Avg Volume',
      avg_edge: 'Avg Edge',
      pct_correct_bias: 'Correct Bias %',
      pct_balanced: 'Balanced %',
    };
    return names[metric] || metric;
  };

  // Format value based on metric type
  const formatValue = (metric: string, value: number): string => {
    if (metric.includes('ratio') || metric.includes('pct')) {
      return `${value.toFixed(1)}%`;
    }
    if (metric === 'avg_combined_price') {
      return `$${value.toFixed(4)}`;
    }
    if (metric === 'avg_volume') {
      return `$${value.toFixed(0)}`;
    }
    return value.toFixed(2);
  };

  return (
    <div className="space-y-6">
      {/* Summary Header */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-green-900/30 border border-green-700 rounded-lg p-4 text-center">
          <p className="text-xs text-green-400">Winning Markets</p>
          <p className="text-3xl font-bold text-green-400">{data.winners.count}</p>
          <p className="text-sm text-green-300">${data.winners.metrics.avg_pnl?.toFixed(2)} avg</p>
        </div>
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-center">
          <p className="text-xs text-red-400">Losing Markets</p>
          <p className="text-3xl font-bold text-red-400">{data.losers.count}</p>
          <p className="text-sm text-red-300">${data.losers.metrics.avg_pnl?.toFixed(2)} avg</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 text-center">
          <p className="text-xs text-gray-400">Win Rate</p>
          <p className="text-3xl font-bold text-white">{winRate.toFixed(1)}%</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 text-center">
          <p className="text-xs text-gray-400">Total Markets</p>
          <p className="text-3xl font-bold text-white">{data.winners.count + data.losers.count}</p>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="bg-gray-900 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-800">
              <th className="text-left px-4 py-3 text-gray-300">Metric</th>
              <th className="text-center px-4 py-3 text-green-400">Winners ({data.winners.count})</th>
              <th className="text-center px-4 py-3 text-red-400">Losers ({data.losers.count})</th>
              <th className="text-center px-4 py-3 text-gray-300">Difference</th>
              <th className="text-center px-4 py-3 text-gray-300">Insight</th>
            </tr>
          </thead>
          <tbody>
            {data.comparison.map((row, idx) => {
              const diff = row.difference || 0;
              const isPositiveBetter = !row.metric.includes('price') && !row.metric.includes('trades');
              const isBetter = isPositiveBetter ? diff > 0 : diff < 0;

              return (
                <tr key={row.metric} className={idx % 2 === 0 ? 'bg-gray-900' : 'bg-gray-800/50'}>
                  <td className="px-4 py-3 text-gray-300 font-medium">
                    {formatMetricName(row.metric)}
                  </td>
                  <td className="px-4 py-3 text-center text-green-400">
                    {formatValue(row.metric, row.winners)}
                  </td>
                  <td className="px-4 py-3 text-center text-red-400">
                    {formatValue(row.metric, row.losers)}
                  </td>
                  <td className={`px-4 py-3 text-center font-medium ${
                    Math.abs(diff) > 5
                      ? isBetter ? 'text-green-400' : 'text-red-400'
                      : 'text-gray-400'
                  }`}>
                    {diff > 0 ? '+' : ''}{formatValue(row.metric, diff)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {Math.abs(diff) > 10 && (
                      <span className={`text-xs px-2 py-1 rounded ${
                        isBetter ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                      }`}>
                        {isBetter ? 'Key Factor' : 'Warning'}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Box Plot Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {data.distributions && Object.entries(data.distributions).map(([key, dist]) => (
          <BoxPlotCard
            key={key}
            title={formatMetricName(`avg_${key}`)}
            winners={dist.winners}
            losers={dist.losers}
            isPercentage={key.includes('ratio')}
          />
        ))}
      </div>

      {/* Key Insights */}
      <div className="bg-gray-900/50 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">Key Loss Pattern Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          {data.comparison.map((c) => {
            const diff = Math.abs(c.difference || 0);
            if (diff < 5) return null;

            const isPositiveBetter = !c.metric.includes('price');
            const winnersBetter = isPositiveBetter
              ? c.winners > c.losers
              : c.winners < c.losers;

            return (
              <div
                key={c.metric}
                className={`p-3 rounded-lg ${
                  winnersBetter
                    ? 'bg-green-900/20 border border-green-800'
                    : 'bg-red-900/20 border border-red-800'
                }`}
              >
                <p className="font-medium text-gray-300">{formatMetricName(c.metric)}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {winnersBetter ? (
                    <>Winners have {diff.toFixed(1)} higher - this correlates with success</>
                  ) : (
                    <>Losers have {diff.toFixed(1)} higher - watch for this pattern</>
                  )}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Interpretation */}
      <div className="bg-gray-900/50 rounded-lg p-4 text-sm text-gray-400">
        <p className="font-medium text-gray-300 mb-2">How to Use This Analysis:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Hedge Ratio</strong>: Higher = more balanced positions, lower loss risk</li>
          <li><strong>Maker Ratio</strong>: Higher = better execution prices, lower costs</li>
          <li><strong>Combined Price</strong>: Lower = more profit potential per complete set</li>
          <li><strong>Correct Bias %</strong>: Higher = better directional prediction</li>
          <li>Large differences between winners and losers indicate actionable patterns</li>
        </ul>
      </div>
    </div>
  );
}

// Box Plot Component
function BoxPlotCard({
  title,
  winners,
  losers,
  isPercentage,
}: {
  title: string;
  winners: BoxPlotData;
  losers: BoxPlotData;
  isPercentage: boolean;
}) {
  const format = (v: number) => (isPercentage ? `${v.toFixed(1)}%` : v.toFixed(2));

  // Create bar chart data for comparison
  const chartData = [
    {
      name: 'Min',
      Winners: winners.min,
      Losers: losers.min,
    },
    {
      name: 'Q1',
      Winners: winners.q1,
      Losers: losers.q1,
    },
    {
      name: 'Median',
      Winners: winners.median,
      Losers: losers.median,
    },
    {
      name: 'Q3',
      Winners: winners.q3,
      Losers: losers.q3,
    },
    {
      name: 'Max',
      Winners: winners.max,
      Losers: losers.max,
    },
  ];

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <h4 className="text-sm font-medium text-gray-300 mb-3">{title} Distribution</h4>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="name" stroke="#9CA3AF" fontSize={10} />
          <YAxis
            tickFormatter={(v) => (isPercentage ? `${v}%` : v.toFixed(2))}
            stroke="#9CA3AF"
            fontSize={10}
          />
          <Tooltip
            content={({ payload, label }) => {
              if (!payload || !payload[0]) return null;
              return (
                <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                  <p className="font-medium">{label}</p>
                  {payload.map((p) => (
                    <p key={p.name} style={{ color: p.color }}>
                      {p.name}: {format(p.value as number)}
                    </p>
                  ))}
                </div>
              );
            }}
          />
          <Bar dataKey="Winners" fill="#10B981" opacity={0.8} />
          <Bar dataKey="Losers" fill="#EF4444" opacity={0.8} />
        </BarChart>
      </ResponsiveContainer>
      <div className="flex justify-between text-xs text-gray-500 mt-2">
        <span>Winners: {format(winners.median)} median</span>
        <span>Losers: {format(losers.median)} median</span>
      </div>
    </div>
  );
}
