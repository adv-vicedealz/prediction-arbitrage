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
  AreaChart,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
} from 'recharts';
import type { PositionEvolutionData, PositionEvolutionPoint } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

interface Props {
  marketSlug: string;
}

export function PositionEvolutionChart({ marketSlug }: Props) {
  const [data, setData] = useState<PositionEvolutionData | null>(null);
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

  if (!data || !data.points || data.points.length === 0) {
    return (
      <div className="text-center text-gray-400 py-12">
        No position data available for this market.
      </div>
    );
  }

  const points = data.points;

  // Add index for x-axis
  const chartData = points.map((d: PositionEvolutionPoint, i: number) => ({
    ...d,
    tradeNum: i + 1,
  }));

  // Get final position stats
  const finalPosition = points[points.length - 1];
  const minHedge = Math.min(...points.map((d: PositionEvolutionPoint) => d.hedge_ratio));
  const maxHedge = Math.max(...points.map((d: PositionEvolutionPoint) => d.hedge_ratio));

  // Filter price correlation timeline to 0-15 minutes only
  const filteredTimeline = data.price_correlation?.timeline
    ? (() => {
        const timeline = data.price_correlation.timeline;
        if (timeline.length === 0) return [];
        const startTs = timeline[0]?.timestamp || 0;
        const endTs = startTs + 15 * 60; // 15 minutes
        return timeline
          .filter((p) => p.timestamp >= startTs && p.timestamp <= endTs)
          .map((p, i) => ({
            ...p,
            minuteIntoMarket: (p.timestamp - startTs) / 60,
            index: i,
          }));
      })()
    : [];

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

      {/* Position vs Price Correlation */}
      {data.price_correlation && filteredTimeline.length > 0 && (
        <>
          {/* Correlation Stats Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className={`rounded-lg p-3 text-center ${Math.abs(data.price_correlation.up_shares_vs_up_price) < 0.3 ? 'bg-gray-800' : data.price_correlation.up_shares_vs_up_price > 0 ? 'bg-yellow-900/30 border border-yellow-700' : 'bg-green-900/30 border border-green-700'}`}>
              <p className="text-xs text-gray-400">UP Position vs UP Price</p>
              <p className={`text-xl font-bold ${data.price_correlation.up_shares_vs_up_price > 0.3 ? 'text-yellow-400' : data.price_correlation.up_shares_vs_up_price < -0.3 ? 'text-green-400' : 'text-gray-400'}`}>
                r = {data.price_correlation.up_shares_vs_up_price.toFixed(3)}
              </p>
              <p className="text-xs text-gray-500">
                {data.price_correlation.up_shares_vs_up_price > 0.3 ? 'Chasing (buys on rise)' :
                 data.price_correlation.up_shares_vs_up_price < -0.3 ? 'Contrarian (buys dips)' : 'Neutral'}
              </p>
            </div>
            <div className={`rounded-lg p-3 text-center ${Math.abs(data.price_correlation.down_shares_vs_down_price) < 0.3 ? 'bg-gray-800' : data.price_correlation.down_shares_vs_down_price > 0 ? 'bg-yellow-900/30 border border-yellow-700' : 'bg-green-900/30 border border-green-700'}`}>
              <p className="text-xs text-gray-400">DOWN Position vs DOWN Price</p>
              <p className={`text-xl font-bold ${data.price_correlation.down_shares_vs_down_price > 0.3 ? 'text-yellow-400' : data.price_correlation.down_shares_vs_down_price < -0.3 ? 'text-green-400' : 'text-gray-400'}`}>
                r = {data.price_correlation.down_shares_vs_down_price.toFixed(3)}
              </p>
              <p className="text-xs text-gray-500">
                {data.price_correlation.down_shares_vs_down_price > 0.3 ? 'Chasing (buys on rise)' :
                 data.price_correlation.down_shares_vs_down_price < -0.3 ? 'Contrarian (buys dips)' : 'Neutral'}
              </p>
            </div>
            <div className={`rounded-lg p-3 text-center ${data.price_correlation.pct_bought_below_avg_up >= 50 ? 'bg-green-900/30 border border-green-700' : 'bg-gray-800'}`}>
              <p className="text-xs text-gray-400">"Bought the Dip" UP</p>
              <p className={`text-xl font-bold ${data.price_correlation.pct_bought_below_avg_up >= 50 ? 'text-green-400' : 'text-gray-400'}`}>
                {data.price_correlation.pct_bought_below_avg_up.toFixed(0)}%
              </p>
              <p className="text-xs text-gray-500">below avg ${data.price_correlation.avg_up_price.toFixed(3)}</p>
            </div>
            <div className={`rounded-lg p-3 text-center ${data.price_correlation.pct_bought_below_avg_down >= 50 ? 'bg-green-900/30 border border-green-700' : 'bg-gray-800'}`}>
              <p className="text-xs text-gray-400">"Bought the Dip" DOWN</p>
              <p className={`text-xl font-bold ${data.price_correlation.pct_bought_below_avg_down >= 50 ? 'text-green-400' : 'text-gray-400'}`}>
                {data.price_correlation.pct_bought_below_avg_down.toFixed(0)}%
              </p>
              <p className="text-xs text-gray-500">below avg ${data.price_correlation.avg_down_price.toFixed(3)}</p>
            </div>
          </div>

          {/* UP Position vs UP Price Chart (0-15 minutes) */}
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">
              UP Position vs UP Price (0-15 min)
              <span className="ml-2 text-xs text-gray-400">
                r = {data.price_correlation.up_shares_vs_up_price.toFixed(3)}
              </span>
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <ComposedChart
                data={filteredTimeline}
                margin={{ top: 10, right: 50, left: 0, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="minuteIntoMarket"
                  type="number"
                  domain={[0, 15]}
                  stroke="#9CA3AF"
                  fontSize={10}
                  tickFormatter={(v) => `${Math.floor(v)}m`}
                />
                <YAxis
                  yAxisId="shares"
                  stroke="#10B981"
                  fontSize={10}
                  label={{ value: 'Shares', angle: -90, position: 'insideLeft', fill: '#10B981', fontSize: 9 }}
                />
                <YAxis
                  yAxisId="price"
                  orientation="right"
                  stroke="#F59E0B"
                  fontSize={10}
                  domain={['auto', 'auto']}
                  tickFormatter={(v) => v.toFixed(2)}
                  label={{ value: 'Price', angle: 90, position: 'insideRight', fill: '#F59E0B', fontSize: 9 }}
                />
                <Tooltip
                  content={({ payload }) => {
                    if (!payload || !payload[0]) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                        <p className="font-medium">{d.minuteIntoMarket?.toFixed(1)}m</p>
                        <p className="text-green-400">UP Shares: {d.up_shares?.toFixed(0)}</p>
                        <p className="text-yellow-400">UP Price: ${d.up_price?.toFixed(4)}</p>
                      </div>
                    );
                  }}
                />
                <Area
                  yAxisId="shares"
                  type="monotone"
                  dataKey="up_shares"
                  stroke="#10B981"
                  fill="#10B981"
                  fillOpacity={0.3}
                />
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="up_price"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              </ComposedChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-6 mt-2 text-xs text-gray-200">
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500/50"></span> UP Position</span>
              <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-yellow-500"></span> UP Price</span>
            </div>
          </div>

          {/* DOWN Position vs DOWN Price Chart (0-15 minutes) */}
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">
              DOWN Position vs DOWN Price (0-15 min)
              <span className="ml-2 text-xs text-gray-400">
                r = {data.price_correlation.down_shares_vs_down_price.toFixed(3)}
              </span>
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <ComposedChart
                data={filteredTimeline}
                margin={{ top: 10, right: 50, left: 0, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="minuteIntoMarket"
                  type="number"
                  domain={[0, 15]}
                  stroke="#9CA3AF"
                  fontSize={10}
                  tickFormatter={(v) => `${Math.floor(v)}m`}
                />
                <YAxis
                  yAxisId="shares"
                  stroke="#EF4444"
                  fontSize={10}
                  label={{ value: 'Shares', angle: -90, position: 'insideLeft', fill: '#EF4444', fontSize: 9 }}
                />
                <YAxis
                  yAxisId="price"
                  orientation="right"
                  stroke="#F59E0B"
                  fontSize={10}
                  domain={['auto', 'auto']}
                  tickFormatter={(v) => v.toFixed(2)}
                  label={{ value: 'Price', angle: 90, position: 'insideRight', fill: '#F59E0B', fontSize: 9 }}
                />
                <Tooltip
                  content={({ payload }) => {
                    if (!payload || !payload[0]) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                        <p className="font-medium">{d.minuteIntoMarket?.toFixed(1)}m</p>
                        <p className="text-red-400">DOWN Shares: {d.down_shares?.toFixed(0)}</p>
                        <p className="text-yellow-400">DOWN Price: ${d.down_price?.toFixed(4)}</p>
                      </div>
                    );
                  }}
                />
                <Area
                  yAxisId="shares"
                  type="monotone"
                  dataKey="down_shares"
                  stroke="#EF4444"
                  fill="#EF4444"
                  fillOpacity={0.3}
                />
                <Line
                  yAxisId="price"
                  type="monotone"
                  dataKey="down_price"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              </ComposedChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-6 mt-2 text-xs text-gray-200">
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500/50"></span> DOWN Position</span>
              <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-yellow-500"></span> DOWN Price</span>
            </div>
          </div>

          {/* Timing Analysis Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className={`rounded-lg p-3 text-center ${data.price_correlation.pct_sold_above_avg_up >= 50 ? 'bg-green-900/30 border border-green-700' : 'bg-gray-800'}`}>
              <p className="text-xs text-gray-400">"Sold the Top" UP</p>
              <p className={`text-xl font-bold ${data.price_correlation.pct_sold_above_avg_up >= 50 ? 'text-green-400' : 'text-gray-400'}`}>
                {data.price_correlation.pct_sold_above_avg_up.toFixed(0)}%
              </p>
              <p className="text-xs text-gray-500">sold above avg</p>
            </div>
            <div className={`rounded-lg p-3 text-center ${data.price_correlation.pct_sold_above_avg_down >= 50 ? 'bg-green-900/30 border border-green-700' : 'bg-gray-800'}`}>
              <p className="text-xs text-gray-400">"Sold the Top" DOWN</p>
              <p className={`text-xl font-bold ${data.price_correlation.pct_sold_above_avg_down >= 50 ? 'text-green-400' : 'text-gray-400'}`}>
                {data.price_correlation.pct_sold_above_avg_down.toFixed(0)}%
              </p>
              <p className="text-xs text-gray-500">sold above avg</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Avg UP Price</p>
              <p className="text-xl font-bold text-green-400">${data.price_correlation.avg_up_price.toFixed(4)}</p>
              <p className="text-xs text-gray-500">market avg</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Avg DOWN Price</p>
              <p className="text-xl font-bold text-red-400">${data.price_correlation.avg_down_price.toFixed(4)}</p>
              <p className="text-xs text-gray-500">market avg</p>
            </div>
          </div>
        </>
      )}

      {/* Hedge Ratio + Cost Basis in ONE ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Hedge Ratio Evolution */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-2">
            Hedge Ratio Evolution
            <span className="ml-2 text-xs text-gray-400">
              Min: {minHedge.toFixed(1)}% | Max: {maxHedge.toFixed(1)}%
            </span>
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="tradeNum" stroke="#9CA3AF" fontSize={10} />
              <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} stroke="#9CA3AF" fontSize={10} />
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
              <ReferenceLine y={100} stroke="#6B7280" strokeDasharray="3 3" />
              <Line type="stepAfter" dataKey="hedge_ratio" stroke="#06B6D4" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Cost Basis Evolution */}
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-2">
            Cost Basis (VWAP)
            {data.summary && (
              <span className="ml-2 text-xs text-gray-400">
                Final: ${data.summary.final_combined_cost.toFixed(4)}
              </span>
            )}
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="tradeNum" stroke="#9CA3AF" fontSize={10} />
              <YAxis domain={[0, 1]} tickFormatter={(v) => `$${v.toFixed(2)}`} stroke="#9CA3AF" fontSize={10} />
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p className="font-medium">Trade #{d.tradeNum}</p>
                      <p className="text-green-400">UP: ${d.up_avg_cost?.toFixed(4)}</p>
                      <p className="text-red-400">DOWN: ${d.down_avg_cost?.toFixed(4)}</p>
                      <p className="text-cyan-400">Combined: ${d.combined_cost?.toFixed(4)}</p>
                    </div>
                  );
                }}
              />
              <ReferenceLine y={1.0} stroke="#6B7280" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="up_avg_cost" stroke="#10B981" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="down_avg_cost" stroke="#EF4444" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="combined_cost" stroke="#06B6D4" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-1 text-xs text-gray-400">
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-green-500"></span> UP</span>
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-red-500"></span> DOWN</span>
            <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-cyan-500"></span> Combined</span>
          </div>
        </div>
      </div>

      {/* P&L Evolution */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">
          P&L Evolution
          {data.summary && data.summary.final_pnl !== null && (
            <span className={`ml-2 text-xs ${data.summary.final_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              Final: ${data.summary.final_pnl.toFixed(2)}
            </span>
          )}
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="tradeNum" stroke="#9CA3AF" fontSize={11} />
            <YAxis stroke="#9CA3AF" fontSize={11} tickFormatter={(v) => `$${v.toFixed(0)}`} />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload[0]) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                    <p className="font-medium">Trade #{d.tradeNum}</p>
                    <p className="text-green-400">Realized: ${d.realized_pnl?.toFixed(2)}</p>
                    <p className="text-yellow-400">Unrealized: ${d.unrealized_pnl?.toFixed(2)}</p>
                    <p className={`font-bold ${d.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      Total: ${d.total_pnl?.toFixed(2)}
                    </p>
                  </div>
                );
              }}
            />
            <ReferenceLine y={0} stroke="#6B7280" strokeDasharray="3 3" />
            <Area type="monotone" dataKey="realized_pnl" stackId="1" stroke="#10B981" fill="#10B981" fillOpacity={0.4} />
            <Area type="monotone" dataKey="unrealized_pnl" stackId="1" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.4} />
          </AreaChart>
        </ResponsiveContainer>
        <div className="flex justify-center gap-6 mt-2 text-xs text-gray-200">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500/60"></span> Realized</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-500/60"></span> Unrealized</span>
        </div>
      </div>

      {/* Entry Quality + Position Summary in ONE ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Entry Quality Analysis */}
        {data.entry_quality && (
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Entry Quality Analysis</h3>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div className={`rounded-lg p-3 text-center ${data.entry_quality.avg_entry_edge > 0 ? 'bg-green-900/30 border border-green-700' : 'bg-red-900/30 border border-red-700'}`}>
                <p className="text-xs text-gray-400">Avg Entry Edge</p>
                <p className={`text-xl font-bold ${data.entry_quality.avg_entry_edge > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {data.entry_quality.avg_entry_edge > 0 ? '+' : ''}{data.entry_quality.avg_entry_edge.toFixed(2)}¢
                </p>
                <p className="text-xs text-gray-500">vs mid price</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-400">% Better Than Mid</p>
                <p className={`text-xl font-bold ${data.entry_quality.pct_positive_edge >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                  {data.entry_quality.pct_positive_edge.toFixed(1)}%
                </p>
                <p className="text-xs text-gray-500">of {data.entry_quality.trade_count} trades</p>
              </div>
            </div>
            <div className={`rounded-lg p-3 text-center ${data.entry_quality.total_edge_value > 0 ? 'bg-green-900/20' : 'bg-red-900/20'}`}>
              <p className="text-xs text-gray-400">Total Edge Value</p>
              <p className={`text-2xl font-bold ${data.entry_quality.total_edge_value > 0 ? 'text-green-400' : 'text-red-400'}`}>
                ${data.entry_quality.total_edge_value.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500">
                {data.entry_quality.total_edge_value > 0 ? 'Saved from good entries' : 'Lost from poor entries'}
              </p>
            </div>
          </div>
        )}

        {/* Position Summary */}
        {data.summary && (
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Position Summary</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-400">UP VWAP</p>
                <p className="text-lg font-bold text-green-400">${data.summary.final_up_vwap.toFixed(4)}</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-3 text-center">
                <p className="text-xs text-gray-400">DOWN VWAP</p>
                <p className="text-lg font-bold text-red-400">${data.summary.final_down_vwap.toFixed(4)}</p>
              </div>
              <div className={`rounded-lg p-3 text-center ${data.summary.final_combined_cost < 1.0 ? 'bg-green-900/30 border border-green-700' : 'bg-red-900/30 border border-red-700'}`}>
                <p className="text-xs text-gray-400">Combined Cost</p>
                <p className={`text-lg font-bold ${data.summary.final_combined_cost < 1.0 ? 'text-green-400' : 'text-red-400'}`}>
                  ${data.summary.final_combined_cost.toFixed(4)}
                </p>
              </div>
              {data.summary.final_pnl !== null ? (
                <div className={`rounded-lg p-3 text-center ${data.summary.final_pnl >= 0 ? 'bg-green-900/30 border border-green-700' : 'bg-red-900/30 border border-red-700'}`}>
                  <p className="text-xs text-gray-400">Final P&L</p>
                  <p className={`text-lg font-bold ${data.summary.final_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${data.summary.final_pnl.toFixed(2)}
                  </p>
                </div>
              ) : (
                <div className="bg-gray-800 rounded-lg p-3 text-center">
                  <p className="text-xs text-gray-400">Winner</p>
                  <p className={`text-lg font-bold ${data.summary.winning_outcome === 'Up' ? 'text-green-400' : data.summary.winning_outcome === 'Down' ? 'text-red-400' : 'text-gray-400'}`}>
                    {data.summary.winning_outcome || 'Pending'}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Position Sizing Pattern - EXPANDED */}
      {data.sizing && data.sizing.buy_sizes.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">
            Position Sizing Pattern
            <span className={`ml-2 text-xs px-2 py-0.5 rounded ${
              data.sizing.pattern === 'DCA' ? 'bg-green-900/50 text-green-400' :
              data.sizing.pattern === 'Variable' ? 'bg-yellow-900/50 text-yellow-400' :
              'bg-red-900/50 text-red-400'
            }`}>
              {data.sizing.pattern}
            </span>
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={data.sizing.buy_sizes.map((size, i) => ({
                buy: i + 1,
                shares: size,
                pctOfTotal: (size / data.sizing.buy_sizes.reduce((a, b) => a + b, 0)) * 100,
              }))}
              margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="buy"
                stroke="#9CA3AF"
                fontSize={11}
                label={{ value: 'Buy Order #', position: 'bottom', fill: '#9CA3AF', fontSize: 10 }}
              />
              <YAxis stroke="#9CA3AF" fontSize={11} label={{ value: 'Shares', angle: -90, position: 'insideLeft', fill: '#9CA3AF', fontSize: 10 }} />
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p className="font-medium">Buy #{d.buy}</p>
                      <p className="text-cyan-400">{d.shares?.toFixed(0)} shares</p>
                      <p className="text-gray-400">{d.pctOfTotal?.toFixed(1)}% of total</p>
                    </div>
                  );
                }}
              />
              <Bar dataKey="shares" radius={[4, 4, 0, 0]}>
                {data.sizing.buy_sizes.map((size, index) => (
                  <Cell
                    key={index}
                    fill={size === Math.max(...data.sizing.buy_sizes) ? '#F59E0B' : '#6366F1'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Avg Size</p>
              <p className="text-lg font-bold text-white">{data.sizing.avg_size.toFixed(0)}</p>
              <p className="text-xs text-gray-500">shares/buy</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">StdDev</p>
              <p className="text-lg font-bold text-white">{data.sizing.stddev.toFixed(0)}</p>
              <p className="text-xs text-gray-500">variation</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">CV (Coefficient)</p>
              <p className={`text-lg font-bold ${data.sizing.coefficient_variation < 0.3 ? 'text-green-400' : data.sizing.coefficient_variation < 0.7 ? 'text-yellow-400' : 'text-red-400'}`}>
                {data.sizing.coefficient_variation.toFixed(3)}
              </p>
              <p className="text-xs text-gray-500">&lt;0.3 = DCA</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Largest Buy</p>
              <p className="text-lg font-bold text-yellow-400">{data.sizing.largest_pct.toFixed(1)}%</p>
              <p className="text-xs text-gray-500">of total volume</p>
            </div>
          </div>
        </div>
      )}

      {/* Interpretation */}
      <div className="bg-gray-900/50 rounded-lg p-4 text-sm text-gray-300">
        <p className="font-medium text-gray-300 mb-2">How to Read This:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Hedge Ratio 100%</strong>: Perfectly balanced UP and DOWN positions</li>
          <li><strong>Combined Cost &lt; $1.00</strong>: Profit potential (arbitrage edge)</li>
          <li><strong>Entry Edge</strong>: How much better trades executed vs mid-market price</li>
          <li><strong>CV (Coefficient of Variation)</strong>: Low (&lt;0.3) = DCA, High (&gt;0.7) = Concentrated</li>
        </ul>
      </div>
    </div>
  );
}
