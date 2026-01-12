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
      <div className="flex justify-center gap-6 text-xs text-gray-400">
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
    </div>
  );
}
