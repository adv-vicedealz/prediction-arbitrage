import { useState, useEffect } from 'react';
import {
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  ReferenceLine,
  LineChart,
  Bar,
} from 'recharts';
import type { MarketOverlayData } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

interface Props {
  marketSlug: string;
}

export function MarketOverlayChart({ marketSlug }: Props) {
  const [data, setData] = useState<MarketOverlayData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const res = await fetch(
          `${API_BASE}/api/deep-analysis/market/${encodeURIComponent(marketSlug)}/overlay`
        );
        const result = await res.json();
        setData(result);
      } catch (err) {
        console.error('Failed to fetch market overlay:', err);
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

  if (!data || !data.market) {
    return (
      <div className="text-center text-gray-400 py-12">
        No data available for this market.
      </div>
    );
  }

  // Combine prices and trades into unified timeline
  const startTime = data.market.start_time;
  const endTime = data.market.end_time;

  // Create price timeline with minute-based x-axis
  const priceData = data.prices.map((p) => ({
    ...p,
    minuteIntoMarket: (p.timestamp - startTime) / 60,
  }));

  // Add trades to timeline
  const tradeData = data.trades.map((t) => ({
    ...t,
    minuteIntoMarket: (t.timestamp - startTime) / 60,
    // For plotting on price axis
    plotPrice: t.outcome === 'Up' ? t.price : t.price,
  }));

  // Filter trades by type for different scatter series
  const buyUpTrades = tradeData.filter((t) => t.side === 'BUY' && t.outcome === 'Up');
  const buyDownTrades = tradeData.filter((t) => t.side === 'BUY' && t.outcome === 'Down');
  const sellUpTrades = tradeData.filter((t) => t.side === 'SELL' && t.outcome === 'Up');
  const sellDownTrades = tradeData.filter((t) => t.side === 'SELL' && t.outcome === 'Down');

  // Calculate trade stats
  const totalUpBuys = buyUpTrades.reduce((sum, t) => sum + t.shares, 0);
  const totalDownBuys = buyDownTrades.reduce((sum, t) => sum + t.shares, 0);
  const totalUpSells = sellUpTrades.reduce((sum, t) => sum + t.shares, 0);
  const totalDownSells = sellDownTrades.reduce((sum, t) => sum + t.shares, 0);

  return (
    <div className="space-y-4">
      {/* Market Info Header */}
      <div className="bg-gray-900 rounded-lg p-4">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-sm font-medium text-gray-300">
              {data.market.question || data.market.slug}
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Winner: <span className={data.market.winning_outcome?.toLowerCase() === 'up' ? 'text-green-400' : 'text-red-400'}>
                {data.market.winning_outcome || 'Unknown'}
              </span>
            </p>
          </div>
          <div className="text-right text-xs text-gray-400">
            <p>{data.prices.length} price snapshots</p>
            <p>{data.trades.length} trades</p>
          </div>
        </div>
      </div>

      {/* Trade Summary */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-400">Buy UP</p>
          <p className="text-lg font-bold text-green-400">{totalUpBuys.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{buyUpTrades.length} trades</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-400">Buy DOWN</p>
          <p className="text-lg font-bold text-red-400">{totalDownBuys.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{buyDownTrades.length} trades</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-400">Sell UP</p>
          <p className="text-lg font-bold text-green-300">{totalUpSells.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{sellUpTrades.length} trades</p>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 text-center">
          <p className="text-xs text-gray-400">Sell DOWN</p>
          <p className="text-lg font-bold text-red-300">{totalDownSells.toFixed(0)}</p>
          <p className="text-xs text-gray-500">{sellDownTrades.length} trades</p>
        </div>
      </div>

      {/* UP Price Chart with Trades */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">UP Price Evolution + Trades</h3>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              type="number"
              dataKey="minuteIntoMarket"
              domain={[0, (endTime - startTime) / 60]}
              tickFormatter={(v) => `${Math.floor(v)}m`}
              stroke="#9CA3AF"
              fontSize={11}
              label={{ value: 'Minutes into Market', position: 'bottom', fill: '#9CA3AF', fontSize: 10 }}
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v) => v.toFixed(2)}
              stroke="#9CA3AF"
              fontSize={11}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload[0]) return null;
                const d = payload[0].payload;
                if (d.up_price !== undefined) {
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p>Time: {d.minuteIntoMarket?.toFixed(1)}m</p>
                      <p>UP Price: {d.up_price?.toFixed(4)}</p>
                      <p>Bid: {d.up_bid?.toFixed(4)} | Ask: {d.up_ask?.toFixed(4)}</p>
                    </div>
                  );
                }
                return (
                  <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                    <p>Time: {d.minuteIntoMarket?.toFixed(1)}m</p>
                    <p>{d.side} {d.outcome}</p>
                    <p>Price: {d.price?.toFixed(4)}</p>
                    <p>Shares: {d.shares?.toFixed(0)}</p>
                    <p>Role: {d.role}</p>
                  </div>
                );
              }}
            />
            {/* Price line */}
            <Line
              data={priceData}
              type="monotone"
              dataKey="up_price"
              stroke="#10B981"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
            {/* Buy UP trades */}
            <Scatter
              data={buyUpTrades}
              dataKey="price"
              fill="#22C55E"
              shape="circle"
            />
            {/* Sell UP trades */}
            <Scatter
              data={sellUpTrades}
              dataKey="price"
              fill="#86EFAC"
              shape="triangle"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* DOWN Price Chart with Trades */}
      <div className="bg-gray-900 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-4">DOWN Price Evolution + Trades</h3>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              type="number"
              dataKey="minuteIntoMarket"
              domain={[0, (endTime - startTime) / 60]}
              tickFormatter={(v) => `${Math.floor(v)}m`}
              stroke="#9CA3AF"
              fontSize={11}
              label={{ value: 'Minutes into Market', position: 'bottom', fill: '#9CA3AF', fontSize: 10 }}
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v) => v.toFixed(2)}
              stroke="#9CA3AF"
              fontSize={11}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload || !payload[0]) return null;
                const d = payload[0].payload;
                if (d.down_price !== undefined) {
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p>Time: {d.minuteIntoMarket?.toFixed(1)}m</p>
                      <p>DOWN Price: {d.down_price?.toFixed(4)}</p>
                      <p>Bid: {d.down_bid?.toFixed(4)} | Ask: {d.down_ask?.toFixed(4)}</p>
                    </div>
                  );
                }
                return (
                  <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                    <p>Time: {d.minuteIntoMarket?.toFixed(1)}m</p>
                    <p>{d.side} {d.outcome}</p>
                    <p>Price: {d.price?.toFixed(4)}</p>
                    <p>Shares: {d.shares?.toFixed(0)}</p>
                    <p>Role: {d.role}</p>
                  </div>
                );
              }}
            />
            {/* Price line */}
            <Line
              data={priceData}
              type="monotone"
              dataKey="down_price"
              stroke="#EF4444"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
            {/* Buy DOWN trades */}
            <Scatter
              data={buyDownTrades}
              dataKey="price"
              fill="#DC2626"
              shape="circle"
            />
            {/* Sell DOWN trades */}
            <Scatter
              data={sellDownTrades}
              dataKey="price"
              fill="#FCA5A5"
              shape="triangle"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex justify-center gap-6 text-xs text-gray-200">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-green-500"></span>
          Buy UP
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-red-600"></span>
          Buy DOWN
        </span>
        <span className="flex items-center gap-1">
          <span className="w-0 h-0 border-l-[6px] border-r-[6px] border-b-[10px] border-transparent border-b-green-300"></span>
          Sell UP
        </span>
        <span className="flex items-center gap-1">
          <span className="w-0 h-0 border-l-[6px] border-r-[6px] border-b-[10px] border-transparent border-b-red-300"></span>
          Sell DOWN
        </span>
      </div>

      {/* NEW: Spread Analysis */}
      {data.spread_analysis && data.spread_analysis.by_timestamp.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">
            Bid-Ask Spread Evolution
            <span className="ml-2 text-xs text-gray-400">
              Avg: {(data.spread_analysis.avg_spread * 100).toFixed(2)}¢ |
              Range: {(data.spread_analysis.min_spread * 100).toFixed(2)}¢ - {(data.spread_analysis.max_spread * 100).toFixed(2)}¢
            </span>
          </h3>
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Avg Spread</p>
              <p className="text-lg font-bold text-cyan-400">{(data.spread_analysis.avg_spread * 100).toFixed(2)}¢</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Min Spread</p>
              <p className="text-lg font-bold text-green-400">{(data.spread_analysis.min_spread * 100).toFixed(2)}¢</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Max Spread</p>
              <p className="text-lg font-bold text-red-400">{(data.spread_analysis.max_spread * 100).toFixed(2)}¢</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart
              data={data.spread_analysis.by_timestamp.map((p, i) => ({
                ...p,
                index: i,
                up_spread_cents: p.up_spread * 100,
                down_spread_cents: p.down_spread * 100,
              }))}
              margin={{ top: 10, right: 30, left: 0, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="index" stroke="#9CA3AF" fontSize={10} tickFormatter={(v) => `${Math.floor(v / 60)}m`} />
              <YAxis stroke="#9CA3AF" fontSize={10} tickFormatter={(v) => `${v.toFixed(1)}¢`} />
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p>UP Spread: {d.up_spread_cents?.toFixed(2)}¢</p>
                      <p>DOWN Spread: {d.down_spread_cents?.toFixed(2)}¢</p>
                    </div>
                  );
                }}
              />
              <Area type="monotone" dataKey="up_spread_cents" stroke="#10B981" fill="#10B981" fillOpacity={0.3} />
              <Area type="monotone" dataKey="down_spread_cents" stroke="#EF4444" fill="#EF4444" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
          <div className="flex justify-center gap-4 mt-2 text-xs text-gray-400">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500/50"></span> UP Spread</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500/50"></span> DOWN Spread</span>
          </div>
        </div>
      )}

      {/* NEW: Market Efficiency (UP + DOWN = 1.0) */}
      {data.efficiency && data.efficiency.by_timestamp.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-4">
            Market Efficiency (UP + DOWN = 1.0 is perfect)
            <span className={`ml-2 text-xs ${Math.abs(data.efficiency.avg_combined - 1.0) < 0.02 ? 'text-green-400' : 'text-yellow-400'}`}>
              Avg: {data.efficiency.avg_combined.toFixed(4)}
            </span>
          </h3>
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Avg Combined</p>
              <p className={`text-lg font-bold ${Math.abs(data.efficiency.avg_combined - 1.0) < 0.02 ? 'text-green-400' : 'text-yellow-400'}`}>
                {data.efficiency.avg_combined.toFixed(4)}
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Deviation from 1.0</p>
              <p className={`text-lg font-bold ${Math.abs(data.efficiency.avg_combined - 1.0) < 0.02 ? 'text-green-400' : 'text-yellow-400'}`}>
                {((data.efficiency.avg_combined - 1.0) * 100).toFixed(2)}%
              </p>
            </div>
            <div className="bg-gray-800 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-400">Arbitrage Window</p>
              <p className={`text-lg font-bold ${data.efficiency.arbitrage_seconds > 60 ? 'text-green-400' : 'text-gray-400'}`}>
                {data.efficiency.arbitrage_seconds}s
              </p>
              <p className="text-xs text-gray-500">when combined &lt; 0.98</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart
              data={data.efficiency.by_timestamp.map((p, i) => ({ ...p, index: i }))}
              margin={{ top: 10, right: 30, left: 0, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="index" stroke="#9CA3AF" fontSize={10} tickFormatter={(v) => `${Math.floor(v / 60)}m`} />
              <YAxis domain={[0.94, 1.06]} stroke="#9CA3AF" fontSize={10} tickFormatter={(v) => v.toFixed(2)} />
              <Tooltip
                content={({ payload }) => {
                  if (!payload || !payload[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                      <p>Combined: {d.combined?.toFixed(4)}</p>
                      <p className={d.combined < 1.0 ? 'text-green-400' : 'text-red-400'}>
                        {d.combined < 1.0 ? 'Potential profit!' : 'Overpaying'}
                      </p>
                    </div>
                  );
                }}
              />
              <ReferenceLine y={1.0} stroke="#6B7280" strokeDasharray="3 3" label={{ value: 'Perfect', fill: '#6B7280', fontSize: 9 }} />
              <ReferenceLine y={0.98} stroke="#10B981" strokeDasharray="3 3" label={{ value: 'Target', fill: '#10B981', fontSize: 9 }} />
              <Line type="monotone" dataKey="combined" stroke="#06B6D4" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* NEW: Volatility by Minute */}
        {data.volatility && data.volatility.by_minute.length > 0 && (
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">
              Price Volatility + Trade Density
              <span className="ml-2 text-xs text-gray-400">
                (r = {data.volatility.vol_trade_correlation.toFixed(3)})
              </span>
            </h3>
            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart
                data={data.volatility.by_minute}
                margin={{ top: 10, right: 30, left: 0, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="minute" stroke="#9CA3AF" fontSize={10} />
                <YAxis yAxisId="left" stroke="#9CA3AF" fontSize={10} tickFormatter={(v) => `${(v * 100).toFixed(1)}%`} />
                <YAxis yAxisId="right" orientation="right" stroke="#9CA3AF" fontSize={10} />
                <Tooltip
                  content={({ payload }) => {
                    if (!payload || !payload[0]) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="bg-gray-800 border border-gray-600 rounded p-2 text-xs">
                        <p>Minute {d.minute}</p>
                        <p>Volatility: {(d.volatility * 100).toFixed(2)}%</p>
                        <p>Trades: {d.trade_count}</p>
                      </div>
                    );
                  }}
                />
                <Bar yAxisId="right" dataKey="trade_count" fill="#6366F1" opacity={0.5} />
                <Line yAxisId="left" type="monotone" dataKey="volatility" stroke="#F59E0B" strokeWidth={2} dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
            <div className="text-xs text-gray-400 text-center mt-2">
              {data.volatility.vol_trade_correlation > 0.3
                ? 'Trades cluster during volatile periods (opportunistic)'
                : data.volatility.vol_trade_correlation < -0.3
                ? 'Trades avoid volatile periods (risk-averse)'
                : 'No strong relationship between volatility and trading'}
            </div>
          </div>
        )}

        {/* NEW: Trade Impact Analysis */}
        {data.trade_impact && (
          <div className="bg-gray-900 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-4">Trade Impact (price change after trade)</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-xs text-gray-400 mb-2">BUY Trades Impact</p>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-green-400">BUY UP</span>
                    <span className={`text-sm font-bold ${data.trade_impact.buy_up_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {data.trade_impact.buy_up_impact > 0 ? '+' : ''}{data.trade_impact.buy_up_impact.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-red-400">BUY DOWN</span>
                    <span className={`text-sm font-bold ${data.trade_impact.buy_down_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {data.trade_impact.buy_down_impact > 0 ? '+' : ''}{data.trade_impact.buy_down_impact.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-xs text-gray-400 mb-2">SELL Trades Impact</p>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-green-400">SELL UP</span>
                    <span className={`text-sm font-bold ${data.trade_impact.sell_up_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {data.trade_impact.sell_up_impact > 0 ? '+' : ''}{data.trade_impact.sell_up_impact.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-red-400">SELL DOWN</span>
                    <span className={`text-sm font-bold ${data.trade_impact.sell_down_impact > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {data.trade_impact.sell_down_impact > 0 ? '+' : ''}{data.trade_impact.sell_down_impact.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-3 text-xs text-gray-400 text-center">
              Shows average price change 30 seconds after each trade type
            </div>
          </div>
        )}
      </div>

      {/* Interpretation */}
      <div className="bg-gray-900/50 rounded-lg p-4 text-sm text-gray-300">
        <p className="font-medium text-gray-300 mb-2">What These Metrics Tell Us:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Spread</strong>: Tighter spreads = lower trading costs, better liquidity</li>
          <li><strong>Efficiency</strong>: Combined &lt; 1.0 means arbitrage profit possible</li>
          <li><strong>Volatility</strong>: High volatility periods offer more trading opportunities</li>
          <li><strong>Trade Impact</strong>: Positive = trades move price in profitable direction</li>
        </ul>
      </div>
    </div>
  );
}
