import { useState, useEffect } from 'react';
import type { RiskMetrics } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

export function RiskMetricsCard() {
  const [data, setData] = useState<RiskMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/deep-analysis/risk-metrics`);
        const result = await res.json();
        setData(result);
      } catch (err) {
        console.error('Failed to fetch risk metrics:', err);
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

  if (!data || data.total_markets === 0) {
    return (
      <div className="text-center text-gray-400 py-12">
        No market data available for risk analysis.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-900 rounded-lg p-4 text-center">
          <p className="text-xs text-gray-400">Total P&L</p>
          <p className={`text-3xl font-bold ${data.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${data.total_pnl.toFixed(2)}
          </p>
          <p className="text-xs text-gray-500">{data.total_markets} markets</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 text-center">
          <p className="text-xs text-gray-400">Mean P&L / Market</p>
          <p className={`text-3xl font-bold ${data.mean_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${data.mean_pnl.toFixed(2)}
          </p>
          <p className="text-xs text-gray-500">StdDev: ${data.pnl_std.toFixed(2)}</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 text-center">
          <p className="text-xs text-gray-400">Win Rate</p>
          <p className={`text-3xl font-bold ${data.win_rate >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
            {data.win_rate.toFixed(1)}%
          </p>
          <p className="text-xs text-gray-500">
            95% CI: [{data.win_rate_ci_low.toFixed(1)}% - {data.win_rate_ci_high.toFixed(1)}%]
          </p>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 text-center">
          <p className="text-xs text-gray-400">Current Streak</p>
          <p className={`text-3xl font-bold ${
            data.current_streak_type === 'win' ? 'text-green-400' : 'text-red-400'
          }`}>
            {data.current_streak} {data.current_streak_type === 'win' ? 'W' : 'L'}
          </p>
          <p className="text-xs text-gray-500">
            Max: {data.win_streak}W / {data.loss_streak}L
          </p>
        </div>
      </div>

      {/* Main Risk Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Sharpe Ratio"
          value={data.sharpe.toFixed(3)}
          description="Risk-adjusted return (mean/std)"
          color={data.sharpe > 0.5 ? 'green' : data.sharpe > 0 ? 'yellow' : 'red'}
          benchmark="Good > 0.5"
        />
        <MetricCard
          title="Max Drawdown"
          value={`$${data.max_drawdown.toFixed(2)}`}
          description="Largest peak-to-trough decline"
          color={data.max_drawdown < 100 ? 'green' : data.max_drawdown < 500 ? 'yellow' : 'red'}
          benchmark="Lower is better"
        />
        <MetricCard
          title="Calmar Ratio"
          value={data.calmar === 999 ? '---' : data.calmar.toFixed(2)}
          description="Total P&L / Max Drawdown"
          color={data.calmar > 3 ? 'green' : data.calmar > 1 ? 'yellow' : 'red'}
          benchmark="Good > 3"
        />
        <MetricCard
          title="Value at Risk (5%)"
          value={`$${data.var_5pct.toFixed(2)}`}
          description="5th percentile loss"
          color={data.var_5pct > -50 ? 'green' : data.var_5pct > -100 ? 'yellow' : 'red'}
          benchmark="Worst expected 5%"
        />
      </div>

      {/* Win Rate Confidence Interval Visualization */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">Win Rate with 95% Confidence Interval</h3>
        <div className="relative h-8 bg-gray-800 rounded-full overflow-hidden">
          {/* Background reference lines */}
          <div className="absolute inset-y-0 left-1/2 w-px bg-gray-600" />

          {/* CI range */}
          <div
            className="absolute inset-y-0 bg-cyan-900/50"
            style={{
              left: `${data.win_rate_ci_low}%`,
              width: `${data.win_rate_ci_high - data.win_rate_ci_low}%`,
            }}
          />

          {/* Win rate marker */}
          <div
            className="absolute inset-y-0 w-1 bg-cyan-400"
            style={{ left: `${data.win_rate}%` }}
          />

          {/* 50% reference */}
          <div className="absolute inset-y-0 left-1/2 flex items-center">
            <span className="text-xs text-gray-500 ml-1">50%</span>
          </div>
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-500">
          <span>0%</span>
          <span className="text-cyan-400">
            Win Rate: {data.win_rate.toFixed(1)}% (CI: {data.win_rate_ci_low.toFixed(1)}% - {data.win_rate_ci_high.toFixed(1)}%)
          </span>
          <span>100%</span>
        </div>
      </div>

      {/* Streak Analysis */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-900 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Longest Win Streak</h4>
          <div className="flex items-center gap-2">
            <div className="flex gap-0.5">
              {Array.from({ length: Math.min(data.win_streak, 10) }).map((_, i) => (
                <div key={i} className="w-3 h-6 bg-green-500 rounded" />
              ))}
            </div>
            <span className="text-xl font-bold text-green-400">{data.win_streak}</span>
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Longest Loss Streak</h4>
          <div className="flex items-center gap-2">
            <div className="flex gap-0.5">
              {Array.from({ length: Math.min(data.loss_streak, 10) }).map((_, i) => (
                <div key={i} className="w-3 h-6 bg-red-500 rounded" />
              ))}
            </div>
            <span className="text-xl font-bold text-red-400">{data.loss_streak}</span>
          </div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Current Streak</h4>
          <div className="flex items-center gap-2">
            <div className="flex gap-0.5">
              {Array.from({ length: Math.min(data.current_streak, 10) }).map((_, i) => (
                <div
                  key={i}
                  className={`w-3 h-6 rounded ${
                    data.current_streak_type === 'win' ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
              ))}
            </div>
            <span className={`text-xl font-bold ${
              data.current_streak_type === 'win' ? 'text-green-400' : 'text-red-400'
            }`}>
              {data.current_streak} {data.current_streak_type === 'win' ? 'Wins' : 'Losses'}
            </span>
          </div>
        </div>
      </div>

      {/* Interpretation */}
      <div className="bg-gray-900/50 rounded-lg p-4 text-sm text-gray-400">
        <p className="font-medium text-gray-300 mb-2">Understanding These Metrics:</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p><strong>Sharpe Ratio</strong>: Measures return per unit of risk. Higher = better risk-adjusted performance.</p>
            <p className="mt-2"><strong>Max Drawdown</strong>: The largest cumulative loss from a peak. Indicates worst-case scenario.</p>
          </div>
          <div>
            <p><strong>Calmar Ratio</strong>: Total return divided by max drawdown. Higher = more return per unit of pain.</p>
            <p className="mt-2"><strong>VaR 5%</strong>: In 5% of cases, expect to lose at least this much on a market.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  description,
  color,
  benchmark,
}: {
  title: string;
  value: string;
  description: string;
  color: 'green' | 'yellow' | 'red';
  benchmark: string;
}) {
  const colorClasses = {
    green: 'text-green-400 border-green-700 bg-green-900/20',
    yellow: 'text-yellow-400 border-yellow-700 bg-yellow-900/20',
    red: 'text-red-400 border-red-700 bg-red-900/20',
  };

  return (
    <div className={`rounded-lg p-4 border ${colorClasses[color]}`}>
      <h4 className="text-sm font-medium text-gray-300">{title}</h4>
      <p className={`text-2xl font-bold mt-1 ${colorClasses[color].split(' ')[0]}`}>{value}</p>
      <p className="text-xs text-gray-500 mt-1">{description}</p>
      <p className="text-xs text-gray-600 mt-1">{benchmark}</p>
    </div>
  );
}
